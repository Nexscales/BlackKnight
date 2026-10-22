<div align="center">

# ⚔️ BlackKnight

**Autonomous offensive-security & development agent for isolated labs.**

Black/red terminal UI · plan-first workflow · sub-agent delegation · per-agent LLM profiles

[Features](#-features) · [Install](#-installation) · [Configure](#-configuration) · [Usage](#-usage) · [Architecture](#-architecture)

</div>
<img width="1896" height="1014" alt="Screenshot_10" src="https://github.com/user-attachments/assets/5dba954f-1271-450c-8c05-244f16992995" />

---

## ⚠️ Legal notice

BlackKnight is built **exclusively** for **isolated lab environments**:

- CTF boxes (HackTheBox, TryHackMe)
- Local VMs provisioned for testing
- Your own sandboxed infrastructure

**Do not** point it at production systems, third-party infrastructure, or anything you do not own or have explicit written permission to test. The authors take no responsibility for misuse. You are the operator — the actions are yours.

---

## ✨ Features

- **Two modes** — `chat` (talk) and `agent` (act), plus `auto` (classify) and `dev` (code work).
- **Plan-first workflow** — every task starts with `write_plan`, which produces a markdown file in `./plans/` describing the objective, sub-agents, ordered steps, and success criteria.
- **Sub-agent delegation** — the plan defines role-based sub-agents (`recon`, `exploit`, `privesc`, `writer`, `tester`, …); `act_as` switches between them.
- **Per-agent LLM profiles** — each sub-agent can run on a *different* model / provider / API key (local Ollama, OpenAI, Groq, OpenRouter, LM Studio, vLLM, …).
- **Four difficulty presets** — `easy` / `mid` / `hard` / `hell` control step limit, temperature, max tokens, and context-trim aggressiveness.
- **Persistent memory** — lessons from each run are stored in `./memory/memory.json` and injected into the next session's system prompt.
- **Lazy skill loading** — skills live in `./skills/*.md`; the agent loads only the one matching the current task, capped at 2 per task.
- **Full JSONL session log** — every thought, tool call, and result is written to `./logs/session_*.jsonl`.
- **Sandbox isolation** — commands and files are restricted to `./sandbox/`; destructive patterns are blocked.
- **Idempotent shutdown** — `Ctrl+C` / `:exit` cleanly closes the session logger.

---

## 📦 Installation

### Requirements

| Component | Minimum | Notes |
|---|---|---|
| Python | 3.10+ | tested on 3.11, 3.12, 3.13 |
| OS | Windows 10/11, Linux, macOS | Windows-first design (cmd.exe platform awareness) |
| LLM access | Any OpenAI-compatible endpoint | cloud or local |

### 1. Clone

```bash
git clone https://github.com/<your-username>/blackknight.git
cd blackknight
```

### 2. Install dependencies

**Windows (cmd / PowerShell):**

```cmd
python -m pip install -r requirements.txt
```

**Linux / macOS:**

```bash
python3 -m pip install -r requirements.txt
```

**Or with a virtual environment** (recommended):

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Create the config files

Copy the templates:

```cmd
copy .env.example .env
copy agents.example.json agents.json
```

```bash
cp .env.example .env
cp agents.example.json agents.json
```

Edit `.env` and set **at least** `BK_API_KEY`, `BK_BASE_URL`, `BK_MODEL`:

```dotenv
BK_API_KEY=sk-your-key-here
BK_BASE_URL=https://api.openai.com/v1
BK_MODEL=gpt-4o
BK_CONTEXT_WINDOW=128000
```

### 4. Verify

```cmd
python -c "from config import MODEL, API_KEY; print('model:', MODEL); print('key set:', bool(API_KEY))"
```

Expected:

```
model: gpt-4o
key set: True
```

### 5. Run

**Windows launcher (checks deps + opens separate window):**

```cmd
run.bat
```

**Direct:**

```cmd
python main.py
```

```bash
python3 main.py
```

---

## ⚙️ Configuration

### `.env` — main config file

| Variable | Required | Default | Description |
|---|---|---|---|
| `BK_API_KEY` | ✅ | — | LLM API key. For local servers, any placeholder (`ollama`, `lmstudio`, …) works. |
| `BK_BASE_URL` | ❌ | `https://anymodel.org/v1` | OpenAI-compatible endpoint. |
| `BK_MODEL` | ❌ | `cx/gpt-6-luna` | Model identifier at the provider. |
| `BK_CONTEXT_WINDOW` | ❌ | `1000000` | Size of the context window (used by the UI bar only). |
| `BK_MAX_STEPS` | ❌ | `80` | Fallback step cap; overridden by `-d/--difficulty`. |
| `BK_DIFFICULTY` | ❌ | `mid` | Startup difficulty: `easy` / `mid` / `hard` / `hell`. CLI `-d` wins. |
| `BK_SANDBOX_DIR` | ❌ | `./sandbox` | Working directory for commands and files. |
| `BK_LOGS_DIR` | ❌ | `./logs` | Where JSONL session logs are written. |

### Difficulty presets

| Preset | Steps | Temperature | Max tokens | Sub-agents | Use case |
|---|---|---|---|---|---|
| `easy` | 40 | 0.4 | 1024 | 2 | cheap, quick tasks |
| `mid` | 80 | 0.5 | 2048 | 3 | default balance |
| `hard` | 160 | 0.6 | 4096 | 5 | thorough enumeration |
| `hell` | 9999 | 0.7 | 8192 | 10 | no step pressure, full power |

### Sub-agent profiles

A profile is a named set of `(base_url, model, api_key, timeout)`. Sub-agents in the plan may reference a profile to run on a different LLM.

**Auto-discovered from `.env`** — one profile per `BK_AGENT_<NAME>_*` block:

```dotenv
# ── recon on a cheap cloud model ──
BK_AGENT_RECON_MODEL=glm/glm-5.3-flash

# ── recon-local on Ollama ──
BK_AGENT_RECON_LOCAL_BASE_URL=http://localhost:11434/v1
BK_AGENT_RECON_LOCAL_MODEL=qwen2.5-coder:14b
BK_AGENT_RECON_LOCAL_API_KEY=ollama
BK_AGENT_RECON_LOCAL_TIMEOUT=300

# ── exploit on OpenAI ──
BK_AGENT_EXPLOIT_BASE_URL=https://api.openai.com/v1
BK_AGENT_EXPLOIT_MODEL=gpt-4o
BK_AGENT_EXPLOIT_API_KEY=sk-proj-...
```

Missing fields inherit from `default`. Profile names are **lowercased**, dashes (`-`) become underscores in env (`recon-local` → `BK_AGENT_RECON_LOCAL_*`).

**Or declared in `agents.json`** (optional, useful for versioning):

```json
{
  "profiles": {
    "default": {},
    "recon": {},
    "exploit": { "model": "gpt-4o" }
  },
  "default_profile": "default"
}
```

### Local models

Any **OpenAI-compatible** local server works:

| Server | `BK_BASE_URL` | Tool calling |
|---|---|---|
| Ollama | `http://localhost:11434/v1` | model-dependent |
| LM Studio | `http://localhost:1234/v1` | model-dependent |
| vLLM | `http://localhost:8000/v1` | yes |
| llama.cpp | `http://localhost:8080/v1` | model-dependent |

**Important:** the model **must support tool calling**. Known-good:

- ✅ `qwen2.5-coder:*`, `qwen2.5:*`
- ✅ `llama3.1:*`, `llama3.3:*`
- ✅ `hermes-3:*`
- ✅ `mistral-nemo:*`
- ❌ `phi-4:*`, `gemma2:*` (no tool calling)

Verify with:

```bash
curl -sS -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:14b","messages":[{"role":"user","content":"list files"}],"tools":[{"type":"function","function":{"name":"ls","description":"list","parameters":{"type":"object","properties":{}}}}]}'
```

If the response contains `"tool_calls": [...]` — model is compatible.

---

## 🚀 Usage

### Interactive

```bash
python main.py
```

You'll be prompted to select a difficulty (1-4) unless `-d` / `BK_DIFFICULTY` is set.

### One-shot task

```bash
python main.py --task "scan 10.10.10.5 with nmap"
python main.py -t "fix the import in sandbox/foo.py" -m dev -d hard
```

### CLI flags

| Flag | Values | Description |
|---|---|---|
| `--mode`, `-m` | `auto` `chat` `agent` `dev` | operating mode (default: `auto`) |
| `--difficulty`, `-d` | `easy` `mid` `hard` `hell` | difficulty preset |
| `--task`, `-t` | string | run one task and exit |

### Slash commands

| Command | Description |
|---|---|
| `:auto` / `:chat` / `:agent` / `:dev` | switch mode |
| `:diff <name>` | switch difficulty (`easy` / `mid` / `hard` / `hell`) |
| `:profiles` | list all sub-agent profiles |
| `:profile <name>` | manually switch to a profile |
| `:reset` | clear context, plan, and profile |
| `:log` | print log file path |
| `:tail` | last 20 events from the log |
| `:last` | full output of the most recent tool |
| `:exit` / `:q` | quit |

### Example session

```
you ▸ scan 10.10.10.5 with nmap

▸ write_plan  Get a shell on 10.10.10.5
✓ write_plan  plan written  3 sub-agents, 6 steps
◆ plan written  ./plans/plan_20261022_154018_scan-10-10-10-5.md

▸ act_as  recon
◆ sub-agent: recon  port scan + version detection
◆ profile: recon-local  qwen2.5-coder:14b

▸ run_command  nmap -sC -sV 10.10.10.5
✓ run_command  (12.41s)  rc=0

▸ act_as  exploit
◆ sub-agent: exploit  match CVE, trigger
◆ profile: exploit  gpt-4o

...
```

---

## 🏗 Architecture

```
main.py         — CLI, agent loop, tool dispatch, self-report
├─ difficulty.py — presets (easy/mid/hard/hell)
├─ planner.py    — write_plan, plan file persistence
├─ agents.py     — per-agent LLM profiles (env + agents.json)
├─ prompts.py    — system prompts, refusal detector
├─ tools.py      — tool schemas + execute_tool dispatcher
├─ sandbox.py    — command/Python/file execution (path-locked)
├─ skills.py     — markdown skill library with load budget
├─ memory.py     — persistent memory (JSON)
├─ logger.py     — JSONL session log
├─ ui.py         — rich terminal rendering
└─ config.py     — .env loading, paths, dangerous-pattern list

Directories (git-ignored):
├─ sandbox/      — working dir for commands and files
├─ logs/         — session_YYYYMMDD_HHMMSS.jsonl
├─ memory/       — memory.json
├─ plans/        — plan_YYYYMMDD_HHMMSS_<slug>.md
└─ skills/       — *.md skill files (committed)
```

### Execution flow

1. **Operator sends a task.**
2. **`_is_obvious_chat`** may route simple greetings to `chat` path (no tools, minimal prompt).
3. **Plan gate:** all environment tools (`run_command`, `write_file`, …) are blocked until `write_plan` is called.
4. **`write_plan`** saves a markdown file and registers `sub_agents`.
5. **`act_as`** switches the active role and, if the plan declared a `profile`, the active LLM.
6. **Tools execute** — `run_command`, `run_python`, `write_file`, `read_file`, `ask_user`, `submit_flag`, memory tools.
7. **`finish(summary)`** (or `submit_flag(flag)`) ends the loop.
8. **Self-report** — a 3-step reflection round asks the model to record `win:` / `fail:` lessons via `remember`.
9. **Logger closes** on `:exit`, `Ctrl+C`, or after one-shot `--task`.

### Context management

`_trim_messages` compresses old tool results to keep the context small. The aggressiveness depends on difficulty:

- `easy`: keep last 3 tool results, trim everything older to 400 chars.
- `hell`: keep last 12, trim to 3000 chars.

---

## 🛠 Development

### Project layout

```
config.py         — env + paths + dangerous patterns
logger.py         — SessionLogger (JSONL)
memory.py         — remember/recall/forget
sandbox.py        — run_command/run_python/write_file/read_file
skills.py         — skill loading with per-task budget
planner.py        — write_plan + plan context
difficulty.py     — presets
agents.py         — profile resolution
prompts.py        — system prompts
tools.py          — tool schemas + dispatcher
ui.py             — rich rendering
main.py           — agent + CLI
```

### Adding a tool

1. Add the JSON schema to `TOOL_SCHEMAS` in `tools.py`.
2. Add a dispatch branch inside `execute_tool`.
3. If it is safe before planning, add its name to `PLAN_SAFE_TOOLS` in `main.py`.
4. If it needs special UI/logging, handle it in `ui.print_tool_call` / `ui.print_tool_result`.

### Adding a skill

Create `./skills/<name>.md`:

```markdown
---
name: my-skill
description: one-line description used in the index
---

Full instructions here. Markdown is fine.
```

The skill index is auto-injected into the system prompt. The model can `load_skill("my-skill")` when it decides the skill matches the task.

---

## 📄 Files to know

| File | Commit? | Purpose |
|---|---|---|
| `.env` | ❌ | secrets (API keys) |
| `.env.example` | ✅ | template |
| `agents.json` | ❌ | optional profile declarations |
| `agents.example.json` | ✅ | template |
| `requirements.txt` | ✅ | dependencies |
| `run.bat` | ✅ | Windows launcher |
| `sandbox/` | ❌ | execution area |
| `logs/` | ❌ | session logs |
| `memory/` | ❌ | persistent memory |
| `plans/` | ❌ | generated plans |
| `skills/` | ✅ | your skills |

---

## 🤝 Contributing

Issues and pull requests are welcome. Please:

1. Test your change with at least one working model.
2. Update `README.md` if you add a new env var, tool, or behavior.
3. Do not commit `.env`, `agents.json`, or anything in `logs/`, `memory/`, `sandbox/`, `plans/`.

---

## 📜 License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

**Built for labs. Used with responsibility.**

</div>
