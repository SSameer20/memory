from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from .models import AstNode, Chunk, ChunkMeta, NodeKind


@dataclass
class ChunkingConfig:
    max_tokens: int = 800
    merge_sibling_paragraphs: bool = True


class StructuralChunker:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self.config = config or ChunkingConfig()

    def chunk(self, root: AstNode, *, doc_id: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        order = 0
        for child in root.children:
            order = self._chunk_node(
                node=child,
                doc_id=doc_id,
                parent_chunk_id=None,
                chunks=chunks,
                order=order,
                inherited_heading_path=[],
            )
        self._link_children(chunks)
        return chunks

    def _chunk_node(
        self,
        *,
        node: AstNode,
        doc_id: str,
        parent_chunk_id: str | None,
        chunks: list[Chunk],
        order: int,
        inherited_heading_path: list[str],
    ) -> int:
        current_heading_path = node.heading_path or inherited_heading_path

        if node.kind not in {NodeKind.document, NodeKind.section, NodeKind.subsection} and not node.children:
            chunks.append(
                self._make_atomic_chunk(
                    doc_id=doc_id,
                    node=node,
                    parent_chunk_id=parent_chunk_id,
                    chunk_order=order,
                    heading_path=current_heading_path,
                )
            )
            return order + 1

        if node.kind in {NodeKind.section, NodeKind.subsection}:
            section_chunk = self._make_chunk(
                doc_id=doc_id,
                node=node,
                text=self._heading_text(node),
                parent_chunk_id=parent_chunk_id,
                chunk_type="section",
                chunk_order=order,
                heading_path=current_heading_path,
                element_types=[node.element_type],
                source_node_ids=[node.node_id],
            )
            chunks.append(section_chunk)
            order += 1
            parent_chunk_id = section_chunk.meta.chunk_id

        buffer: list[AstNode] = []
        for child in node.children:
            if child.kind in {NodeKind.section, NodeKind.subsection}:
                if buffer:
                    chunks.append(
                        self._flush_buffer(
                            doc_id=doc_id,
                            parent_chunk_id=parent_chunk_id,
                            buffer=buffer,
                            chunk_order=order,
                            heading_path=current_heading_path,
                        )
                    )
                    order += 1
                    buffer = []
                order = self._chunk_node(
                    node=child,
                    doc_id=doc_id,
                    parent_chunk_id=parent_chunk_id,
                    chunks=chunks,
                    order=order,
                    inherited_heading_path=current_heading_path,
                )
                continue

            if self._is_atomic_node(child):
                if buffer:
                    chunks.append(
                        self._flush_buffer(
                            doc_id=doc_id,
                            parent_chunk_id=parent_chunk_id,
                            buffer=buffer,
                            chunk_order=order,
                            heading_path=current_heading_path,
                        )
                    )
                    order += 1
                    buffer = []

                chunks.append(
                    self._make_atomic_chunk(
                        doc_id=doc_id,
                        node=child,
                        parent_chunk_id=parent_chunk_id,
                        chunk_order=order,
                        heading_path=current_heading_path,
                    )
                )
                order += 1
            else:
                buffer.append(child)
                if self._buffer_tokens(buffer) >= self.config.max_tokens:
                    chunks.append(
                        self._flush_buffer(
                            doc_id=doc_id,
                            parent_chunk_id=parent_chunk_id,
                            buffer=buffer,
                            chunk_order=order,
                            heading_path=current_heading_path,
                        )
                    )
                    order += 1
                    buffer = []

        if buffer:
            chunks.append(
                self._flush_buffer(
                    doc_id=doc_id,
                    parent_chunk_id=parent_chunk_id,
                    buffer=buffer,
                    chunk_order=order,
                    heading_path=current_heading_path,
                )
            )
            order += 1

        return order

    def _is_atomic_node(self, node: AstNode) -> bool:
        return node.kind in {
            NodeKind.table,
            NodeKind.figure,
            NodeKind.code,
        }

    def _heading_text(self, node: AstNode) -> str:
        if node.heading_path:
            return "\n".join(f"{'#' * min(i + 1, 6)} {heading}" for i, heading in enumerate(node.heading_path))
        return node.text

    def _serialize_node(self, node: AstNode) -> str:
        if node.kind == NodeKind.list_item:
            return f"- {node.text.strip()}"
        if node.kind in {NodeKind.table, NodeKind.figure, NodeKind.code}:
            return node.text.strip()
        return node.text.strip()

    def _buffer_tokens(self, buffer: list[AstNode]) -> int:
        return sum(self._approx_tokens(self._serialize_node(node)) for node in buffer)

    def _approx_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def _make_chunk(
        self,
        *,
        doc_id: str,
        node: AstNode,
        text: str,
        parent_chunk_id: str | None,
        chunk_type: str,
        chunk_order: int,
        heading_path: list[str],
        element_types: list[str],
        source_node_ids: list[str],
    ) -> Chunk:
        pages = node.pages.copy()
        meta = ChunkMeta(
            chunk_id=str(uuid4()),
            doc_id=doc_id,
            parent_chunk_id=parent_chunk_id,
            chunk_order=chunk_order,
            section=heading_path[0] if heading_path else None,
            subsection=heading_path[1] if len(heading_path) > 1 else None,
            heading_path=heading_path.copy(),
            page_numbers=pages,
            page_start=min(pages) if pages else None,
            page_end=max(pages) if pages else None,
            element_types=element_types,
            source_node_ids=source_node_ids,
            token_count=self._approx_tokens(text),
            char_count=len(text),
            chunk_type=chunk_type,
        )
        return Chunk(text=text, meta=meta)

    def _flush_buffer(
        self,
        *,
        doc_id: str,
        parent_chunk_id: str | None,
        buffer: list[AstNode],
        chunk_order: int,
        heading_path: list[str],
    ) -> Chunk:
        text = "\n\n".join(self._serialize_node(node) for node in buffer if self._serialize_node(node))
        pages = sorted({page for node in buffer for page in node.pages})
        fake_node = AstNode(
            node_id=str(uuid4()),
            kind=NodeKind.paragraph,
            element_type="buffer",
            pages=pages,
        )
        return self._make_chunk(
            doc_id=doc_id,
            node=fake_node,
            text=text,
            parent_chunk_id=parent_chunk_id,
            chunk_type="content",
            chunk_order=chunk_order,
            heading_path=heading_path,
            element_types=[node.element_type for node in buffer],
            source_node_ids=[node.node_id for node in buffer],
        )

    def _make_atomic_chunk(
        self,
        *,
        doc_id: str,
        node: AstNode,
        parent_chunk_id: str | None,
        chunk_order: int,
        heading_path: list[str],
    ) -> Chunk:
        text = self._serialize_node(node)
        return self._make_chunk(
            doc_id=doc_id,
            node=node,
            text=text,
            parent_chunk_id=parent_chunk_id,
            chunk_type=node.kind.value,
            chunk_order=chunk_order,
            heading_path=heading_path,
            element_types=[node.element_type],
            source_node_ids=[node.node_id],
        )

    def _link_children(self, chunks: list[Chunk]) -> None:
        by_parent: dict[str, list[str]] = {}
        for chunk in chunks:
            if chunk.meta.parent_chunk_id:
                by_parent.setdefault(chunk.meta.parent_chunk_id, []).append(chunk.meta.chunk_id)

        for chunk in chunks:
            chunk.meta.child_chunk_ids = by_parent.get(chunk.meta.chunk_id, [])
