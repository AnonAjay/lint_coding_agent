# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Lint Coding Agent Environment Client Implementation."""

import os
import sys
from typing import Dict, Any

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

# 🚀 CRITICAL FIX: Robust Absolute/Relative Import logic
# This ensures that whether running via 'uv run' or as a module, it finds the models.
try:
    from models import LintCodingAgentAction, LintCodingAgentObservation
except ImportError:
    try:
        from .models import LintCodingAgentAction, LintCodingAgentObservation
    except ImportError:
        # Final fallback for unusual container environments
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models import LintCodingAgentAction, LintCodingAgentObservation


class LintCodingAgentEnv(
    EnvClient[LintCodingAgentAction, LintCodingAgentObservation, State]
):
    """
    Lead Architect Client for the Lint Coding Agent Environment.
    
    Maintains the persistent WebSocket/HTTP handshake with the Hugging Face Space.
    Handles the 15-level VFS state transitions and serializes specialized 
    Pydantic models for code-based architectural fixes.
    """

    def _step_payload(self, action: LintCodingAgentAction) -> Dict[str, Any]:
        """
        Serializes the Action for the OpenEnv transport layer.
        
        The 'explanation' field is utilized by the server to monitor 
        agency taxation and sub-agent spawning logic.
        """
        return {
            "code_solution": action.code_solution,
            "explanation": action.explanation,
        }

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[LintCodingAgentObservation]:
        """
        Parses the multi-file VFS search space and detailed feedback 
        received from the environment server.
        """
        obs_data = payload.get("observation", {})
        
        # 🛡️ Defensive Mapping: Ensure no field is None to prevent Pydantic crashes
        observation = LintCodingAgentObservation(
            level=obs_data.get("level", 1),
            language=obs_data.get("language", "Python"),
            problem_statement=obs_data.get("problem_statement", "Task initiated."),
            code_context=obs_data.get("code_context", "{}"),  # VFS JSON string
            last_test_results=obs_data.get("last_test_results", ""),
            reward=payload.get("reward", 0.0), # SDK priority on top-level payload
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
        Maintains session integrity for persistent agent tracking across 15 levels.
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )