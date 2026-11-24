"""Authenticated, revision-bound saves of the board and its paper-table photograph."""
import base64
import binascii
import json
import zlib
from datetime import datetime, timezone

import engine as E


MAX_PHOTO = 192 * 1024
PROGRESS = ("party", "heroes", "scene", "story", "log", "fundedSeats", "freeplay")
HOLD = "Стол на паузе или встреча завершена. Создатель может продолжить игру."


def status(table):
    return table.get("sessionStatus", "active")


def summary(table):
    return {"status": status(table), "points": [row["meta"] for row in reversed(table.get("checkpoints", []))]}


def validate_photo(value):
    if not isinstance(value, str) or len(value) > 4 * ((MAX_PHOTO + 2) // 3):
        raise ValueError("Фотография превышает 192 КиБ.")
    if not value:
        return
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("Не удалось прочитать фотографию.") from None
    if len(data) <= MAX_PHOTO and data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9"):
        pos, dimensions = 2, False
        while pos + 4 < len(data) and data[pos] == 255:
            marker = data[pos + 1]
            size = int.from_bytes(data[pos+2:pos+4], "big")
            if size < 2 or pos + 2 + size > len(data):
                break
            if marker in (192, 193, 194) and size >= 11:
                dims = [int.from_bytes(data[i:i+2], "big") for i in (pos+5, pos+7)]
                dimensions = all(0 < n <= 1600 for n in dims)
            if marker == 218:
                if dimensions and pos + 2 + size < len(data) - 2:
                    return
                break
            pos += size + 2
    raise ValueError("Для поля нужна фотография JPEG до 1600 пикселей.")


def capture(table, sid, kind, note="", photo=""):
    progress = {key: table[key] for key in PROGRESS if key in table}
    raw = json.dumps(progress, ensure_ascii=False, separators=(",", ":")).encode()
    stamp = E.campaign_stamp(table, sid, table["seats"][sid]["heroId"])
    scene = table.get("scene") or {}
    if table.get("mode") == "free":
        sheet = (table.get("freeplay", {}).get("sheets", {}).get(sid) or {})
        stamp.update(chapter=None, day=None, realm="", hero=sheet.get("name", stamp["player"]))
        scene = {"title": table.get("title") or "Свободный стол"}
    history = table.setdefault("checkpoints", [])
    history.append({"meta": {"id": history[-1]["meta"]["id"] + 1 if history else 1,
                             "author": stamp["player"], "hero": stamp["hero"], "day": stamp["day"],
                             "chapter": stamp["chapter"], "realm": stamp["realm"], "kind": kind,
                             "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "title": scene.get("title") or "Карта берегов", "round": scene.get("round"),
                             "note": note, "hasPhoto": bool(photo), "revision": table["rev"]},
                    "snapshot": base64.b64encode(zlib.compress(raw)).decode("ascii"), "photo": photo})


def apply(table, sid, body):
    if sid not in table["seats"]:
        raise PermissionError("Сначала войдите за стол.")
    op = body.get("op")
    if op not in ("save", "pause", "finish", "resume", "restore", "photo"):
        raise ValueError("Неизвестное действие с сохранением.")
    if op not in ("save", "photo") and sid != table.get("host"):
        raise PermissionError("Встречей управляет создатель стола.")
    point = None
    if op in ("photo", "restore"):
        pid = body.get("id")
        point = next((r for r in table.get("checkpoints", []) if type(pid) is int and r["meta"]["id"] == pid), None)
        if not point:
            raise ValueError("Этого сохранения нет у данного стола.")
    if op == "photo":
        if not point["meta"]["hasPhoto"]:
            raise ValueError("К сохранению не прикрепили фотографию.")
        return {"photo": point["photo"]}
    if type(body.get("rev")) is not int or body["rev"] != table["rev"]:
        raise ValueError("Стол изменился. Сверьте прогресс и подтвердите сохранение ещё раз.")
    current = status(table)
    if ((op == "pause" and current != "active") or (op == "finish" and current == "finished")
            or (op == "resume" and current == "active")):
        raise ValueError("Состояние встречи уже изменилось.")
    if op in ("save", "pause", "finish"):
        note, photo = body.get("note", ""), body.get("photo", "")
        if not isinstance(note, str) or len(note) > 280:
            raise ValueError("Заметка должна помещаться в 280 знаков.")
        validate_photo(photo)
        capture(table, sid, op, note.strip(), photo)
    if op == "restore":
        saved = json.loads(zlib.decompress(base64.b64decode(point["snapshot"])))
        capture(table, sid, "before_restore", "Перед возвратом к сохранению №" + str(point["meta"]["id"]))
        for key in PROGRESS:
            if key in saved:
                table[key] = saved[key]
            else:
                table.pop(key, None)
        for seat in table["seats"].values():
            seat["heroId"] = None
        for hid, hero in table["heroes"].items():
            if hero["owner"] in table["seats"]:
                table["seats"][hero["owner"]]["heroId"] = hid
            else:
                hero["owner"] = None
    if op != "save":
        table["sessionStatus"] = {"pause": "paused", "restore": "paused", "resume": "active", "finish": "finished"}[op]
    verb = {"save": "Сохранён игровой прогресс.", "pause": "Игра поставлена на паузу.",
            "finish": "Игровая встреча завершена.", "resume": "Игра продолжена.",
            "restore": f"Восстановлено сохранение №{body.get('id')}. Проверьте расстановку поля."}[op]
    E.log(table, sid, "session", verb)
