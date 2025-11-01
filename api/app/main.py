from fastapi import FastAPI

app = FastAPI(title="AI Workflow API", version="0.1.0")


@app.get("/api/health")
def health():
    """Minimal liveness endpoint for UI and n8n checks."""
    return {"status": "ok"}
