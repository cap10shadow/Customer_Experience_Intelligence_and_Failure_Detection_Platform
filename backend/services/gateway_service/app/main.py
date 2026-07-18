from fastapi import FastAPI

app = FastAPI(title="Gateway Service")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "gateway_service"}
