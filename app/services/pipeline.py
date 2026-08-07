from __future__ import annotations

import json
import logging
from pathlib import Path

import pypdfium2 as pdfium
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import DoclingDocument

from .chunking import ChunkingConfig, StructuralChunker
from .models import AstNode, Chunk, ProcessedDocument, NodeKind
from .structure import DocumentStructureExtractor

logger = logging.getLogger(__name__)


class DocumentPipeline:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.structure_extractor = DocumentStructureExtractor()
        self.chunker = StructuralChunker(ChunkingConfig(max_tokens=800))
        self._ocr_converter = self._build_ocr_converter()

    def _build_pdf_pipeline_options(self) -> PdfPipelineOptions:
        options = PdfPipelineOptions()
        options.do_ocr = True
        return options

    def _build_ocr_converter(self) -> DocumentConverter | None:
        try:
            import importlib.util

            if importlib.util.find_spec("onnxruntime") is None:
                return None
        except Exception:
            return None

        options = self._build_pdf_pipeline_options()
        options.ocr_options = RapidOcrOptions(lang=["en"], backend="onnxruntime")
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=options)
            }
        )

    def process(self, *, pdf_path: Path, filename: str, document_id: str) -> ProcessedDocument:
        docling_document, source_mode = self._convert_document(pdf_path)
        if docling_document is not None:
            ast = self.structure_extractor.build_ast(
                docling_document, document_id=document_id, filename=filename
            )
            docling_payload = docling_document.export_to_dict()
        else:
            ast = self._build_fallback_ast(
                pdf_path=pdf_path, document_id=document_id, filename=filename
            )
            docling_payload = None

        chunks = self.chunker.chunk(ast, doc_id=document_id)

        return ProcessedDocument(
            document_id=document_id,
            filename=filename,
            pdf_path=str(pdf_path),
            source_mode=source_mode,
            section_count=self._count_sections(ast),
            chunk_count=len(chunks),
            ast=ast,
            chunks=chunks,
            docling_document=docling_payload,
            summary=self._build_summary(ast, chunks),
        )

    def persist(self, processed: ProcessedDocument) -> tuple[Path | None, Path, Path]:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        docling_path: Path | None = None
        if processed.docling_document is not None:
            docling_path = self.storage_dir / f"{processed.document_id}.docling.json"
            docling_path.write_text(
                json.dumps(processed.docling_document, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        ast_path = self.storage_dir / f"{processed.document_id}.ast.json"
        ast_path.write_text(
            processed.ast.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

        chunks_path = self.storage_dir / f"{processed.document_id}.chunks.json"
        chunks_path.write_text(
            json.dumps([chunk.model_dump(mode="json") for chunk in processed.chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return docling_path, ast_path, chunks_path

    def _convert_document(self, pdf_path: Path) -> tuple[DoclingDocument | None, str]:
        if self._ocr_converter is not None:
            try:
                result = self._ocr_converter.convert(pdf_path)
                return result.document, "docling_ocr"
            except Exception as exc:
                logger.warning(
                    "Docling OCR conversion failed, using local PDF text fallback: %s",
                    exc,
                )
        return None, "pdfium_text"

    def _build_fallback_ast(self, *, pdf_path: Path, document_id: str, filename: str) -> AstNode:
        pages: list[tuple[int, str]] = []
        pdf = pdfium.PdfDocument(str(pdf_path))
        try:
            for index in range(len(pdf)):
                page = pdf[index]
                text = page.get_textpage().get_text_range()
                text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
                if not text:
                    continue
                pages.append((index + 1, text))
        finally:
            pdf.close()
        ast = self.structure_extractor.build_ast_from_pages(
            pages, document_id=document_id, filename=filename
        )
        ast.metadata["source"] = "pdfium_text"
        return ast

    def _count_sections(self, ast: AstNode) -> int:
        return sum(1 for node in self._walk(ast) if node.kind in {NodeKind.section, NodeKind.subsection})

    def _build_summary(self, ast: AstNode, chunks: list[Chunk]) -> dict:
        top_headings = [node.title for node in ast.children if node.kind in {NodeKind.section, NodeKind.subsection}]
        return {
            "top_headings": [heading for heading in top_headings if heading],
            "chunk_orders": [chunk.meta.chunk_order for chunk in chunks[:10]],
            "chunk_types": sorted({chunk.meta.chunk_type for chunk in chunks}),
        }

    def _walk(self, node: AstNode):
        yield node
        for child in node.children:
            yield from self._walk(child)
