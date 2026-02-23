import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> None:
    ports = [8000, 5173]
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, encoding="utf-8", errors="replace")
    except Exception:
        return

    pids: set[int] = set()
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
        for port in ports:
            if local.endswith(f":{port}"):
                try:
                    pids.add(int(pid_str))
                except Exception:
                    pass

    for pid in sorted(pids):
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False, capture_output=True, text=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
