"""Personal promises shared by all seats, with a decision and a separate receipt."""
import engine as E
from personal_quests import QUESTS


def view(table, story):
    party = table["party"]
    quiet = (story["page"] not in ("verdict", "epilogue") and not table["scene"]
             and not party["fightDue"] and not party["weatherDue"])
    rows = []
    for hid, quest in QUESTS.items():
        record = story.get("personalPromises", {}).get(hid)
        if not record and not (quiet and table["heroes"][hid]["owner"]):
            continue
        decision, reply = (E.realms[n - 1][0] for n in (quest.realm, quest.reply_realm))
        row = {"key": hid, "ownerHero": hid, "actor": hid, "name": quest.title, "record": record,
               "route": f"Место решения — {decision}. Ответ ждёт в королевстве {reply}.",
               "text": "", "choices": []}
        if not record:
            row.update(text=quest.offer, choices=[{"id": "take", "label": "Дать слово"}])
        elif "outcome" not in record:
            if quiet and party["realm"] == quest.realm:
                row.update(text=quest.meeting, choices=[{"id": k, "label": p.label} for k, p in quest.paths.items()])
        elif record["outcome"] in quest.paths:
            if "receipt" not in record:
                row.update(actor=None, text=f"Ваш ответ ждёт подписи в королевстве {reply}.")
                if quiet and party["realm"] == quest.reply_realm:
                    row["choices"] = [{"id": "receive", "label": "Принять ответ для отряда"}]
            if story["page"] == "epilogue":
                row["afterword"] = quest.paths[record["outcome"]].epilogue
        elif story["page"] == "epilogue":
            row["afterword"] = quest.unfinished
        rows.append(row)
    return rows


def act(table, seat, story, hero, card, choice):
    if card["actor"] and hero != card["actor"]:
        return E.fail(table, "Это слово может дать и исполнить только его герой.")
    hid = card["key"]
    quest = QUESTS[hid]
    stamp = E.campaign_stamp(table, seat, hero)
    if choice == "take":
        story.setdefault("personalPromises", {})[hid] = {"taken": stamp}
        line = "Дано слово. " + card["route"]
    elif choice == "receive":
        record = card["record"]
        index = quest.reply_realm - 1
        glory = table["party"]["glory"]
        before = glory[index]
        glory[index] = min(4, before + 1)
        line = quest.paths[record["outcome"]].reply
        record["receipt"] = {"when": stamp, "mode": "visit", "text": line,
                             "changes": [{"name": "Местная слава", "before": before, "after": glory[index]}]}
    else:
        path = quest.paths[choice]
        card["record"].update(outcome=choice, closed=stamp, label=path.label, scene=path.scene, changes=[])
        line = path.scene
    table["story"] = story
    E.log(table, seat, "story", E.HERO_BY[hero]["name"] + " · " + quest.title + ". " + line)
    return {"ok": True}


def finish(table, seat, story):
    stamp = E.campaign_stamp(table, seat)
    for hid, record in story.get("personalPromises", {}).items():
        quest = QUESTS[hid]
        if "outcome" not in record:
            record.update(outcome="late", label="Слово осталось открытым", closed=stamp,
                          scene=quest.unfinished, changes=[])
        elif record["outcome"] in quest.paths and "receipt" not in record:
            record["receipt"] = {"when": stamp, "mode": "courier", "text": quest.paths[record["outcome"]].reply,
                                 "changes": []}


def echoes(story):
    if story["page"] != "epilogue":
        return []
    lines = []
    for hid, record in story.get("personalPromises", {}).items():
        quest = QUESTS[hid]
        receipt = record.get("receipt", {})
        if receipt.get("mode") == "courier":
            lines.append("Письмо к последнему звону. " + receipt["text"])
        path = quest.paths.get(record.get("outcome"))
        lines.append(path.epilogue if path else quest.unfinished)
    return lines
