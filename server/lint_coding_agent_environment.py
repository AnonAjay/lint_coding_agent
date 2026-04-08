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
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        self.max_levels = 20

    def reset(self) -> LintCodingAgentObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        return self._get_observation("Environment ready! Resolve Level 1.", 0.0, False)

    def step(self, action: LintCodingAgentAction) -> LintCodingAgentObservation:
        self._state.step_count += 1
        
        # 1. GET CURRENT TASK
        goal = CURRICULUM.get(self.level, CURRICULUM[1])
        
        # 2. THE GRADER (Rule: Programmatic score 0.0 - 1.0)
        # Check if the agent's message contains the required fix/keyword
        is_correct = goal["ans"].lower() in action.message.lower()
        
        # 3. MEANINGFUL REWARD (Rule: Signal over trajectory)
        if is_correct:
            reward = 1.0
            self.level += 1
            feedback = f"Correct! Level {self.level - 1} cleared."
        else:
            reward = -0.1  # Penalty for incorrect code/syntax errors
            feedback = f"Incorrect. Retry Level {self.level}. Hint: {goal['task']}"

        # 4. DONE CRITERIA
        # Done if max levels reached or agent gives up
        done = self.level > self.max_levels or "QUIT" in action.message.upper()

        return self._get_observation(feedback, reward, done)

    def _get_observation(self, feedback: str, reward: float, done: bool) -> LintCodingAgentObservation:
        # Get the task context for the current level
        goal = CURRICULUM.get(self.level, CURRICULUM[1])
        
        # Combine the curriculum info into the echoed_message for the LLM to read
        display_text = f"{feedback}\nLevel: {self.level}\nLang: {goal['lang']}\nContext: {goal['context']}"
        
        return LintCodingAgentObservation(
            echoed_message=display_text,
            message_length=len(display_text),
            done=done,
            reward=reward,
            metadata={"level": self.level, "step": self._state.step_count}
        )

    @property
    def state(self) -> State:
        return self._state