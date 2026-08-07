from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from .models import AstNode, Chunk, NodeKind, ProcessedDocument
from .pipeline import DocumentPipeline

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self) -> None:
        self.storage_dir = Path(__file__).resolve().parents[1] / "storage"
        self.pipeline = DocumentPipeline(self.storage_dir)

    async def save(self, file: UploadFile) -> dict:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        original_name = Path(file.filename or "upload").name
        if Path(original_name).suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")

        document_id = uuid4().hex
        stored_name = f"{document_id}_{original_name}"
        pdf_path = self.storage_dir / stored_name

        contents = await file.read()
        pdf_path.write_bytes(contents)

        processed: ProcessedDocument = await asyncio.to_thread(
            self.pipeline.process,
            pdf_path=pdf_path,
            filename=original_name,
            document_id=document_id,
        )
        docling_path, ast_path, chunks_path = self.pipeline.persist(processed)

        markdown_preview = self._render_structured_markdown(processed.ast)
        preview_path = pdf_path.with_suffix(".structured.md")
        preview_path.write_text(markdown_preview, encoding="utf-8")

        return {
            "document_id": document_id,
            "filename": original_name,
            "stored_filename": stored_name,
            "pdf_path": str(pdf_path),
            "docling_path": str(docling_path) if docling_path else None,
            "ast_path": str(ast_path),
            "chunks_path": str(chunks_path),
            "preview_path": str(preview_path),
            "source_mode": processed.source_mode,
            "section_count": processed.section_count,
            "chunk_count": processed.chunk_count,
            "summary": processed.summary,
            "chunks": [chunk.model_dump(mode="json") for chunk in processed.chunks],
            "markdown_preview": markdown_preview,
        }

    def _render_structured_markdown(self, ast: AstNode) -> str:
        parts: list[str] = []
        self._append_ast_markdown(ast, parts, level=0, path=[])
        return "\n\n".join(part for part in parts if part.strip()).strip()

    def _append_ast_markdown(
        self,
        node: AstNode,
        parts: list[str],
        *,
        level: int,
        path: list[str],
    ) -> None:
        current_path = path.copy()

        if node.kind == NodeKind.document:
            parts.append(f"# {node.title or 'Document'}")
            for child in node.children:
                self._append_ast_markdown(child, parts, level=1, path=current_path)
            return

        if node.kind in {NodeKind.section, NodeKind.subsection}:
            heading_level = min(len(node.heading_path) + 1, 6)
            heading_text = node.title or node.text or "Untitled"
            parts.append(f"{'#' * heading_level} {heading_text}")
            if node.page_start is not None and node.page_end is not None:
                if node.page_start == node.page_end:
                    parts.append(f"_Pages: {node.page_start}_")
                else:
                    parts.append(f"_Pages: {node.page_start}-{node.page_end}_")
            for child in node.children:
                self._append_ast_markdown(
                    child,
                    parts,
                    level=level + 1,
                    path=current_path + [heading_text],
                )
            return

        if node.kind == NodeKind.table:
            parts.append(self._render_block_header("Table", node))
            parts.append("```text")
            parts.append(node.text.strip() or "[empty table]")
            parts.append("```")
            return

        if node.kind == NodeKind.figure:
            parts.append(self._render_block_header("Figure", node))
            if node.text.strip():
                parts.append(node.text.strip())
            else:
                parts.append("[figure]")
            return

        if node.kind == NodeKind.code:
            parts.append(self._render_block_header("Code", node))
            parts.append("```")
            parts.append(node.text.strip())
            parts.append("```")
            return

        if node.kind == NodeKind.list_item:
            parts.append(f"- {node.text.strip()}")
            return

        if node.kind == NodeKind.paragraph:
            parts.append(node.text.strip())
            return

        if node.kind == NodeKind.page_break:
            parts.append("---")
            return

        if node.text.strip():
            parts.append(node.text.strip())
        for child in node.children:
            self._append_ast_markdown(child, parts, level=level + 1, path=current_path)

    def _render_block_header(self, label: str, node: AstNode) -> str:
        page_info = ""
        if node.page_start is not None and node.page_end is not None:
            if node.page_start == node.page_end:
                page_info = f" | Page {node.page_start}"
            else:
                page_info = f" | Pages {node.page_start}-{node.page_end}"
        heading_info = ""
        if node.heading_path:
            heading_info = f" | {' > '.join(node.heading_path)}"
        return f"> {label}{page_info}{heading_info}"


document = DocumentService()
