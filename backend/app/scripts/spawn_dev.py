import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from time import sleep


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _start_backend(root: Path) -> subprocess.Popen:
    backend_dir = root / "backend"
    python_exe = backend_dir / "venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        raise RuntimeError(f"backend venv not found: {python_exe}")

    logs_dir = backend_dir / ".dev"
    _ensure_dir(logs_dir)
    out = open(logs_dir / "backend.log", "a", encoding="utf-8")
    err = open(logs_dir / "backend.err.log", "a", encoding="utf-8")

    args = [
        str(python_exe),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    return subprocess.Popen(
        args,
        cwd=str(backend_dir),
        stdout=out,
        stderr=err,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )


def _start_frontend(root: Path) -> subprocess.Popen:
    frontend_dir = root / "frontend"
    logs_dir = frontend_dir / ".dev"
    _ensure_dir(logs_dir)
    out = open(logs_dir / "frontend.log", "a", encoding="utf-8")
    err = open(logs_dir / "frontend.err.log", "a", encoding="utf-8")

    vite_bin = frontend_dir / "node_modules" / "vite" / "bin" / "vite.js"
    if vite_bin.exists():
        node_cmd = "node.exe" if os.name == "nt" else "node"
        args = [node_cmd, str(vite_bin), "--host", "127.0.0.1", "--port", "5173"]
    else:
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        args = [npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"]
    return subprocess.Popen(
        args,
        cwd=str(frontend_dir),
        stdout=out,
        stderr=err,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )


def main() -> None:
    root = _repo_root()
    meta_dir = root / ".dev"
    _ensure_dir(meta_dir)

    backend = _start_backend(root)
    frontend = _start_frontend(root)

    sleep(1)
    listen = {}
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, encoding="utf-8", errors="replace")
        for line in out.splitlines():
            line = line.strip()
            if not line.startswith("TCP"):
                continue
            parts = [p for p in line.split(" ") if p]
            if len(parts) < 5:
                continue
            local = parts[1]
            state = parts[3]
            pid_str = parts[4]
            if state != "LISTENING":
                continue
            if local.endswith(":8000"):
                listen["backend_listen_pid"] = int(pid_str)
            if local.endswith(":5173"):
                listen["frontend_listen_pid"] = int(pid_str)
    except Exception:
        listen = {}

    payload = {
        "started_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "backend_pid": backend.pid,
        "frontend_pid": frontend.pid,
        **listen,
    }
    (meta_dir / "pids.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
