---
title: Lint Coding Agent
emoji: 💻
colorFrom: red
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
base_path: /v1
tags:
  - openenv
  - agentic-ai
  - python
---

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&height=200&section=header&text=Lint%20Coding%20Agent&fontSize=70&animation=fadeIn&fontAlignY=35" width="100%" />

<p align="center">
  <img src="https://img.shields.io/badge/System_Status-Online-31c854?style=for-the-badge&logo=statuspage&logoColor=white" />
  <img src="https://img.shields.io/badge/Maintained%3F-yes-2ea44f?style=for-the-badge" />
  <img src="https://img.shields.io/badge/PRs-welcome-orange?style=for-the-badge&logo=github" />
</p>

### ⚡ Autonomous Software Engineering Sandbox
*Training agents to navigate codebases, one level at a time through 15 stages of architectural complexity.*

---

## 🛠️ System Architecture

> **System Status:** `Running` 🟢 | **Sandbox:** `Docker` 🐳 | **Interface:** `FastAPI` 🚀

This Space hosts the **Lint Coding Agent Environment**, a Virtual File System (VFS) based curriculum designed for evaluating Agentic AI. It exposes a standardized OpenEnv API for remote interaction.

### 🌐 Key Endpoints
- **API Documentation:** [`/v1/docs`](./v1/docs)
- **Health Check:** [`/health`](./health)
- **WebSocket Handshake:** [`/v1/ws`](./v1/ws)

---

## 🚀 Quick Start (Local Inference)

To connect your local agent to this hosted environment, use the following `inference.py` pattern:

```python
from client import LintCodingAgentEnv
from models import LintCodingAgentAction

# Direct URL to this Space
ADDRESS = "[https://anonajay-lint-coding-agent.hf.space/v1](https://anonajay-lint-coding-agent.hf.space/v1)"

async def run_sprint():
    async with LintCodingAgentEnv(base_url=ADDRESS) as env:
        result = await env.reset()
        print(f"Level {result.observation.level} Initialized.")
        
        # Action Loop
        result = await env.step(LintCodingAgentAction(
            code_solution="print('Architect Fix')",
            explanation="Initial level validation"
        ))

## Building the Docker Image

Before using the environment, you need to build the Docker image:

```bash
# From project root
docker build -t lint_coding_agent-env:latest -f server/Dockerfile .
```

## Deploying to Hugging Face Spaces

You can easily deploy your OpenEnv environment to Hugging Face Spaces using the `openenv push` command:

```bash
# From the environment directory (where openenv.yaml is located)
openenv push

# Or specify options
openenv push --namespace my-org --private
```

The `openenv push` command will:
1. Validate that the directory is an OpenEnv environment (checks for `openenv.yaml`)
2. Prepare a custom build for Hugging Face Docker space (enables web interface)
3. Upload to Hugging Face (ensuring you're logged in)

### Prerequisites

- Authenticate with Hugging Face: The command will prompt for login if not already authenticated

### Options

- `--directory`, `-d`: Directory containing the OpenEnv environment (defaults to current directory)
- `--repo-id`, `-r`: Repository ID in format 'username/repo-name' (defaults to 'username/env-name' from openenv.yaml)
- `--base-image`, `-b`: Base Docker image to use (overrides Dockerfile FROM)
- `--private`: Deploy the space as private (default: public)

### Examples

```bash
# Push to your personal namespace (defaults to username/env-name from openenv.yaml)
openenv push

# Push to a specific repository
openenv push --repo-id my-org/my-env

# Push with a custom base image
openenv push --base-image ghcr.io/meta-pytorch/openenv-base:latest

# Push as a private space
openenv push --private

# Combine options
openenv push --repo-id my-org/my-env --base-image custom-base:latest --private
```

After deployment, your space will be available at:
`https://huggingface.co/spaces/<repo-id>`

The deployed space includes:
- **Web Interface** at `/web` - Interactive UI for exploring the environment
- **API Documentation** at `/docs` - Full OpenAPI/Swagger interface
- **Health Check** at `/health` - Container health monitoring
- **WebSocket** at `/ws` - Persistent session endpoint for low-latency interactions

## Environment Details

### Action
**LintCodingAgentAction**: Contains a single field
- `message` (str) - The message to echo back

### Observation
**LintCodingAgentObservation**: Contains the echo response and metadata
- `echoed_message` (str) - The message echoed back
- `message_length` (int) - Length of the message
- `reward` (float) - Reward based on message length (length × 0.1)
- `done` (bool) - Always False for echo environment
- `metadata` (dict) - Additional info like step count

### Reward
The reward is calculated as: `message_length × 0.1`
- "Hi" → reward: 0.2
- "Hello, World!" → reward: 1.3
- Empty message → reward: 0.0

## Advanced Usage

### Connecting to an Existing Server

If you already have a Lint Coding Agent environment server running, you can connect directly:

```python
from lint_coding_agent import LintCodingAgentEnv

# Connect to existing server
lint_coding_agentenv = LintCodingAgentEnv(base_url="<ENV_HTTP_URL_HERE>")

# Use as normal
result = lint_coding_agentenv.reset()
result = lint_coding_agentenv.step(LintCodingAgentAction(message="Hello!"))
```

Note: When connecting to an existing server, `lint_coding_agentenv.close()` will NOT stop the server.

### Using the Context Manager

The client supports context manager usage for automatic connection management:

```python
from lint_coding_agent import LintCodingAgentAction, LintCodingAgentEnv

# Connect with context manager (auto-connects and closes)
with LintCodingAgentEnv(base_url="http://localhost:8000") as env:
    result = env.reset()
    print(f"Reset: {result.observation.echoed_message}")
    # Multiple steps with low latency
    for msg in ["Hello", "World", "!"]:
        result = env.step(LintCodingAgentAction(message=msg))
        print(f"Echoed: {result.observation.echoed_message}")
```

The client uses WebSocket connections for:
- **Lower latency**: No HTTP connection overhead per request
- **Persistent session**: Server maintains your environment state
- **Efficient for episodes**: Better for many sequential steps

### Concurrent WebSocket Sessions

The server supports multiple concurrent WebSocket connections. To enable this,
modify `server/app.py` to use factory mode:

```python
# In server/app.py - use factory mode for concurrent sessions
app = create_app(
    LintCodingAgentEnvironment,  # Pass class, not instance
    LintCodingAgentAction,
    LintCodingAgentObservation,
    max_concurrent_envs=4,  # Allow 4 concurrent sessions
)
```

Then multiple clients can connect simultaneously:

```python
from lint_coding_agent import LintCodingAgentAction, LintCodingAgentEnv
from concurrent.futures import ThreadPoolExecutor

def run_episode(client_id: int):
    with LintCodingAgentEnv(base_url="http://localhost:8000") as env:
        result = env.reset()
        for i in range(10):
            result = env.step(LintCodingAgentAction(message=f"Client {client_id}, step {i}"))
        return client_id, result.observation.message_length

# Run 4 episodes concurrently
with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(run_episode, range(4)))
```

## Development & Testing

### Direct Environment Testing

Test the environment logic directly without starting the HTTP server:

```bash
# From the server directory
python3 server/lint_coding_agent_environment.py
```

This verifies that:
- Environment resets correctly
- Step executes actions properly
- State tracking works
- Rewards are calculated correctly

### Running Locally

Run the server locally for development:

```bash
uvicorn server.app:app --reload
```

## Project Structure

```
lint_coding_agent/
├── .github/                   # GitHub Actions (CI/CD for testing)
│   └── workflows/
│       └── test.yml
├── .dockerignore              # Keep build context small
├── .gitignore                 # Ignore __pycache__, .venv, etc.
├── README.md                  # Enhanced with the code I gave you
├── openenv.yaml               # OpenEnv configuration
├── pyproject.toml             # Modern build system (replacing setup.py)
├── uv.lock                    # Fast dependency locking
├── src/                       # Source code directory
│   └── lint_coding_agent/     # The actual package
│       ├── __init__.py        # Expose main classes here
│       ├── client.py          # User-facing client
│       ├── models.py          # Pydantic/Data schemas
│       └── server/            # Server-side logic
│           ├── __init__.py
│           ├── app.py         # FastAPI/WS entry point
│           ├── core.py        # renamed from lint_coding_agent_environment.py
│           └── templates/     # Your 15-level folders should live here
│               ├── level_1/
│               └── ...
├── tests/                     # Dedicated test suite
│   ├── __init__.py
│   ├── test_client.py
│   └── test_env_logic.py
└── Dockerfile                 # Multi-stage build for production
```
