from fastapi import FastAPI


app = FastAPI(
    title="Memory",
    version="1.0.0"
)


@app.get("/")
async def home():
    return {
        "message": "Memory is running 🚀"
    }


@app.get("/health")
async def Health():
    return {
        "message": "Health Check"
    }

