# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Lint Coding Agent Environment.

This module creates an HTTP server that exposes the LintCodingAgentEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""

import sys
import os
import argparse
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# --- ELITE LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("ArchitectApp")

# --- ARCHITECT'S PATH INJECTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

for path in [project_root, current_dir]:
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
# 1. Create the environment logic app
base_app = create_app(
    LintCodingAgentEnvironment,
    LintCodingAgentAction,
    LintCodingAgentObservation,
)

# 2. Create the Main Wrapper App
app = FastAPI(title="AnonAjay Architect API")

# --- DEBUG MIDDLEWARE ---
# This will print every single request coming from Hugging Face to your logs
@app.middleware("http")
async def debug_logging(request: Request, call_next):
    logger.info(f"📡 Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"✅ Response Status: {response.status_code}")
    return response

# --- MOUNTING (The /v1 Fix) ---
# This ensures that /v1/reset and /v1/ws are explicitly mapped
app.mount("/v1", base_app)

# --- CORS SECURITY ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "online", "message": "Lead Architect Server is Active"}

def main():
    """
    Entry point for the OpenEnv Server.
    Standardized to port 7860 for Hugging Face deployment.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    
    logger.info(f"🚀 OpenEnv Sandbox Starting on {args.host}:{args.port}")
    logger.info(f"📍 Mount Point: /v1 mapped to OpenEnv Core")
    
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port, 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )

if __name__ == "__main__":
    main()