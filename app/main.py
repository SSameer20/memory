from fastapi import FastAPI
from app.api.router import api_router


app = FastAPI(
    title="Memory",
    version="1.0.0"
)


app.include_router(api_router)

@app.get("/")
async def home():
    return {
        "message": "App is running 🚀"
    }


@app.get("/health")
async def Health():
    return {
        "message": "Health Check"
    }

