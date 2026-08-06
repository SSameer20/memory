from fastapi import FastAPI

app = FastAPI(
    title="My First FastAPI",
    version="1.0.0"
)



@app.get("/")
async def home():
    return {
        "message": "FastAPI is running 🚀"
    }

