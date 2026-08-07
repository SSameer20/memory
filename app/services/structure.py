from __future__ import annotations

from collections.abc import Iterable
from uuid import uuid4

from docling_core.types.doc import (
    ContentLayer,
    DocItem,
    DocItemLabel,
    PictureItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)
from docling_core.types.doc.document import DoclingDocument

from .models import AstNode, NodeKind


class DocumentStructureExtractor:
    def build_ast(self, doc: DoclingDocument, *, document_id: str, filename: str) -> AstNode:
        root = AstNode(
            node_id=document_id,
            kind=NodeKind.document,
            element_type="document",
            title=filename,
            metadata={"filename": filename},
        )

        heading_stack: list[AstNode] = [root]
        heading_path: list[str] = []
        order = 0

        for item, level in doc.iterate_items(
            with_groups=True,
            traverse_pictures=True,
            included_content_layers=set(ContentLayer),
        ):
            if not self._should_include(item):
                continue

            pages = self._extract_pages(item)
            page_start = min(pages) if pages else None
            page_end = max(pages) if pages else None
            node_kind = self._kind_for_item(item)
            item_text = self._extract_text(doc, item)
            refs = self._extract_refs(item)

            if isinstance(item, (TitleItem, SectionHeaderItem)):
                heading_text = item_text.strip()
                if not heading_text:
                    continue

                heading_path = heading_path[: max(level, 0)]
                heading_path.append(heading_text)

                while len(heading_stack) > level + 1:
                    heading_stack.pop()

                node = AstNode(
                    node_id=str(uuid4()),
                    kind=node_kind,
                    element_type=type(item).__name__,
                    text=heading_text,
                    title=heading_text,
                    page_start=page_start,
                    page_end=page_end,
                    pages=pages,
                    heading_path=heading_path.copy(),
                    order=order,
                    source_refs=refs,
                    metadata={"level": level},
                )
                order += 1
                heading_stack[-1].children.append(node)
                heading_stack.append(node)
                continue

            node = AstNode(
                node_id=str(uuid4()),
                kind=node_kind,
                element_type=type(item).__name__,
                text=item_text,
                page_start=page_start,
                page_end=page_end,
                pages=pages,
                heading_path=heading_path.copy(),
                order=order,
                source_refs=refs,
                metadata={"level": level},
            )
            order += 1
            heading_stack[-1].children.append(node)

        return root

    def _should_include(self, item: object) -> bool:
        return isinstance(item, (DocItem, PictureItem, TableItem, TextItem))

    def _kind_for_item(self, item: object) -> NodeKind:
        if isinstance(item, TitleItem):
            return NodeKind.section
        if isinstance(item, SectionHeaderItem):
            return NodeKind.subsection
        if isinstance(item, TableItem):
            return NodeKind.table
        if isinstance(item, PictureItem):
            return NodeKind.figure
        if hasattr(item, "label") and getattr(item, "label", None) in {
            DocItemLabel.CODE,
        }:
            return NodeKind.code
        if hasattr(item, "label") and getattr(item, "label", None) in {
            DocItemLabel.LIST_ITEM,
        }:
            return NodeKind.list_item
        return NodeKind.paragraph

    def _extract_pages(self, item: object) -> list[int]:
        pages: list[int] = []
        for prov in getattr(item, "prov", []) or []:
            page_no = getattr(prov, "page_no", None)
            if isinstance(page_no, int):
                pages.append(page_no)
        return sorted(set(pages))

    def _extract_refs(self, item: object) -> list[str]:
        refs: list[str] = []
        self_ref = getattr(item, "self_ref", None)
        if self_ref:
            refs.append(str(self_ref))
        return refs

    def _extract_text(self, doc: DoclingDocument, item: object) -> str:
        if isinstance(item, TableItem):
            try:
                return item.export_to_dataframe(doc=doc).to_markdown(index=False)
            except Exception:
                return getattr(item, "text", "") or ""
        if isinstance(item, PictureItem):
            caption = getattr(item, "caption", None)
            if caption:
                return str(caption)
            return getattr(item, "text", "") or "[Figure]"
        return getattr(item, "text", "") or ""

