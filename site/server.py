"""Start a shared Море имён table on a trusted home network. Python 3.10+."""
import argparse
import hashlib
import http.cookies
import json
import mimetypes
import os
import re
import secrets
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import engine as E
import service

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATIC = HERE / "static"
PACK = ROOT / "Море имён"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Problem(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class GameServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, db):
        self.db = str(db)
        self.secure = os.getenv("TABLE_HTTPS") == "1"
        self.ai_key = os.getenv("OPENAI_API_KEY")
        self.local_model = os.getenv("OLLAMA_MODEL")
        self.ai_lock = threading.BoundedSemaphore(2)
        self.lan_addresses = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")]
        self.rate_lock = threading.Lock()
        self.recent = {}
        with self.transaction(False) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS rooms(code TEXT PRIMARY KEY, data TEXT NOT NULL)")
        super().__init__(address, Handler)

    @contextmanager
    def transaction(self, write):
        conn = sqlite3.connect(self.db, timeout=10, isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def limit(self, key, max_calls, seconds):
        with self.rate_lock:
            now = time.monotonic()
            if len(self.recent) > 512:
                self.recent = {k: v for k, v in self.recent.items() if v[0] > now}
            until, count = self.recent.get(key, (0, 0))
            if until <= now:
                until, count = now + seconds, 0
            if count >= max_calls:
                raise Problem(429, "Слишком много запросов. Подождите немного и повторите.")
            self.recent[key] = (until, count + 1)

    def answer(self, table, question):
        fallback = service.narration(table, question)
        if not (self.ai_key or self.local_model):
            return "Сказитель", fallback
        if not self.ai_lock.acquire(blocking=False):
            raise Problem(429, "Ведущий отвечает другому игроку. Повторите вопрос через несколько секунд.")
        try:
            prompt = E.prompt_for(table, question) + "\nОткрытая страница: " + service.narration(table, "зачитай") + "\nПравило или подсказка: " + fallback
            if service.story.visible(table)["meeting"]:
                prompt += "\nВстреча в пути: " + service.narration(table, "встреча")
            if self.local_model:
                url = "http://127.0.0.1:11434/api/generate"
                body = {"model": self.local_model, "prompt": prompt, "stream": False}
                headers = {}
            else:
                url = "https://api.openai.com/v1/responses"
                body = {"model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), "input": prompt, "store": False}
                headers = {"Authorization": "Bearer " + self.ai_key}
            req = urllib.request.Request(url, encode(body), {"Content-Type": "application/json", **headers})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read(1_000_000))
            if self.local_model:
                answer = data.get("response", "")
            else:
                answer = "\n".join(part["text"] for msg in data.get("output", [])
                                   for part in msg.get("content", []) if part.get("type") == "output_text")
            if not answer.strip():
                raise ValueError("empty response")
            return "ИИ-ведущий", answer.strip()[:3000]
        except (OSError, ValueError, KeyError, TypeError):
            return "Сказитель", "Модель сейчас недоступна. " + fallback
        finally:
            self.ai_lock.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "MoreImen/1"

    def setup(self):
        super().setup()
        self.connection.settimeout(12)

    def log_message(self, pattern, *args):
        pass  # Neither room invitations nor names belong in the console.

    def reply(self, status, data, content="application/json; charset=utf-8", cookie=None):
        if isinstance(data, dict) and data.get("state") and self.server.server_address[0] == "0.0.0.0" and self.server.lan_addresses:
            if urlsplit("//" + self.headers.get("Host", "")).hostname in ("localhost", "127.0.0.1"):
                data["state"]["inviteOrigin"] = f"http://{self.server.lan_addresses[0]}:{self.server.server_port}"
        payload = encode(data) if not isinstance(data, bytes) else data
        self.send_response(status)
        self.send_header("Content-Type", content)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "private, no-store" if content.startswith(("application/json", "text/html")) else "public, max-age=3600")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if cookie:
            self.send_header("Set-Cookie", f"more_table={cookie}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000" + ("; Secure" if self.server.secure else ""))
        self.end_headers()
        self.wfile.write(payload)

    def cookie(self):
        jar = http.cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except http.cookies.CookieError:
            return "", ""
        value = jar["more_table"].value if "more_table" in jar else ""
        code, _, token = value.partition(".")
        return code, digest(token) if token else ""

    def room(self, conn):
        code, identity = self.cookie()
        row = conn.execute("SELECT data FROM rooms WHERE code=?", (code,)).fetchone()
        if row and identity:
            table = E.restore(json.loads(row[0]))
            sid = E.find_seat(table, identity)
            if sid:
                table["model"] = bool(self.server.ai_key or self.server.local_model)
                return table, sid
        raise Problem(401, "Войдите по коду или откройте новый стол.")

    def save(self, conn, table):
        conn.execute("UPDATE rooms SET data=? WHERE code=?", (encode(E.serial(table)), table["code"]))

    def create_or_join(self, path, body):
        name = body.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > 24:
            raise Problem(400, "Введите имя длиной от 1 до 24 знаков.")
        self.server.limit((path, self.client_address[0]), 30 if path.endswith("join") else 12, 300)
        token = secrets.token_urlsafe(32)
        with self.server.transaction(True) as conn:
            if path == "/api/create":
                table = E.new_table()
                table["code"] = "".join(secrets.choice(ALPHABET) for _ in range(12))
                conn.execute("INSERT INTO rooms VALUES (?,?)", (table["code"], "{}"))
            else:
                code = str(body.get("code", "")).strip().upper()
                row = conn.execute("SELECT data FROM rooms WHERE code=?", (code,)).fetchone()
                if not row:
                    raise Problem(404, "Стол с таким кодом не найден. Сверьте код с приглашением.")
                table = E.restore(json.loads(row[0]))
                existing, identity = self.cookie()
                known = E.find_seat(table, identity) if existing == code else None
                if known:
                    return {"state": service.snapshot(table, known)}, None
            sid = E.create_seat(table, name, digest(token))
            if path.endswith("create"):
                table["host"] = sid
            table["model"] = bool(self.server.ai_key or self.server.local_model)
            self.save(conn, table)
        return {"state": service.snapshot(table, sid)}, table["code"] + "." + token

    def route(self):
        url = urlsplit(self.path)
        path = url.path
        if self.command == "GET":
            if path == "/api/lobby":
                return self.reply(200, E.compendium(None))
            if path in ("/api/book", "/api/state"):
                with self.server.transaction(False) as conn:
                    table, sid = self.room(conn)
                    same = parse_qs(url.query).get("since") == [str(table["rev"])]
                    value = E.compendium(table) if path.endswith("book") else {"state": None if same else service.snapshot(table, sid)}
                return self.reply(200, value)
            file = None
            if path in ("/", "/index.html"):
                file = STATIC / "index.html"
            elif path == "/rules.pdf":
                file = PACK / "01 Правила.pdf"
            elif path == "/static/frame.js":
                file = HERE / "frame.js"
            elif re.fullmatch(r"/static/(?:[\w-]+/)*[\w.-]+", path, re.ASCII):
                candidate = (STATIC / path[8:]).resolve()
                if candidate.is_relative_to(STATIC) and not any(s.startswith(".") for s in candidate.relative_to(STATIC).parts):
                    file = candidate
            elif match := re.fullmatch(r"/figures/([HMBKV]\d{2,3})\.stl", path, re.ASCII):
                ref = match[1]
                group = {"H": "объёмные герои", "M": "объёмные существа", "B": "объёмные боссы"}.get(ref[0], "местность")
                file = PACK / "3D" / group / (ref + ".stl")
            if not file or not file.is_file():
                raise Problem(404, "Страница не найдена.")
            return self.reply(200, file.read_bytes(), mimetypes.guess_type(str(file))[0] or "application/octet-stream")
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            raise Problem(403, "Откройте сам игровой стол для этого действия.")
        if self.headers.get_content_type() != "application/json":
            raise Problem(415, "Ожидается JSON.")
        length = int(self.headers.get("Content-Length", "0"))
        if not 1 <= length <= 5000:
            raise Problem(413, "Слишком большой запрос.")
        body = json.loads(self.rfile.read(length))
        if not isinstance(body, dict):
            raise Problem(400, "Некорректная команда.")
        if path in ("/api/create", "/api/join"):
            value, cookie = self.create_or_join(path, body)
            return self.reply(200, value, cookie=cookie)
        if path not in ("/api/action", "/api/gm"):
            raise Problem(404, "Действие не найдено.")
        if path.endswith("gm"):
            with self.server.transaction(False) as conn:
                table, sid = self.room(conn)
                question = body.get("question")
                if not isinstance(question, str) or not 1 <= len(question.strip()) <= 500:
                    raise Problem(400, "Введите вопрос до 500 знаков.")
                self.server.limit(("gm", table["code"]), 12, 60)
                source_rev = table["rev"]
            author, answer = self.server.answer(table, question)
        with self.server.transaction(True) as conn:
            table, sid = self.room(conn)
            if path.endswith("gm"):
                if table["rev"] != source_rev:
                    raise Problem(409, "Пока ведущий отвечал, стол изменился. Задайте вопрос ещё раз.")
                E.log(table, sid, "question", question.strip())
                E.log(table, "table", "gm", author + ". " + answer)
            else:
                result = service.act(table, sid, body)
                if not result["ok"]:
                    raise Problem(409, result["error"])
            self.save(conn, table)
        return self.reply(200, {"state": service.snapshot(table, sid)})

    def dispatch(self):
        try:
            self.route()
        except Problem as exc:
            self.reply(exc.status, {"error": str(exc)})
        except PermissionError as exc:
            self.reply(403, {"error": str(exc)})
        except (ValueError, TypeError, KeyError, IndexError):
            self.reply(400, {"error": "Некорректные данные. Обновите страницу и проверьте поля."})
        except sqlite3.OperationalError:
            self.reply(503, {"error": "Хранилище временно недоступно. Повторите действие."})
        except (ConnectionError, TimeoutError):
            pass

    do_GET = do_POST = dispatch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--db", type=Path, default=HERE / "data" / "rooms.sqlite3")
    args = ap.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    server = GameServer((args.bind, args.port), args.db)
    local = f"http://127.0.0.1:{server.server_port}/"
    print("Открыть на компьютере:", local, flush=True)
    if args.bind == "0.0.0.0":
        for address in sorted(set(socket.gethostbyname_ex(socket.gethostname())[2])):
            if not address.startswith("127."):
                print("За одним Wi-Fi откройте на телефоне:", f"http://{address}:{server.server_port}/", flush=True)
    if args.open:
        webbrowser.open(local)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
