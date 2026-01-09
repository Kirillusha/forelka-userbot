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


def _is_public_tunnel_url(url: str) -> bool:
    # Отсекаем служебные ссылки, которые localhost.run печатает в приветствии
    if "admin.localhost.run" in url:
        return False
    if "localhost.run/docs" in url:
        return False
    if "twitter.com/localhost_run" in url:
        return False
    return True


def run_quick_tunnel(local_url: str) -> int:
    """
    Запускает туннель через localhost.run (SSH reverse tunnel).
    Команда живёт, пока вы её не остановите (Ctrl+C).
    """
    # Важно: когда stdout не TTY (например его читает main.py через PIPE),
    # Python может буферить print(). Делаем line-buffering.
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass

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
    lhr_user = os.environ.get("FORELKA_LHR_USER", "").strip()  # например: nokey
    # На localhost.run поддерживается -R <remote_port>:<local_host>:<local_port>
    # и опционально -o RequestTTY=yes, чтобы сервис показывал ссылку в stdout.
    # Если задан subdomain, обычно используют host вида <sub>.localhost.run
    # Сначала пробуем "free tunnel without key" через nokey@localhost.run
    # (если сервис это поддерживает). Если пользователь явно указал FORELKA_LHR_USER —
    # используем его.
    base_host = f"{subdomain}.localhost.run" if subdomain else "localhost.run"
    candidates = []
    if lhr_user:
        candidates.append(f"{lhr_user}@{base_host}")
    else:
        candidates.extend([f"nokey@{base_host}", base_host])

    url_re = re.compile(r"(https?://[a-zA-Z0-9.-]+\.(?:localhost\.run|lhr\.life))")

    last_output = ""
    quiet = os.environ.get("FORELKA_TUNNEL_QUIET", "").strip() in ("1", "true", "yes", "on")
    for remote in candidates:
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
            remote,
        ]
        if not quiet:
            print("Запускаю туннель:", " ".join(cmd), flush=True)
            print("Ожидайте URL вида https://....localhost.run (иногда домен lhr.life)", flush=True)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                last_output = (last_output + line)[-8000:]
                if not quiet:
                    sys.stdout.write(line)
                m = url_re.search(line)
                if m:
                    url = m.group(1)
                    if _is_public_tunnel_url(url):
                        print("Ваш публичный URL:", url, flush=True)
        except KeyboardInterrupt:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                return proc.wait(timeout=10)
            except Exception:
                return 1

        # Если процесс завершился сразу — пробуем следующий кандидат
        rc = proc.poll()
        if rc is not None:
            if "Permission denied" in last_output or "publickey" in last_output:
                print("\nlocalhost.run требует ключ. Пробую другой режим...\n", flush=True)
                continue
            return rc

        # Если не завершился — значит туннель поднят (живёт пока не остановят)
        try:
            return proc.wait()
        finally:
            try:
                proc.terminate()
            except Exception:
                pass

    raise RuntimeError(
        "Не удалось поднять localhost.run туннель без ключа.\n"
        "Варианты:\n"
        "- Попробуйте установить/создать SSH ключ и настроить доступ в admin.localhost.run\n"
        "- Или задайте FORELKA_LHR_USER=nokey (если сервис поддерживает)\n"
    )


if __name__ == "__main__":
    host = os.environ.get("FORELKA_WEB_HOST", "127.0.0.1")
    port = os.environ.get("FORELKA_WEB_PORT", "8000")
    code = run_quick_tunnel(f"http://{host}:{port}")
    raise SystemExit(code)

