from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class DocumentService:
    def __init__(self) -> None:
        self.storage_dir = Path(__file__).resolve().parents[1] / "storage"

    async def save(self, file: UploadFile) -> dict:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        original_name = Path(file.filename or "upload").name
        stored_name = f"{uuid4().hex}_{original_name}"
        destination = self.storage_dir / stored_name

        contents = await file.read()
        destination.write_bytes(contents)

        return {
            "filename": original_name,
            "stored_filename": stored_name,
            "path": str(destination),
            "content_type": file.content_type,
            "size": len(contents),
        }


document = DocumentService()
