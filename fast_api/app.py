import os
import sys
from pathlib import Path


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent


# Ensure AI-Backend and repository root are available
# for imports.
for path_entry in (
    str(BASE_DIR),
    str(REPO_DIR),
):
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)


# ============================================================
# PYTHONPATH FOR UVICORN RELOAD WORKERS
# ============================================================

existing_pythonpath = os.environ.get(
    "PYTHONPATH",
    ""
)

if str(BASE_DIR) not in existing_pythonpath:

    os.environ["PYTHONPATH"] = (
        f"{BASE_DIR}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(BASE_DIR)
    )


# ============================================================
# FASTAPI
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# ROUTES
# ============================================================

try:

    from fast_api.routes import (
        router,
        WindowsPathJsonRoute,
    )

except (
    ImportError,
    ModuleNotFoundError,
):

    from fast_api.routes import (
        router,
        WindowsPathJsonRoute,
    )


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(

    title=(
        "Sovereign Industrial "
        "AI Workbench API"
    ),

    description=(
        "On-premise confidential AI "
        "workbench using local "
        "open-weight models "
        "(SIH PS #117)"
    ),

    version="1.0.0",
)


# ============================================================
# WINDOWS PATH RESPONSE HANDLING
# ============================================================

app.router.route_class = (
    WindowsPathJsonRoute
)


# ============================================================
# CORS
# ============================================================

# ------------------------------------------------------------
# Development configuration
# ------------------------------------------------------------
#
# If your React/Streamlit frontend is running locally,
# these are typical origins.
#
# For production, replace this with the exact frontend
# origins used inside the organization.
# ------------------------------------------------------------

ALLOWED_ORIGINS = [

    "http://localhost:3000",

    "http://127.0.0.1:3000",

    "http://localhost:5173",

    "http://127.0.0.1:5173",

    "http://localhost:8501",

    "http://127.0.0.1:8501",
]


app.add_middleware(

    CORSMiddleware,

    allow_origins=ALLOWED_ORIGINS,

    allow_credentials=True,

    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],

    allow_headers=[
        "Content-Type",
        "Authorization",
    ],
)


# ============================================================
# REGISTER API ROUTES
# ============================================================

app.include_router(
    router
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get(
    "/health",
    tags=["System"]
)
def health_check():

    return {

        "status": "ok",

        "service": (
            "Sovereign Industrial "
            "AI Workbench"
        ),

        "mode": "on-premise",

    }


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get(
    "/",
    tags=["System"]
)
def root():

    return {

        "service": (
            "Sovereign Industrial "
            "AI Workbench API"
        ),

        "status": "running",

        "mode": "on-premise",

        "docs": "/docs",

    }


# ============================================================
# DEVELOPMENT SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "fast_api.app:app",

        host="127.0.0.1",

        port=8000,

        reload=True,

        app_dir=str(BASE_DIR),
    )