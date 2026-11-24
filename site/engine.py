"""Table rules for Море имён. One 2d6 formula for the screen and the physical dice."""
from __future__ import annotations

import random
import re
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))

from foes import families, foes  # noqa: E402
from extras import local as local_cases  # noqa: E402
from field_guide import GUIDES  # noqa: E402
from card_lore import card_lore  # noqa: E402
from party import heroes as HERO_ROWS  # noqa: E402
from party import items as ITEM_ROWS  # noqa: E402
from party import schools  # noqa: E402
from world import acts, coords, edges, endings, realms, sea  # noqa: E402

MOBS, BOSSES = foes()
MOB_BY = {m["id"]: m for m in MOBS}
BOSS_BY = {b["id"]: b for b in BOSSES}
SCHOOL_COLOR = ["#487956", "#9b673c", "#745b89", "#a45440", "#397e8b", "#ac813e"]
STAT_NAME = {"might": "Мощь", "agility": "Ловкость", "will": "Воля"}
STAT_INDEX = {"might": 0, "agility": 1, "will": 2}
CONDITIONS = ["метка", "немота", "путы", "озноб", "надлом", "кровь"]
MEET = {
    "simple": {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3},
    "normal": {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6},
    "hard": {1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7},
}
ROAD = {
    1: "столкновение местной семьи",
    2: "встречный человек",
    3: "находка: +1 припас",
    4: "след портала",
    5: "плохая погода",
    6: "спокойная дорога",
}
ORACLE = {
    1: "нет, и осложнение",
    2: "нет, и осложнение",
    3: "нет",
    4: "да, но цена: 1 припас или 1 день",
    5: "да",
    6: "да",
}
LAYOUTS = {
    "bell": [(0.13, 0.72), (0.41, 0.72), (0.71, 0.70), (0.46, 0.30), (0.16, 0.28), (0.78, 0.30)],
    "dungeon": [(0.12, 0.52), (0.31, 0.52), (0.50, 0.77), (0.50, 0.29), (0.71, 0.52), (0.89, 0.52)],
    "siege": [(0.15, 0.53), (0.46, 0.53), (0.29, 0.78), (0.29, 0.27), (0.72, 0.76), (0.81, 0.30)],
}
SCENES = {
    "bell": {
        "title": "Колокол у брода",
        "zones": ["Площадь", "Мостки", "Звонница", "Отмель", "Амбар", "Лодка"],
        "links": [(1, 2), (2, 3), (2, 4), (1, 5), (5, 3), (4, 6), (6, 3)],
        "entry": 4,
        "note": "Герои в 1, Лада в 3, стража в 4. До конца третьего раунда: удержать коромысло, снять язык или уговорить Ладу.",
    },
    "dungeon": {
        "title": "Подземелье",
        "zones": ["Вход", "Развилка", "Архив", "Обвал", "Цистерна", "Затвор"],
        "links": [(1, 2), (2, 3), (2, 4), (3, 5), (4, 5), (5, 6)],
        "entry": 4,
        "note": "Улика в архиве, затвор в 6. Дверь 5–6 закрыта, пока не дёрнут рычаг или не собьют затвор.",
    },
    "siege": {
        "title": "Застава",
        "zones": ["Двор", "Ворота", "Бомбарда", "Катапульта", "Дорога", "Склон"],
        "links": [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (2, 5), (2, 6), (5, 6)],
        "entry": 5,
        "note": "Отряд в 1–4. Волны в 5 и 6 на раундах 1 и 3. Выдержать 4 раунда, ворота выше нуля.",
    },
}
EDGES = set()
for a, b in edges:
    EDGES.add((a, b))
    EDGES.add((b, a))
SEA = set(sea) | {(b, a) for a, b in sea}

# Witness choices sit beside the printed card. The label is the whole consequence.
FORKS = {
    "H01": ("Карта брата зашита в подкладку. У Трёх Ив её можно показать.",
            "Показать стежок: улика «стежок» и одно преимущество на поиск.",
            (("clue", "стежок"), ("boon", "adv", "Преимущество на один поиск")),
            "Промолчать: один раз щит 2 в начале сцены.",
            (("boon", "shield", "Щит 2 в начале одной сцены"),)),
    "H02": ("Дорога Лиора кончается в чужом море.",
            "Привить яблоню: 1 припас. Следующая плохая погода не съедает день.",
            (("supply", -1), ("flag", "skipWeather")),
            "Хранить память дороги: +1 к одной проверке.",
            (("boon", "plus", "+1 к одной своей проверке"),)),
    "H03": ("Один сапог Ильвы помнит море, другой — сушу.",
            "Шагнуть чешуёй: 1 припас и одно преимущество.",
            (("supply", -1), ("boon", "adv", "Преимущество на один бросок")),
            "Остаться на коже: щит 2 в начале одной сцены.",
            (("boon", "shield", "Щит 2 в начале одной сцены"),)),
    "H04": ("В обвалившейся штольне Бром узнал свой почерк.",
            "Прочитать дату вслух: +1 подозрение и улика «дата».",
            (("suspicion", 1), ("clue", "дата")),
            "Списать молча: +1 к одной проверке, без улики.",
            (("boon", "plus", "+1 к одной своей проверке"),)),
    "H05": ("Тора не выносит налога на слух.",
            "Отказать налогу: −1 слава здесь и +1 голос улицы.",
            (("glory", -1), ("street", 1)),
            "Заплатить 2 серебра и оставить щит 2 на одну сцену.",
            (("silver", -2), ("boon", "shield", "Щит 2 в начале одной сцены"))),
    "H06": ("Келл носит вторую каску пропавшей напарницы.",
            "Оставить каску в выработке: след портала этой области.",
            (("trace",),),
            "Не снимать каску: щит 2 в начале одной сцены.",
            (("boon", "shield", "Щит 2 в начале одной сцены"),)),
    "H07": ("Последнюю строку письма сестры Мара не показывает.",
            "Прочитать на отливе: улика «воск», +1 прилив, +2 ОЗ себе.",
            (("clue", "воск"), ("tide", 1), ("hp", 2)),
            "Спрятать письмо: +1 к одной проверке.",
            (("boon", "plus", "+1 к одной своей проверке"),)),
    "H08": ("Яса оставляет горький сон себе.",
            "Выпить горькое: снять с себя состояния и +1 ОЗ.",
            (("clear",), ("hp", 1)),
            "Продать сладкое: +2 серебра и −1 ОЗ.",
            (("silver", 2), ("hp", -1))),
    "H09": ("Веста зажигает свечу каждой забытой семье.",
            "Зажечь свечу: 1 припас и −1 подозрение.",
            (("supply", -1), ("suspicion", -1)),
            "Сберечь свечу: щит 2 в начале одной сцены.",
            (("boon", "shield", "Щит 2 в начале одной сцены"),)),
    "H10": ("Под застёжкой Ивара два герба.",
            "Показать второй герб: +1 припас и +1 подозрение.",
            (("supply", 1), ("suspicion", 1)),
            "Скрыть герб: щит 2 в начале одной сцены.",
            (("boon", "shield", "Щит 2 в начале одной сцены"),)),
    "H11": ("Рена должна поединок и забыла имя соперницы.",
            "Спросить имя: улика «поединок» и одно преимущество.",
            (("clue", "поединок"), ("boon", "adv", "Преимущество на один бросок")),
            "Не открывать приглашение: +1 к одной проверке.",
            (("boon", "plus", "+1 к одной своей проверке"),)),
    "H12": ("Знамя Оллена без названия части.",
            "Поднять знамя: один раз армия отменит фигуру без политической цены.",
            (("flag", "freeArmy"),),
            "Держать знамя свёрнутым: щит 2 в начале одной сцены.",
            (("boon", "shield", "Щит 2 в начале одной сцены"),)),
    "H13": ("Соль на ладони Нея тянется к западу.",
            "Пойти за солью: улика «соль» и одно преимущество.",
            (("clue", "соль"), ("boon", "adv", "Преимущество на один бросок")),
            "Спрятать соль: +1 к одной проверке.",
            (("boon", "plus", "+1 к одной своей проверке"),)),
    "H14": ("В зеркале Теи на одно пятно больше.",
            "Изучить пятно: 1 припас и улика «залы». Это не ключ портала.",
            (("supply", -1), ("clue", "залы")),
            "Закрыть зеркало: +1 к одной проверке.",
            (("boon", "plus", "+1 к одной своей проверке"),)),
    "H15": ("Один раз башенные часы сосчитали Эсса в ответ.",
            "Ответить часам: −1 искра. Можно услышать следующее забытое слово, не двигая раунд.",
            (("spark", -1), ("boon", "word", "Назвать следующее забытое слово")),
            "Промолчать: одно преимущество.",
            (("boon", "adv", "Преимущество на один бросок"),)),
    "H16": ("Гран хранит ключ, который не успел попросить.",
            "Отдать ключ воротам: один бесплатный ремонт на 2.",
            (("boon", "repair", "Бесплатный ремонт ворот на 2"),),
            "Оставить ключ: +1 к одной проверке.",
            (("boon", "plus", "+1 к одной своей проверке"),)),
    "H17": ("В паузе песни Урсы кто-то начал отзываться.",
            "Оставить паузу: +1 подозрение и улика «свидетель».",
            (("suspicion", 1), ("clue", "свидетель")),
            "Допеть список: +2 ОЗ себе.",
            (("hp", 2),)),
    "H18": ("Рох ищет на мосту доски, которые помнят его мать.",
            "Довериться доскам: один отход со сцены не считается поражением.",
            (("flag", "safeRetreat"),),
            "Выбрать крепкие доски: одно преимущество.",
            (("boon", "adv", "Преимущество на один бросок"),)),
}


def tier_of(level):
    return min(5, (int(level) + 1) // 2)


def max_hp(level, stock):
    return 8 + (tier_of(level) - 1) * 2 + (2 if stock else 0)


def max_sparks(spark):
    return 3 + (1 if spark else 0)


def clamp(n, lo, hi):
    return max(lo, min(hi, n))


def roman(n):
    return "I II III IV V".split()[n - 1]


def weapon_of(item):
    text = item["text"]
    if text.startswith("Мощь"):
        stat = "might"
    elif text.startswith("Ловкость"):
        stat = "agility"
    elif text.startswith("Воля"):
        stat = "will"
    else:
        stat = None
    reach = re.search(r"дальность (\d)", text)
    base = re.search(r"база (\d)", text)
    if stat is None:
        return None
    return {"stat": stat, "reach": int(reach.group(1)) if reach else 0, "base": int(base.group(1)) if base else 1}


def load_rules():
    raw = "\n".join((ROOT / "design" / filename).read_text(encoding="utf-8")
                    for filename in ("rules.md", "promises.md", "first-session.md", "offline.md"))
    chunks = re.split(r"(?m)^(?=# )", raw)
    out = []
    for chunk in chunks:
        lines = chunk.strip().splitlines()
        if not lines:
            continue
        out.append({"title": lines[0].lstrip("# ").strip(), "body": "\n".join(lines[1:]).strip()})
    return out


RULES = load_rules()
ITEMS = []
for i, row in enumerate(ITEM_ROWS):
    ITEMS.append({"id": f"I{i+1:02}", "name": row[0], "slot": row[1], "price": int(row[2]), "text": row[3]})
ITEM_BY = {it["id"]: it for it in ITEMS}


def hero_card(i, row):
    hid = f"H{i+1:02}"
    school = schools[i // 3]
    weapon = ITEMS[int(row[3]) - 1]
    prompt, a_label, _, b_label, _ = FORKS[hid]
    return {
        "id": hid,
        "name": row[0],
        "role": row[1],
        "school": school,
        "schoolIndex": i // 3,
        "color": SCHOOL_COLOR[i // 3],
        "might": int(row[2][0]),
        "agility": int(row[2][1]),
        "will": int(row[2][2]),
        "weaponId": weapon["id"],
        "technique": row[4],
        "talent": row[5],
        "story": row[6],
        "profile": card_lore(hid),
        "bond": row[7],
        "fork": {"prompt": prompt, "a": a_label, "b": b_label},
    }


HERO_CARDS = [hero_card(i, row) for i, row in enumerate(HERO_ROWS)]
HERO_BY = {h["id"]: h for h in HERO_CARDS}


def bestiary():
    mobs = [{
        "id": m["id"], "name": m["name"], "area": m["area"], "t": m["t"], "hp": m["hp"],
        "defense": m["defense"], "dmg": m["dmg"], "reach": m["reach"],
        "ability": m["ability"], "trait": m["trait"], "loss": m["loss"], "profile": card_lore(m["id"]),
    } for m in MOBS]
    bosses = [{
        "id": b["id"], "name": b["name"], "area": b["area"], "t": b["t"], "hp": b["hp"],
        "defense": b["defense"], "dmg": b["dmg"], "reach": b["reach"],
        "decree": b["decree"], "ability": b["ability"], "omen": b["omen"],
        "signal": b["signal"], "counter": b["counter"], "loss": b["loss"], "profile": card_lore(b["id"]),
    } for b in BOSSES]
    return mobs, bosses


BESTIARY_MOBS, BESTIARY_BOSSES = bestiary()
FAMILY_NAMES = [row[0] for row in families]


def blank_hero(hid):
    card = HERO_BY[hid]
    return {
        "owner": None, "hp": 8, "maxHp": 8, "sparks": 3, "maxSparks": 3, "shield": 0,
        "conditions": [], "fork": None, "boons": [], "weapon": card["weaponId"],
        "potions": ["I19"], "zone": None, "advantageNext": False, "plusNext": False,
        "pendingShield": 0, "ignoreNextHit": False, "capstoneReady": True, "guideReady": True,
        "growth": {"talent": False, "spark": False, "stock": False, "guide": False, "capstone": None},
        "pencil": "",
    }


def fresh_party():
    return {
        "level": 1, "seals": 0, "silver": 0, "supplies": 3, "tide": 0, "scars": 0,
        "suspicion": 0, "day": 0, "shards": 0, "debts": 0, "street": 0, "chapter": 1,
        "realm": 1, "glory": [0] * 10, "portals": ["unknown"] * 10, "clues": [],
        "opened": [1], "deeds": [], "shopClosed": None, "bitter": False, "dealt": False,
        "flags": [], "weatherDue": False, "fightDue": False, "lastRoad": None,
        "rested": False,
    }


def new_table():
    return {
        "rev": 1, "seq": 1, "seats": {}, "party": fresh_party(),
        "heroes": {h["id"]: blank_hero(h["id"]) for h in HERO_CARDS},
        "scene": None, "log": [], "model": False, "rng": random.SystemRandom(), "test_dice": False,
    }


def campaign_stamp(table, seat, hero=None):
    party = table["party"]
    return {"day": party["day"], "chapter": party["chapter"], "realm": realms[party["realm"] - 1][0],
            "player": table["seats"][seat]["name"], "hero": HERO_BY[hero]["name"] if hero else ""}


def bump(table):
    table["rev"] += 1


def log(table, seat, kind, text, dice=None):
    table["seq"] += 1
    name = table["seats"].get(seat, {}).get("name", "Стол")
    table["log"].append({"id": table["seq"], "seat": seat, "name": name, "kind": kind, "text": text, "dice": dice})
    if len(table["log"]) > 180:
        table["log"] = table["log"][-180:]
    bump(table)


def fail(table, message):
    return {"ok": False, "error": message, "rev": table["rev"]}


def party_n(table):
    return max(1, sum(1 for h in table["heroes"].values() if h["owner"]))


def claimed(table):
    return [hid for hid, h in table["heroes"].items() if h["owner"]]


def hid_of(table, hero):
    for hid, other in table["heroes"].items():
        if other is hero:
            return hid
    return None


def hero_token(table, hid):
    scene = table["scene"]
    if not scene or not hid:
        return None
    for token in scene["tokens"]:
        if token["kind"] == "hero" and token["ref"] == hid:
            return token
    return None


def mirror(table):
    for hid, hero in table["heroes"].items():
        token = hero_token(table, hid)
        if token:
            hero["hp"] = token["hp"]
            hero["shield"] = token["shield"]
            hero["zone"] = token["zone"]


def add_tide(table, n):
    notes = []
    party = table["party"]
    party["tide"] += n
    while party["tide"] >= 6:
        party["tide"] -= 6
        party["scars"] += 1
        party["shopClosed"] = party["realm"]
        if party["scars"] >= 3:
            party["bitter"] = True
        notes.append("Прилив дошёл до 6. Лавка этой области закрыта до конца следующей сцены, на карте шрам.")
        if party["bitter"]:
            notes.append("Три шрама: финал получит горькое послесловие. Играть дальше можно.")
    return notes


def apply_effects(table, hero, effects):
    party = table["party"]
    notes = []
    for effect in effects:
        kind = effect[0]
        if kind == "clue" and effect[1] not in party["clues"]:
            party["clues"].append(effect[1])
        elif kind == "silver":
            party["silver"] = max(0, party["silver"] + effect[1])
        elif kind == "supply":
            party["supplies"] = clamp(party["supplies"] + effect[1], 0, 6)
        elif kind == "suspicion":
            party["suspicion"] = clamp(party["suspicion"] + effect[1], 0, 4)
        elif kind == "tide":
            notes += add_tide(table, effect[1])
        elif kind == "glory":
            i = party["realm"] - 1
            party["glory"][i] = clamp(party["glory"][i] + effect[1], 0, 4)
        elif kind == "street":
            party["street"] += effect[1]
        elif kind == "hp":
            hero["hp"] = clamp(hero["hp"] + effect[1], 0 if effect[1] < 0 else 1, hero["maxHp"])
            if effect[1] < 0:
                hero["hp"] = clamp(hero["hp"], 1, hero["maxHp"])
        elif kind == "spark":
            hero["sparks"] = clamp(hero["sparks"] + effect[1], 0, hero["maxSparks"])
        elif kind == "trace":
            i = party["realm"] - 1
            if party["portals"][i] == "unknown":
                party["portals"][i] = "trace"
        elif kind == "clear":
            hero["conditions"] = []
        elif kind == "flag":
            if effect[1] not in party["flags"]:
                party["flags"].append(effect[1])
        elif kind == "boon":
            hero["boons"].append({"id": effect[1], "label": effect[2]})
    mirror_one(table, hero)
    return notes


def mirror_one(table, hero):
    hid = hid_of(table, hero)
    token = hero_token(table, hid)
    if token:
        token["hp"] = hero["hp"]
        token["maxHp"] = hero["maxHp"]


def graph(links):
    g = {i: set() for i in range(1, 7)}
    for a, b in links:
        g[a].add(b)
        g[b].add(a)
    return g


def shortest(g, start, goal):
    if start == goal:
        return [start]
    if start not in g or goal not in g:
        return None
    seen = {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        for nxt in sorted(g[node]):
            if nxt in seen:
                continue
            nxt_path = path + [nxt]
            if nxt == goal:
                return nxt_path
            seen.add(nxt)
            queue.append((nxt, nxt_path))
    return None


def living_heroes(scene):
    return [t for t in scene["tokens"] if t["kind"] == "hero" and t["hp"] > 0 and t["zone"]]


def d6s(table, n, forced, physical=False):
    if forced is not None:
        if not physical and not table.get("test_dice"):
            forced = None
        elif not isinstance(forced, list) or len(forced) != n or any(type(face) is not int or not 1 <= face <= 6 for face in forced):
            raise ValueError(f"Введите {n} значений от 1 до 6.")
    if forced is None:
        return [table["rng"].randint(1, 6) for _ in range(n)]
    return list(forced)


def split_dice(faces, mode):
    if len(faces) == 2:
        return list(faces), []
    indexed = list(enumerate(faces))
    ordered = sorted(indexed, key=lambda it: (it[1], it[0]))
    chosen = ordered[-2:] if mode == "advantage" else ordered[:2]
    chosen_i = {i for i, _ in chosen}
    kept = [face for i, face in indexed if i in chosen_i]
    dropped = [face for i, face in indexed if i not in chosen_i]
    return kept, dropped


def judge(total, pair, dc, combat):
    natural = sum(pair)
    if natural == 12:
        return "успех", "Чистые 12: успех и маленькое преимущество, +1 искра не выше максимума."
    if natural == 2:
        return "провал", "Чистые 2: провал."
    if dc is None:
        return "бросок", ""
    if total >= dc:
        return "успех", ""
    if combat:
        return "промах", "В бою любой недобор — промах."
    short = dc - total
    if short <= 2:
        return "цена", "Недобор 1–2 вне боя: откажитесь или примите успех с объявленной ценой."
    return "провал", "Недобор 3 и больше: провал с ценой."


def seat_hero(table, seat):
    hid = table["seats"][seat].get("heroId")
    if not hid:
        return None, None
    return hid, table["heroes"][hid]


def can_growth(level, growth, key):
    if key == "capstone":
        return level >= 10 and not growth["capstone"]
    pair = ("talent", "spark") if key in ("talent", "spark") else ("stock", "guide")
    other = pair[1] if key == pair[0] else pair[0]
    need = 2 if pair[0] == "talent" else 4
    second = 6 if pair[0] == "talent" else 8
    if growth[key] or level < need:
        return False
    if growth[other]:
        return level >= second
    return True


def offer_names(level, growth):
    keys = ["talent", "spark", "stock", "guide", "capstone"]
    return [key for key in keys if can_growth(level, growth, key)]


def realm_public(i, party):
    row = realms[i]
    opened = (i + 1) in party["opened"]
    deed = (i + 1) in party["deeds"]
    portal = party["portals"][i]
    data = {
        "id": i + 1, "name": row[0], "people": row[1], "capital": row[2], "village": row[3],
        "biome": row[4], "monarch": row[5], "npc": row[6], "want": row[7], "case": row[12],
        "x": coords[i][0], "y": coords[i][1], "families": FAMILY_NAMES[i * 3:(i + 1) * 3],
        "fieldGuide": GUIDES[i + 1],
        "glory": party["glory"][i], "portal": portal, "visited": opened, "deedOpen": deed,
    }
    if deed:
        data["dungeon"] = row[8]
        data["floors"] = local_cases[i][6].split(" / ")
        data["relic"] = row[9]
        data["pact"] = row[10]
        data["outcomes"] = row[13]
        data["reward"] = row[14]
    if portal != "unknown":
        data["portalHint"] = row[11]
    return data


def act_public(party):
    opened = []
    for i, act in enumerate(acts):
        if i + 1 <= party["chapter"]:
            opened.append({"n": i + 1, "title": act[0], "opening": act[1], "setup": act[2], "goal": act[3], "outcome": act[4], "coda": act[5]})
        else:
            opened.append({"n": i + 1, "title": act[0], "sealed": True})
    return opened


def compendium(table):
    party = table["party"] if table else fresh_party()
    ends = [{"title": e[0], "when": e[1], "text": e[2]} for e in endings] if party["chapter"] >= 5 else [{"title": e[0], "sealed": True} for e in endings]
    return {
        "title": "Море имён",
        "heroes": HERO_CARDS,
        "items": ITEMS,
        "realms": [realm_public(i, party) for i in range(10)],
        "edges": [list(pair) for pair in edges],
        "sea": [list(pair) for pair in sea],
        "acts": act_public(party),
        "endings": ends,
        "rules": RULES,
        "mobs": BESTIARY_MOBS,
        "bosses": BESTIARY_BOSSES,
        "roads": [{"n": n, "text": ROAD[n]} for n in range(1, 7)],
        "oracle": [{"n": n, "text": ORACLE[n]} for n in range(1, 7)],
    }


def public_hero(table, hid):
    hero = table["heroes"][hid]
    card = HERO_BY[hid]
    level = table["party"]["level"]
    owner = table["seats"].get(hero["owner"], {}) if hero["owner"] else {}
    return {
        "id": hid, "owner": hero["owner"], "ownerName": owner.get("name"),
        "hp": hero["hp"], "maxHp": hero["maxHp"], "sparks": hero["sparks"], "maxSparks": hero["maxSparks"],
        "shield": hero["shield"], "conditions": list(hero["conditions"]), "fork": hero["fork"],
        "boons": list(hero["boons"]), "weapon": hero["weapon"], "potions": list(hero["potions"]),
        "zone": hero["zone"], "advantageNext": hero["advantageNext"], "plusNext": hero["plusNext"],
        "pendingShield": hero["pendingShield"], "ignoreNextHit": hero["ignoreNextHit"],
        "capstoneReady": hero["capstoneReady"], "guideReady": hero["guideReady"],
        "growth": dict(hero["growth"]), "pencil": hero["pencil"],
        "tier": tier_of(level), "bonus": tier_of(level) - 1,
        "offers": offer_names(level, hero["growth"]),
        "color": card["color"],
    }


def view(table, seat):
    you = table["seats"][seat]
    scene = table["scene"]
    return {
        "rev": table["rev"], "code": table.get("code"),
        "you": {"id": seat, "name": you["name"], "heroId": you.get("heroId")},
        "seats": [{"id": s["id"], "name": s["name"], "heroId": s.get("heroId")} for s in table["seats"].values()],
        "party": table["party"],
        "heroes": {hid: public_hero(table, hid) for hid in table["heroes"]},
        "scene": scene,
        "log": table["log"][-80:],
        "model": bool(table.get("model")),
        "n": party_n(table),
    }


def serial(table):
    skip = {"rng", "test_dice"}
    data = {k: v for k, v in table.items() if k not in skip}
    return data


def restore(data):
    data["rng"] = random.SystemRandom()
    data["test_dice"] = False
    data.setdefault("model", False)
    scene = data.get("scene")
    if scene and scene["id"] == "bell" and (data.get("story") or {}).get("page") == "bell":
        scene.setdefault("storyBell", True)
    return data


def my_hero(table, seat):
    hid, hero = seat_hero(table, seat)
    if not hero:
        raise PermissionError("Сначала возьмите героя: лист откроется у вас.")
    return hid, hero


def do_roll(table, seat, action):
    kind = action.get("kind", "check")
    physical = action.get("source") == "table"
    forced = action.get("faces") if physical else action.get("dice")
    if physical and not forced:
        return fail(table, "Введите грани, выпавшие за столом.")
    if kind in ("road", "oracle"):
        faces = d6s(table, 1, forced, physical)
        table_name = ROAD if kind == "road" else ORACLE
        text = f"{'Дорога' if kind == 'road' else 'Вопрос да/нет'}: {faces[0]} — {table_name[faces[0]]}. Это один d6, не проверка 2d6."
        dice = {"faces": faces, "kept": faces, "dropped": [], "total": faces[0], "result": table_name[faces[0]], "formula": f"d6 = {faces[0]}"}
        dice["source"] = "table" if physical else "screen"
        log(table, seat, "dice", ("За столом. " if physical else "") + text, dice)
        return {"ok": True}
    hid, hero = my_hero(table, seat)
    card = HERO_BY[hid]
    level = table["party"]["level"]
    step = tier_of(level) - 1
    mode = action.get("mode", "flat")
    if mode not in ("flat", "advantage", "disadvantage"):
        return fail(table, "Неизвестный режим броска.")
    spend_spark = bool(action.get("spark"))
    if spend_spark and "немота" in hero["conditions"]:
        return fail(table, "Немота не позволяет тратить искры.")
    if spend_spark and hero["sparks"] < 1:
        return fail(table, "Искр нет.")
    stat_key = action.get("stat", "might")
    attack = kind == "attack"
    weapon = weapon_of(ITEM_BY[hero["weapon"]]) if attack else None
    if attack and weapon is None:
        weapon = {"stat": "might", "reach": 0, "base": 1}
    if attack:
        stat_key = weapon["stat"]
    if stat_key not in STAT_INDEX:
        return fail(table, "Нужна Мощь, Ловкость или Воля.")
    stat_value = [card["might"], card["agility"], card["will"]][STAT_INDEX[stat_key]]
    target = None
    if attack and action.get("target"):
        target = next((t for t in table["scene"]["tokens"] if t["id"] == action["target"]), None) if table["scene"] else None
        if target is None:
            return fail(table, "Цели на поле нет.")
        if target["hp"] <= 0:
            return fail(table, "Цель уже лежит.")
        token = hero_token(table, hid)
        if token and target.get("zone"):
            paths = graph(table["scene"]["links"])
            if table["scene"].get("door"):
                paths[5].discard(6)
                paths[6].discard(5)
            route = shortest(paths, token["zone"], target["zone"])
            if not route:
                return fail(table, "Цель находится за закрытым проходом.")
            dist = len(route) - 1
            if dist > weapon["reach"]:
                return fail(table, f"Дальность оружия {weapon['reach']}, до цели {dist}. Подойдите или смените оружие.")
    dc = action.get("dc")
    combat = bool(action.get("combat") or attack)
    if attack and target is not None:
        dc = target["defense"]
        combat = True
    first_hound_attack = target and target["ref"] == "M001" and not target.get("attacked")
    ready_advantage = hero["advantageNext"] or first_hound_attack
    if ready_advantage:
        mode = "flat" if mode == "disadvantage" else "advantage"
    adv_note = ("Помеха и преимущество погасили друг друга." if mode == "flat"
                else "Преимущество: 3d6, две лучшие.") if ready_advantage else ""
    faces = d6s(table, 3 if mode != "flat" else 2, forced, physical)
    if ready_advantage:
        hero["advantageNext"] = False
    if first_hound_attack:
        target["attacked"] = True
    kept, dropped = split_dice(faces, mode)
    plus = 1 if hero["plusNext"] else 0
    if plus:
        hero["plusNext"] = False
    spark_mod = 1 if spend_spark else 0
    if spend_spark:
        hero["sparks"] -= 1
    total = sum(kept) + stat_value + step + spark_mod + plus
    result, note = judge(total, kept, dc, combat)
    if sum(kept) == 12 and hero["sparks"] < hero["maxSparks"]:
        hero["sparks"] += 1
    bits = [f"{'3d6' if mode != 'flat' else '2d6'} ({'+'.join(map(str, kept))})"]
    if dropped:
        bits.append("отброшено " + "+".join(map(str, dropped)))
    bits.append(f"{STAT_NAME[stat_key]} {stat_value}")
    bits.append(f"ступень {step}")
    if spark_mod:
        bits.append("искра 1")
    if plus:
        bits.append("личный +1")
    formula = " + ".join(bits) + f" = {total}"
    if dc is not None:
        formula += f" против {dc}"
    damage = None
    if attack and result == "успех" and target is not None:
        damage = weapon["base"] + step
        hurt(target, damage, False)
        mirror(table)
    elif attack and result == "успех":
        damage = weapon["base"] + step
    text = formula
    if note:
        text += " " + note
    if adv_note:
        text += " " + adv_note
    if damage is not None:
        text += f" Урон {damage}: база {weapon['base']} + ступень {step}."
        if target is not None:
            text += f" У {target['name']} осталось {target['hp']}."
    label = action.get("label")
    if label:
        text = label + ". " + text
    dice = {
        "faces": faces, "kept": kept, "dropped": dropped, "total": total, "dc": dc,
        "result": result, "formula": formula, "damage": damage, "mode": mode,
    }
    dice["source"] = "table" if physical else "screen"
    log(table, seat, "dice", ("За столом. " if physical else "") + text, dice)
    return {"ok": True}


def hurt(token, amount, direct):
    amount = max(0, int(amount))
    if token.get("ignoreNextHit") and amount > 0:
        token["ignoreNextHit"] = False
        token["ignored"] = True
        return 0
    if not direct:
        use = min(token.get("shield", 0), amount)
        token["shield"] = token.get("shield", 0) - use
        amount -= use
    token["hp"] = max(0, token["hp"] - amount)
    return amount


def place_hero_token(table, hid, zone):
    hero = table["heroes"][hid]
    card = HERO_BY[hid]
    if hero["pendingShield"]:
        hero["shield"] = max(hero["shield"], hero["pendingShield"])
        hero["pendingShield"] = 0
    token = {
        "id": f"t{table['seq']}", "kind": "hero", "ref": hid, "name": card["name"],
        "zone": zone, "hp": hero["hp"], "maxHp": hero["maxHp"], "defense": 9,
        "shield": hero["shield"], "color": card["color"], "reach": 0, "tier": tier_of(table["party"]["level"]),
    }
    table["seq"] += 1
    hero["zone"] = zone
    hero["capstoneReady"] = True
    return token


def foe_token(table, card, zone, kind, hp, waiting=False):
    table["seq"] += 1
    return {
        "id": f"t{table['seq']}", "kind": kind, "ref": card["id"], "name": card["name"],
        "zone": zone if not waiting else 0, "hp": hp, "maxHp": hp, "defense": card["defense"],
        "dmg": card["dmg"], "reach": card["reach"], "tier": card["t"], "shield": 0,
        "waiting": waiting, "ability": card.get("ability", ""), "trait": card.get("trait", ""),
        "loss": card.get("loss", ""), "decree": card.get("decree", ""), "omen": card.get("omen", ""),
        "signal": card.get("signal", ""), "counter": card.get("counter", ""),
    }


def start_scene(table, seat, kind):
    if kind not in SCENES:
        return fail(table, "Такого поля нет.")
    if table["party"]["weatherDue"]:
        return fail(table, "Сначала решите погоду: припас или потерянный день.")
    spec = SCENES[kind]
    tokens = []
    heroes = claimed(table)
    if not heroes:
        return fail(table, "Никто ещё не взял героя.")
    zones = [1, 1, 1, 1, 1, 1] if kind == "bell" else ([1, 2, 3, 4, 1, 2] if kind == "siege" else [1] * 6)
    for i, hid in enumerate(heroes):
        table["heroes"][hid]["sparks"] = table["heroes"][hid]["maxSparks"]
        tokens.append(place_hero_token(table, hid, zones[i % len(zones)]))
    scene = {
        "id": kind, "title": spec["title"], "round": 1, "zones": spec["zones"], "links": spec["links"],
        "layout": LAYOUTS[kind], "entry": spec["entry"], "note": spec["note"], "tokens": tokens,
        "holds": 0, "door": kind == "dungeon", "goal": None,
        "gate": 3 + len(heroes) if kind == "siege" else None,
        "gateMax": 3 + len(heroes) if kind == "siege" else None,
        "words": ["дом", "мать", "я"] if kind == "bell" else [],
    }
    table["scene"] = scene
    if kind == "bell":
        tokens.append({
            "id": "lada", "kind": "npc", "ref": "lada", "name": "Лада", "zone": 3,
            "hp": 1, "maxHp": 1, "defense": 9, "shield": 0, "color": "#c6a15a",
        })
        spawn_cards(table, "M001", MEET["simple"][min(6, len(heroes))], 4, waiting=False)
        log(table, seat, "scene", "Колокол у брода. Лада не отпускает верёвку. Забытое слово этого раунда: дом. Что вы делаете?")
    elif kind == "dungeon":
        row = realms[table["party"]["realm"] - 1]
        log(table, seat, "scene", f"Вход в {row[8]}. Глубина ступени {roman(tier_of(table['party']['level']))}. Рычаг в архиве, затвор ещё закрыт.")
    else:
        log(table, seat, "scene", f"Застава. Ворота {scene['gate']}. Первая волна выходит на дорогу и склон, когда вы позовёте её.")
    table["party"]["shopClosed"] = None
    table["party"]["rested"] = False
    bump(table)
    return {"ok": True}


def spawn_cards(table, ref, count, zone, waiting=False, hp_each=None):
    kind = "boss" if ref.startswith("B") else "foe"
    card = BOSS_BY[ref] if kind == "boss" else MOB_BY[ref]
    scene = table["scene"]
    made = []
    for _ in range(count):
        hp = hp_each if hp_each is not None else card["hp"]
        token = foe_token(table, card, zone, kind, hp, waiting)
        scene["tokens"].append(token)
        made.append(token["name"])
    return made


def pick_mob(area, tier, family, high):
    fam = area * 3 + family
    variant = (tier - 1) * 2 + (1 if high else 0)
    index = fam * 10 + variant
    return MOBS[index]["id"]


def do_spawn(table, seat, action):
    if not table["scene"]:
        return fail(table, "Сначала откройте поле: брод, глубины или застава.")
    kind = action.get("meet", "simple")
    n = min(6, party_n(table))
    if action.get("ref"):
        ref = action["ref"].upper()
        pool = BOSS_BY if ref.startswith("B") else MOB_BY
        if ref not in pool:
            return fail(table, "Такой карты нет.")
        card = pool[ref]
        hp = card["hp"] * n if ref.startswith("B") else card["hp"]
        zone = int(action.get("zone") or table["scene"]["entry"])
        spawn_cards(table, ref, 1, zone, hp_each=hp)
        log(table, seat, "scene", f"На поле {card['name']} в зоне {zone}. ОЗ {hp}.")
        return {"ok": True}
    if kind == "boss":
        area = table["party"]["realm"] - 1
        tier = int(action.get("tier") or tier_of(table["party"]["level"]))
        found = [b for b in BOSSES if b["area"] == area and b["t"] == tier]
        if not found:
            return fail(table, "В этой области нет босса такой ступени.")
        card = found[0]
        hp = card["hp"] * n
        spawn_cards(table, card["id"], 1, table["scene"]["entry"], hp_each=hp)
        log(table, seat, "scene", f"Босс {card['name']} выходит один. ОЗ на карте {card['hp']} × {n} героев = {hp}. {card['omen']}")
        return {"ok": True}
    if kind not in MEET:
        return fail(table, "Встреча: простая, обычная, тяжёлая или босс.")
    count = MEET[kind][n]
    area = table["party"]["realm"] - 1
    tier = tier_of(table["party"]["level"])
    family = int(action.get("family") if action.get("family") is not None else table["rng"].randrange(3))
    high = bool(action.get("high"))
    ref = pick_mob(area, tier, family, high)
    waiting = 1 if kind == "hard" else 0
    now = count - waiting
    entry = table["scene"]["entry"]
    spawn_cards(table, ref, now, entry, waiting=False)
    if waiting:
        spawn_cards(table, ref, waiting, entry, waiting=True)
    name = MOB_BY[ref]["name"]
    late = " Последняя фигура войдёт в раунде 2." if waiting else ""
    log(table, seat, "scene", f"Для {n} героев встреча «{kind}»: {count} × {name}.{late}")
    return {"ok": True}


def nearest(scene, g, zone, skipped):
    best = None
    for hero in living_heroes(scene):
        if hero["id"] in skipped:
            continue
        path = shortest(g, zone, hero["zone"])
        if not path:
            continue
        key = (len(path) - 1, hero["hp"], hero["ref"])
        if best is None or key < best[0]:
            best = (key, hero, path)
    return best


def enemy_phase(table, seat):
    scene = table["scene"]
    if not scene:
        return fail(table, "Поля нет, страже некого искать.")
    if scene.get("storyBell"):
        if scene.get("goal") or scene["round"] > 3:
            return fail(table, "Переправа уже решилась. Запишите исход первой главы.")
        if scene.get("enemyRound") == scene["round"]:
            return fail(table, "Гончие уже ходили в этом раунде.")
        for hid, applied in list(scene.get("bellBreach", {}).items()):
            if applied < scene["round"]:
                conditions = table["heroes"][hid]["conditions"]
                if "надлом" in conditions:
                    conditions.remove("надлом")
                del scene["bellBreach"][hid]
        scene["enemyRound"] = scene["round"]
    g = graph(scene["links"])
    if scene.get("door"):
        g[5].discard(6)
        g[6].discard(5)
    foes = [t for t in scene["tokens"] if t["kind"] in ("foe", "boss") and t["hp"] > 0 and not t.get("waiting")]
    if not foes:
        log(table, seat, "scene", "На поле нет стоящей стражи.")
        return {"ok": True}
    lines = []
    for foe in foes:
        n = len(living_heroes(scene)) or 1
        orders = 1
        if foe["kind"] == "boss":
            orders = (n + 1) // 2
            if scene["round"] == 1 and n == 3:
                orders = 1
            if scene["round"] == 1 and n == 5:
                orders = 2
        skipped = set()
        for _ in range(orders):
            pick = nearest(scene, g, foe["zone"] or scene["entry"], skipped)
            if pick is None:
                lines.append(f"{foe['name']} не находит новую цель. Остаток приказа пропадает.")
                break
            (_, hero, path) = pick
            if foe["kind"] == "boss":
                skipped.add(hero["id"])
            dist = len(path) - 1
            if foe["kind"] == "boss" and scene.get("keeperBound"):
                if foe["hp"] < foe["maxHp"]:
                    scene["keeperBound"] = False
                elif dist > foe["reach"]:
                    lines.append(f"{foe['name']} удерживает затвор и остаётся на месте.")
                    continue
            if dist > foe["reach"] and len(path) > 1:
                foe["zone"] = path[1]
                path = shortest(g, foe["zone"], hero["zone"])
                dist = len(path) - 1
                lines.append(f"{foe['name']} шагает в {scene['zones'][foe['zone']-1]}.")
            if dist <= foe["reach"]:
                bonus = foe["tier"] + (1 if foe["kind"] == "boss" else 0)
                faces = d6s(table, 2, None)
                total = sum(faces) + bonus
                record = table["heroes"][hero["ref"]]
                defense = 9
                note = ""
                dealt = 0
                if sum(faces) == 2:
                    result = "промах"
                    note = "Чистые 2."
                elif sum(faces) == 12 or total >= defense:
                    result = "попадание"
                    if record["ignoreNextHit"]:
                        record["ignoreNextHit"] = False
                        note = "Герой игнорирует это попадание."
                    else:
                        token = hero
                        dealt = foe["dmg"]
                        if foe["ref"] == "M001":
                            if "надлом" in record["conditions"]:
                                record["conditions"].remove("надлом")
                                dealt += 1
                            else:
                                record["conditions"].append("надлом")
                                if scene.get("storyBell"):
                                    scene.setdefault("bellBreach", {})[token["ref"]] = scene["round"]
                                note = " Надлом до конца следующего хода героя."
                        before = token["shield"]
                        hurt(token, dealt, False)
                        used = before - token["shield"]
                        note = f"Урон {dealt}" + (f", щит поглотил {used}" if used else "") + f", осталось {token['hp']}." + note
                        record["hp"] = token["hp"]
                        record["shield"] = token["shield"]
                else:
                    result = "промах"
                lines.append(f"{foe['name']} бьёт {hero['name']}: 2d6 ({faces[0]}+{faces[1]}) + {bonus} = {total} против {defense}. {result}. {note}")
            elif len(path) > 1:
                foe["zone"] = path[1]
                lines.append(f"{foe['name']} не достаёт и шагает ещё, в {scene['zones'][foe['zone']-1]}.")
    log(table, seat, "dice", " ".join(lines))
    return {"ok": True}


def connected(a, b):
    return (a, b) in EDGES


def do_travel(table, seat, action):
    party = table["party"]
    if table["scene"]:
        return fail(table, "Сначала закройте поле. Порталом из боя не уходят.")
    if party["weatherDue"]:
        return fail(table, "Сначала решите погоду.")
    if party["fightDue"]:
        return fail(table, "Сначала разыграйте дорожную стычку и закройте её на столе.")
    dest = int(action.get("dest") or 0)
    if action.get("via") not in (None, "road", "portal"):
        return fail(table, "Выберите дорогу или открытую арку.")
    if action.get("via") == "portal":
        if not 1 <= dest <= 10 or dest == party["realm"] or any(
            party["portals"][n - 1] != "open" for n in (party["realm"], dest)
        ):
            return fail(table, "Нужны две разные открытые арки.")
        pay = action.get("pay")
        if pay == "supply" and party["supplies"] > 0:
            party["supplies"] -= 1
            price = "Израсходован 1 припас."
        elif pay == "tide":
            price = " ".join(["Прилив +1.", *add_tide(table, 1)])
        else:
            return fail(table, "Для арки выберите 1 припас или +1 прилив.")
        party["realm"] = dest
        if dest not in party["opened"]:
            party["opened"].append(dest)
        log(table, seat, "road", f"Арка в {realms[dest - 1][0]}. День {party['day']}. {price}")
        return {"ok": True, "road": None}
    if not 1 <= dest <= 10 or not connected(party["realm"], dest):
        return fail(table, "Между этими областями нет дороги.")
    sea_edge = (party["realm"], dest) in SEA
    pay = action.get("pay")
    physical = "faces" in action
    if physical:
        faces = action["faces"]
        if not isinstance(faces, list) or len(faces) != 1 or type(faces[0]) is not int or not 1 <= faces[0] <= 6:
            return fail(table, "Введите одну грань дорожного d6 от 1 до 6.")
    if sea_edge:
        if pay == "silver":
            if party["silver"] < 1:
                return fail(table, "На морской путь нужно 1 серебро или 1 припас.")
            party["silver"] -= 1
        elif pay == "supply":
            if party["supplies"] < 1:
                return fail(table, "На морской путь нужно 1 серебро или 1 припас.")
            party["supplies"] -= 1
        else:
            return fail(table, "Морской путь: скажите, чем платите.")
    party["realm"] = dest
    if dest not in party["opened"]:
        party["opened"].append(dest)
    party["day"] += 1
    for hero in table["heroes"].values():
        if hero["growth"]["guide"]:
            hero["guideReady"] = True
    notes = []
    if party["day"] % 3 == 0:
        notes += add_tide(table, 1)
    if "calmRoad" in party["flags"]:
        party["flags"].remove("calmRoad")
        face = None
        road = "дорога без события: яблоня Лиора"
    else:
        face = d6s(table, 1, action.get("faces") if physical else action.get("dice"), physical=physical)[0]
        road = apply_road(table, face)
    name = realms[dest - 1][0]
    extra = (" " + " ".join(notes)) if notes else ""
    shown = (f" Настольный d6={face}." if physical else f" d6={face}.") if face else ""
    fare = (" Морская плата — " + ("1 серебро." if pay == "silver" else "1 припас.")) if sea_edge else ""
    log(table, seat, "road", f"День {party['day']}. Путь в {name}.{fare}{shown} {road}.{extra}")
    return {"ok": True, "road": face}


def apply_road(table, face):
    party = table["party"]
    party["lastRoad"] = face
    if face == 3:
        party["supplies"] = min(6, party["supplies"] + 1)
    elif face == 4:
        i = party["realm"] - 1
        if party["portals"][i] == "unknown":
            party["portals"][i] = "trace"
    elif face == 5:
        if "skipWeather" in party["flags"]:
            party["flags"].remove("skipWeather")
            return ROAD[5] + ", но чешуя Ильвы проходит её без потери"
        party["weatherDue"] = True
        return ROAD[5] + ". Потратьте припас или потеряйте день"
    elif face == 1:
        party["fightDue"] = True
    return ROAD[face]


def do_weather(table, seat, action):
    party = table["party"]
    if not party["weatherDue"]:
        return fail(table, "Погоды нет.")
    choice = action.get("pay")
    if choice == "supply":
        if party["supplies"] < 1:
            return fail(table, "Припаса нет, остаётся потерять день.")
        party["supplies"] -= 1
        party["weatherDue"] = False
        log(table, seat, "road", "Плохую погоду закрыли припасом.")
    elif choice == "day":
        party["day"] += 1
        notes = add_tide(table, 1) if party["day"] % 3 == 0 else []
        party["weatherDue"] = False
        log(table, seat, "road", "Потерян день. Второе дорожное событие не бросают. " + " ".join(notes))
    else:
        return fail(table, "Нужен припас или день.")
    return {"ok": True}


def move_token(table, seat, action):
    scene = table["scene"]
    if not scene:
        return fail(table, "Поля нет.")
    token = next((t for t in scene["tokens"] if t["id"] == action.get("id")), None)
    if token is None:
        return fail(table, "Фигуры нет.")
    zone = int(action.get("zone") or 0)
    if not 1 <= zone <= 6:
        return fail(table, "Зоны нумеруют от 1 до 6.")
    if token["kind"] == "hero":
        owner = table["heroes"][token["ref"]]["owner"]
        if owner != seat:
            return fail(table, "Этого героя двигает его игрок.")
        here = token["zone"]
        if here and zone != here:
            if zone not in graph(scene["links"]).get(here, []):
                return fail(table, "Один шаг ведёт только в соседнюю зону.")
            if scene.get("door") and {here, zone} == {5, 6}:
                return fail(table, "Дверь между цистерной и затвором ещё закрыта.")
    token["zone"] = zone
    if token["kind"] == "hero":
        table["heroes"][token["ref"]]["zone"] = zone
    log(table, seat, "move", f"{token['name']} теперь в зоне {zone}, {scene['zones'][zone-1]}.")
    return {"ok": True}


def spend_boon(table, seat, action):
    hid, hero = my_hero(table, seat)
    boon_id = action.get("boon")
    boon = next((b for b in hero["boons"] if b["id"] == boon_id), None)
    if boon is None:
        return fail(table, "Такой пометки нет.")
    if boon_id == "adv":
        hero["advantageNext"] = True
    elif boon_id == "plus":
        hero["plusNext"] = True
    elif boon_id == "shield":
        if table["scene"]:
            hero["shield"] = max(hero["shield"], 2)
            token = hero_token(table, hid)
            if token:
                token["shield"] = hero["shield"]
        else:
            hero["pendingShield"] = 2
    elif boon_id == "repair":
        scene = table["scene"]
        if not scene or scene["id"] != "siege":
            return fail(table, "Ключ Грана чинит ворота только на заставе.")
        scene["gate"] = min(scene["gateMax"], scene["gate"] + 2)
    elif boon_id == "word":
        scene = table["scene"]
        pending = [w for w in (scene or {}).get("words", []) if w]
        if not scene or scene["id"] != "bell":
            return fail(table, "Часы Эсса слышны у колокола.")
        nxt = scene["round"]
        if nxt < len(pending):
            log(table, seat, "gm", f"Часы называют следующее слово, раунд не двигается: {pending[nxt]}.")
        else:
            log(table, seat, "gm", "Новых забытых слов на этом берегу нет.")
    else:
        return fail(table, "Эту пометку стол не умеет применить.")
    hero["boons"] = [b for b in hero["boons"] if b is not boon]
    if boon_id != "word":
        log(table, seat, "hero", f"{HERO_BY[hid]['name']} тратит пометку: {boon['label']}.")
    else:
        bump(table)
    return {"ok": True}


def do_grow(table, seat, action):
    hid, hero = my_hero(table, seat)
    key = action.get("pick")
    level = table["party"]["level"]
    if key == "capstone":
        choice = action.get("which")
        if choice not in ("ignore", "renew") or not can_growth(level, hero["growth"], "capstone"):
            return fail(table, "Десятый уровень ещё не открыт.")
        hero["growth"]["capstone"] = choice
        log(table, seat, "hero", "На десятом уровне выбран " + ("пропуск одного попадания" if choice == "ignore" else "возврат двух искр") + " раз за сцену.")
        return {"ok": True}
    if key not in ("talent", "spark", "stock", "guide") or not can_growth(level, hero["growth"], key):
        return fail(table, "Этот рост сейчас нельзя взять.")
    hero["growth"][key] = True
    if key == "spark":
        hero["maxSparks"] = max_sparks(True)
        hero["sparks"] += 1
    if key == "stock":
        hero["maxHp"] += 2
        hero["hp"] += 2
    names = {"talent": "личный талант", "spark": "+1 к максимуму искр", "stock": "Запас, +2 ОЗ", "guide": "Проводник"}
    log(table, seat, "hero", f"{HERO_BY[hid]['name']} берёт рост: {names[key]}.")
    return {"ok": True}


def do_fork(table, seat, action):
    hid, hero = my_hero(table, seat)
    if hero["fork"]:
        return fail(table, "Личный выбор уже сделан.")
    side = action.get("side")
    if side not in ("a", "b"):
        return fail(table, "Нужна одна из двух ветвей.")
    prompt, a_label, a_fx, b_label, b_fx = FORKS[hid]
    label, effects = (a_label, a_fx) if side == "a" else (b_label, b_fx)
    if any(effect[0] == "supply" and effect[1] < 0 and table["party"]["supplies"] + effect[1] < 0 for effect in effects):
        return fail(table, "На эту ветвь не хватает припаса.")
    if any(effect[0] == "silver" and effect[1] < 0 and table["party"]["silver"] + effect[1] < 0 for effect in effects):
        return fail(table, "На эту ветвь не хватает серебра.")
    if any(effect[0] == "spark" and effect[1] < 0 and hero["sparks"] + effect[1] < 0 for effect in effects):
        return fail(table, "На эту ветвь не хватает искры.")
    hero["fork"] = side
    notes = apply_effects(table, hero, effects)
    text = f"{HERO_BY[hid]['name']}: {label}"
    if notes:
        text += " " + " ".join(notes)
    log(table, seat, "hero", text)
    return {"ok": True}


def technique(table, seat):
    hid, hero = my_hero(table, seat)
    if hero["sparks"] < 1:
        return fail(table, "Приём стоит 1 искру.")
    if "немота" in hero["conditions"]:
        return fail(table, "Немота: искры тратить нельзя.")
    hero["sparks"] -= 1
    log(table, seat, "hero", f"Приём, 1 искра. {HERO_BY[hid]['technique']}")
    return {"ok": True}


def potion(table, seat, action):
    hid, hero = my_hero(table, seat)
    if "I19" not in hero["potions"] and not hero["potions"]:
        return fail(table, "Флакона на поясе нет.")
    target_id = action.get("target") or hid
    target = table["heroes"].get(target_id)
    if target is None or not target["owner"]:
        return fail(table, "Зелье отдают герою за столом.")
    if target_id != hid:
        mine = hero_token(table, hid)
        theirs = hero_token(table, target_id)
        if table["scene"] and (not mine or not theirs or abs_zone(table, mine["zone"], theirs["zone"]) > 1):
            return fail(table, "Флакон передают себе или союзнику на дальности 1.")
    bottle = "I19" if "I19" in hero["potions"] else hero["potions"][0]
    hero["potions"].remove(bottle)
    if bottle == "I19":
        target["hp"] = min(target["maxHp"], target["hp"] + 3)
        mirror_one(table, target)
        log(table, seat, "hero", f"Красный отвар: {HERO_BY[target_id]['name']} получает 3 ОЗ, теперь {target['hp']}.")
    else:
        log(table, seat, "hero", f"Выпит {bottle}. Эффект с карты запишите на планшет.")
    return {"ok": True}


def abs_zone(table, a, b):
    if not a or not b:
        return 99
    path = shortest(graph(table["scene"]["links"]), a, b)
    if not path:
        return 99
    return len(path) - 1


def help_ally(table, seat, action):
    hid, hero = my_hero(table, seat)
    ally = table["heroes"].get(action.get("target"))
    if ally is None or action.get("target") == hid:
        return fail(table, "Помогают другому герою.")
    if table["scene"]:
        mine = hero_token(table, hid)
        theirs = hero_token(table, action["target"])
        if not mine or not theirs or mine["zone"] != theirs["zone"]:
            return fail(table, "Помощь даёт союзник в той же зоне.")
    ally["advantageNext"] = True
    log(table, seat, "hero", f"{HERO_BY[hid]['name']} помогает {HERO_BY[action['target']]['name']}: преимущество на один названный бросок.")
    return {"ok": True}


def end_scene(table, seat, action):
    scene = table["scene"]
    if not scene:
        return fail(table, "Поле уже пустое.")
    victory = bool(action.get("victory"))
    retreat = bool(action.get("retreat"))
    if retreat and "safeRetreat" in table["party"]["flags"]:
        table["party"]["flags"].remove("safeRetreat")
        retreat = False
        note = "Отход по доскам Роха не считается поражением."
    elif retreat:
        note = "Общее отступление. Это поражение сцены, даже если кто-то ещё стоял."
    elif victory:
        note = "Сцена закрыта победой. Лежащих поднимают на 1 ОЗ."
        for hero in table["heroes"].values():
            if hero["owner"] and hero["hp"] <= 0:
                hero["hp"] = 1
    else:
        note = "Поле убрано. Награду, если она была, запишите отдельно."
    for hero in table["heroes"].values():
        hero["shield"] = 0
        hero["conditions"] = []
        hero["zone"] = None
        hero["ignoreNextHit"] = False
    table["scene"] = None
    table["party"]["fightDue"] = False
    log(table, seat, "scene", note)
    return {"ok": True}


def reward(table, seat, action):
    kind = action.get("kind", "normal")
    n = party_n(table)
    step = tier_of(table["party"]["level"])
    if kind == "boss":
        silver = 2 * n + 2 * step
        text = f"Награда босса: {silver} серебра. Ещё один предмет ценой до {4 + 2 * step}."
    elif kind == "prologue":
        silver = n + step
        text = f"Брод удержан: обычное серебро {silver}, 1 печать и один след портала."
        table["party"]["seals"] += 1
        if table["party"]["portals"][0] == "unknown":
            table["party"]["portals"][0] = "trace"
        bank(table)
    else:
        silver = n + step
        text = f"Обычная награда: {silver} серебра."
    table["party"]["silver"] += silver
    log(table, seat, "hero", text)
    return {"ok": True}


def bank(table):
    party = table["party"]
    while party["seals"] >= 2 and party["level"] < 10:
        party["seals"] -= 2
        party["level"] += 1
        before = {hid: hero["maxHp"] for hid, hero in table["heroes"].items()}
        sync_levels_absolute(table, before)
        log(table, "table", "hero", f"Две печати. Весь отряд теперь уровня {party['level']}, ступень {roman(tier_of(party['level']))}.")


def sync_levels_absolute(table, before):
    level = table["party"]["level"]
    for hid, hero in table["heroes"].items():
        old = before[hid]
        hero["maxHp"] = max_hp(level, hero["growth"]["stock"])
        hero["maxSparks"] = max_sparks(hero["growth"]["spark"])
        hero["hp"] = clamp(hero["hp"] + (hero["maxHp"] - old), 0, hero["maxHp"])
        token = hero_token(table, hid)
        if token:
            token["maxHp"] = hero["maxHp"]
            token["hp"] = hero["hp"]


def local_voice(table, question):
    party = table["party"]
    realm = realms[party["realm"] - 1]
    act = acts[party["chapter"] - 1]
    board = f"Вы в {realm[0]}, день {party['day']}, глава {act[0]}."
    scene = table["scene"]
    if scene:
        where = []
        for token in scene["tokens"]:
            if token.get("waiting"):
                continue
            zone = scene["zones"][token["zone"] - 1] if token.get("zone") else "вне поля"
            where.append(f"{token['name']} — {zone}")
        board += " На поле: " + "; ".join(where) + "."
        if scene["id"] == "bell" and scene["round"] <= len(scene["words"]):
            board += f" Забытое слово раунда {scene['round']}: {scene['words'][scene['round']-1]}."
    q = (question or "").lower()
    if not q or any(word in q for word in ("где мы", "что происходит", "зачитай")):
        return board + " " + act[1]
    stems = [w[:4] for w in re.findall(r"[а-яё0-9]{4,}", q) if w not in {"можно", "такое", "такой", "делать"}]
    hits = []
    for section in RULES:
        for para in section["body"].splitlines():
            score = sum(stem in para.lower() for stem in stems)
            if score and not para.startswith("#"):
                hits.append((score, section["title"], para))
    if hits:
        _, title, clip = max(hits, key=lambda hit: hit[0])
        return board + f"\n\nИз книги «{title}». {clip}"
    return board + " Ответа в книге по этим словам не нашлось. Попробуйте «искра», «дальность» или «привал»."


def prompt_for(table, question):
    party = table["party"]
    act = acts[party["chapter"] - 1]
    realm = realm_public(party["realm"] - 1, party)
    scene = table["scene"]
    brief = {
        "realm": {k: realm[k] for k in ("name", "capital", "village", "npc", "want", "case") if k in realm},
        "chapter": act[0],
        "opening": act[1],
        "goal": act[3],
        "tide": party["tide"],
        "suspicion": party["suspicion"],
        "day": party["day"],
        "clues": party["clues"],
        "scene": None if not scene else {
            "title": scene["title"], "round": scene["round"], "note": scene["note"],
            "tokens": [{"name": t["name"], "zone": t.get("zone"), "hp": t.get("hp")} for t in scene["tokens"] if not t.get("waiting")],
        },
    }
    recent = [line["text"] for line in table["log"][-8:]]
    return (
        "Ты ведущий стола «Море имён». Это авторская средневековая игра на двух шестигранниках, не Dungeons & Dragons. "
        "Говори по-русски, на «вы», коротко, два–пять предложений, и закончи одним конкретным выбором, если сцена открыта. "
        "Проверка: 2d6 + одна характеристика + ступень − 1. Порог бытовой 7, трудный 9, исключительный 11. "
        "Чистые 12 — успех, чистые 2 — провал. В бою любой недобор — промах. Дорога и вопрос «да/нет» — один d6. "
        "Не назначай числа костей: бросок делает стол. Не выдумывай ключ портала и не рассказывай закрытые главы. "
        "Если страницы нет в состоянии, скажи, что она ещё закрыта.\n\n"
        f"СОСТОЯНИЕ: {brief}\nПОСЛЕДНЕЕ: {recent}\nВОПРОС: {question}"
    )


def apply(table, seat, action):
    if seat not in table["seats"]:
        return fail(table, "Вас нет за этим столом.")
    if "rev" in action and action["rev"] != table["rev"]:
        return fail(table, "Стол уже сдвинулся. Повторите.")
    op = action.get("op")
    try:
        if op == "rename":
            name = clean_name(action.get("name", ""))
            table["seats"][seat]["name"] = name
            log(table, seat, "seat", f"Имя за столом: {name}.")
        elif op == "claim":
            return claim(table, seat, action.get("hero", ""))
        elif op == "release":
            return release(table, seat)
        elif op == "roll":
            return do_roll(table, seat, action)
        elif op == "grow":
            return do_grow(table, seat, action)
        elif op == "fork":
            return do_fork(table, seat, action)
        elif op == "boon":
            return spend_boon(table, seat, action)
        elif op == "technique":
            return technique(table, seat)
        elif op == "potion":
            return potion(table, seat, action)
        elif op == "help":
            return help_ally(table, seat, action)
        elif op == "hp":
            return set_track(table, seat, action, "hp")
        elif op == "sparks":
            return set_track(table, seat, action, "sparks")
        elif op == "condition":
            return toggle_condition(table, seat, action)
        elif op == "shield":
            return set_shield(table, seat, action)
        elif op == "move":
            return move_token(table, seat, action)
        elif op == "travel":
            return do_travel(table, seat, action)
        elif op == "weather":
            return do_weather(table, seat, action)
        elif op == "scene":
            return start_scene(table, seat, action.get("kind"))
        elif op == "spawn":
            return do_spawn(table, seat, action)
        elif op == "enemies":
            return enemy_phase(table, seat)
        elif op == "round":
            return next_round(table, seat)
        elif op == "end":
            return end_scene(table, seat, action)
        elif op == "reward":
            return reward(table, seat, action)
        elif op == "seal":
            table["party"]["seals"] += 1
            bank(table)
            log(table, seat, "hero", f"Печать опыта. Сейчас {table['party']['seals']} из 2 до следующего уровня.")
        elif op == "resource":
            return resource(table, seat, action)
        elif op == "portal":
            return mark_portal(table, seat, action)
        elif op == "deed":
            realm = int(action.get("realm") or table["party"]["realm"])
            if realm not in table["party"]["deeds"]:
                table["party"]["deeds"].append(realm)
            log(table, seat, "scene", f"Открыто местное дело: {realms[realm-1][12]}.")
        elif op == "chapter":
            if table["party"]["chapter"] >= 5:
                return fail(table, "Дальше только финал.")
            table["party"]["chapter"] += 1
            act = acts[table["party"]["chapter"] - 1]
            log(table, seat, "scene", f"Открыта глава. {act[0]}. {act[1]}")
        elif op == "deal":
            return deal(table, seat)
        elif op == "rest":
            return rest(table, seat)
        elif op == "lodge":
            return lodge(table, seat)
        elif op == "note":
            text = str(action.get("text", "")).strip()[:280]
            if not text:
                return fail(table, "Пустая строка.")
            log(table, seat, "note", text)
        elif op == "pencil":
            hid, hero = my_hero(table, seat)
            hero["pencil"] = str(action.get("text", ""))[:180]
            bump(table)
        elif op == "capstone":
            return use_capstone(table, seat)
        elif op == "army":
            return use_army(table, seat)
        elif op == "reroll":
            return reroll_road(table, seat, action)
        elif op == "bell":
            return bell(table, seat, action)
        elif op == "lever":
            return lever(table, seat)
        elif op == "clearFight":
            table["party"]["fightDue"] = False
            log(table, seat, "road", "Дорожную стычку закрыли на столе.")
        else:
            return fail(table, "Такого действия нет.")
    except PermissionError as exc:
        return fail(table, str(exc))
    except ValueError as exc:
        return fail(table, str(exc))
    return {"ok": True}


def claim(table, seat, hid):
    hid = str(hid).upper()
    if hid not in table["heroes"]:
        return fail(table, "Такого героя нет.")
    hero = table["heroes"][hid]
    if hero["owner"] and hero["owner"] != seat:
        return fail(table, "Этого героя уже взяли.")
    current = table["seats"][seat].get("heroId")
    if current and current != hid:
        return fail(table, "Сначала отпустите своего героя.")
    if len(table["seats"]) and sum(1 for s in table["seats"].values() if s.get("heroId")) >= 6 and not current:
        return fail(table, "За столом уже шесть героев.")
    fresh = hero["hp"] == 8 and hero["sparks"] == 3 and not hero["fork"] and not any(hero["growth"].values())
    hero["owner"] = seat
    table["seats"][seat]["heroId"] = hid
    level = table["party"]["level"]
    hero["maxHp"] = max_hp(level, hero["growth"]["stock"])
    hero["maxSparks"] = max_sparks(hero["growth"]["spark"])
    if fresh:
        hero["hp"] = hero["maxHp"]
        hero["sparks"] = hero["maxSparks"]
    else:
        hero["hp"] = min(hero["hp"], hero["maxHp"])
    if table["scene"]:
        table["scene"]["tokens"] = [t for t in table["scene"]["tokens"] if not (t["kind"] == "hero" and t["ref"] == hid)]
        table["scene"]["tokens"].append(place_hero_token(table, hid, 1))
    log(table, seat, "hero", f"За стол садится {HERO_BY[hid]['name']}, {HERO_BY[hid]['role'].lower()}. {HERO_BY[hid]['story']}")
    return {"ok": True}


def release(table, seat):
    hid = table["seats"][seat].get("heroId")
    if not hid:
        return fail(table, "Герой и так не взят.")
    table["heroes"][hid]["owner"] = None
    table["heroes"][hid]["zone"] = None
    table["seats"][seat]["heroId"] = None
    if table["scene"]:
        table["scene"]["tokens"] = [t for t in table["scene"]["tokens"] if not (t["kind"] == "hero" and t["ref"] == hid)]
    log(table, seat, "hero", f"{HERO_BY[hid]['name']} отходит от стола между главами.")
    return {"ok": True}


def set_track(table, seat, action, key):
    hid = action.get("hero") or table["seats"][seat].get("heroId")
    hero = table["heroes"].get(hid or "")
    if hero is None or hero["owner"] != seat:
        return fail(table, "Правьте планшет своего героя.")
    value = int(action.get("value"))
    if key == "hp":
        hero["hp"] = clamp(value, 0, hero["maxHp"])
        mirror_one(table, hero)
        token = hero_token(table, hid)
        if token:
            token["hp"] = hero["hp"]
    else:
        hero["sparks"] = clamp(value, 0, hero["maxSparks"])
    log(table, seat, "hero", f"Карандаш: {HERO_BY[hid]['name']} теперь {hero['hp']}/{hero['maxHp']} ОЗ, искры {hero['sparks']}/{hero['maxSparks']}.")
    return {"ok": True}


def toggle_condition(table, seat, action):
    name = action.get("name")
    if name not in CONDITIONS:
        return fail(table, "Такого состояния нет.")
    target = action.get("token")
    if table["scene"] and target:
        token = next((t for t in table["scene"]["tokens"] if t["id"] == target), None)
        if token is None:
            return fail(table, "Фигуры нет.")
        bag = token.setdefault("conditions", [])
        if name in bag:
            bag.remove(name)
        else:
            bag.append(name)
        if token["kind"] == "hero":
            table["heroes"][token["ref"]]["conditions"] = list(bag)
        log(table, seat, "hero", f"{token['name']}: {name} {'снята' if name not in bag else 'лежит'}.")
        return {"ok": True}
    hid, hero = my_hero(table, seat)
    if name in hero["conditions"]:
        hero["conditions"].remove(name)
    else:
        hero["conditions"].append(name)
    log(table, seat, "hero", f"{HERO_BY[hid]['name']}: {', '.join(hero['conditions']) or 'состояний нет'}.")
    return {"ok": True}


def set_shield(table, seat, action):
    hid, hero = my_hero(table, seat)
    hero["shield"] = clamp(int(action.get("value", 2)), 0, 6)
    token = hero_token(table, hid)
    if token:
        token["shield"] = hero["shield"]
    log(table, seat, "hero", f"Щит {HERO_BY[hid]['name']}: {hero['shield']}.")
    return {"ok": True}


def resource(table, seat, action):
    key = action.get("key")
    delta = int(action.get("delta", 0))
    party = table["party"]
    if key == "silver":
        party["silver"] = max(0, party["silver"] + delta)
    elif key == "supply":
        party["supplies"] = clamp(party["supplies"] + delta, 0, 6)
    elif key == "suspicion":
        party["suspicion"] = clamp(party["suspicion"] + delta, 0, 4)
    elif key == "shard":
        party["shards"] = max(0, party["shards"] + delta)
    elif key == "tide":
        if delta < 0:
            party["tide"] = max(0, party["tide"] + delta)
        else:
            add_tide(table, delta)
    elif key == "glory":
        i = int(action.get("realm") or party["realm"]) - 1
        party["glory"][i] = clamp(party["glory"][i] + delta, 0, 4)
    else:
        return fail(table, "Такого счётчика нет.")
    log(table, seat, "hero", "Счётчик поправлен карандашом.")
    return {"ok": True}


def mark_portal(table, seat, action):
    realm = int(action.get("realm") or table["party"]["realm"]) - 1
    state = action.get("state")
    if state not in ("unknown", "trace", "open"):
        return fail(table, "Арка: неизвестна, след или открыта.")
    table["party"]["portals"][realm] = state
    log(table, seat, "scene", f"Арка {realms[realm][0]}: {state}.")
    return {"ok": True}


def deal(table, seat):
    if table["party"]["dealt"]:
        return fail(table, "Стартовое серебро уже роздано.")
    n = party_n(table)
    if n < 1:
        return fail(table, "Сначала раздайте героев.")
    table["party"]["silver"] += 4 * n
    table["party"]["supplies"] = max(table["party"]["supplies"], 3)
    table["party"]["dealt"] = True
    log(table, seat, "hero", f"Раскладка: {4 * n} серебра в общую казну, припасы на столе, у каждого 8 ОЗ, 3 искры и красный отвар.")
    return {"ok": True}


def rest(table, seat):
    if table["scene"]:
        return fail(table, "Привал бывает после сцены, не в бою.")
    if table["party"]["rested"]:
        return fail(table, "После этой сцены привал уже был.")
    if table["party"]["supplies"] < 1:
        return fail(table, "Нужен 1 общий припас.")
    table["party"]["supplies"] -= 1
    table["party"]["rested"] = True
    for hero in table["heroes"].values():
        if hero["owner"]:
            hero["hp"] = min(hero["maxHp"], hero["hp"] + 2)
    log(table, seat, "hero", "Привал: 1 припас, всем своим +2 ОЗ.")
    return {"ok": True}


def lodge(table, seat):
    if table["scene"]:
        return fail(table, "Ночлег не ставят посреди поля.")
    if table["party"]["silver"] < 2:
        return fail(table, "Ночлег стоит 2 серебра, либо отработайте его днём на бумаге.")
    table["party"]["silver"] -= 2
    for hero in table["heroes"].values():
        if hero["owner"]:
            hero["hp"] = hero["maxHp"]
            hero["conditions"] = []
            hero["sparks"] = hero["maxSparks"]
    log(table, seat, "hero", "Ночлег. Сердца полные, искры полные, краткие состояния сняты.")
    return {"ok": True}


def use_capstone(table, seat):
    hid, hero = my_hero(table, seat)
    if hero["growth"]["capstone"] is None or not hero["capstoneReady"]:
        return fail(table, "Десятый дар уже потрачен в этой сцене или ещё не взят.")
    hero["capstoneReady"] = False
    if hero["growth"]["capstone"] == "ignore":
        hero["ignoreNextHit"] = True
        token = hero_token(table, hid)
        if token:
            token["ignoreNextHit"] = True
        log(table, seat, "hero", f"{HERO_BY[hid]['name']} пропустит следующее попадание.")
    else:
        hero["sparks"] = min(hero["maxSparks"], hero["sparks"] + 2)
        log(table, seat, "hero", f"{HERO_BY[hid]['name']} возвращает 2 искры.")
    return {"ok": True}


def use_army(table, seat):
    if "freeArmy" not in table["party"]["flags"]:
        return fail(table, "Знамя Оллена ещё не поднято.")
    scene = table["scene"]
    if not scene:
        return fail(table, "Армия является на поле.")
    foe = next((t for t in scene["tokens"] if t["kind"] == "foe" and t["hp"] > 0), None)
    if foe is None:
        return fail(table, "Снимать некого.")
    foe["hp"] = 0
    table["party"]["flags"].remove("freeArmy")
    log(table, seat, "scene", f"Союзная армия снимает {foe['name']} без политической цены.")
    return {"ok": True}


def reroll_road(table, seat, action):
    party = table["party"]
    if party["lastRoad"] is None:
        return fail(table, "Дорога ещё не брошена.")
    hid, hero = my_hero(table, seat)
    if not hero["growth"]["guide"] or not hero["guideReady"]:
        return fail(table, "Проводник уже потрачен или не взят.")
    hero["guideReady"] = False
    party["weatherDue"] = False
    party["fightDue"] = False
    face = d6s(table, 1, action.get("dice"))[0]
    text = apply_road(table, face)
    log(table, seat, "road", f"Проводник перекидывает дорогу. Второй результат обязателен: {face} — {text}.")
    return {"ok": True}


def bell(table, seat, action):
    scene = table["scene"]
    if not scene or scene["id"] != "bell":
        return fail(table, "Это действие брода.")
    if scene.get("goal") or scene["round"] > 3 or scene.get("enemyRound") == scene["round"]:
        return fail(table, "Сейчас действие у брода недоступно. Сверьте раунд и исход.")
    what = action.get("do")
    hid, hero = my_hero(table, seat)
    token = hero_token(table, hid)
    if not token or not hero["hp"]:
        return fail(table, "Действовать может стоящий герой на поле.")
    if what in ("hold", "song") and token["zone"] != 3 or what == "tongue" and token["zone"] != 4:
        return fail(table, "Коромысло и песня доступны в звоннице (3), язык — на отмели (4).")
    if what == "shield":
        target = next((t for t in scene["tokens"] if t["id"] == action.get("target", token["id"])
                       and t["kind"] == "hero" and t["zone"] == token["zone"] and t["hp"] > 0), None)
        if not target:
            return fail(table, "Выберите себя или стоящего союзника в своей зоне.")
        target["shield"] = max(target["shield"], 2)
        scene.setdefault("bellShields", []).append(target["ref"])
        mirror(table)
        log(table, seat, "scene", f"{target['name']} получает щит 2 до следующего хода защитника.")
        return {"ok": True}
    if what == "raise":
        target = next((t for t in scene["tokens"] if t["id"] == action.get("target")
                       and t["kind"] == "hero" and t["zone"] == token["zone"] and not t["hp"]), None)
        if not target or target["ref"] in scene.get("bellRaised", []):
            return fail(table, "Нужен павший союзник рядом, которого ещё не поднимали действием в этой сцене.")
        scene.setdefault("bellRaised", []).append(target["ref"])
        target["hp"] = 2
        mirror(table)
        log(table, seat, "scene", f"{token['name']} поднимает героя {target['name']}: 2 ОЗ.")
        return {"ok": True}
    roll = {key: action[key] for key in ("mode","spark","source","faces","dice") if key in action}
    if what == "hold":
        stat = action.get("stat", "might")
        if stat not in ("might", "will"):
            return fail(table, "Для коромысла нужна Мощь или Воля.")
        result = do_roll(table, seat, {**roll, "kind":"check", "stat":stat, "combat":True, "dc":7, "label":"Коромысло"})
        if not result.get("ok"):
            return result
        if table["log"][-1]["dice"]["result"] == "успех":
            scene["holds"] += 1
            log(table, seat, "scene", f"Коромысло удержано {scene['holds']} из 2.")
            if scene["holds"] >= 2:
                scene["goal"] = "коромысло"
                log(table, seat, "gm", "Верёвка слушается. Переправа ещё помнит берег. Можно закрывать брод победой.")
        return {"ok": True}
    if what == "tongue":
        alive = [t for t in scene["tokens"] if t["kind"] == "foe" and t["hp"] > 0]
        if alive:
            return fail(table, "Гончие ещё на ногах. Сначала одолейте их.")
        scene["goal"] = "язык"
        log(table, seat, "gm", "Язык колокола снят. В меди остаётся улика. Можно закрывать брод победой.")
        return {"ok": True}
    if what == "song":
        if "I19" not in hero["potions"]:
            return fail(table, "Для песни нужен свой красный отвар I19.")
        result = do_roll(table, seat, {**roll, "kind":"check", "stat":"will", "combat":True, "dc":8, "label":"Песня Лады"})
        if not result.get("ok"):
            return result
        if table["log"][-1]["dice"]["result"] != "успех":
            return {"ok": True}
        hero["potions"].remove("I19")
        scene["goal"] = "песня"
        log(table, seat, "gm", "Лада поёт старую песню. Флакон остаётся у неё. Список пропавших ещё можно договорить.")
        return {"ok": True}
    return fail(table, "У брода три выхода: коромысло, язык или песня.")


def lever(table, seat):
    scene = table["scene"]
    if not scene or scene["id"] != "dungeon":
        return fail(table, "Рычаг стоит в архиве подземелья.")
    scene["door"] = False
    log(table, seat, "scene", "Рычаг в архиве открывает дверь между цистерной и затвором. Броска нет.")
    return {"ok": True}


def next_round(table, seat):
    scene = table["scene"]
    if not scene:
        return fail(table, "Раунды считают на поле.")
    if scene.get("storyBell"):
        if scene["round"] > 3 or scene.get("goal"):
            return fail(table, "Сначала запишите исход переправы.")
        if scene.get("enemyRound") != scene["round"]:
            return fail(table, "Сначала разыграйте ход гончих.")
        for hid in scene.pop("bellShields", []):
            table["heroes"][hid]["shield"] = 0
            token = hero_token(table, hid)
            if token:
                token["shield"] = 0
        scene.pop("bellTurns", None)
    scene["round"] += 1
    for token in scene["tokens"]:
        if token.get("waiting") and scene["round"] >= 2:
            token["waiting"] = False
            token["zone"] = scene["entry"]
    words = ""
    if scene["id"] == "bell" and scene["round"] <= len(scene["words"]):
        words = f" Забытое слово: {scene['words'][scene['round']-1]}."
    if scene["id"] == "bell" and scene["round"] > 3 and not scene.get("goal"):
        log(table, seat, "scene", "Третий удар. Цель не выполнена. Запишите, что мост опустел.")
        return {"ok": True}
    log(table, seat, "scene", f"Раунд {scene['round']}.{words}")
    return {"ok": True}


def clean_name(name):
    name = re.sub(r"\s+", " ", str(name)).strip()
    name = "".join(ch for ch in name if ch.isprintable())
    return (name or "Гость")[:24]


def create_seat(table, name, token):
    if len(table["seats"]) >= 7:
        raise PermissionError("За столом уже семеро.")
    sid = f"s{table['seq']}"
    table["seq"] += 1
    table["seats"][sid] = {"id": sid, "name": clean_name(name), "token": token, "heroId": None}
    log(table, sid, "seat", f"{table['seats'][sid]['name']} садится к столу.")
    return sid


def find_seat(table, token):
    for seat in table["seats"].values():
        if seat["token"] == token:
            return seat["id"]
    return None
