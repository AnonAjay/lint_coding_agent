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

# --- PATH INJECTION BLOCK ---
# Get the absolute path of the directory containing this file (server/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory
project_root = os.path.dirname(current_dir)

# Add both to sys.path to cover all import styles
if current_dir not in sys.path:
    sys.path.append(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
# ----------------------------

try:
    from openenv.core.env_server.http_server import create_app
except ImportError:
    raise ImportError("openenv-core is not installed. Run 'uv sync'.")

# Try imports with absolute certainty
try:
    # If models.py is in the root
    from models import LintCodingAgentAction, LintCodingAgentObservation
    # If environment is in the same folder as app.py
    from lint_coding_agent_environment import LintCodingAgentEnvironment
except ImportError:
    try:
        # Fallback for structured package
        from lint_coding_agent.models import LintCodingAgentAction, LintCodingAgentObservation
        from lint_coding_agent.server.lint_coding_agent_environment import LintCodingAgentEnvironment
    except ImportError as e:
        print(f"CRITICAL IMPORT ERROR: {e}")
        print(f"Python Path: {sys.path}")
        raise

# Create the app
app = create_app(
    LintCodingAgentEnvironment,
    LintCodingAgentAction,
    LintCodingAgentObservation,
    env_name="lint_coding_agent",
    max_concurrent_envs=1,
)

def main():
    """Standardized entry point for OpenEnv validation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    
    print(f"Starting server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()