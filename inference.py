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
import logging
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# --- PATH INJECTION ---
# Ensures local 'client' and 'models' are prioritized over installed site-packages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from client import LintCodingAgentEnv
    from models import LintCodingAgentAction
except ImportError as e:
    print(f"CRITICAL: Local architecture files missing: {e}")
    sys.exit(1)

load_dotenv()

# --- CONFIGURATION ---
# API_KEY is sourced from HF_TOKEN for hackathon compliance
API_KEY = os.environ.get("HF_TOKEN") or os.environ.get("API_KEY")
# Base URL for the Hugging Face Inference Router
API_BASE_URL = os.environ.get("API_BASE_URL") or "https://router.huggingface.co/hf-inference/v1"
MODEL_NAME = os.environ.get("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

# ADDRESS points to your Hugging Face Space API mount (/v1)
ADDRESS = (os.environ.get("ADDRESS") or "https://anonajay-lint-coding-agent.hf.space/v1").rstrip("/")

TASK_NAME = "multi-lang-lint-v1"
BENCHMARK = "lint-coding-v1"
MAX_STEPS = 15 

# Architect System Prompt: Enforces strict code-only output
SYSTEM_PROMPT = textwrap.dedent("""
    You are a Lead Architect. You will receive a VFS (Virtual File System) JSON.
    Identify the bug and provide the FIX.
    Respond ONLY with the corrected code. No explanations. No markdown blocks.
""").strip()

# --- STDOUT LOGGING PROTOCOL (HACKATHON SPEC) ---
def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]):
    # Ensure action string is sanitized for single-line STDOUT compliance
    action_clean = str(action).replace("\n", " ").replace("\r", " ").strip()[:50]
    err_str = str(error).replace("\n", " ") if error else "null"
    print(f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={str(done).lower()} error={err_str}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

async def main():
    # OpenAI client pointing to the Hugging Face Router
    # If 404 continues, ensure API_BASE_URL does not end in a slash.
    llm_client = OpenAI(base_url=API_BASE_URL.rstrip("/"), api_key=API_KEY)
    
    rewards, steps_taken, success = [], 0, False
    last_error = None

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Connecting to the Environment Space
        async with LintCodingAgentEnv(
            base_url=ADDRESS,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ArchitectClient/1.0",
                "Referer": ADDRESS.replace("/v1", "")
            }
        ) as env:
            
            # 🏁 Level 1 Handshake (Reset)
            result = await env.reset()
            
            for step in range(1, MAX_STEPS + 1):
                obs = result.observation
                steps_taken = step
                
                # Context Construction
                user_prompt = (
                    f"LEVEL: {obs.level}\n"
                    f"LANGUAGE: {obs.language}\n"
                    f"VFS STATE: {obs.code_context}\n"
                    f"OBJECTIVE: {obs.problem_statement}"
                )

                # LLM Inference with Wait-for-Model support
                completion = llm_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    extra_headers={"x-wait-for-model": "true"}
                )
                
                action_text = (completion.choices[0].message.content or "").strip()
                
                # Step Transition (Action Execution)
                result = await env.step(LintCodingAgentAction(
                    code_solution=action_text,
                    explanation=f"Architect Fix: Level {obs.level}"
                ))
                
                current_reward = result.reward if result.reward is not None else 0.0
                rewards.append(current_reward)
                
                log_step(step, action_text, current_reward, result.done, None)
                
                if result.done:
                    # Success logic based on clearing the 15-level sprint
                    success = (sum(rewards) >= 1.0) 
                    break

    except Exception as e:
        last_error = str(e)
        log_step(steps_taken + 1, "execution_fault", 0.0, True, last_error)
    
    finally:
        # Score normalization [0, 1]
        total_score = sum(rewards) / len(rewards) if rewards else 0.0
        log_end(success, steps_taken, min(total_score, 1.0), rewards)

if __name__ == "__main__":
    asyncio.run(main())