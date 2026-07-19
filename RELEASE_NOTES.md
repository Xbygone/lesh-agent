# Lesh Agent v1.5.1 — Security & Rewrite Release

> v1.5.1 supersedes v1.5.0: it fixes a packaging issue (missing bundled dependencies in the exe) and completes the full English localization of the app.

## 🌍 Fully English

The entire interface, agent prompts, logs and documentation are now in English. The agent replies in whatever language you write in.

## 🛡️ Security (Critical)

- Removed all embedded secrets (Supabase URL/key, Fernet encryption key) from the source code. The app now runs **100% locally by default**; API keys are encrypted with a per-machine key generated on first run and stored under `~/.lesh/`.
- Passwords are **never written to disk** anymore; auto-login now uses Supabase refresh tokens.
- Fixed a path traversal vulnerability (`startswith` replaced with `realpath` + `commonpath`; sibling-prefix folders and symlink escapes are now blocked).
- Every terminal command the agent wants to run now goes through a **user approval dialog** (with an optional auto-approve switch). Obviously destructive commands are always blocked.
- Added timeouts and output limits to terminal commands.
- Git history has been fully scrubbed of leaked credentials.

## 🐛 Bug Fixes

- Fixed the packaged exe crashing on startup (`ModuleNotFoundError: customtkinter`) — builds now run in a clean, dedicated virtual environment with all dependencies bundled.
- Added missing dependencies (`duckduckgo-search`, `beautifulsoup4`) that prevented the app from starting from source.
- Fixed a pip recursion bug that made the packaged exe relaunch itself on startup.
- Auto-updater no longer runs when launched from source (it could overwrite your git working tree). It now only runs in the packaged exe.
- Fixed UI freezes caused by a network request on every keystroke; API keys are now saved on focus loss.
- Fixed "Software Office" mode wiping the chat history.
- Migrated GitHub Models to the new endpoint (`models.github.ai/inference`) with publisher-prefixed model IDs — the old endpoint was deprecated.
- Fixed a phantom widget reference, grid overlaps, and the status label rendering on top of the model card.
- Corrected Ollama model names (e.g. `phi4-mini`) and refreshed all model catalogs (Gemini 2.5, current Groq models).
- Commit & Push now always uses your GitHub PAT instead of whichever provider key happened to be selected.

## ✨ New UI

- Interface rebuilt from scratch: overlap-free responsive layout, tabbed Diff/Log inspector, colorized git diff (+/-), live status indicators.
- **Stop** button while the agent is running, one-click **New Chat**, Enter / Shift+Enter support.
- Command approval dialog and an "Auto-approve commands" switch.
- You/Agent badges in the chat stream, highlighted `<think>` reasoning and tool calls.

## ⚠️ Upgrade Notes

- API keys saved by older versions were encrypted with a compromised shared key and are now invalid — please re-enter your keys once.
- Supabase cloud sync is optional; you can connect your own instance via `.env` (see `.env.example`).
