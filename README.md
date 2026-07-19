<p align="center">
  <img src="assets/logo.jpg" width="250" alt="Lesh Logo">
</p>

# Lesh - Local Agent Coder

Lesh is an advanced, autonomous AI coding agent designed to run primarily locally, ensuring total privacy and control over your data. With its powerful self-updating mechanism and elegant Material Design 3 interface, Lesh streamlines your coding workflow and acts as your personalized AI pair programmer.

## Features

- 💬 **Persistent Chat Sessions**: Your past chat sessions are automatically saved in the `.lesh/sessions/` directory. You can easily access, review, and continue from any past chat using the sidebar.
- ⚡ **Auto-Updating System**: The packaged app checks for new versions via the GitHub API, downloads the zip payload, replaces the old files and restarts itself. (Disabled when running from source to protect your git working tree.)
- 🤖 **Multi-LLM Capabilities**:
  - **Local (Ollama)**: True privacy. Supports `qwen2.5-coder`, `deepseek-r1` and more.
  - **Cloud Providers**: GitHub Models (`models.github.ai`), Google AI Studio (Gemini), Groq Cloud and NVIDIA Build via your own API keys.
  - **Oto-Pilot**: Routes easy tasks to the local model and hard ones to the cloud automatically.
  - **Yazılım Ofisi**: 5-expert cross-provider consensus pipeline for complex tasks.
- 🛡️ **Command Approval**: Every terminal command the agent wants to run is shown to you in an approval dialog first (optional auto-approve switch). File operations are sandboxed to the selected workspace.
- 🔐 **Key Storage**: 100% local by default — API keys are encrypted with a per-machine key and stored in `~/.lesh/`. Optional Supabase cloud sync (bring your own instance via `.env`) with Row Level Security. Passwords are never written to disk; sessions restore via refresh tokens.
- 📁 **Workspace Management**: Bind a folder to the agent. It will read files, execute commands, run code, and git commit & push with one click.
- 📦 **One-Dir Architecture**: Packaged as a single directory executable (`--onedir`), keeping it completely open-source and transparent for you to inspect and modify.

## Quick Start

1. Download the latest `lesh-agent.zip` (Lesh Agent) from the [Releases](../../releases) tab.
2. Extract the folder to a desired location on your computer.
3. Run `lesh-agent.exe`.
4. Click **Select Workspace** to bind a project folder.
5. (Optional) Enter your API tokens for cloud providers or select `Yerel (Ollama)` to run completely locally.
6. Start coding!

## Developer Setup

If you want to run the python code directly or build the application yourself:

```bash
git clone https://github.com/Xbygone/lesh-agent.git
cd lesh-agent
pip install -r requirements.txt
python main.py
```

Optional cloud sync / release settings live in `.env` (see `.env.example`). Without a `.env` the app runs fully local.

### Tests

```bash
python smoke_test.py
```

### Auto-Release

To create a new release executable and push it to GitHub (reads `GITHUB_TOKEN` from `.env`):
```bash
python release.py 1.5.0
```

This will update the internal version, build with PyInstaller, zip the dist folder, create/update the GitHub release and upload the payload.

## Security Notes

- The agent can only read/write files inside the workspace you select (realpath + commonpath sandbox).
- Terminal commands require your explicit approval unless you enable auto-approve; obviously destructive commands are always blocked.
- No secrets ship inside the source or binary. Credentials are encrypted at rest with a per-machine key (`~/.lesh/.keyfile`).

## License

Open Source. Developed with 💙 by the Lesh Community.
