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
# Prioritizes local 'client' and 'models' to ensure architectural integrity
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from client import LintCodingAgentEnv
    from models import LintCodingAgentAction
except ImportError as e:
    print(f"CRITICAL: Local architecture files missing: {e}")
    sys.exit(1)

load_dotenv()

# --- CONFIGURATION ---
# Compliance: Uses HF_TOKEN as the primary secret
API_KEY = os.environ.get("HF_TOKEN") or os.environ.get("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

# Stability: Direct model endpoint to bypass global router 404s
API_BASE_URL = os.environ.get("API_BASE_URL") or f"https://api-inference.huggingface.co/models/{MODEL_NAME}/v1"

# Target: Your Hugging Face Space API Mount
ADDRESS = (os.environ.get("ADDRESS") or "https://anonajay-lint-coding-agent.hf.space").rstrip("/")

TASK_NAME = "multi-lang-lint-v1"
BENCHMARK = "lint-coding-v1"
MAX_STEPS = 15 

# Architect Prompt: Forces code-only output
SYSTEM_PROMPT = textwrap.dedent("""
    You are a Lead Architect. You will receive a VFS (Virtual File System) JSON.
    Identify the bug and provide the FIX.
    Respond ONLY with the corrected code. No explanations. No markdown blocks.
""").strip()

# --- STDOUT LOGGING PROTOCOL (HACKATHON SPEC) ---
def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]):
    action_clean = str(action).replace("\n", " ").replace("\r", " ").strip()[:50]
    err_str = str(error).replace("\n", " ") if error else "null"
    print(f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={str(done).lower()} error={err_str}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

async def main():
    # OpenAI client initialization
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    rewards, steps_taken, success = [], 0, False
    last_error = None

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    # --- RESILIENCE RETRY HANDSHAKE ---
    # Fixes the 503 Reject error by allowing the Space time to stabilize
    max_retries = 3
    env = None
    
    try:
        for attempt in range(max_retries):
            try:
                env_context = LintCodingAgentEnv(
                    base_url=ADDRESS,
                    headers={
                        "Authorization": f"Bearer {API_KEY}",
                        "User-Agent": "ArchitectClient/1.0",
                        "Referer": ADDRESS.replace("/v1", "")
                    }
                )
                env = await env_context.__aenter__()
                result = await env.reset()
                break # Connection secured
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Handshake 503/Delay (Attempt {attempt+1}). Retrying in 5s...", file=sys.stderr)
                    await asyncio.sleep(5)
                else:
                    raise e

        # --- MAIN AGENTIC LOOP ---
        for step in range(1, MAX_STEPS + 1):
            obs = result.observation
            steps_taken = step
            
            user_prompt = (
                f"LEVEL: {obs.level}\n"
                f"LANGUAGE: {obs.language}\n"
                f"VFS STATE: {obs.code_context}\n"
                f"OBJECTIVE: {obs.problem_statement}"
            )

            # Inference with 'wait-for-model' header
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
            
            # Step Transition
            result = await env.step(LintCodingAgentAction(
                code_solution=action_text,
                explanation=f"Architect Fix: Level {obs.level}"
            ))
            
            current_reward = result.reward if result.reward is not None else 0.0
            rewards.append(current_reward)
            
            log_step(step, action_text, current_reward, result.done, None)
            
            if result.done:
                success = (sum(rewards) >= 1.0) 
                break

    except Exception as e:
        last_error = str(e)
        log_step(steps_taken + 1, "execution_fault", 0.0, True, last_error)
    
    finally:
        if env:
            await env_context.__aexit__(None, None, None)
        
        # Final Metrics
        avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
        log_end(success, steps_taken, min(avg_reward, 1.0), rewards)

if __name__ == "__main__":
    asyncio.run(main())