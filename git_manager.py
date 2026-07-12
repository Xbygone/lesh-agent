import subprocess

def run_git_command(command, workspace_path):
    """Git komutunu verilen çalışma dizininde çalıştırır."""
    try:
        result = subprocess.run(
            command,
            cwd=workspace_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}

def get_current_branch(workspace_path):
    """Mevcut branch adını döndürür."""
    res = run_git_command(["git", "branch", "--show-current"], workspace_path)
    if res["success"]:
        return res["output"].strip()
    return "unknown"

def get_diff(workspace_path):
    """Kaydedilmemiş değişikliklerin diff'ini döndürür."""
    res = run_git_command(["git", "diff"], workspace_path)
    if res["success"]:
        return res["output"]
    return ""

def is_git_repo(workspace_path):
    """Klasörün bir git reposu olup olmadığını kontrol eder."""
    res = run_git_command(["git", "rev-parse", "--is-inside-work-tree"], workspace_path)
    return res["success"]

def commit_and_push(workspace_path, commit_message):
    """Değişiklikleri add, commit ve push yapar, terminal logunu döndürür."""
    log = ""
    branch = get_current_branch(workspace_path)
    if branch == "unknown":
        return False, "Git reposu değil veya branch bulunamadı."
    
    # git add .
    add_res = run_git_command(["git", "add", "."], workspace_path)
    log += f"> git add .\n{add_res['output']}{add_res['error']}\n"
    
    # git commit
    commit_res = run_git_command(["git", "commit", "-m", commit_message], workspace_path)
    log += f"> git commit -m \"{commit_message}\"\n{commit_res['output']}{commit_res['error']}\n"
    
    if "nothing to commit" in commit_res['output'] or "working tree clean" in commit_res['output']:
        return True, log + "\n[INFO] Gönderilecek değişiklik bulunamadı."
        
    # git push
    push_res = run_git_command(["git", "push", "origin", branch], workspace_path)
    log += f"> git push origin {branch}\n{push_res['output']}{push_res['error']}\n"
    
    return push_res["success"], log
