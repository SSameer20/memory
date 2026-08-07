from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services import documentService

router = APIRouter(
    prefix="/document",
    tags=["Document"],
)


# Upload a document
@router.post("/")
async def Upload_Documents(file: UploadFile = File(...)):
    try:
        saved_file = await documentService.save(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": "upload complete",
        "file": saved_file,
        "markdown_preview": saved_file["markdown_preview"],
    }

# Get Document
@router.get("/{doc_id}")
async def Get_Documents():
    return {"message" : "docuemnt retrieved"}
