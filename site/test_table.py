"""Rules the screen must share with the printed table."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine as E


def seat(table, name="Игрок"):
    return E.create_seat(table, name, "tok-" + name)


def play(table, sid, **action):
    out = E.apply(table, sid, action)
    assert out.get("ok"), out
    return out


def table():
    game = E.new_table()
    game["test_dice"] = True
    game["code"] = "КЕДР"
    return game


def test_numbers():
    assert E.tier_of(1) == 1 and E.tier_of(2) == 1 and E.tier_of(5) == 3 and E.tier_of(10) == 5
    assert E.max_hp(5, False) == 12
    assert E.max_hp(1, False) == 8
    assert E.max_sparks(False) == 3


def test_two_players_and_dice():
    game = table()
    a = seat(game, "Ася")
    b = seat(game, "Бор")
    play(game, a, op="claim", hero="H01")
    denied = E.apply(game, b, {"op": "claim", "hero": "H01"})
    assert not denied["ok"]
    play(game, b, op="claim", hero="H04")
    play(game, a, op="roll", kind="check", stat="might", dc=11, dice=[6, 6])
    last = game["log"][-1]
    assert last["dice"]["result"] == "успех"
    assert last["dice"]["total"] == 12
    assert game["heroes"]["H01"]["sparks"] == 3
    play(game, a, op="roll", kind="check", stat="might", dc=7, spark=True, dice=[1, 1])
    last = game["log"][-1]
    assert last["dice"]["result"] == "провал"
    assert game["heroes"]["H01"]["sparks"] == 2
    play(game, a, op="roll", kind="check", stat="agility", dc=9, mode="advantage", dice=[1, 6, 6])
    last = game["log"][-1]
    assert last["dice"]["kept"] == [6, 6]
    assert "2" in last["dice"]["formula"] or "Ловкость 2" in last["text"]
    stale = E.apply(game, a, {"op": "note", "text": "поздно", "rev": 1})
    assert not stale["ok"]
    seen = E.view(game, b)
    assert any(line["dice"] and line["dice"]["total"] == 12 for line in seen["log"])
    assert "token" not in str(seen["seats"])


def test_growth_and_fork():
    game = table()
    a = seat(game)
    play(game, a, op="claim", hero="H01")
    for _ in range(8):
        play(game, a, op="seal")
    hero = game["heroes"]["H01"]
    assert game["party"]["level"] == 5
    assert hero["hp"] == 12 and hero["maxHp"] == 12
    play(game, a, op="grow", pick="talent")
    assert hero["growth"]["talent"] and "spark" not in [x for x in hero["growth"] if hero["growth"][x] and x == "spark"]
    denied = E.apply(game, a, {"op": "grow", "pick": "spark"})
    assert not denied["ok"]
    play(game, a, op="fork", side="a")
    assert "стежок" in game["party"]["clues"]
    assert hero["boons"][0]["id"] == "adv"
    denied = E.apply(game, a, {"op": "fork", "side": "b"})
    assert not denied["ok"]


def test_bell_and_boss():
    game = table()
    a = seat(game, "Ася")
    b = seat(game, "Бор")
    play(game, a, op="claim", hero="H01")
    play(game, b, op="claim", hero="H16")
    play(game, a, op="scene", kind="bell")
    foes = [t for t in game["scene"]["tokens"] if t["kind"] == "foe"]
    assert len(foes) == 1 and foes[0]["ref"] == "M001" and foes[0]["zone"] == 4
    assert any(t["name"] == "Лада" and t["zone"] == 3 for t in game["scene"]["tokens"])
    foe = foes[0]
    play(game, a, op="enemies")
    assert foe["zone"] != 4
    play(game, a, op="end", victory=True)
    assert game["scene"] is None
    play(game, a, op="scene", kind="dungeon")
    play(game, a, op="spawn", meet="boss")
    boss = next(t for t in game["scene"]["tokens"] if t["kind"] == "boss")
    card = E.BOSS_BY[boss["ref"]]
    assert boss["hp"] == card["hp"] * 2
    play(game, a, op="spawn", meet="simple")
    spawned = [t for t in game["scene"]["tokens"] if t["kind"] == "foe"]
    assert len(spawned) == 1


def test_travel_hides_portals():
    game = table()
    a = seat(game)
    play(game, a, op="claim", hero="H01")
    book = E.compendium(game)
    assert "portalHint" not in book["realms"][0]
    assert book["acts"][1]["sealed"] is True
    play(game, a, op="deal")
    play(game, a, op="travel", dest=4, pay="silver", dice=[4])
    assert game["party"]["realm"] == 4
    assert game["party"]["portals"][3] == "trace"
    assert game["party"]["silver"] == 4 - 1
    book = E.compendium(game)
    assert "portalHint" in book["realms"][3]
    assert "portalHint" not in book["realms"][0]
    play(game, a, op="weather") if False else None
    assert E.local_voice(game, "как тратить искру").startswith("Вы в")
    assert "искр" in E.local_voice(game, "как тратить искру").lower()


def test_frame_contract():
    # The JS module is the source. This locks the same signs in Python.
    plane_w, img_w, img_h = 20, 2010, 1350
    plane_h = plane_w * img_h / img_w

    def paper(px, py):
        ix = 54 + (px / 100) * (1956 - 54)
        iy = 184 + (py / 100) * (1225 - 184)
        u, v = ix / img_w, iy / img_h
        return (u - 0.5) * plane_w, (v - 0.5) * plane_h

    assert paper(50, 0)[1] < paper(50, 50)[1] < paper(50, 100)[1]
    assert paper(100, 50)[0] > 0
    vx, vz = paper(22, 65)
    cx, cz = paper(50, 50)
    assert vx < cx and vz > cz


if __name__ == "__main__":
    test_numbers()
    test_two_players_and_dice()
    test_growth_and_fork()
    test_bell_and_boss()
    test_travel_hides_portals()
    test_frame_contract()
    print("ok")
