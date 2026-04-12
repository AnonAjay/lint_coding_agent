# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Lint Coding Agent Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import LintCodingAgentAction, LintCodingAgentObservation


class LintCodingAgentEnv(
    EnvClient[LintCodingAgentAction, LintCodingAgentObservation, State]
):
    """
    Client for the Lint Coding Agent Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> with LintCodingAgentEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.echoed_message)
        ...
        ...     result = client.step(LintCodingAgentAction(message="Hello!"))
        ...     print(result.observation.echoed_message)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = LintCodingAgentEnv.from_docker_image("lint_coding_agent-env:latest")
        >>> try:
        ...     result = client.reset()
        ...     result = client.step(LintCodingAgentAction(message="Test"))
        ... finally:
        ...     client.close()
    """

"""Lint Coding Agent Environment Client Implementation."""

from typing import Dict, Any
from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import LintCodingAgentAction, LintCodingAgentObservation
except ImportError:
    from models import LintCodingAgentAction, LintCodingAgentObservation


class LintCodingAgentEnv(
    EnvClient[LintCodingAgentAction, LintCodingAgentObservation, State]
):
    """
    Lead Architect Client for the Lint Coding Agent Environment.
    
    Supports complex state transitions within the Virtual File System (VFS)
    and handles the specialized Pydantic models for code-based actions.
    """

    def _step_payload(self, action: LintCodingAgentAction) -> Dict[str, Any]:
        """
        Serializes the Action for the OpenEnv WebSocket/HTTP transport.
        
        Note: The 'explanation' field is vital here as the server uses it 
        to track recursive sub-agent spawning for taxation.
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
        
        # Mapping the raw JSON observation to our Pydantic Model
        observation = LintCodingAgentObservation(
            level=obs_data.get("level", 1),
            language=obs_data.get("language", "Python"),
            problem_statement=obs_data.get("problem_statement", ""),
            code_context=obs_data.get("code_context", "{}"),  # This is our VFS JSON string
            last_test_results=obs_data.get("last_test_results", ""),
            reward=obs_data.get("reward", 0.0),
            done=obs_data.get("done", False),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> State:
        """
        Maintains the session integrity for persistent agent tracking.
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )