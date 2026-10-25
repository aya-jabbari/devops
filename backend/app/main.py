from fastapi import FastAPI

app = FastAPI(title="SupportOps API")


@app.get("/health")
def health():
    return {"status": "ok"}