from fastapi import APIRouter, UploadFile, File
from services.service import documentService

router = APIRouter(
    prefix="/document",
    tags=["Document"],
)


# Upload a document
@router.post("/")
async def Upload_Documents(file: UploadFile = File(...)):
    saved_file = await documentService.save(file)
    return {"message": "upload complete", "file": saved_file}

# Get Document
@router.get("/{doc_id}")
async def Get_Documents():
    return {"message" : "docuemnt retrieved"}
