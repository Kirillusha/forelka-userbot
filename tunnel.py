import os
import re
import shutil
import stat
import subprocess
import sys
import urllib.request


CLOUDFLARED_DIR = os.path.join(os.path.dirname(__file__), ".bin")
CLOUDFLARED_PATH = os.path.join(CLOUDFLARED_DIR, "cloudflared")


def _download_cloudflared_linux_amd64(dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    with urllib.request.urlopen(url, timeout=60) as r, open(dst, "wb") as f:
        f.write(r.read())
    st = os.stat(dst)
    os.chmod(dst, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def ensure_cloudflared() -> str:
    if shutil.which("cloudflared"):
        return "cloudflared"
    if not os.path.exists(CLOUDFLARED_PATH):
        print("cloudflared не найден — скачиваю бинарник (linux-amd64)...")
        _download_cloudflared_linux_amd64(CLOUDFLARED_PATH)
    return CLOUDFLARED_PATH


def run_quick_tunnel(local_url: str) -> int:
    """
    Запускает trycloudflare quick tunnel.
    Команда живёт, пока вы её не остановите (Ctrl+C).
    """
    exe = ensure_cloudflared()
    cmd = [exe, "tunnel", "--url", local_url, "--no-autoupdate"]
    print("Запускаю туннель:", " ".join(cmd))
    print("Ожидайте URL вида https://....trycloudflare.com")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url_re = re.compile(r"(https://[a-zA-Z0-9-]+\.trycloudflare\.com)")
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            m = url_re.search(line)
            if m:
                print("\nВаш публичный URL:", m.group(1))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            return proc.wait(timeout=10)
        except Exception:
            return 1


if __name__ == "__main__":
    host = os.environ.get("FORELKA_WEB_HOST", "127.0.0.1")
    port = os.environ.get("FORELKA_WEB_PORT", "8000")
    code = run_quick_tunnel(f"http://{host}:{port}")
    raise SystemExit(code)

