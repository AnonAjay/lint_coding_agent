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
import textwrap
import json
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# 🚀 THE FIX: Import the base EnvClient. It is async by default.
from openenv import EnvClient

# Load local .env for testing
load_dotenv()

# IMPORT YOUR ACTION CLASS
try:
    from models import LintCodingAgentAction
except ImportError:
    from lint_coding_agent.models import LintCodingAgentAction

# --- CONFIGURATION ---
API_KEY = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN")
API_BASE_URL = os.environ.get("API_BASE_URL") or "https://router.huggingface.co/hf-inference/v1"
MODEL_NAME = os.environ.get("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
ADDRESS = "https://anonajay-lint-coding-agent.hf.space"

TASK_NAME = "multi-lang-lint-v1"
BENCHMARK = "lint-coding-v1"
MAX_STEPS = 10

SYSTEM_PROMPT = "You are an expert architect. Fix the code in the VFS. Return ONLY raw code."

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    action_clean = action.replace("\n", " ").strip()[:50]
    print(f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={str(done).lower()} error={error or 'null'}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    rewards: List[float] = []
    steps_taken = 0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        # 🚀 THE CRITICAL HANDSHAKE:
        # Use EnvClient directly. Use 'base_url' as the keyword.
        async with EnvClient(base_url=ADDRESS) as env:
            
            # Reset Environment
            result = await env.reset()
            
            for step in range(1, MAX_STEPS + 1):
                obs = result.observation
                
                try:
                    vfs_display = json.dumps(json.loads(obs.code_context), indent=2)
                except:
                    vfs_display = obs.code_context

                user_prompt = f"VFS Structure:\n{vfs_display}\n\nTask: {obs.problem_statement}"

                # LLM Call
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=200,
                )
                
                action_text = (completion.choices[0].message.content or "").strip()
                
                # State Transition (Awaited)
                result = await env.step(LintCodingAgentAction(
                    code_solution=action_text, 
                    explanation=f"Async fix level {obs.level}"
                ))
                
                reward = result.reward or 0.0
                done = result.done
                
                rewards.append(reward)
                steps_taken = step
                log_step(step, action_text, reward, done, None)

                if done:
                    success = True
                    break

    except Exception as e:
        if steps_taken == 0:
            log_step(1, "error_retry", 0.0, True, str(e))
    
    finally:
        score = sum(rewards) / len(rewards) if rewards else 0.0
        log_end(success, steps_taken, score, rewards)

if __name__ == "__main__":
    asyncio.run(main())