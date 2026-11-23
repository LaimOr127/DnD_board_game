"""Invoke the shared table engine from the browser host's dedicated worker."""
import json
import re

import engine as E
import service


def handle(raw):
    req = json.loads(raw)
    path = req["path"]
    body = req.get("body") or {}
    token = req["token"]
    if not isinstance(body, dict) or not re.fullmatch(r"[a-f0-9]{64}", token):
        raise ValueError("Неверное удостоверение игрока.")
    if path in ("/api/create", "/api/join"):
        name = body.get("name", "")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 24:
            raise ValueError("Введите имя длиной от 1 до 24 знаков.")
    table = E.restore(req["saved"]) if req.get("saved") else E.new_table()
    sid = E.find_seat(table, token)
    before = table["rev"]
    if path == "/api/create" and req["local"] and not req.get("saved"):
        table["code"] = req["code"]
        sid = E.create_seat(table, name, token)
        table["host"] = sid
    elif path == "/api/join" and not sid:
        sid = E.create_seat(table, name, token)
    elif not sid:
        raise ValueError("Войдите по приглашению стола.")
    if sid == table["host"] and not req["local"]:
        raise ValueError("Вести стол можно только из вкладки создателя.")
    if bool(table.get("model")) != bool(req.get("model")):
        table["model"] = bool(req.get("model"))
        E.bump(table)
    if path in ("/api/gm", "/internal/prompt"):
        q = body.get("question")
        if not isinstance(q, str) or not q.strip() or len(q) > 500:
            raise ValueError("Введите вопрос, до 500 знаков.")
        answer = service.narration(table, q)
        if path == "/internal/prompt":
            scene = service.story.visible(table)
            party = table["party"]
            battlefield = table.get("scene") or {}
            facts = {
                "область": E.realms[party["realm"] - 1][0],
                "день": party["day"], "столкновение": battlefield.get("title"),
                "фигуры": [(t["name"], t.get("zone"), t.get("hp")) for t in battlefield.get("tokens", [])[:18]],
                "сцена": scene["text"][:1400], "вопрос сцены": scene["prompt"],
                "варианты": [c["label"] for c in scene["choices"]],
                "встреча в пути": scene["meeting"], "последние вести": scene["news"][-3:],
                "из книги": answer[:1100],
                "недавние события": [row["text"][:180] for row in table["log"][-3:]],
            }
            return json.dumps({"value": {"facts": facts, "rev": table["rev"]}, "saved": None}, ensure_ascii=False)
        if req.get("sourceRev") is not None and before != req["sourceRev"]:
            raise ValueError("Пока ведущий отвечал, ситуация изменилась. Задайте вопрос ещё раз.")
        E.log(table, sid, "question", q)
        E.log(table, "table", "gm", ("ИИ-ведущий. " + req["answer"]) if req.get("answer") else "Сказитель. " + answer)
    elif path == "/api/action":
        result = service.act(table, sid, body)
        if not result["ok"]:
            raise ValueError(result["error"])
    elif path not in ("/api/create", "/api/join", "/api/book", "/api/state"):
        raise ValueError("Неизвестное действие.")
    if path == "/api/book":
        value = E.compendium(table)
    elif path == "/api/state" and str(req.get("since")) == str(table["rev"]):
        value = {"state": None}
    else:
        value = {"state": service.snapshot(table, sid)}
    return json.dumps({"value": value, "saved": E.serial(table) if table["rev"] != before else None},
                      ensure_ascii=False, separators=(",", ":"))
