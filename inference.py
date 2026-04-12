"""
Inference Script Example
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    LOCAL_IMAGE_NAME The name of the local image to use for the environment if you are using from_docker_image()
                     method

- Defaults are set only for API_BASE_URL and MODEL_NAME 
    (and should reflect your active inference setup):
    API_BASE_URL = os.getenv("API_BASE_URL", "<your-active-endpoint>")
    MODEL_NAME = os.getenv("MODEL_NAME", "<your-active-model>")
    
- The inference script must be named `inference.py` and placed in the root directory of the project
- Participants must use OpenAI Client for all LLM calls using above variables

STDOUT FORMAT
- The script must emit exactly three line types to stdout, in this order:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after env.close(), always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw last_action_error string, or null if none.
    - All fields on a single line with no newlines within a line.
    - Each tasks should return score in [0, 1]

  Example:
    [START] task=click-test env=miniwob model=Qwen3-VL-30B
    [STEP] step=1 action=click('123') reward=0.00 done=false error=null
    [STEP] step=2 action=fill('456','text') reward=0.00 done=false error=null
    [STEP] step=3 action=click('789') reward=1.00 done=true error=null
    [END] success=true steps=3 score=1.00 rewards=0.00,0.00,1.00
"""

import asyncio
import os
import sys
import json
import textwrap
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# 🚀 THE BREAKPOINT FIX
# Force the current directory into the front of the path.
# This ensures 'from client import ...' hits YOUR file, not a library.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from client import LintCodingAgentEnv
    from models import LintCodingAgentAction
except ImportError as e:
    print(f"CRITICAL: Local architecture files missing: {e}")
    sys.exit(1)

load_dotenv()

# --- CONFIGURATION ---
API_KEY = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN")
API_BASE_URL = os.environ.get("API_BASE_URL") or "https://router.huggingface.co/hf-inference/v1"
MODEL_NAME = os.environ.get("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
ADDRESS = os.environ.get("ADDRESS") or "https://anonajay-lint-coding-agent.hf.space"

TASK_NAME = "multi-lang-lint-v1"
BENCHMARK = "lint-coding-v1"
MAX_STEPS = 15 

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are a Lead Architect. You will receive a VFS (Virtual File System) JSON.
    Identify the bug in the code provided in the context.
    Respond ONLY with the corrected code. No explanations. No markdown blocks.
    """
).strip()

def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]):
    # Cleanup for clean STDOUT logging required by Scaler
    action_clean = action.replace("\n", " ").strip()[:50]
    print(f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={str(done).lower()} error={error or 'null'}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

async def main():
    # OpenAI client handles the handshake with the Qwen/Scaler proxy
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    rewards, steps_taken, success = [], 0, False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        # 🏁 THE ASYNC HANDSHAKE
        # Using the local wrapper ensures we can handle the 15-level VFS state
        async with LintCodingAgentEnv(base_url=ADDRESS) as env:
            
            # Reset triggers the server to load Level 1 from templates
            result = await env.reset()
            
            for step in range(1, MAX_STEPS + 1):
                obs = result.observation
                
                # Context parsing for the 15 levels
                vfs_display = obs.code_context

                user_prompt = (
                    f"LEVEL: {obs.level}\n"
                    f"LANGUAGE: {obs.language}\n"
                    f"VFS STATE:\n{vfs_display}\n\n"
                    f"OBJECTIVE: {obs.problem_statement}"
                )

                # LLM Inference with Architect precision
                completion = llm_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
                
                action_text = (completion.choices[0].message.content or "").strip()
                
                # 🚀 STEP TRANSITION
                # The await here is critical because LintCodingAgentEnv is Async
                result = await env.step(LintCodingAgentAction(
                    code_solution=action_text,
                    explanation=f"Architect Fix Level {obs.level}"
                ))
                
                reward = result.reward or 0.0
                rewards.append(reward)
                steps_taken = step
                
                log_step(step, action_text, reward, result.done, None)
                
                if result.done:
                    # Success logic: Average reward threshold for the sprint
                    success = (sum(rewards) / len(rewards)) >= 0.1
                    break

    except Exception as e:
        log_step(steps_taken + 1, "phase2_exec_error", 0.0, True, str(e))
    
    finally:
        score = sum(rewards) / len(rewards) if rewards else 0.0
        log_end(success, steps_taken, score, rewards)

if __name__ == "__main__":
    asyncio.run(main())