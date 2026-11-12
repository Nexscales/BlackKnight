<p align="center">
    <img width="271" height="116" alt="Screenshot_22" src="https://github.com/user-attachments/assets/252d6536-5a1e-4b2d-8d55-8cfd8d949874" />
</p>
desktop not good working sorry (i am fixing)

# ☠️ BlackKnight

> Autonomous offensive-security agent for isolated lab environments.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-2.0.0-brightgreen.svg)](https://github.com/Nexscales/BlackKnight/releases)

BlackKnight is a modular, terminal-based autonomous agent designed for **authorized security testing** inside sandboxed lab environments. It combines a planner, sub-agent orchestration, a command sandbox, and persistent memory to carry out multi-step security workflows with minimal human intervention.

---

## ⚠️ Legal Disclaimer

BlackKnight is intended **exclusively** for use in isolated, self-owned, or explicitly authorized environments (CTFs, home labs, training ranges, bug-bounty scopes with written permission).

**Do not** use this tool against systems you do not own or have explicit permission to test. Unauthorized use may violate local and international laws. The author assumes **no liability** for misuse or damage caused by this software.

---


## 📑 Table of Contents

- [Features](#-features)
- [Demo](#-demo)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Modes](#-modes)
- [CLI Reference](#-cli-reference)
- [Slash Commands](#-slash-commands)
- [Project Structure](#-project-structure)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## ☠️ Features

- 🧠 **Planner** — decomposes high-level goals into executable steps.
- 🤖 **Sub-agent orchestration** — specialized agents per task (recon, exploit, report, etc.).
- 🔒 **Sandboxed execution** — commands run in an isolated workspace (`sandbox/`).
- 💾 **Persistent memory** — retains context and prior findings across sessions.
- 🎛️ **Multiple run modes** — interactive chat, step-by-step agent, full auto, and dev.
- 🖥️ **Terminal UI** — rich CLI experience with slash commands.
- 📝 **Structured logging** — plans, logs, and memory stored in dedicated directories.

---

## 🎬 Demo

> _Screenshot / GIF placeholder — add an image here to show BlackKnight in action._

$ python main.py --mode auto --goal "enumerate open services on 10.10.10.5"
text
<img width="1528" height="978" alt="Screenshot_23" src="https://github.com/user-attachments/assets/7bcc5b16-92ab-4de2-aa5e-81d0528e10d9" />
<img width="1109" height="376" alt="Screenshot_26" src="https://github.com/user-attachments/assets/95001118-13ef-4bf2-9235-d41162c5e1db" />


---

## 🧩 Requirements

- **Python** 3.10 or newer
- **pip** (or `uv` / `poetry`)
- OS: Linux, macOS, or Windows (WSL recommended for Windows)

---

## ☠️ Installation

```bash
# 1. Clone the repository
git clone https://github.com/Nexscales/BlackKnight.git
cd BlackKnight

# 2. (Optional) Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example environment file
cp .env.example .env
cp agents.example.json agents.json

# 5. Edit .env and agents.json with your keys and agent profiles

Windows quick start:
bat

run.bat

Use diag.bat to run environment diagnostics.
⚙️ Configuration

BlackKnight is configured through two files:
File	Purpose
.env	API keys, model selection, runtime flags
agents.json	Sub-agent profiles and capabilities

Both files are git-ignored — never commit them. Use the provided .example templates as a starting point.
Key environment variables
Variable	Description
LLM_API_KEY	API key for the backing LLM provider
LLM_MODEL	Model identifier
SANDBOX_DIR	Path to the sandbox workspace
LOG_LEVEL	Logging verbosity (INFO, DEBUG, etc.)

    See .env.example for the full list.

🕹️ Usage
bash

python main.py --mode <mode> [options]

Example
bash

python main.py --mode agent --goal "scan 10.10.10.0/24 and summarize findings"
```
🎭 Modes
Mode	Description
chat	Interactive conversational mode
agent	Step-by-step agent with confirmation prompts
auto	Fully autonomous execution of a goal
dev	Developer mode with verbose output and debugging tools
📇 CLI Reference
Flag	Description
--mode	Run mode (chat, agent, auto, dev)
--goal	High-level objective to pursue
--config	Path to a custom config file
--no-sandbox	⚠️ Disable sandbox (lab use only)
--verbose	Enable verbose logging
⌨️ Slash Commands

Available inside interactive modes:
Command	Description
/help	Show available commands
/plan	Display the current plan
/memory	Inspect persistent memory
/logs	Show recent execution logs
/agents	List registered sub-agents
/reset	Reset the current session
/exit	Quit BlackKnight
📂 Project Structure
text

BlackKnight/
├── main.py              # Entry point
├── config.py            # Configuration loader
├── planner.py           # Task planner
├── agents.py            # Sub-agent orchestration
├── sandbox.py           # Command sandbox
├── memory/              # Persistent memory (git-ignored)
├── logs/                # Execution logs (git-ignored)
├── plans/               # Generated plans (git-ignored)
├── sandbox/             # Isolated workspace (git-ignored)
├── requirements.txt
├── .env.example
├── agents.example.json
├── run.bat / diag.bat
└── LICENSE

🗺️ Roadmap

    Plugin API for third-party sub-agents

    Web UI for plan inspection
    
    Exportable HTML/PDF reports
    
    Multi-target parallel execution

🤝 Contributing

Contributions are welcome! Please:

    Fork the repository.

    Create a feature branch (git checkout -b feature/my-feature).

    Commit your changes (git commit -m "Add my feature").

    Push the branch (git push origin feature/my-feature).

    Open a Pull Request.

For major changes, please open an issue first to discuss what you'd like to change.
📄 License

Distributed under the MIT License. See LICENSE for details.
<p align="center"> <sub>Built for the lab, not for the wild. ⚔️</sub> </p> ```
