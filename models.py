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
    Optional fields with defaults prevent 422 Validation Errors during 
    high-latency inference or manual UI testing.
    """
    code_solution: Optional[str] = Field(
        default="", 
        description="The full code fix or specific patch for the repository."
    )
    explanation: Optional[str] = Field(
        default="Direct architectural intervention.", 
        description="Reasoning for the fix; utilized for tracking sub-agent logic or taxation."
    )

class LintCodingAgentObservation(Observation):
    """
    Observation schema for the VFS (Virtual File System) Search Space.
    
    Provides the multi-file repository state, environment feedback, and 
    curriculum progression.
    """
    level: int = Field(
        default=1, 
        description="Current difficulty level in the 15-level roadmap."
    )
    language: str = Field(
        default="Python", 
        description="The primary programming language of the current task."
    )
    problem_statement: str = Field(
        default="", 
        description="The technical objective, bug description, or mission prompt."
    )
    code_context: str = Field(
        default="{}", 
        description="JSON-stringified Virtual File System (VFS) map containing repo files."
    )
    last_test_results: Optional[str] = Field(
        default=None, 
        description="Standard output from linters, compilers, or test suites."
    )
    
    # --- MANDATORY FIELDS FOR OPENENV PROTOCOL ---
    # These must be explicitly defined to allow the SDK to handle state transitions.
    reward: float = Field(
        default=0.0, 
        description="The scalar reward signal from the previous action transition."
    )
    done: bool = Field(
        default=False, 
        description="Boolean flag indicating if the episode/curriculum has concluded."
    )
    
    # --- EXTENSIBILITY ---
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Extended context for tool discovery (MCP), file structure, or sub-agent logs."
    )
