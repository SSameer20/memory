from fastapi import UploadFile


class ChunkService:

    async def pdf(self, file: UploadFile) -> list[Chunk]:
        # 1. Parse PDF
        # 2. Process each page
        # 3. Extract native text
        # 4. Extract meaningful images
        # 5. OCR only required images
        # 6. Merge page content
        # 7. Chunk
        pass

    def text(self, content: str) -> list[Chunk]:
        # Normal text chunking
        pass

    async def image(self, file: bytes) -> list[Chunk]:
        # OCR / vision processing
        pass
    """
    Service responsible for splitting different types of content
    into smaller chunks suitable for processing or embedding.
    """

    def pdf(self, file: UploadFile) -> List[str]:
        """
        Extract and chunk text from a PDF file.
        """
        pass

    def text(self, content: str) -> List[str]:
        """
        Chunk plain text content.
        """
        pass

    def image(self, image_path: str) -> List[str]:
        """
        Extract and chunk content from an image.
        """
        pass