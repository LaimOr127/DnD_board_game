"""One set of table permissions and actions for LAN and browser-hosted rooms."""
import engine as E
import roadside
import story


PERSONAL = {"claim", "roll", "grow", "fork", "boon", "technique", "potion",
            "hp", "sparks", "pencil", "capstone", "release", "move", "note",
            "equip", "condition", "help"}
SHARED = {"story", "enemies", "round", "reward", "seal", "travel", "weather",
          "rest", "lodge", "spawn", "scene", "end", "deal", "lever", "clearFight",
          "resource", "portal", "deed", "creatureHp", "bell", "roadFight", "meeting"}


def snapshot(table, sid):
    state = E.view(table, sid)
    state.update(host=table.get("host") == sid, story=story.visible(table))
    for hero in state["heroes"].values():
        hero["equipment"] = table["heroes"][hero["id"]].get("equipment", {})
        if hero["owner"] != sid:
            hero.pop("pencil", None)
    return state


def narration(table, question):
    page = story.visible(table)
    q = question.lower().strip(" ?.!")
    if any(word in q for word in ("встреч", "попутчик", "на дороге")):
        meeting = page["meeting"]
        if meeting:
            return "\n".join([meeting["npc"] + ". " + meeting["text"], *meeting["voices"],
                              *(c["label"] for c in meeting["choices"])])
        return "Встреча на дороге доступна в мирной остановке до эпилога. Прежние решения сохранены в дорожном журнале."
    if q == "вести" or any(word in q for word in ("какие вести", "вести из", "вести с дороги", "весть", "последств", "отклик")):
        received = [r["news"] for r in page["roadJournal"] if r["news"]]
        return "\n".join(received) if received else "Из пройденных королевств пока нет вестей."
    if not q or any(w in q for w in ("зачитай", "где мы", "что происходит", "что дальше", "расскажи сцену")):
        return "\n".join(filter(None, (page["text"], *page["echoes"], *page["news"], page["prompt"])))
    return E.local_voice(table, question)


def act(table, sid, action):
    if sid not in table["seats"] or not isinstance(action, dict):
        return E.fail(table, "Сначала войдите в комнату.")
    op = action.get("op")
    if not isinstance(op, str) or op not in PERSONAL | SHARED:
        return E.fail(table, "Неизвестное действие.")
    if op in SHARED and sid != table.get("host"):
        return E.fail(table, "Общее поле меняет создатель стола.")
    if "rev" in action and action["rev"] != table["rev"]:
        return E.fail(table, "Стол изменился. Проверьте новое положение и повторите.")
    # Bounds apply before the domain engine, including actions sent outside the UI.
    for field, low, high in (("zone", 1, 6), ("dest", 1, 10), ("realm", 1, 10),
                             ("dc", 1, 40), ("tier", 1, 5), ("family", 0, 2),
                             ("value", 0, 1000), ("delta", -10, 10)):
        if field in action and (type(action[field]) is not int or not low <= action[field] <= high):
            return E.fail(table, f"Число вне диапазона {low}–{high}.")
    if any(not isinstance(v, (str, int, bool)) or isinstance(v, str) and len(v) > 500
           for k, v in action.items() if k != "faces"):
        return E.fail(table, "Неверный формат действия.")
    scene = table["scene"]
    if op == "roadFight":
        if scene or not table["party"]["fightDue"]:
            return E.fail(table, "На дороге сейчас нет ожидающей стычки.")
        result = E.start_scene(table, sid, "dungeon")
        if result["ok"]:
            table["scene"].update(title="Стычка на дороге", door=False, note="Разыграйте встречу с местной семьёй на поле из шести зон.")
            E.do_spawn(table, sid, {"meet":"simple"})
        return result
    if op == "scene" and scene:
        return E.fail(table, "Сначала завершите текущее поле.")
    if op == "spawn" and scene and len(scene["tokens"]) >= 40:
        return E.fail(table, "На этом поле уже достаточно фигур.")
    if op == "deal" and not E.claimed(table):
        return E.fail(table, "Сначала выберите хотя бы одного героя.")
    if op == "move" and sid != table.get("host"):
        own = E.hero_token(table, table["seats"][sid]["heroId"])
        if not own or own["id"] != action.get("id"):
            return E.fail(table, "Вы можете двигать свою фигуру.")
    _, own_hero = E.seat_hero(table, sid)
    if scene and own_hero and own_hero["hp"] == 0 and op in {"move", "technique", "help", "potion", "roll"} and action.get("kind") not in {"oracle", "road"}:
        return E.fail(table, "Герой лежит. Сначала союзник должен помочь ему подняться.")
    if op == "condition" and action.get("hero", table["seats"][sid]["heroId"]) != table["seats"][sid]["heroId"]:
        return E.fail(table, "Выберите своего героя.")
    if op == "equip":
        if not own_hero:
            return E.fail(table, "Сначала выберите героя.")
        slot, item = action.get("slot"), E.ITEM_BY.get(action.get("item"))
        if slot not in {"Оружие", "Шлем", "Нагрудник", "Обувь"} or not item or item["slot"] != slot:
            return E.fail(table, "Вещь должна подходить выбранному слоту.")
        if slot == "Оружие":
            own_hero["weapon"] = item["id"]
        else:
            own_hero.setdefault("equipment", {})[slot] = item["id"]
        E.log(table, sid, "hero", "Снаряжение с бумажного листа: " + item["name"] + ". " + item["text"])
        return {"ok": True}
    if op == "claim" and scene and table["seats"][sid]["heroId"]:
        return E.fail(table, "Герой уже на поле.")
    if op == "release" and scene:
        return E.fail(table, "Сменить героя можно после сцены.")
    if op == "roll":
        if action.get("kind", "check") not in {"check", "attack", "road", "oracle"}:
            return E.fail(table, "Неизвестная проверка.")
        if action.get("target") and not any(t["id"] == action["target"] and
                t["kind"] in ("foe", "boss") and not t.get("waiting") for t in (scene or {}).get("tokens", [])):
            return E.fail(table, "Выберите противника на поле.")
    if op == "creatureHp":
        token = next((t for t in (scene or {}).get("tokens", []) if t["id"] == action.get("id")
                      and t["kind"] in ("boss", "foe")), None)
        if not token or "value" not in action:
            return E.fail(table, "Выберите противника и его здоровье.")
        token["hp"] = min(token["maxHp"], action["value"])
        E.log(table, sid, "scene", f"{token['name']} — {token['hp']} из {token['maxHp']} ОЗ по итогам хода на столе.")
        return {"ok": True}
    if op == "story":
        return story.choose(table, sid, action)
    if op == "meeting":
        return roadside.choose(table, sid, table.get("story") or story.initial(table), action)
    result = E.apply(table, sid, action)
    if op == "travel" and result.get("road") == 2:
        history = table.get("story") or story.initial(table)
        meeting = roadside.current(table, history)
        if meeting and meeting["stage"] == "rumour":
            roadside.choose(table, sid, history, {"realm": meeting["realm"], "chapter": table["party"]["chapter"], "choice": "listen"})
    if result["ok"] and op == "round":
        story.siege_wave(table, sid)
    if result["ok"] and op == "deal":
        table["fundedSeats"] = [s["id"] for s in table["seats"].values() if s["heroId"]]
    if result["ok"] and op == "claim" and table["party"]["dealt"] and sid not in table.get("fundedSeats", []):
        table.setdefault("fundedSeats", []).append(sid)
        table["party"]["silver"] += 4
        E.log(table, sid, "hero", "Новый участник добавляет 4 стартовых серебра в казну.")
    return result
