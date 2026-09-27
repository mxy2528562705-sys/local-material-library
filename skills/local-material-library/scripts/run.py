"""Bootstrap the library without installing packages into the user's Python."""
import os
from pathlib import Path
import subprocess
import sys
import venv
import hashlib


def main():
    if sys.version_info < (3, 10):
        raise SystemExit("Please install Python 3.10 or newer.")
    root = Path(__file__).resolve().parents[1]
    env = root / ".venv"
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    requirements = root / "requirements.txt"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = env / "requirements.sha256"
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(env)
    if not marker.exists() or marker.read_text() != digest:
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirements)], check=True)
        marker.write_text(digest)
    os.execv(str(python), [str(python), str(root / "scripts/library.py"), "serve", *sys.argv[1:]])


if __name__ == "__main__":
    main()
