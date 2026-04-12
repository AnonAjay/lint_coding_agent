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

# --- PATH INJECTION ---
# We force the project root into sys.path to ensure 'models' and 'server' 
# are resolvable regardless of how the container starts.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

for path in [project_root, current_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Debug: Verifying the manifest is reachable before the app boots
json_check = os.path.join(current_dir, "QUESTIONS.json")
print(f"[DEBUG] Manifest check: {json_check} exists: {os.path.exists(json_check)}")

# --- OPENENV CORE IMPORTS ---
try:
    from openenv.core.server import create_app
except ImportError:
    try:
        from openenv.core.env_server.http_server import create_app
    except ImportError:
        print("CRITICAL: 'openenv' library missing. Check requirements.txt.")
        raise

# --- DOMAIN SPECIFIC IMPORTS ---
try:
    # Importing from the root models.py and the logic-heavy environment
    from models import LintCodingAgentAction, LintCodingAgentObservation
    from server.lint_coding_agent_environment import LintCodingAgentEnvironment
except ImportError as e:
    print(f"[IMPORT WARNING] Standard path failed, trying relative fallback: {e}")
    try:
        from lint_coding_agent_environment import LintCodingAgentEnvironment
        from models import LintCodingAgentAction, LintCodingAgentObservation
    except ImportError as final_e:
        print(f"CRITICAL: Application structure invalid. {final_e}")
        raise

# --- APP FACTORY ---
# create_app wraps the Environment and Pydantic models into a FastAPI instance
app = create_app(
    LintCodingAgentEnvironment,
    LintCodingAgentAction,
    LintCodingAgentObservation,
)

def main():
    """
    Entry point for the OpenEnv Server.
    The proxy_headers and forwarded_allow_ips are MANDATORY for 
    Hugging Face Spaces to communicate with the Scaler Portal.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    
    print(f"🚀 OpenEnv Multi-Agent Sandbox Starting...")
    print(f"📍 Search Space: VFS Templates Enabled")
    print(f"📍 Network: {args.host}:{args.port}")
    
    # proxy_headers allows FastAPI to correctly identify the original 
    # request IP through the Hugging Face Load Balancer.
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port, 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )

if __name__ == "__main__":
    main()