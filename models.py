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
from typing import List, Optional

class LintCodingAgentAction(Action):
    """The agent provides the code solution for the current level."""
    code_solution: str = Field(..., description="The full code or fix for the level")
    explanation: str = Field(..., description="Short reasoning for the fix")

class LintCodingAgentObservation(Observation):
    """The environment provides the code challenge and the results of the linter/compiler."""
    level: int = Field(..., description="Current difficulty level (1-20)")
    language: str = Field(..., description="Programming language (e.g., Python, JS)")
    problem_statement: str = Field(..., description="The coding task or bug description")
    code_context: str = Field(..., description="The broken or incomplete code snippet")
    last_test_results: Optional[str] = Field(default=None, description="Output from the previous run")
