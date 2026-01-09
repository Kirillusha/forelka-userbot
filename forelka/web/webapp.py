import json
import os
import time
import secrets
import asyncio
from dataclasses import dataclass
from typing import Dict, Optional

from flask import Flask, redirect, render_template_string, request
from pyrogram import Client
from pyrogram.errors import (
    BadRequest,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
    PasswordHashInvalid,
)


APP_TITLE = "Forelka • Telegram Web Login"
STATE_TTL_SECONDS = 10 * 60


@dataclass
class LoginState:
    token: str
    created_at: float
    api_id: int
    api_hash: str
    phone: str
    session_name: str
    phone_code_hash: str


_states: Dict[str, LoginState] = {}
_clients: Dict[str, Client] = {}

def _ensure_event_loop():
    """
    Pyrogram (и Python 3.12+) требует event loop в текущем потоке.
    Flask dev-server часто обрабатывает запросы в Thread-*, где loop не задан.
    """
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


def _cleanup():
    now = time.time()
    expired = [k for k, v in _states.items() if (now - v.created_at) > STATE_TTL_SECONDS]
    for token in expired:
        _states.pop(token, None)
        c = _clients.pop(token, None)
        try:
            if c:
                c.disconnect()
        except Exception:
            pass


def _api_file_for_user(user_id: int) -> str:
    return f"telegram_api-{user_id}.json"


def _save_api(user_id: int, api_id: int, api_hash: str) -> None:
    path = _api_file_for_user(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"api_id": api_id, "api_hash": api_hash}, f, indent=2)


def _rename_session(temp_name: str, user_id: int) -> str:
    src = f"{temp_name}.session"
    dst = f"forelka-{user_id}.session"
    if not os.path.exists(src):
        raise FileNotFoundError(f"Session file not found: {src}")
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)
    return dst


INDEX_HTML = """
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title }}</title>
    <style>
      :root { color-scheme: dark; }
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0b0f17; color: #e7eefc; }
      .wrap { max-width: 820px; margin: 0 auto; padding: 32px 16px; }
      .card { background: #111a2b; border: 1px solid #1f2b44; border-radius: 16px; padding: 20px; }
      h1 { margin: 0 0 8px; font-size: 22px; }
      p { margin: 0 0 14px; color: #b7c7e6; line-height: 1.45; }
      label { display: block; margin: 10px 0 6px; color: #cfe0ff; font-weight: 600; }
      input { width: 100%; box-sizing: border-box; border-radius: 12px; border: 1px solid #263656; background: #0b1220; color: #e7eefc; padding: 12px 12px; }
      button { margin-top: 14px; border: 0; border-radius: 12px; background: #4b7bff; color: white; padding: 12px 14px; font-weight: 700; cursor: pointer; }
      button:hover { filter: brightness(1.05); }
      .err { background: #2a1520; border: 1px solid #5a2136; color: #ffd6e6; padding: 12px; border-radius: 12px; margin: 12px 0; }
      .ok { background: #13251c; border: 1px solid #254c36; color: #d9ffe9; padding: 12px; border-radius: 12px; margin: 12px 0; }
      .muted { color: #98acd3; font-size: 13px; }
      code { background: #0b1220; border: 1px solid #263656; padding: 2px 6px; border-radius: 8px; }
      .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      @media (max-width: 640px) { .row { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>Forelka Autefication</h1>
        <p>Этот сайт создан для аутентификации сессии<code>forelka-&lt;id&gt;.session</code>, которую потом использует ваш юзербот.</p>
        <p class="muted">API ID / API HASH берутся в <code>my.telegram.org</code>. Они нужны один раз</p>

        {% if error %}<div class="err"><b>Ошибка:</b> {{ error }}</div>{% endif %}

        <form method="post" action="/start">
          <div class="row">
            <div>
              <label>API ID</label>
              <input name="api_id" inputmode="numeric" placeholder="123456" required />
            </div>
            <div>
              <label>API HASH</label>
              <input name="api_hash" placeholder="0123456789abcdef..." required />
            </div>
          </div>
          <label>Телефон</label>
          <input name="phone" inputmode="tel" placeholder="+79991234567" required />
          <button type="submit">Отправить код</button>
        </form>
      </div>
    </div>
  </body>
</html>
"""


CODE_HTML = """
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title }}</title>
    <style>
      :root { color-scheme: dark; }
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0b0f17; color: #e7eefc; }
      .wrap { max-width: 820px; margin: 0 auto; padding: 32px 16px; }
      .card { background: #111a2b; border: 1px solid #1f2b44; border-radius: 16px; padding: 20px; }
      label { display: block; margin: 10px 0 6px; color: #cfe0ff; font-weight: 600; }
      input { width: 100%; box-sizing: border-box; border-radius: 12px; border: 1px solid #263656; background: #0b1220; color: #e7eefc; padding: 12px 12px; }
      button { margin-top: 14px; border: 0; border-radius: 12px; background: #4b7bff; color: white; padding: 12px 14px; font-weight: 700; cursor: pointer; }
      .err { background: #2a1520; border: 1px solid #5a2136; color: #ffd6e6; padding: 12px; border-radius: 12px; margin: 12px 0; }
      p { margin: 0 0 14px; color: #b7c7e6; line-height: 1.45; }
      code { background: #0b1220; border: 1px solid #263656; padding: 2px 6px; border-radius: 8px; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>Введите код</h1>
        <p>Код отправлен на номер <code>{{ phone }}</code>. Если включена 2FA — после кода попросим пароль.</p>

        {% if error %}<div class="err"><b>Ошибка:</b> {{ error }}</div>{% endif %}

        <form method="post" action="/verify-code">
          <input type="hidden" name="token" value="{{ token }}" />
          <label>Код из Telegram</label>
          <input name="code" inputmode="numeric" placeholder="12345" required />
          <button type="submit">Подтвердить</button>
        </form>
      </div>
    </div>
  </body>
</html>
"""


PASSWORD_HTML = """
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title }}</title>
    <style>
      :root { color-scheme: dark; }
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0b0f17; color: #e7eefc; }
      .wrap { max-width: 820px; margin: 0 auto; padding: 32px 16px; }
      .card { background: #111a2b; border: 1px solid #1f2b44; border-radius: 16px; padding: 20px; }
      label { display: block; margin: 10px 0 6px; color: #cfe0ff; font-weight: 600; }
      input { width: 100%; box-sizing: border-box; border-radius: 12px; border: 1px solid #263656; background: #0b1220; color: #e7eefc; padding: 12px 12px; }
      button { margin-top: 14px; border: 0; border-radius: 12px; background: #4b7bff; color: white; padding: 12px 14px; font-weight: 700; cursor: pointer; }
      .err { background: #2a1520; border: 1px solid #5a2136; color: #ffd6e6; padding: 12px; border-radius: 12px; margin: 12px 0; }
      p { margin: 0 0 14px; color: #b7c7e6; line-height: 1.45; }
      code { background: #0b1220; border: 1px solid #263656; padding: 2px 6px; border-radius: 8px; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>2FA пароль</h1>
        <p>Для аккаунта включена облачная парольная защита (2FA). Введите пароль, чтобы завершить авторизацию.</p>
        {% if error %}<div class="err"><b>Ошибка:</b> {{ error }}</div>{% endif %}
        <form method="post" action="/verify-password">
          <input type="hidden" name="token" value="{{ token }}" />
          <label>Пароль</label>
          <input name="password" type="password" required />
          <button type="submit">Завершить вход</button>
        </form>
      </div>
    </div>
  </body>
</html>
"""


SUCCESS_HTML = """
<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{{ title }}</title>
    <style>
      :root { color-scheme: dark; }
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0b0f17; color: #e7eefc; }
      .wrap { max-width: 820px; margin: 0 auto; padding: 32px 16px; }
      .card { background: #111a2b; border: 1px solid #1f2b44; border-radius: 16px; padding: 20px; }
      .ok { background: #13251c; border: 1px solid #254c36; color: #d9ffe9; padding: 12px; border-radius: 12px; margin: 12px 0; }
      code { background: #0b1220; border: 1px solid #263656; padding: 2px 6px; border-radius: 8px; }
      p { margin: 0 0 14px; color: #b7c7e6; line-height: 1.45; }
      a { color: #9db7ff; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>Готово</h1>
        <div class="ok"><b>Сессия создана:</b> <code>{{ session_file }}</code></div>
        <p><b>Следующий шаг:</b> Ваш юзербот уже запущен,если понадобится вновь запустить его введите: <code>python main.py</code>.</p>
        <p class="muted">API данные сохранены в <code>{{ api_file }}</code>, чтобы запуск мог восстановить клиент при необходимости.</p>
        <p><a href="/">Создать ещё одну сессию</a></p>
      </div>
    </div>
  </body>
</html>
"""


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        _cleanup()
        return render_template_string(INDEX_HTML, title=APP_TITLE, error=request.args.get("error"))

    @app.post("/start")
    def start():
        _cleanup()
        _ensure_event_loop()
        try:
            api_id = int(request.form.get("api_id", "").strip())
            api_hash = request.form.get("api_hash", "").strip()
            phone = request.form.get("phone", "").strip()
            if not api_hash or not phone:
                raise ValueError("Заполните все поля.")
        except Exception:
            return redirect("/?error=" + "Неверные данные (api_id/api_hash/phone).")

        token = secrets.token_urlsafe(24)
        session_name = f"temp-web-{token}"

        client = Client(session_name, api_id=api_id, api_hash=api_hash)
        try:
            client.connect()
            sent = client.send_code(phone)
        except PhoneNumberInvalid:
            try:
                client.disconnect()
            except Exception:
                pass
            return redirect("/?error=" + "Неверный номер телефона.")
        except BadRequest as e:
            try:
                client.disconnect()
            except Exception:
                pass
            return redirect("/?error=" + f"Telegram API error: {type(e).__name__}")

        state = LoginState(
            token=token,
            created_at=time.time(),
            api_id=api_id,
            api_hash=api_hash,
            phone=phone,
            session_name=session_name,
            phone_code_hash=sent.phone_code_hash,
        )
        _states[token] = state
        _clients[token] = client

        return render_template_string(CODE_HTML, title=APP_TITLE, token=token, phone=phone, error=None)

    def _get_state_and_client(token: str) -> tuple[Optional[LoginState], Optional[Client]]:
        _cleanup()
        st = _states.get(token)
        c = _clients.get(token)
        if not st or not c:
            return None, None
        return st, c

    @app.post("/verify-code")
    def verify_code():
        _ensure_event_loop()
        token = (request.form.get("token") or "").strip()
        code = (request.form.get("code") or "").strip().replace(" ", "")
        st, c = _get_state_and_client(token)
        if not st or not c:
            return redirect("/?error=" + "Сессия входа истекла, начните заново.")

        try:
            c.sign_in(phone_number=st.phone, phone_code_hash=st.phone_code_hash, phone_code=code)
        except SessionPasswordNeeded:
            return render_template_string(PASSWORD_HTML, title=APP_TITLE, token=token, error=None)
        except PhoneCodeInvalid:
            return render_template_string(CODE_HTML, title=APP_TITLE, token=token, phone=st.phone, error="Неверный код.")
        except PhoneCodeExpired:
            return redirect("/?error=" + "Код истёк, начните заново.")
        except BadRequest as e:
            return render_template_string(CODE_HTML, title=APP_TITLE, token=token, phone=st.phone, error=f"Telegram API error: {type(e).__name__}")

        return _finalize_login(token, st, c)

    @app.post("/verify-password")
    def verify_password():
        _ensure_event_loop()
        token = (request.form.get("token") or "").strip()
        password = request.form.get("password") or ""
        st, c = _get_state_and_client(token)
        if not st or not c:
            return redirect("/?error=" + "Сессия входа истекла, начните заново.")

        try:
            c.check_password(password=password)
        except PasswordHashInvalid:
            return render_template_string(PASSWORD_HTML, title=APP_TITLE, token=token, error="Неверный пароль.")
        except BadRequest as e:
            return render_template_string(PASSWORD_HTML, title=APP_TITLE, token=token, error=f"Telegram API error: {type(e).__name__}")

        return _finalize_login(token, st, c)

    def _finalize_login(token: str, st: LoginState, c: Client):
        try:
            me = c.get_me()
            user_id = int(me.id)
            _save_api(user_id, st.api_id, st.api_hash)
            session_file = _rename_session(st.session_name, user_id)
        finally:
            try:
                c.disconnect()
            except Exception:
                pass
            _states.pop(token, None)
            _clients.pop(token, None)

        return render_template_string(
            SUCCESS_HTML,
            title=APP_TITLE,
            session_file=session_file,
            api_file=_api_file_for_user(user_id),
        )

    return app


if __name__ == "__main__":
    host = os.environ.get("FORELKA_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("FORELKA_WEB_PORT", "8000"))
    app = create_app()
    # Важно: threaded=False чтобы один и тот же Pyrogram Client не прыгал между потоками
    # между шагами (код / 2FA), иначе будут ошибки event loop / thread safety.
    app.run(host=host, port=port, debug=False, threaded=False)


