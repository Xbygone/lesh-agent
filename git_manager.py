"""Git helpers: diff, branch info and one-click commit & push."""

import subprocess
import urllib.parse


def run_git_command(command, workspace_path, timeout=15):
    """Runs a git command in the given working directory with a timeout."""
    try:
        result = subprocess.run(
            command,
            cwd=workspace_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
        )
        return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": f"Command timed out (>{timeout}s)."}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


def get_current_branch(workspace_path):
    """Returns the current branch name."""
    res = run_git_command(["git", "branch", "--show-current"], workspace_path)
    if res["success"]:
        return res["output"].strip()
    return "unknown"


def get_diff(workspace_path):
    """Returns the diff of uncommitted changes."""
    res = run_git_command(["git", "diff"], workspace_path)
    if res["success"]:
        out = res["output"]
        if len(out) > 50000:
            return out[:50000] + "\n\n... (diff too large, truncated)"
        return out
    return ""


def is_git_repo(workspace_path):
    """Checks whether the folder is a git repository."""
    res = run_git_command(["git", "rev-parse", "--is-inside-work-tree"], workspace_path)
    return res["success"]


def get_remote_url(workspace_path):
    res = run_git_command(["git", "config", "--get", "remote.origin.url"], workspace_path)
    if res["success"]:
        return res["output"].strip()
    return ""


def commit_and_push(workspace_path, commit_message, pat_token=None):
    """Adds, commits and pushes changes; returns (success, terminal log)."""
    log = ""
    branch = get_current_branch(workspace_path)
    if branch == "unknown":
        return False, "Not a git repository, or no branch found."

    # git add .
    add_res = run_git_command(["git", "add", "."], workspace_path)
    log += f"> git add .\n{add_res['output']}{add_res['error']}\n"

    # git commit
    commit_res = run_git_command(["git", "commit", "-m", commit_message], workspace_path)
    log += f"> git commit -m \"{commit_message}\"\n{commit_res['output']}{commit_res['error']}\n"

    if "nothing to commit" in commit_res["output"] or "working tree clean" in commit_res["output"]:
        return True, log + "\n[INFO] No changes to push."

    # Push command preparation
    remote_url = get_remote_url(workspace_path)
    push_command = ["git", "push", "origin", branch]

    if pat_token and remote_url.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(remote_url)
            netloc = f"{pat_token}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            secure_url = parsed._replace(netloc=netloc).geturl()
            push_command = ["git", "push", secure_url, branch]
            log += f"> git push https://<TOKEN_HIDDEN>@{parsed.hostname}{parsed.path} {branch}\n"
        except Exception:
            log += f"> git push origin {branch}\n"
    else:
        log += f"> git push origin {branch}\n"

    push_res = run_git_command(push_command, workspace_path, timeout=30)

    # Security: mask the token if it appears in error output
    error_output = push_res["error"]
    if pat_token and pat_token in error_output:
        error_output = error_output.replace(pat_token, "<TOKEN_HIDDEN>")

    log += f"{push_res['output']}{error_output}\n"

    return push_res["success"], log
