import json
import unittest

import engine as E
import promises
import service
import story


class PromiseTest(unittest.TestCase):
    def setUp(self):
        self.game = E.new_table()
        self.host = E.create_seat(self.game, "Анна", "a")
        self.guest = E.create_seat(self.game, "Ира", "b")
        self.game["host"] = self.host
        self.party = self.game["party"]
        for seat, hero in [(self.host, "H01"), (self.guest, "H07")]:
            self.assertTrue(service.act(self.game, seat, {"op": "claim", "hero": hero})["ok"])

    def promise(self, seat, parcel, choice, ok=True, **overrides):
        data = {"op": "promise", "parcel": parcel, "choice": choice, "realm": self.party["realm"],
                "chapter": self.party["chapter"], "hero": self.game["seats"][seat]["heroId"], **overrides}
        before = json.dumps(E.serial(self.game))
        result = service.act(self.game, seat, data)
        self.assertEqual(ok, result["ok"], result)
        if not ok:
            self.assertEqual(before, json.dumps(E.serial(self.game)))

    def place(self, realm, chapter, page):
        self.party.update(realm=realm, chapter=chapter)
        self.game.setdefault("story", story.initial(self.game))["page"] = page

    def pick(self, choice, paper=False):
        data = {"op": "story", "choice": choice, "scene": story.visible(self.game)["id"], "paper":paper}
        result = service.act(self.game, self.host, data)
        self.assertTrue(result["ok"], result)

    def test_tally_payment_cannot_partially_spend_or_repeat_and_receipt_survives(self):
        self.promise(self.host, "tally", "take")
        self.promise(self.guest, "tally", "take", False)
        self.place(1, 4, "hearing")
        self.party["silver"] = 1
        self.promise(self.guest, "tally", "buy", False)
        self.party["silver"] = 3
        self.promise(self.guest, "tally", "buy")
        self.promise(self.host, "tally", "case", False)
        record = self.game["story"]["promises"]["tally"]
        self.assertEqual(("Сойка", "Анна", "Мара", "Ира"),
                         (record["taken"]["hero"], record["taken"]["player"], record["closed"]["hero"], record["closed"]["player"]))
        self.assertEqual([(3, 1), (0, 1)], [(v["before"], v["after"]) for v in record["changes"]])
        self.assertEqual((1, 1, 0), (self.party["silver"], self.party["street"], self.party["debts"]))
        self.place(1, 5, "heartRoad")
        self.assertIn(promises.ERRANDS["tally"].paths["buy"].later, story.visible(self.game)["echoes"])
        self.place(1, 5, "verdict")
        self.pick("publish")
        expected = story.visible(self.game)
        self.assertIn("публикации — 1", expected["verdictReceipt"]["reason"])
        self.assertEqual(expected["title"], expected["verdictReceipt"]["title"])
        self.assertIn(promises.ERRANDS["tally"].paths["buy"].epilogue, expected["echoes"])
        self.assertEqual(expected, story.visible(E.restore(json.loads(json.dumps(E.serial(self.game))))))
        self.party["street"] = 0
        self.assertEqual(expected["verdictReceipt"], story.visible(self.game)["verdictReceipt"])

    def test_ineligible_actor_wrong_route_and_exact_deadlines(self):
        for args in [{"hero": "H07"}, {"realm": 3}, {"chapter": 2}]:
            self.promise(self.host, "letter", "take", False, **args)
        spectator = E.create_seat(self.game, "Чтец", "c")
        self.promise(spectator, "letter", "take", False)
        for flag in ("weatherDue", "fightDue"):
            self.party[flag] = True
            self.promise(self.host, "letter", "take", False)
            self.party[flag] = False
        self.party["realm"] = 3
        self.promise(self.host, "letter", "take", False)
        self.party["realm"] = 1
        self.promise(self.host, "letter", "take")
        self.promise(self.host, "tally", "take")
        self.promise(self.guest, "letter", "board", False)
        self.place(6, 3, "gateRoad")
        self.pick("arrive")
        self.promise(self.guest, "letter", "board", False)
        self.pick("lada")
        self.place(1, 4, "courtRoad")
        self.pick("enter")
        self.assertIn(promises.ERRANDS["letter"].missed[0], story.visible(self.game)["echoes"])
        self.pick("council")
        self.promise(self.guest, "tally", "case", False)
        for r in self.game["story"]["promises"].values():
            self.assertEqual(("late", [], ""), (r["outcome"], r["changes"], r["closed"]["hero"]))
        self.place(1, 5, "verdict")
        self.pick("open")
        final = story.visible(self.game)
        self.assertTrue(all(e.missed[1] in final["echoes"] for e in promises.ERRANDS.values()))

    def test_letter_and_case_limits_actual_benefits_and_no_unearned_outcome(self):
        for key, choice, realm, chapter, page, value in [
                ("letter", "board", 6, 3, "gateRoad", (0, 1)),
                ("letter", "hand", 6, 3, "gateRoad", (6, 6)),
                ("tally", "case", 1, 4, "courtRoad", (4, 4))]:
            with self.subTest(choice=choice):
                self.setUp()
                self.promise(self.host, key, "take")
                self.place(realm, chapter, page)
                self.party["supplies"], self.party["glory"][0] = 6, 4
                self.promise(self.guest, key, choice)
                change, = self.game["story"]["promises"][key]["changes"]
                self.assertEqual(value, (change["before"], change["after"]))
                passage = promises.ERRANDS[key].paths[choice]
                self.assertNotIn(passage.epilogue, str(story.visible(self.game)))
                self.place(1, 4 if key == "letter" else 5, "hearing" if key == "letter" else "heartRoad")
                self.assertIn(passage.later, story.visible(self.game)["echoes"])

    def test_chapter_total_includes_arriving_news_once_and_legacy_history_stays_unknown(self):
        self.place(1, 1, "prologue")
        for key in ["listen", "tablecloth"]:
            self.assertTrue(service.act(self.game, self.host, {"op":"meeting", "realm":1, "chapter":1, "choice":key})["ok"])
        self.pick("ribbon")
        self.pick("empty", paper=True)
        page = story.visible(self.game)
        entry, = page["milestones"]
        self.assertEqual((1, "Анна"), (entry["when"]["chapter"], entry["when"]["player"]))
        self.assertIn({"name":"Голос улицы", "before":0, "after":1}, entry["changes"])
        self.assertEqual(1, page["roadJournal"][0]["signed"]["chapter"])
        del self.game["story"]["milestones"]
        del self.game["story"]["meetings"]["1"]["signed"]
        old = story.visible(E.restore(json.loads(json.dumps(E.serial(self.game)))))
        self.assertEqual([], old["milestones"])
        self.assertIsNone(old["roadJournal"][0]["signed"])

    def test_road_fight_must_be_resolved_before_hearing_or_travel(self):
        self.place(1, 4, "courtRoad")
        self.party["fightDue"] = True
        self.assertFalse(service.act(self.game, self.host, {"op":"travel", "dest":3})["ok"])
        self.assertFalse(story.visible(self.game)["choices"])
        self.assertFalse(service.act(self.game, self.host, {"op":"story","scene":"courtRoad","choice":"enter"})["ok"])
        self.assertTrue(service.act(self.game, self.host, {"op":"clearFight"})["ok"])
        self.pick("enter")
        self.assertEqual("hearing", story.visible(self.game)["id"])


if __name__ == "__main__":
    unittest.main()
