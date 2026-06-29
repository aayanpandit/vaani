from fastapi import FastAPI

app = FastAPI(title="Vaani API", version="0.1.0")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Vaani",
        "version": "0.1.0",
    }