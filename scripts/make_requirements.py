"""Write requirements.txt (direct dependencies pinned to what is installed here) and
requirements.lock.txt (everything installed, for exact local reproduction).

requirements.txt is what CI and Docker install: it has no Windows-only packages, so it works on Linux.
"""
import subprocess
import sys
from importlib import metadata
from pathlib import Path

DIRECT = ["chromadb", "fastembed", "rank_bm25", "sqlglot", "mcp", "requests", "python-dotenv",
          "fastapi", "uvicorn", "httpx", "pytest", "pytest-cov"]

lines, missing = [], []
for name in DIRECT:
    try:
        lines.append(f"{name}=={metadata.version(name)}")
    except metadata.PackageNotFoundError:
        missing.append(name)
if missing:
    sys.exit(f"Not installed: {', '.join(missing)}. Run: pip install {' '.join(missing)}")

Path("requirements.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
frozen = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True).stdout
Path("requirements.lock.txt").write_text(frozen, encoding="utf-8")
print(f"requirements.txt: {len(lines)} direct packages; requirements.lock.txt: {len(frozen.splitlines())} packages")
print("\n".join(lines))