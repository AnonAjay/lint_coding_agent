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
from fastapi.middleware.cors import CORSMiddleware

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
app = create_app(
    LintCodingAgentEnvironment,
    LintCodingAgentAction,
    LintCodingAgentObservation,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits your local machine to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def main():
    """
    Entry point for the OpenEnv Server.
    Standardized to port 7860 for Hugging Face deployment.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    
    print(f"🚀 OpenEnv Sandbox Starting on {args.host}:{args.port}")
    print(f"📍 Security: CORS Middleware Active (Allow All)")
    
    # proxy_headers + forwarded_allow_ips are vital for HF's reverse proxy
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port, 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )

if __name__ == "__main__":
    main()