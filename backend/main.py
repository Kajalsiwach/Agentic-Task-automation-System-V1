import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add project root and backend dir to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.core.config import PROJECT_NAME, VERSION
from backend.app.database.session import engine, Base, init_db
from backend.app.api.endpoints import router as api_router

# Create database tables and apply backward-compatible migrations
init_db()

app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description="TaskForge: AI-Powered Natural-Language Task Automation System"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api")
# Also alias /tasks and /agent directly at root for direct standard route compatibility
app.include_router(api_router, prefix="")

# Mount frontend static directory if present
FRONTEND_DIR = PROJECT_ROOT / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
