from fastapi import FastAPI

app = FastAPI(
    title="Memory",
    version="1.0.0"
)



@app.get("/")
async def home():
    return {
        "message": "FastAPI is running 🚀"
    }

