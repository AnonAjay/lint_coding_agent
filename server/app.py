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

# --- ROBUST PATH INJECTION ---
# This ensures that whether the server is run from the root or the /server folder,
# it can always find models.py and the environment class.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

for path in [current_dir, project_root]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Debug: Print path in logs so we can see what the container sees
print(f"DEBUG: Python Path is {sys.path}")

try:
    # Use the specific OpenEnv factory method
    from openenv.core.server import create_app
except ImportError:
    # Fallback for different library versions
    try:
        from openenv.core.env_server.http_server import create_app
    except ImportError:
        print("CRITICAL: 'openenv' library not found in environment.")
        raise

# Absolute Import Attempts
try:
    from models import LintCodingAgentAction, LintCodingAgentObservation
    from server.lint_coding_agent_environment import LintCodingAgentEnvironment
except ImportError as e:
    print(f"IMPORT WARNING: Standard imports failed, trying relative... Error: {e}")
    try:
        from .lint_coding_agent_environment import LintCodingAgentEnvironment
        # If models is in root and we are in server/, we need '..'
        sys.path.append(project_root)
        from models import LintCodingAgentAction, LintCodingAgentObservation
    except ImportError as final_e:
        print(f"CRITICAL: All import attempts failed. {final_e}")
        raise

# --- APP INITIALIZATION ---
# env_name must match the name in your openenv.yaml
app = create_app(
    LintCodingAgentEnvironment,
    LintCodingAgentAction,
    LintCodingAgentObservation,
)

def main():
    """Entry point for local testing and Docker execution."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    
    print(f"Starting OpenEnv Server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()