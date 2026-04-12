# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Lint Coding Agent Environment.

The lint_coding_agent environment is a simple test environment that echoes back messages.
"""

from openenv.core.env_server.types import Action, Observation
from pydantic import Field
from typing import Dict, Any, Optional

class LintCodingAgentAction(Action):
    """
    Action schema for the Lead Architect.
    The agent provides the fix and an explanation that tracks orchestration intent.
    Optional fields prevent 422 Validation Errors during manual UI testing.
    """
    code_solution: Optional[str] = Field(
        default="", 
        description="The full code or specific fix for the repo"
    )
    explanation: Optional[str] = Field(
        default="Direct intervention", 
        description="Reasoning for the fix; used to track sub-agent spawning or taxation"
    )

class LintCodingAgentObservation(Observation):
    """
    Observation schema for the VFS Search Space.
    Provides the multi-file repository state and environment feedback.
    """
    level: int = Field(default=1, description="Current difficulty level (1-15)")
    language: str = Field(default="Python", description="Programming language context")
    problem_statement: str = Field(default="", description="The mission objective or bug description")
    code_context: str = Field(default="{}", description="JSON-stringified Virtual File System (VFS) map")
    last_test_results: Optional[str] = Field(default=None, description="Linter output or execution logs")
    
    # Mandatory for OpenEnv SDK to track episode state
    reward: float = Field(default=0.0, description="Reward from the previous transition")
    done: bool = Field(default=False, description="Whether the curriculum is complete")
    
    # Metadata for 'God-level' tool discovery (MCP, Sub-agents)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="VFS structure and available tools")
