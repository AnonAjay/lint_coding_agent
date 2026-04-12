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
import logging
from uuid import uuid4
from typing import Tuple, Dict, Any, List
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

# Setup Logging for the Logic Engine
logger = logging.getLogger("ArchitectEnvironment")

# --- ABSOLUTE IMPORT FIX ---
try:
    from models import LintCodingAgentAction, LintCodingAgentObservation
except ImportError:
    from ..models import LintCodingAgentAction, LintCodingAgentObservation

class LintCodingAgentEnvironment(Environment):
    """
    Advanced Repository Sandbox. 
    Handles VFS synchronization for 15 levels with real-time debug telemetry.
    """
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        self.failed_queue = []
        self.vfs: Dict[str, str] = {}
        
        # --- DYNAMIC PATH RESOLUTION ---
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(self.current_dir, "QUESTIONS.json")
        self.templates_base = os.path.join(self.current_dir, "templates")
        
        logger.info(f"🏗️ Initializing Environment Logic from: {self.current_dir}")
        
        try:
            with open(json_path, "r") as f:
                self.curriculum = json.load(f)
            self.all_levels = sorted(list(self.curriculum.keys()), key=int)
            logger.info(f"📚 Curriculum Loaded: {len(self.all_levels)} levels found.")
        except Exception as e:
            logger.error(f"❌ CRITICAL DATA ERROR: {e}")
            self.curriculum = {"1": {"lang": "Python", "task": "Fallback: Init", "template_dir": "level_1", "ans": "print"}}
            self.all_levels = ["1"]
        
        self.max_levels = int(self.all_levels[-1]) if self.all_levels else 1

    def reset(self) -> LintCodingAgentObservation:
        """Full state reset for Phase 2 scoring."""
        logger.info("🔄 Resetting Environment State...")
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.level = 1
        self.failed_queue = []
        return self._load_template_state("Environment Reset: 15-Level Sprint Initialized.")

    def _load_template_state(self, msg: str) -> LintCodingAgentObservation:
        """Loads physical files into the VFS with debug tracking."""
        task_data = self.curriculum.get(str(self.level), {})
        template_dir_name = task_data.get("template_dir", f"level_{self.level}")
        template_path = os.path.join(self.templates_base, template_dir_name)
        
        logger.info(f"📂 Loading Template for Level {self.level}: {template_path}")
        
        self.vfs = {}
        if os.path.exists(template_path):
            for root, _, files in os.walk(template_path):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, template_path)
                    try:
                        with open(full_p, 'r', encoding='utf-8') as file:
                            self.vfs[rel_p] = file.read()
                        logger.info(f"  📄 VFS Mounted: {rel_p}")
                    except Exception as e:
                        logger.error(f"  ⚠️ VFS Read Error {rel_p}: {e}")
        else:
            logger.error(f"❌ CRITICAL: Level path missing: {template_path}")
            
        return self._get_observation(msg, 0.0, False)

    def _check_hijacking(self, action: LintCodingAgentAction) -> Tuple[bool, str, float]:
        """Anti-adversarial monitor to prevent agent shortcuts."""
        new_code = action.code_solution or ""
        if len(new_code.strip()) < 10:
             return True, "HIJACK: Solution rejected for insufficient depth.", -2.0
        
        code_only = re.sub(r'#.*', '', new_code).strip()
        if len(code_only) < 5:
            return True, "HIJACK: Solution contains only comments.", -1.5

        return False, "", 0.0

    def _is_syntactically_valid(self, code: str, lang: str) -> Tuple[bool, str]:
        """Verifies solution validity based on language type."""
        if lang.lower() == "python":
            try:
                ast.parse(code)
                return True, "Syntax Valid"
            except SyntaxError as e:
                return False, f"SyntaxError: {e.msg} (Line {e.lineno})"
        return (True, "Non-Python/No-Verify") if len(code) > 5 else (False, "Empty Solution")

    def step(self, action: LintCodingAgentAction) -> LintCodingAgentObservation:
        self._state.step_count += 1
        task_data = self.curriculum.get(str(self.level))
        
        logger.info(f"👣 STEP {self._state.step_count} | Level: {self.level}")

        # 1. Monitoring
        is_hijacked, hijack_msg, penalty = self._check_hijacking(action)
        if is_hijacked:
            logger.warning(f"🚫 {hijack_msg}")
            return self._get_observation(hijack_msg, penalty, False)

        # 2. Execution & Verification
        syntax_ok, error_msg = self._is_syntactically_valid(action.code_solution, task_data["lang"])
        
        if not syntax_ok:
            reward = -0.2
            feedback = f"Transition Failed: {error_msg}"
            logger.info(f"❌ Syntax Invalid: {error_msg}")
        else:
            # Check logic against the 'ans' substring in manifest
            logic_ok = task_data["ans"].lower() in action.code_solution.lower()
            
            if logic_ok:
                reward = 1.0
                feedback = f"Level {self.level} Success."
                logger.info(f"✅ Success! Solution matches '{task_data['ans']}'")
                self.level += 1
            else:
                reward = 0.1
                feedback = f"Syntax OK | Logic Missing: {task_data['task']}"
                logger.info(f"⚠️ Logic Mismatch. Expected logic containing: '{task_data['ans']}'")
                if str(self.level) not in self.failed_queue:
                    self.failed_queue.append(str(self.level))

        # 3. Handle Progression
        done = self.level > self.max_levels
        
        if not done and reward > 0.8:
            return self._load_template_state(feedback)

        return self._get_observation(feedback, reward, done)

    def _get_observation(self, feedback: str, reward: float, done: bool) -> LintCodingAgentObservation:
        lookup_level = min(self.level, self.max_levels)
        task_data = self.curriculum.get(str(lookup_level), self.curriculum.get("1"))
        
        return LintCodingAgentObservation(
            level=self.level,
            language=task_data["lang"],
            problem_statement=f"{feedback} | Current Task: {task_data['task']}",
            code_context=json.dumps(self.vfs), 
            last_test_results=feedback,
            reward=reward,
            done=done,
            metadata={
                "step": self._state.step_count,
                "vfs_files": list(self.vfs.keys()),
                "total_levels": self.max_levels
            }
        )

    @property
    def state(self) -> State:
        return self._state