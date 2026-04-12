# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Lint Coding Agent Environment Client Implementation."""

import os
import sys
from typing import Dict, Any, Optional

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

# --- ROBUST IMPORT LOGIC ---
try:
    from models import LintCodingAgentAction, LintCodingAgentObservation
except ImportError:
    try:
        from .models import LintCodingAgentAction, LintCodingAgentObservation
    except ImportError:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models import LintCodingAgentAction, LintCodingAgentObservation

class LintCodingAgentEnv(
    EnvClient[LintCodingAgentAction, LintCodingAgentObservation, State]
):
    """
    Lead Architect Client for the Lint Coding Agent Environment.
    
    Optimized for Hugging Face Spaces with custom header support to bypass
    CSRF/Origin 403 Forbidden rejections.
    """

    def __init__(
        self, 
        base_url: str, 
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """
        Initialize the client with optional headers for Hugging Face authentication.
        """
        # We pass headers to the parent EnvClient which uses them for HTTP/WS sessions
        super().__init__(base_url=base_url, headers=headers, **kwargs)

    def _step_payload(self, action: LintCodingAgentAction) -> Dict[str, Any]:
        """
        Serializes the Action for the OpenEnv transport layer.
        """
        return {
            "code_solution": action.code_solution,
            "explanation": action.explanation,
        }

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[LintCodingAgentObservation]:
        """
        Parses the multi-file VFS search space and mapping it to our Pydantic Model.
        """
        # The payload usually nests the observation
        obs_data = payload.get("observation", {})
        
        observation = LintCodingAgentObservation(
            level=obs_data.get("level", 1),
            language=obs_data.get("language", "Python"),
            problem_statement=obs_data.get("problem_statement", "Running..."),
            code_context=obs_data.get("code_context", "{}"),
            last_test_results=obs_data.get("last_test_results", ""),
            reward=payload.get("reward", 0.0), 
            done=payload.get("done", False),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> State:
        """
        Maintains session integrity across the 15-level sprint.
        """
        return State(
            episode_id=payload.get("episode_id") or payload.get("session_id"),
            step_count=payload.get("step_count", 0),
        )