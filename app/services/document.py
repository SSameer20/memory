from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from .models import Chunk, ProcessedDocument
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

        markdown_preview = self._render_markdown_preview(processed.chunks)
        preview_path = pdf_path.with_suffix(".preview.md")
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

    def _render_markdown_preview(self, chunks: list[Chunk]) -> str:
        parts: list[str] = []
        for chunk in chunks:
            heading = " > ".join(chunk.meta.heading_path)
            page_label = ", ".join(map(str, chunk.meta.page_numbers))
            header = []
            if heading:
                header.append(f"### {heading}")
            if page_label:
                header.append(f"_Pages: {page_label}_")
            if header:
                parts.append("\n".join(header))
            if chunk.text.strip():
                parts.append(chunk.text.strip())
        return "\n\n---\n\n".join(parts).strip()


document = DocumentService()

