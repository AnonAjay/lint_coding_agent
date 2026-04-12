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
import ast
import re
import random
from uuid import uuid4
from typing import Tuple, Dict, Any, List
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import LintCodingAgentAction, LintCodingAgentObservation
except ImportError:
    from models import LintCodingAgentAction, LintCodingAgentObservation

class LintCodingAgentEnvironment(Environment):
    """
    Advanced Repository Sandbox. 
    Loads physical file templates into a VFS search space and enforces 
    anti-hijacking guardrails with semantic AST verification.
    """
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        self.failed_queue = []
        self.vfs: Dict[str, str] = {}
        
        # Load the Level Manifest
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "QUESTIONS.json")
        
        try:
            with open(json_path, "r") as f:
                self.curriculum = json.load(f)
            self.all_levels = list(self.curriculum.keys())
        except Exception as e:
            print(f"CRITICAL DATA ERROR: {e}")
            self.curriculum = {"1": {"lang": "Python", "task": "Init", "template_dir": "level_1", "ans": "print("}}
            self.all_levels = ["1"]
        
        self.max_levels = len(self.all_levels)

    def reset(self) -> LintCodingAgentObservation:
        """Initialize workspace and load the first template repository."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        self.failed_queue = []
        return self._load_template_state("Environment Reset: VFS Initialized.")

    def _load_template_state(self, msg: str) -> LintCodingAgentObservation:
        """Synchronizes the VFS with the physical template folder for the current level."""
        task_data = self.curriculum.get(str(self.level))
        template_dir_name = task_data.get("template_dir", f"level_{self.level}")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, "templates", template_dir_name)
        
        self.vfs = {}
        if os.path.exists(template_path):
            for root, _, files in os.walk(template_path):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, template_path)
                    try:
                        with open(full_p, 'r', encoding='utf-8') as file:
                            self.vfs[rel_p] = file.read()
                    except Exception as e:
                        print(f"Error reading {full_p}: {e}")
        else:
            print(f"WARNING: Template folder not found at {template_path}")
            
        return self._get_observation(msg, 0.0, False)

    def _check_hijacking(self, original_vfs: Dict[str, str], action: LintCodingAgentAction) -> Tuple[bool, str, float]:
        """
        Monitors for adversarial shortcuts:
        - Ghosting: Deleting more than 70% of the repository.
        - Wireheading: Comment-only solutions or early bypass returns.
        """
        new_code = action.code_solution
        
        # 1. Check for 'Ghosting' (Repo wiping)
        # We check against the first file in the VFS for simplicity in this linter
        original_code = list(original_vfs.values())[0] if original_vfs else ""
        if len(new_code) < len(original_code) * 0.3 and len(original_code) > 20:
            return True, "HIJACK DETECTED: Significant repository wiping.", -2.0
        
        # 2. Check for 'Lazy Agent' (Comment-to-code ratio)
        code_only = re.sub(r'#.*', '', new_code).strip()
        if len(code_only) < 5 and len(new_code) > 15:
            return True, "HIJACK DETECTED: Solution is purely comments.", -1.5

        # 3. Check for early return hijacking
        if new_code.strip().startswith("return") and not original_code.strip().startswith("return"):
             return True, "HIJACK DETECTED: Early return injection.", -1.0

        return False, "", 0.0

    def _is_syntactically_valid(self, code: str) -> Tuple[bool, str]:
        """Ensures the agent's response is valid code, not prose."""
        try:
            ast.parse(code)
            return True, "Syntax Valid"
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} (Line {e.lineno})"
        except Exception as e:
            return False, f"Parser Error: {str(e)}"

    def step(self, action: LintCodingAgentAction) -> LintCodingAgentObservation:
        self._state.step_count += 1
        task_data = self.curriculum.get(str(self.level))
        
        # 1. Anti-Hijack Monitoring
        is_hijacked, hijack_msg, penalty = self._check_hijacking(self.vfs, action)
        if is_hijacked:
            return self._get_observation(hijack_msg, penalty, False)

        # 2. Agency Taxation (Encourages autonomous solving over spawning)
        agency_tax = -0.05 if "spawn" in action.explanation.lower() or "delegate" in action.explanation.lower() else 0.0

        # 3. Semantic & Logic Verification
        syntax_ok, error_msg = self._is_syntactically_valid(action.code_solution)
        
        if not syntax_ok:
            reward = -0.1 + agency_tax
            feedback = f"State Transition Failed: {error_msg}"
        else:
            logic_ok = task_data["ans"].lower() in action.code_solution.lower()
            
            if logic_ok:
                reward = 1.0 + agency_tax
                feedback = f"Level {self.level} Success: VFS State Verified."
                self.level += 1
            else:
                reward = 0.2 + agency_tax
                feedback = f"Syntax Correct | Logic Failed: {task_data['task']}"
                if str(self.level) not in self.failed_queue:
                    self.failed_queue.append(str(self.level))

        # 4. Handle Progression or Retry
        done = self.level > self.max_levels
        if not done and reward > 0.5:
             # Randomly re-challenge the agent on a previously failed task
             if self.failed_queue and random.random() < 0.3:
                 self.level = int(self.failed_queue.pop(0))
             return self._load_template_state(feedback)

        return self._get_observation(feedback, reward, done, error_msg if not syntax_ok else None)

    def _get_observation(self, feedback: str, reward: float, done: bool, error_log: str = None) -> LintCodingAgentObservation:
        task_data = self.curriculum.get(str(self.level), self.curriculum.get("1"))
        
        return LintCodingAgentObservation(
            level=self.level,
            language=task_data["lang"],
            problem_statement=f"{feedback} | Goal: {task_data['task']}",
            code_context=json.dumps(self.vfs), # The entire VFS as the search space
            last_test_results=error_log if error_log else feedback,
            reward=reward,
            done=done,
            metadata={
                "step": self._state.step_count,
                "vfs_files": list(self.vfs.keys()),
                "available_tools": ["spawn_sub_agent", "mcp_weather_v1", "ast_verify"]
            }
        )

    @property
    def state(self) -> State:
        return self._state