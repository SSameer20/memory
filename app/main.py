from fastapi import FastAPI
from app.lib.config import config

app = FastAPI(
    title="Memory",
    version="1.0.0"
)


@app.get("/")
async def home():
    print(config.pinecone.api_key)
    print(config.pinecone.profile_index)

    return {
        "message": "Memory is running 🚀"
    }


@app.get("/health")
async def Health():
    return {
        "message": "Health Check"
    }

