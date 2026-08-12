from fastapi import UploadFile


class EmbedService:
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
       
    
        