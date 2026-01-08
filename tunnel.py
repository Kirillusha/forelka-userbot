import os
import re
import shutil
import subprocess
import sys


def ensure_ssh() -> str:
    exe = shutil.which("ssh")
    if not exe:
        raise RuntimeError("ssh не найден. Установите OpenSSH (например в Termux: pkg install openssh).")
    return exe


def run_quick_tunnel(local_url: str) -> int:
    """
    Запускает туннель через localhost.run (SSH reverse tunnel).
    Команда живёт, пока вы её не остановите (Ctrl+C).
    """
    ssh = ensure_ssh()
    # local_url вида http://127.0.0.1:8000
    # ssh -R 80:localhost:8000 localhost.run
    try:
        host_port = local_url.split("://", 1)[1]
        host, port_s = host_port.split(":", 1)
        port = int(port_s)
    except Exception:
        raise RuntimeError(f"Bad local_url: {local_url}")

    subdomain = os.environ.get("FORELKA_LHR_SUBDOMAIN", "").strip()
    # На localhost.run поддерживается -R <remote_port>:<local_host>:<local_port>
    # и опционально -o RequestTTY=yes, чтобы сервис показывал ссылку в stdout.
    # Если задан subdomain, обычно используют host вида <sub>.localhost.run
    remote_host = f"{subdomain}.localhost.run" if subdomain else "localhost.run"

    cmd = [
        ssh,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ServerAliveInterval=30",
        "-R",
        f"80:{host}:{port}",
        remote_host,
    ]
    print("Запускаю туннель:", " ".join(cmd))
    print("Ожидайте URL вида https://....localhost.run (иногда домен lhr.life)")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url_re = re.compile(r"(https?://[a-zA-Z0-9.-]+\.(?:localhost\.run|lhr\.life))")
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

