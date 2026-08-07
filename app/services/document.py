import logging
import importlib.util
import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
import pypdfium2 as pdfium

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self) -> None:
        self.storage_dir = Path(__file__).resolve().parents[1] / "storage"
        self._ocr_converter = self._build_ocr_converter()

    def _build_pdf_pipeline_options(self, *, do_ocr: bool) -> PdfPipelineOptions:
        options = PdfPipelineOptions()
        options.do_ocr = do_ocr
        return options

    def _build_ocr_converter(self) -> DocumentConverter | None:
        if importlib.util.find_spec("onnxruntime") is None:
            return None

        options = self._build_pdf_pipeline_options(do_ocr=True)
        options.ocr_options = RapidOcrOptions(lang=["en"], backend="onnxruntime")
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=options)
            }
        )

    def _extract_pdf_text_markdown(self, pdf_path: Path) -> str:
        document = pdfium.PdfDocument(str(pdf_path))
        try:
            pages: list[str] = []
            for index in range(len(document)):
                page = document[index]
                text = page.get_textpage().get_text_range()
                text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
                if text:
                    pages.append(f"## Page {index + 1}\n\n{text}")
            return "\n\n---\n\n".join(pages).strip()
        finally:
            document.close()

    def _convert_to_markdown(self, pdf_path: Path) -> tuple[str, str]:
        if self._ocr_converter is not None:
            try:
                result = self._ocr_converter.convert(pdf_path)
                markdown = result.document.export_to_markdown(traverse_pictures=True)
                return markdown, "ocr"
            except Exception as exc:
                logger.warning(
                    "OCR conversion failed, falling back to local PDF text extraction: %s",
                    exc,
                )

        return self._extract_pdf_text_markdown(pdf_path), "pdf_text"

    async def save(self, file: UploadFile) -> dict:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        original_name = Path(file.filename or "upload").name
        if Path(original_name).suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported for OCR conversion.")

        stored_name = f"{uuid4().hex}_{original_name}"
        destination = self.storage_dir / stored_name

        contents = await file.read()
        destination.write_bytes(contents)

        markdown, markdown_source = await asyncio.to_thread(
            self._convert_to_markdown, destination
        )
        markdown_path = destination.with_suffix(".md")
        markdown_path.write_text(markdown, encoding="utf-8")

        return {
            "filename": original_name,
            "stored_filename": stored_name,
            "path": str(destination),
            "markdown_path": str(markdown_path),
            "content_type": file.content_type,
            "size": len(contents),
            "markdown": markdown,
            "markdown_source": markdown_source,
            "ocr_enabled": self._ocr_converter is not None,
        }


document = DocumentService()
