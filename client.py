# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Lint Coding Agent Environment Client Implementation."""

import os
import sys
import logging
from typing import Dict, Any, Optional
from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArchitectBridge")

# --- ROBUST IMPORT LOGIC ---
try:
    from models import LintCodingAgentAction, LintCodingAgentObservation
except ImportError:
    try:
        from .models import LintCodingAgentAction, LintCodingAgentObservation
    except ImportError:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from models import LintCodingAgentAction, LintCodingAgentObservation

class LintCodingAgentEnv(EnvClient[LintCodingAgentAction, LintCodingAgentObservation, State]):
    """
    Client-side bridge for the Lint Coding Agent.
    Handles serialization and parsing with manual header injection to bypass HF 403s.
    """
    
    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None, **kwargs):
        """
        Custom initializer that manually handles headers to bypass 
        library-level 'unexpected keyword argument' errors.
        """
        # 1. Initialize parent without headers to satisfy strict SDK constructors
        super().__init__(base_url=base_url, **kwargs)
        
        # 2. Manual Injection: Bypass the constructor limitation
        # Most EnvClient versions use an internal session. We force the headers there.
        if headers:
            logger.info(f"🛡️ Injecting {len(headers)} security headers into transport session...")
            # Target the standard openenv transport attributes
            self.headers = headers 
            
            # Deep injection for httpx/websocket backends if they exist
            if hasattr(self, '_client') and hasattr(self._client, 'headers'):
                self._client.headers.update(headers)
        
        logger.info(f"🔗 Architect Bridge Active | Target: {base_url}")

    def _step_payload(self, action: LintCodingAgentAction) -> Dict[str, Any]:
        """Serializes the Pydantic action into a dictionary for transport."""
        logger.info(f"📤 Preparing Payload | Action: {action.explanation[:30]}...")
        return {
            "code_solution": action.code_solution, 
            "explanation": action.explanation
        }

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[LintCodingAgentObservation]:
        """Parses the raw JSON response from the server into Pydantic models."""
        logger.info(f"📥 Received Response | Keys: {list(payload.keys())}")
        
        obs_data = payload.get("observation", {})
        
        # Defensive mapping to the Observation Model
        observation = LintCodingAgentObservation(
            level=obs_data.get("level", 1),
            language=obs_data.get("language", "Python"),
            problem_statement=obs_data.get("problem_statement", ""),
            code_context=obs_data.get("code_context", "{}"),
            last_test_results=obs_data.get("last_test_results", ""),
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
            metadata=obs_data.get("metadata", {}),
        )
        
        return StepResult(
            observation=observation, 
            reward=payload.get("reward", 0.0), 
            done=payload.get("done", False)
        )

    def _parse_state(self, payload: Dict[str, Any]) -> State:
        """Extracts the session state to maintain continuity across 15 levels."""
        eid = payload.get("episode_id") or payload.get("session_id")
        logger.info(f"🔗 Session Linked | ID: {eid}")
        return State(
            episode_id=eid, 
            step_count=payload.get("step_count", 0)
        )