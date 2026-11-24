"""A story-independent tabletop sheet and a pool of identical fair dice."""
from math import comb

import engine as E


def default_sheet(seat):
    return {"name": seat["name"], "hp": 10, "maxHp": 10, "energy": 3, "maxEnergy": 3, "power": 0}


def view(table):
    data = table.get("freeplay", {})
    sheets = data.get("sheets", {})
    return {"sheets": {sid: sheets.get(sid, default_sheet(seat)) for sid, seat in table["seats"].items()},
            "rolls": data.get("rolls", [])}


def chance(count, sides, modifier, target):
    # Count tuples with sum strictly below the target using bounded stars and bars.
    k = target - modifier - 1 - count
    if k < 0:
        return 100
    if k >= count * (sides - 1):
        return 0
    missed = sum((-1)**j * comb(count, j) * comb(k - j*sides + count, count)
                 for j in range(min(count, k // sides) + 1))
    outcomes = sides**count
    return 100 * (outcomes - missed) / outcomes


def bounded(body, key, lo, hi):
    return type(body.get(key)) is int and lo <= body[key] <= hi


def act(table, sid, body):
    if type(body.get("rev")) is not int or body["rev"] != table["rev"]:
        return E.fail(table, "Положение изменилось. Сверьтесь с планшетом и повторите.")
    if body["op"] == "freeSheet":
        name = body.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 32 or not name.strip().isprintable():
            return E.fail(table, "Введите имя персонажа длиной от 1 до 32 знаков.")
        limits = (("maxHp", 0, 9999), ("maxEnergy", 0, 9999), ("power", -999, 999))
        if (not all(bounded(body, *field) for field in limits)
                or not bounded(body, "hp", 0, body["maxHp"]) or not bounded(body, "energy", 0, body["maxEnergy"])):
            return E.fail(table, "Проверьте показатели и их пределы.")
        sheet = {key: body[key] for key in ("hp", "maxHp", "energy", "maxEnergy", "power")}
        sheet["name"] = name.strip()
        table.setdefault("freeplay", {}).setdefault("sheets", {})[sid] = sheet
        E.log(table, sid, "hero", f"{sheet['name']} · здоровье {sheet['hp']}/{sheet['maxHp']}, "
              f"энергия {sheet['energy']}/{sheet['maxEnergy']}, мощь {sheet['power']}.")
    else:
        if (not bounded(body, "count", 1, 10) or type(body.get("sides")) is not int
                or body["sides"] not in (4, 6, 8, 10, 12, 20, 100) or not bounded(body, "modifier", -100, 100)
                or not bounded(body, "target", -100, 1100)):
            return E.fail(table, "Проверьте формулу броска и порог.")
        count, sides, mod, target = (body[k] for k in ("count", "sides", "modifier", "target"))
        faces = body.get("faces")
        if "faces" in body and (not isinstance(faces, list) or len(faces) != count
                                 or not all(type(n) is int and 1 <= n <= sides for n in faces)):
            return E.fail(table, "Введите по одной допустимой грани на каждый кубик.")
        if faces is None:
            faces = [table["rng"].randint(1, sides) for _ in range(count)]
        total = sum(faces) + mod
        formula = f"{count}d{sides}" + (f"{mod:+}" if mod else "")
        row = {"player": table["seats"][sid]["name"], "formula": formula, "faces": faces, "target": target,
               "total": total, "chance": chance(count, sides, mod, target), "success": total >= target,
               "source": "table" if "faces" in body else "site"}
        data = table.setdefault("freeplay", {})
        data["rolls"] = (data.get("rolls", []) + [row])[-100:]
        E.log(table, sid, "roll", f"{formula} · {faces} → {total}, порог {target}.")
    return {"ok": True}
