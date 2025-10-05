from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
import logging

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
AUDIO_SERVICE_URL = os.getenv("AUDIO_SERVICE_URL", "http://audio-service:8003")
CONVERSATION_SERVICE_URL = os.getenv("CONVERSATION_SERVICE_URL", "http://conversation-service:8007")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Munshi UI Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

client = httpx.AsyncClient(timeout=90.0)  # Increased for generate-sentence endpoint which can take 40-60s
security = HTTPBearer(auto_error=False)

async def api_request(url, method="GET", **kwargs):
    """Helper function for API requests"""
    try:
        response = await client.request(method, url, **kwargs)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            detail = response.json().get("detail", f"{method} failed") if response.headers.get("content-type") == "application/json" else f"{method} failed"
            raise HTTPException(status_code=response.status_code, detail=detail)
    except httpx.RequestError as e:
        logger.error(f"Service error: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ui-service"}

@app.post("/api/auth/login")
async def login(credentials: dict):
    return await api_request(f"{AUTH_SERVICE_URL}/auth/login", "POST", json=credentials)

@app.post("/api/auth/register")
async def register(user_data: dict):
    return await api_request(f"{AUTH_SERVICE_URL}/auth/register", "POST", json=user_data)

@app.get("/api/auth/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="No token provided")
    return await api_request(
        f"{AUTH_SERVICE_URL}/auth/verify", 
        headers={"Authorization": f"Bearer {credentials.credentials}"}
    )

@app.post("/api/audio/process")
async def process_audio(file: UploadFile = File(...), credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await api_request(
        f"{AUDIO_SERVICE_URL}/audio/process",
        "POST",
        files={"file": (file.filename, file.file, file.content_type)},
        headers={"Authorization": f"Bearer {credentials.credentials}"}
    )

@app.post("/api/conversation/chat")
async def chat(data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    logger.info(f"Chat request: {data}")
    result = await api_request(
        f"{CONVERSATION_SERVICE_URL}/chat",
        "POST",
        json=data,
        headers={"Authorization": f"Bearer {credentials.credentials}"}
    )
    logger.info(f"Chat response: {result}")
    return result

@app.get("/api/conversation/user/{user_id}/generate-sentence")
async def generate_sentence(user_id: str, language: str, difficulty: str = "beginner", credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await api_request(
        f"{CONVERSATION_SERVICE_URL}/user/{user_id}/generate-sentence?language={language}&difficulty={difficulty}",
        "POST",
        headers={"Authorization": f"Bearer {credentials.credentials}"}
    )

@app.post("/api/conversation/evaluate-pronunciation")
async def evaluate_pronunciation(data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await api_request(
        f"{CONVERSATION_SERVICE_URL}/evaluate-pronunciation",
        "POST",
        json=data,
        headers={"Authorization": f"Bearer {credentials.credentials}"}
    )

# Serve React static files - mount assets directory
app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

@app.get("/{path:path}")
async def serve_react_app(path: str):
    """Serve React app for all routes"""
    # Don't handle API routes or assets (already mounted)
    if path.startswith("api") or path.startswith("assets"):
        return None

    # Check if it's a static file in dist
    if path:
        file_path = f"dist/{path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

    # Return index.html for all non-API routes (SPA routing)
    return FileResponse("dist/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )