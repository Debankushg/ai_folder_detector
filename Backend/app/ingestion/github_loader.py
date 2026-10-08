"""Clone a public GitHub repository (shallow)."""
import re
import shutil
import subprocess
from pathlib import Path

GITHUB_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(?:\.git)?/?$")


def clone_github(url: str, dest: Path) -> Path:
    url = url.strip()
    if not GITHUB_RE.match(url):
        raise ValueError("Only https://github.com/<owner>/<repo> URLs are supported.")
    target = dest / "repo"
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", "--", url, str(target)],
            check=True, capture_output=True, timeout=120,
            env={"GIT_TERMINAL_PROMPT": "0", "PATH": "/usr/bin:/bin:/usr/local/bin"},
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(f"git clone failed: {e.stderr.decode(errors='ignore')[:300]}")
    except subprocess.TimeoutExpired:
        raise ValueError("git clone timed out.")
    shutil.rmtree(target / ".git", ignore_errors=True)
    return target
