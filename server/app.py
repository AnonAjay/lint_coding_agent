# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import sys
import os
import argparse
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# --- ELITE LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("ArchitectApp")

# --- ARCHITECT'S PATH INJECTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

# Injecting all possible roots for the module loader
for path in [project_root, current_dir, os.getcwd()]:
    if path not in sys.path:
        sys.path.insert(0, path)

# --- OPENENV CORE IMPORTS ---
try:
    from openenv.core.server import create_app
except ImportError:
    from openenv.core.env_server.http_server import create_app

# --- DOMAIN SPECIFIC IMPORTS ---
from models import LintCodingAgentAction, LintCodingAgentObservation
from server.lint_coding_agent_environment import LintCodingAgentEnvironment

# --- APP FACTORY ---
# 1. Create the internal engine
base_app = create_app(
    LintCodingAgentEnvironment,
    LintCodingAgentAction,
    LintCodingAgentObservation,
)

# 2. Main Wrapper - Crucial config for Hugging Face UI restoration
app = FastAPI(
    title="AnonAjay Architect API",
    description="Meta x HF Hackathon: Multi-Lang Lint Coding Agent",
    version="1.0.0",
    redirect_slashes=False, # KILLER FIX: Prevents 307 loops that hide the UI
    docs_url="/docs",       # Direct UI access
    openapi_url="/openapi.json"
)

# --- DEBUG TELEMETRY ---
@app.middleware("http")
async def debug_logging(request: Request, call_next):
    logger.info(f"📡 Incoming: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"✅ Outcome: {response.status_code}")
    return response

# --- MOUNTING STRATEGY ---
@app.get("/v1")
async def v1_root():
    """Explicitly defined to prevent 404s on the mount root."""
    return {"message": "OpenEnv API v1 is active", "ui": "/v1/docs"}

# Mount the OpenEnv core
app.mount("/v1", base_app)

# --- CORS & INFRASTRUCTURE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "online", "engine": "LintCodingAgent", "port": 7860}

@app.get("/")
def home():
    """Automatically redirect root visitors to the documentation."""
    return RedirectResponse(url="/v1/docs")

def main():
    """Hugging Face Entry Point."""
    # Standard HF Spaces use port 7860
    port = int(os.environ.get("PORT", 7860))
    
    logger.info(f"🚀 Lead Architect Server spinning up on port {port}")
    logger.info(f"📍 Docs available at: https://anonajay-lint-coding-agent.hf.space/v1/docs")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )

if __name__ == "__main__":
    main()