"""Document-agnostic block classification and section detection.

The detector deliberately knows nothing about document domains.  It consumes
ordered blocks and uses layout and text signals to reconstruct a hierarchy.
Docling is only one possible producer of those blocks.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from statistics import mean
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


class BlockType(str, Enum):
    heading = "heading"
    subheading = "subheading"
    paragraph = "paragraph"
    list_item = "list_item"
    table = "table"
    caption = "caption"
    header_footer = "header_footer"
    unknown = "unknown"


@dataclass(slots=True)
class Block:
    text: str
    order: int
    page: int | None = None
    page_end: int | None = None
    lines: list[str] = field(default_factory=list)
    element_type: str = "text"
    source_refs: list[str] = field(default_factory=list)
    indentation: float | None = None
    whitespace_before: float | None = None
    whitespace_after: float | None = None
    explicit_type: BlockType | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        raw_lines = [line.rstrip() for line in (self.lines or self.text.splitlines())]
        self.text = "\n".join(raw_lines).strip()
        self.lines = self.text.splitlines() or ([self.text] if self.text else [])


@dataclass(slots=True)
class ClassifiedBlock:
    block: Block
    type: BlockType
    level: int = 0
    confidence: float = 0.0
    signals: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentNode:
    type: BlockType | str
    text: str = ""
    level: int = 0
    confidence: float | None = None
    block: Block | None = None
    children: list["DocumentNode"] = field(default_factory=list)


@dataclass(slots=True)
class DocumentTree:
    root: DocumentNode


class BlockClassifier:
    """Score blocks using independent signals.

    New signals can be added to ``_heading_signals`` or ``_classify`` without
    changing tree construction.  Explicit source labels are treated as strong
    evidence, not as document-specific section names.
    """

    _list_re = re.compile(r"^\s*[-*+•]\s+")
    _numbered_re = re.compile(r"^\s*(?P<prefix>(?:\d+(?:\.\d+)*(?:[.)])?|[A-Za-z][.)]))\s+")
    _page_re = re.compile(r"^\s*(?:#{1,6}\s*)?page\s+\d+(?:\s+of\s+\d+)?\s*$", re.I)
    _pages_re = re.compile(r"^\s*pages?\s*:\s*\d+(?:\s*[-/]\s*\d+)?\s*$", re.I)
    _separator_re = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")

    def classify_many(self, blocks: Sequence[Block]) -> list[ClassifiedBlock]:
        result: list[ClassifiedBlock] = []
        for index, block in enumerate(blocks):
            previous = result[-1] if result else None
            following = blocks[index + 1] if index + 1 < len(blocks) else None
            result.append(self.classify(block, previous=previous, following=following))
        return result

    def classify(
        self,
        block: Block,
        *,
        previous: ClassifiedBlock | None = None,
        following: Block | None = None,
    ) -> ClassifiedBlock:
        if self._is_page_artifact(block.text):
            return ClassifiedBlock(block, BlockType.unknown, confidence=1.0, signals={"page_artifact": 1.0})

        explicit = block.explicit_type
        if explicit in {BlockType.table, BlockType.caption, BlockType.list_item}:
            return ClassifiedBlock(block, explicit, confidence=1.0, signals={"source_label": 1.0})
        if self._list_re.match(block.text) or self._looks_like_numbered_list(block, previous, following):
            return ClassifiedBlock(block, BlockType.list_item, confidence=0.98, signals={"bullet": 1.0})

        signals = self._heading_signals(block, previous=previous, following=following)
        score = sum(signals.values())
        confidence = max(0.0, min(1.0, 0.5 + score / 2.0))
        if explicit in {BlockType.heading, BlockType.subheading}:
            score += 1.5
            confidence = max(confidence, 0.95)
        if score >= 1.3:
            level = self._heading_level(block, signals)
            kind = BlockType.heading if level <= 1 else BlockType.subheading
            return ClassifiedBlock(block, kind, level=level, confidence=confidence, signals=signals)
        return ClassifiedBlock(block, BlockType.paragraph, confidence=max(0.5, 1.0 - confidence / 3), signals=signals)

    def _heading_signals(
        self,
        block: Block,
        *,
        previous: ClassifiedBlock | None,
        following: Block | None,
    ) -> dict[str, float]:
        text = block.text.strip()
        words = re.findall(r"\b\w+[\w'-]*\b", text)
        lines = [line.strip() for line in block.lines if line.strip()]
        avg_line_length = mean(len(line) for line in lines) if lines else 0
        title_ratio = self._title_case_ratio(words)
        upper_ratio = self._upper_ratio(words)
        signals: dict[str, float] = {}
        if 0 < len(words) <= 14:
            signals["short"] = 0.55
        if len(lines) <= 3 and avg_line_length <= 90:
            signals["compact"] = 0.35
        if title_ratio >= 0.65:
            signals["title_case"] = 0.35
        if upper_ratio >= 0.75 and len(words) <= 12:
            signals["uppercase"] = 0.45
        if self._numbered_re.match(text):
            signals["numbering"] = 0.55
        if not re.search(r"[.!?,;:]$", text):
            signals["no_terminal_punctuation"] = 0.3
        if block.whitespace_before is not None and block.whitespace_after is not None:
            if block.whitespace_before > 1 or block.whitespace_after > 1:
                signals["whitespace"] = 0.3
        if block.indentation is not None:
            if block.indentation <= 0:
                signals["aligned"] = 0.1
            else:
                signals["indented"] = -0.15
        if previous and previous.type in {BlockType.paragraph, BlockType.list_item}:
            signals["follows_content"] = 0.15
        if following and len(following.text.split()) > len(words) * 1.5:
            signals["precedes_longer_content"] = 0.2
        if len(words) > 24 or avg_line_length > 140:
            signals["too_long"] = -1.0
        if re.search(r"[.!?,;:]$", text) and len(words) > 6:
            signals["sentence_like"] = -0.65
        if self._list_re.match(text):
            signals["list_like"] = -1.5
        return signals

    def _heading_level(self, block: Block, signals: dict[str, float]) -> int:
        match = self._numbered_re.match(block.text)
        if match:
            prefix = match.group("prefix").rstrip(".)")
            return min(6, prefix.count(".") + 1)
        if block.explicit_type == BlockType.subheading:
            return 2
        return 1 if signals.get("uppercase", 0) or signals.get("numbering", 0) else 2

    def _looks_like_numbered_list(
        self,
        block: Block,
        previous: ClassifiedBlock | None,
        following: Block | None,
    ) -> bool:
        """Use neighboring marker runs to distinguish lists from numbered headings."""
        if not self._numbered_re.match(block.text):
            return False
        marker = self._numbered_re.match(block.text).group("prefix")
        neighbors = [previous.block.text] if previous is not None else []
        if following is not None:
            neighbors.append(following.text)
        return any(
            match and match.group("prefix") != marker
            for text in neighbors
            for match in [self._numbered_re.match(text)]
        )

    @staticmethod
    def _title_case_ratio(words: list[str]) -> float:
        meaningful = [word for word in words if any(char.isalpha() for char in word)]
        return sum(word[0].isupper() for word in meaningful) / len(meaningful) if meaningful else 0.0

    @staticmethod
    def _upper_ratio(words: list[str]) -> float:
        meaningful = [word for word in words if any(char.isalpha() for char in word)]
        return sum(word.isupper() for word in meaningful) / len(meaningful) if meaningful else 0.0

    def _is_page_artifact(self, text: str) -> bool:
        return bool(self._page_re.match(text) or self._pages_re.match(text) or self._separator_re.match(text))


class SectionDetector:
    """Build a hierarchy from an ordered stream of classified blocks."""

    def __init__(self, classifier: BlockClassifier | None = None) -> None:
        self.classifier = classifier or BlockClassifier()

    def detect(self, blocks: Iterable[Block], *, title: str = "Document") -> DocumentTree:
        classified = self.classifier.classify_many(list(blocks))
        root = DocumentNode(type="document", text=title)
        stack: list[DocumentNode] = [root]
        for item in classified:
            if item.type == BlockType.unknown:
                continue
            if item.type in {BlockType.heading, BlockType.subheading}:
                while len(stack) > 1 and stack[-1].level >= item.level:
                    stack.pop()
                node = DocumentNode(
                    type=item.type,
                    text=item.block.text,
                    level=item.level,
                    confidence=item.confidence,
                    block=item.block,
                )
                stack[-1].children.append(node)
                stack.append(node)
                continue
            stack[-1].children.append(
                DocumentNode(type=item.type, text=item.block.text, block=item.block, confidence=item.confidence)
            )
        return DocumentTree(root=root)


class DocumentStructureExtractor:
    """Adapt Docling output to the generic section detector."""

    def __init__(self, detector: SectionDetector | None = None) -> None:
        self.detector = detector or SectionDetector()

    def build_ast(self, doc: DoclingDocument, *, document_id: str, filename: str) -> AstNode:
        blocks = list(self._blocks_from_docling(doc))
        tree = self.detector.detect(blocks, title=filename)
        return self._tree_to_ast(tree.root, document_id=document_id, filename=filename)

    def build_ast_from_pages(self, pages: Iterable[tuple[int, str]], *, document_id: str, filename: str) -> AstNode:
        blocks: list[Block] = []
        order = 0
        for page, text in pages:
            lines = text.splitlines()
            paragraph_lines: list[str] = []
            for line in lines + [""]:
                candidate = line.strip()
                if not candidate:
                    if paragraph_lines:
                        blocks.append(Block(text="\n".join(paragraph_lines), order=order, page=page, page_end=page, element_type="PdfText"))
                        order += 1
                        paragraph_lines = []
                    continue
                candidate_block = Block(text=candidate, order=order, page=page, page_end=page, element_type="PdfText")
                candidate_classification = self.detector.classifier.classify(candidate_block)
                candidate_type = candidate_classification.type
                if candidate_type == BlockType.unknown and candidate_classification.signals.get("page_artifact"):
                    continue
                if candidate_type in {BlockType.heading, BlockType.subheading, BlockType.list_item}:
                    if paragraph_lines:
                        blocks.append(Block(text="\n".join(paragraph_lines), order=order, page=page, page_end=page, element_type="PdfText"))
                        order += 1
                        paragraph_lines = []
                    blocks.append(candidate_block)
                    order += 1
                else:
                    paragraph_lines.append(line)
        tree = self.detector.detect(blocks, title=filename)
        return self._tree_to_ast(tree.root, document_id=document_id, filename=filename)

    def _blocks_from_docling(self, doc: DoclingDocument) -> Iterable[Block]:
        for order, (item, _level) in enumerate(doc.iterate_items(
            with_groups=True,
            traverse_pictures=True,
            included_content_layers=set(ContentLayer),
        )):
            if not isinstance(item, (DocItem, PictureItem, TableItem, TextItem)):
                continue
            text = self._extract_text(doc, item).strip()
            if not text and not isinstance(item, PictureItem):
                continue
            pages = self._extract_pages(item)
            explicit = None
            if isinstance(item, TableItem):
                explicit = BlockType.table
            elif isinstance(item, (TitleItem, SectionHeaderItem)):
                explicit = BlockType.heading if isinstance(item, TitleItem) else BlockType.subheading
            elif getattr(item, "label", None) == DocItemLabel.LIST_ITEM:
                explicit = BlockType.list_item
            yield Block(
                text=text or "[Figure]",
                order=order,
                page=min(pages) if pages else None,
                page_end=max(pages) if pages else None,
                element_type=type(item).__name__,
                source_refs=self._extract_refs(item),
                explicit_type=explicit,
                metadata={"docling_label": str(getattr(item, "label", ""))},
            )

    def _tree_to_ast(self, node: DocumentNode, *, document_id: str, filename: str, path: list[str] | None = None) -> AstNode:
        path = path or []
        if node.type == "document":
            ast = AstNode(node_id=document_id, kind=NodeKind.document, element_type="document", title=filename, metadata={"filename": filename})
            child_path = path
        else:
            block = node.block
            heading_path = path + [node.text] if node.type in {BlockType.heading, BlockType.subheading} else path
            kind = self._node_kind(node.type)
            ast = AstNode(
                node_id=str(uuid4()), kind=kind, element_type=block.element_type if block else node.type.value,
                text=node.text, title=node.text if kind in {NodeKind.section, NodeKind.subsection} else None,
                page_start=block.page if block else None, page_end=block.page_end if block else None,
                pages=self._pages(block), heading_path=heading_path, order=block.order if block else 0,
                source_refs=block.source_refs if block else [], metadata={"confidence": node.confidence, **(block.metadata if block else {})},
            )
            child_path = heading_path
        for child in node.children:
            ast.children.append(self._tree_to_ast(child, document_id=document_id, filename=filename, path=child_path))
        if ast.kind in {NodeKind.section, NodeKind.subsection} and ast.children:
            descendant_pages = sorted({page for child in ast.children for page in child.pages})
            if descendant_pages:
                ast.pages = sorted(set(ast.pages).union(descendant_pages))
                ast.page_start = min(ast.pages)
                ast.page_end = max(ast.pages)
        return ast

    @staticmethod
    def _node_kind(block_type: BlockType | str) -> NodeKind:
        return {
            BlockType.heading: NodeKind.section,
            BlockType.subheading: NodeKind.subsection,
            BlockType.paragraph: NodeKind.paragraph,
            BlockType.list_item: NodeKind.list_item,
            BlockType.table: NodeKind.table,
            BlockType.caption: NodeKind.caption,
        }.get(block_type, NodeKind.unknown)

    @staticmethod
    def _pages(block: Block | None) -> list[int]:
        if not block or block.page is None:
            return []
        end = block.page_end or block.page
        return list(range(block.page, end + 1))

    @staticmethod
    def _extract_pages(item: object) -> list[int]:
        return sorted({prov.page_no for prov in (getattr(item, "prov", []) or []) if isinstance(getattr(prov, "page_no", None), int)})

    @staticmethod
    def _extract_refs(item: object) -> list[str]:
        ref = getattr(item, "self_ref", None)
        return [str(ref)] if ref else []

    @staticmethod
    def _extract_text(doc: DoclingDocument, item: object) -> str:
        if isinstance(item, TableItem):
            try:
                return item.export_to_dataframe(doc=doc).to_markdown(index=False)
            except Exception:
                return getattr(item, "text", "") or "[Table]"
        if isinstance(item, PictureItem):
            caption = getattr(item, "caption", None)
            return str(caption) if caption else getattr(item, "text", "") or "[Figure]"
        return getattr(item, "text", "") or ""
