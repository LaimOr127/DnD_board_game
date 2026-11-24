"""The two shared parcels from Three Willows, including their dated receipts."""
from typing import NamedTuple

import engine as E
import personal


class Ending(NamedTuple):
    label: str
    scene: str
    resource: str
    later: str
    epilogue: str


class Errand(NamedTuple):
    name: str
    offer: str
    route: str
    handover: str
    realm: int
    pages: tuple
    paths: dict
    missed: tuple


ERRANDS = {
    "letter": Errand(
        "Письмо с выкройкой рукава",
        "Нера, переплётчица Трёх Ив, даёт вам конверт, прошитый красной ниткой. «Брат может забыть, что у него есть сестра. Дайте ему примерить бумажный рукав. Я всегда кроила левый чуть шире».",
        "В главе III найдите возницу Савела в Красном Яру до начала осады.",
        "Савел просовывает руку в бумажный рукав и вдруг вспоминает, как обжёг локоть у сестриной печи. Под выкройкой второй лист с местами в обозе. «Если повесим его на ворота, люди найдут телеги. Начальник заставы их тоже увидит». Савел готов к обоим решениям.",
        6, ("gateRoad",),
        {"board": Ending("Вывесить с согласия Савела список телег", "Савел сам прибивает лист. К вечеру семьи нашли свои телеги, а писарь успел переписать номера осей.", "street",
                         "У судебного крыльца родители называют номера телег и требуют пропустить возниц в зал. Савел прячет обожжённый локоть в новом рукаве.",
                         "После последнего звона Савел красит оси в разные цвета. Теперь место в обозе может найти даже тот, кто разучился читать."),
         "hand": Ending("Передать лист Савелу для обхода дворов", "Савел с дочерью обходят знакомые дворы. Вы успеваете предупредить свою улицу. Для соседней уже закрыли калитку. Дочь делится дорожным хлебом.", "supplies",
                        "К судебному крыльцу пришла семья с соседней улицы. Девочка из обоза садится рядом и записывает, в какую калитку постучать в следующий раз.",
                        "Дочь Савела ведёт отдельную тетрадь дворов, где ей однажды не открыли. Первую страницу она показывает Нере.")},
        ("Когда ворота закрылись, Савел ушёл с обозом. Возница с последней подводы вызвался отвезти конверт обратно в Три Ивы. На корешке Нера оставила пустое место для ответа.",
         "Первый ответ приходит без подписи. Нера хранит оба конверта в одном переплёте. Однажды посетитель просит примерить широкий левый рукав. Она закрывает мастерскую до утра.")),
    "tally": Errand(
        "Бирка лодочного долга",
        "У Неры две половины ореховой бирки. Зарубки на них сходятся. «Лодочница Ила возила людей в долг. Казна обещала ей весло за каждую ходку. Теперь в реестре должниками стоят пассажиры». Нера просит довезти бирку до слушания.",
        "В главе IV принесите бирку Иле в Верфеград до решения королевского слушания.",
        "Ила ставит на пол мокрое весло. Она нашла книгу рейсов. Суд может признать сам порядок ошибочным, но потребует оставить обе половины как доказательство. Или Ила примет выкуп по этой бирке и тут же вычеркнет знакомые семьи. «Сначала скажите им, что станет с остальными».",
        1, ("courtRoad", "hearing"),
        {"case": Ending("Оставить бирку суду как образец для других дел", "Ила оставляет обе половины в суде. Семьи пока ждут, зато теперь любая пристань может сослаться на дело лодочницы.", "glory",
                        "К лестнице Сердца пришёл гребец с другой реки. Впервые его жалобу приняли по номеру дела Илы, хотя его деревни на карте уже нет.",
                        "Ила вырезает две новые половинки. Одну вешает у причала, другую отдаёт первому пассажиру вместе с номером судебного дела."),
         "buy": Ending("Выкупить бирку за 2 серебра и вычеркнуть семьи", "Ила получает плату и перечёркивает долги пассажиров именно этого рейса. Они могут говорить на площади от своего имени. В остальных книгах прежние строки ещё на месте.", "buy",
                       "У лестницы Сердца с вами здороваются бывшие должники. Ила просит их запомнить имя следующего лодочника в очереди за выкупом.",
                       "По утрам Ила кладёт выкупленную бирку в ладонь первому пассажиру. За день она проходит через целую лодку рук и вечером возвращается к ней.")},
        ("Суд завершил слушание и принял книгу с прежними долгами. Ила забрала весло и открыла на пристани очередь просителей.",
         "На пристани Илы стоит длинная скамья. Нера приносит чистую тетрадь и остаётся записывать людей до последнего парома.")),
}


def view(table, story):
    party = table["party"]
    quiet = not (table["scene"] or party["weatherDue"] or party["fightDue"])
    cards = []
    for key, errand in ERRANDS.items():
        record = story.get("promises", {}).get(key)
        at_desk = quiet and party["realm"] == 1 and party["chapter"] <= 2
        if not record and not at_desk:
            continue
        row = {"key": key, "name": errand.name, "route": errand.route, "record": record,
               "text": "", "choices": []}
        if story["page"] == "epilogue" and record and "outcome" in record:
            outcome = record["outcome"]
            row["afterword"] = errand.missed[1] if outcome == "late" else errand.paths[outcome].epilogue
        if not record:
            row.update(text=errand.offer, choices=[{"id": "take", "label": "Взять поручение"}])
        elif "outcome" not in record and quiet and party["realm"] == errand.realm and story["page"] in errand.pages:
            row.update(text=errand.handover, choices=[{"id": k, "label": p.label} for k, p in errand.paths.items()])
        cards.append(row)
    return cards + personal.view(table, story)


def act(table, seat, story, action):
    hero, _ = E.seat_hero(table, seat)
    party = table["party"]
    if not hero or action.get("hero") != hero:
        return E.fail(table, "Выберите своего героя и откройте книгу снова.")
    if action.get("chapter") != party["chapter"] or action.get("realm") != party["realm"]:
        return E.fail(table, "Отряд уже сменил место или главу. Сверьтесь с книгой.")
    card = next((c for c in view(table, story) if c["key"] == action.get("parcel")), None)
    choice = action.get("choice")
    if not card or not any(c["id"] == choice for c in card["choices"]):
        return E.fail(table, "Эта запись сейчас недоступна. Проверьте срок и состояние поручения.")
    if "ownerHero" in card:
        return personal.act(table, seat, story, hero, card, choice)
    errand = ERRANDS[card["key"]]
    if choice == "take":
        story.setdefault("promises", {})[card["key"]] = {"taken": E.campaign_stamp(table, seat, hero)}
        text = "Поручение принято. " + errand.route
    else:
        path = errand.paths[choice]
        changes = []
        if path.resource == "buy" and party["silver"] < 2:
            return E.fail(table, "Для выкупа нужны 2 общих серебра. Пополните казну или передайте бирку суду.")
        tracks = {"buy": [("silver", -2), ("street", 1)], "street": [("street", 1)],
                  "supplies": [("supplies", 1)], "glory": [("glory", 1)]}[path.resource]
        for key, delta in tracks:
            if key == "glory":
                before = party["glory"][0]
                after = party["glory"][0] = min(4, before + delta)
            else:
                before = party[key]
                after = party[key] = min(6, before + delta) if key == "supplies" else before + delta
            name = {"glory": "Слава Вельна", "supplies": "Припасы", "silver": "Серебро", "street": "Голос улицы"}[key]
            changes.append({"name": name, "before": before, "after": after})
        card["record"].update(outcome=choice, closed=E.campaign_stamp(table, seat, hero), label=path.label,
                              scene=path.scene, changes=changes)
        text = path.scene
    table["story"] = story
    E.log(table, seat, "story", E.HERO_BY[hero]["name"] + " · " + errand.name + ". " + text)
    return {"ok": True}


def close_window(table, seat, story, page):
    key = {"gateRoad": "letter", "hearing": "tally"}.get(page)
    record = story.get("promises", {}).get(key)
    if record and "outcome" not in record:
        text = ERRANDS[key].missed[0]
        record.update(outcome="late", closed=E.campaign_stamp(table, seat), label="Срок прошёл", scene=text, changes=[])
        E.log(table, seat, "gm", text)


def echoes(story):
    lines = []
    for key, record in story.get("promises", {}).items():
        outcome = record.get("outcome")
        page = story["page"]
        if not outcome or page not in ("epilogue", "hearing" if key == "letter" else "heartRoad"):
            continue
        errand = ERRANDS[key]
        if outcome == "late":
            lines.append(errand.missed[1] if page == "epilogue" else errand.missed[0])
        else:
            path = errand.paths[outcome]
            lines.append(path.epilogue if page == "epilogue" else path.later)
    return lines + personal.echoes(story)
