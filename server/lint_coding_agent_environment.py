# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Lint Coding Agent Environment Implementation.

A simple test environment that echoes back messages sent to it.
Perfect for testing HTTP server infrastructure.
"""

from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import LintCodingAgentAction, LintCodingAgentObservation
except ImportError:
    from models import LintCodingAgentAction, LintCodingAgentObservation

# MANDATORY: Real-world task data for Level 1, 10, and 20 (Easy, Medium, Hard)
CURRICULUM = {
    1: {"lang": "Python", "task": "Fix Syntax: Python 2 to 3", "context": "print 'Hello'", "ans": "print("},
    10: {"lang": "Python", "task": "Libraries: Fix JSON load", "context": "json.load('{\"a\":1}')", "ans": "json.loads"},
    20: {"lang": "Python", "task": "Optimization: Use Set lookup", "context": "if x in [1,2,3]:", "ans": "set(["},
}

class LintCodingAgentEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        # Initialize internal state using OpenEnv's State object
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        self.max_levels = 20

    def reset(self) -> LintCodingAgentObservation:
        """Reset the environment to the first level."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        return self._get_observation("Environment ready! Resolve Level 1.", 0.0, False)

    def step(self, action: LintCodingAgentAction) -> LintCodingAgentObservation:
        """Process the agent's code solution and return a strict observation."""
        self._state.step_count += 1
        
        # 1. GET CURRENT TASK
        goal = CURRICULUM.get(self.level, CURRICULUM[1])
        
        # 2. THE GRADER 
        # Accessing 'code_solution' and 'explanation' from your strict Action model
        solution = action.code_solution
        explanation = action.explanation
        
        # Case-insensitive check for the required fix keyword
        is_correct = goal["ans"].lower() in solution.lower()
        
        # 3. REWARD LOGIC
        if is_correct:
            reward = 1.0
            self.level += 1
            feedback = f"Correct! Level {self.level - 1} cleared. Reasoning noted: {explanation}"
        else:
            reward = -0.1
            feedback = f"Incorrect. Retry Level {self.level}. Hint: {goal['task']}"

        # 4. DONE CRITERIA
        # Finish if max levels hit or if the agent explicitly quits
        done = self.level > self.max_levels or "QUIT" in solution.upper()

        return self._get_observation(feedback, reward, done)

    def _get_observation(self, feedback: str, reward: float, done: bool) -> LintCodingAgentObservation:
        """Helper to package internal state into the Pydantic Observation model."""
        goal = CURRICULUM.get(self.level, CURRICULUM[1])
        
        # This MUST match the fields in your LintCodingAgentObservation exactly
        return LintCodingAgentObservation(
            level=self.level,
            language=goal["lang"],
            problem_statement=f"{feedback} | Task: {goal['task']}",
            code_context=goal["context"],
            last_test_results=feedback,
            reward=reward,
            done=done,
            metadata={
                "step": self._state.step_count,
                "episode_id": self._state.episode_id
            }
        )

    @property
    def state(self) -> State:
        return self._state