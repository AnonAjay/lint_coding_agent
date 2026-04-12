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

import os
import textwrap
import json
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv
from openenv import SyncEnvClient as OpenEnv

# Load local .env for testing
load_dotenv()

# IMPORT YOUR ACTION CLASS
try:
    from models import LintCodingAgentAction
except ImportError:
    from lint_coding_agent.models import LintCodingAgentAction

# --- MANDATORY CONFIGURATION FOR SCALER PORTAL ---
# Phase 2 Failure Fix: Ensure these variables are dynamically pulled.
API_KEY = os.environ.get("API_KEY") or os.environ.get("HF_TOKEN")
API_BASE_URL = os.environ.get("API_BASE_URL") or "https://router.huggingface.co/hf-inference/v1"
MODEL_NAME = os.environ.get("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

# Your Specific Environment Address (The 'Server' part)
ADDRESS = "https://anonajay-lint-coding-agent.hf.space"

# Task Metadata
TASK_NAME = os.environ.get("MY_ENV_TASK", "multi-lang-lint-v1")
BENCHMARK = os.environ.get("MY_ENV_BENCHMARK", "lint-coding-v1")

MAX_STEPS = 10
TEMPERATURE = 0.2
MAX_TOKENS = 150
SUCCESS_SCORE_THRESHOLD = 0.1 

# SYSTEM PROMPT (Lead Architect Persona)
SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an expert multi-lingual software architect.
    You will receive a Virtual File System (VFS) as a JSON map.
    Your task: Find the bug in the files and return ONLY the raw code fix.
    No explanations, no markdown blocks. Just code.
    """
).strip()

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Lead Architect Tip: Truncate action for logs to keep them single-line
    action_clean = action.replace("\n", " ").strip()[:50]
    print(f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    success_val = str(success).lower()
    print(f"[END] success={success_val} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

def main() -> None:
    # Initialize OpenAI Client via Scaler Proxy
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # Initialize the OpenEnv client
    env = OpenEnv(ADDRESS)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        # 1. Reset Environment & Load VFS
        result = env.reset()
        
        for step in range(1, MAX_STEPS + 1):
            obs = result.observation
            
            # 2. Parse VFS Search Space for the Agent
            # obs.code_context is now a JSON string of the repo
            try:
                vfs_data = json.loads(obs.code_context)
                vfs_display = json.dumps(vfs_data, indent=2)
            except:
                vfs_display = obs.code_context

            user_prompt = (
                f"Virtual File System:\n{vfs_display}\n\n"
                f"Task: {obs.problem_statement}\n"
                f"Instruction: Locate and fix the bug."
            )

            # 3. LLM Inference via Scaler Proxy
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            
            action_text = (completion.choices[0].message.content or "").strip()
            
            # 4. Environment Step (The State Transition)
            result = env.step(LintCodingAgentAction(
                code_solution=action_text, 
                explanation=f"Architect fix for {obs.language} at level {obs.level}"
            ))
            
            reward = result.reward or 0.0
            done = result.done
            
            rewards.append(reward)
            steps_taken = step

            # 5. Log Step immediately for the Portal Grader
            log_step(step=step, action=action_text, reward=reward, done=done, error=None)

            if done:
                success = True
                break

        score = sum(rewards) / len(rewards) if rewards else 0.0
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        error_msg = str(e).replace("\n", " ")
        if steps_taken == 0:
            log_step(step=1, action="error_retry", reward=0.0, done=True, error=error_msg)
    
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    main()