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

import json
import os
from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import LintCodingAgentAction, LintCodingAgentObservation
except ImportError:
    from models import LintCodingAgentAction, LintCodingAgentObservation

class LintCodingAgentEnvironment(Environment):
    """
    A data-driven environment that loads a 50-level curriculum from a JSON file.
    Designed for professional code-linting agent evaluation.
    """
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        # Initialize internal state using OpenEnv's State object
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        
        # --- DATA LOADING BLOCK ---
        # Get the path to QUESTIONS.json relative to this file to avoid pathing errors in Docker
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "QUESTIONS.json")
        
        try:
            with open(json_path, "r") as f:
                self.curriculum = json.load(f)
        except Exception as e:
            print(f"CRITICAL ERROR: Could not load QUESTIONS.json: {e}")
            # Minimal fallback to prevent total server crash
            self.curriculum = {"1": {"lang": "Python", "task": "Fallback", "context": "print 'Hi'", "ans": "print("}}
        
        self.max_levels = len(self.curriculum)

    def reset(self) -> LintCodingAgentObservation:
        """Reset the environment to the beginning of the curriculum."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        return self._get_observation("Curriculum Loaded. Ready for Level 1.", 0.0, False)

    def step(self, action: LintCodingAgentAction) -> LintCodingAgentObservation:
        """Process the agent's solution against the current JSON task."""
        self._state.step_count += 1
        
        # Get current level data (JSON keys are strings)
        task_data = self.curriculum.get(str(self.level), self.curriculum.get("1"))
        
        # Logic: Extract fields from the strict Action model
        solution = action.code_solution
        explanation = action.explanation
        
        # Case-insensitive grading logic
        is_correct = task_data["ans"].lower() in solution.lower()
        
        if is_correct:
            reward = 1.0
            self.level += 1
            feedback = f"Correct! Level {self.level - 1} cleared. Reason: {explanation}"
        else:
            reward = -0.1
            feedback = f"Incorrect fix. Retry Level {self.level}. Hint: {task_data['task']}"

        # Done if all levels complete or agent gives up
        done = self.level > self.max_levels or "QUIT" in solution.upper()

        return self._get_observation(feedback, reward, done)

    def _get_observation(self, feedback: str, reward: float, done: bool) -> LintCodingAgentObservation:
        """Helper to package internal data into the strict Observation Pydantic model."""
        # Use string indexing for JSON curriculum access
        task_data = self.curriculum.get(str(self.level), self.curriculum.get("1"))
        
        return LintCodingAgentObservation(
            level=self.level,
            language=task_data["lang"],
            problem_statement=f"{feedback} | Goal: {task_data['task']}",
            code_context=task_data["context"],
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