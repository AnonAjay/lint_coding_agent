# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.

import sys
import os
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- ELITE LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("ArchitectApp")

# --- ARCHITECT'S PATH INJECTION ---
# Absolute priority: Ensure the server finds your logic and models
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "server"))

# --- OPENENV CORE IMPORTS ---
try:
    from openenv.core.env_server.http_server import create_app
except ImportError:
    # Fallback for different library versions
    from openenv.core.server import create_app

# --- DOMAIN SPECIFIC IMPORTS ---
from models import LintCodingAgentAction, LintCodingAgentObservation
from server.lint_coding_agent_environment import LintCodingAgentEnvironment

# --- THE FLATTENED APP ---
# We build the app directly to avoid '307 Temporary Redirect' and '503' Proxy blocks
app = create_app(
    LintCodingAgentEnvironment,
    LintCodingAgentAction,
    LintCodingAgentObservation,
)

# Explicitly override metadata for the auto-generated UI
app.title = "AnonAjay Architect API"
app.description = "Meta Hackathon: Flattened High-Performance Build"

# --- CORS SECURITY ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """Simple health probe to keep the Space alive."""
    return {"status": "online", "engine": "ready"}

# Note: The OpenEnv 'create_app' automatically handles /reset, /step, and /ws at the root.

def main():
    """Hugging Face Deployment Entry Point."""
    port = int(os.environ.get("PORT", 7860))
    
    logger.info(f"🚀 Launching FLATTENED Architect Engine on Port {port}")
    logger.info(f"📍 Swagger UI: https://anonajay-lint-coding-agent.hf.space/docs")
    
    # We remove ws_ping_interval to let the HF Proxy manage the keep-alive
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        proxy_headers=True, 
        forwarded_allow_ips="*",
        timeout_keep_alive=60
    )

if __name__ == "__main__":
    main()