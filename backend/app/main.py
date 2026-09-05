from fastapi import FastAPI

app = FastAPI(title="Trident API")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
