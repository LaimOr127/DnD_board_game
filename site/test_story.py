"""Check printed routes, actual world transitions and private unopened pages."""
import json
import unittest

import engine as E
import story


class StoryTests(unittest.TestCase):
    def setUp(self):
        self.table = E.new_table()
        self.table["test_dice"] = True
        self.seat = E.create_seat(self.table, "Сойка", "local-test")
        self.play("claim", hero="H01")
        self.play("deal")

    def play(self, op, **data):
        result = E.apply(self.table, self.seat, {"op": op, **data})
        self.assertTrue(result["ok"], result)

    def pick(self, choice, paper=False):
        card = story.visible(self.table)
        result = story.choose(self.table, self.seat, {"scene": card["id"], "choice": choice, "paper":paper})
        self.assertTrue(result["ok"], (card, result))

    def go(self, *realms):
        for realm in realms:
            self.play("travel", dest=realm, dice=[6])

    def reach_court(self):
        self.pick("spoon")
        self.assertEqual("M001", self.table["scene"]["tokens"][-1]["ref"])
        self.pick("empty", paper=True)
        self.assertIn("медная крошка", self.table["party"]["clues"])
        self.assertFalse(story.visible(self.table)["choices"])
        self.go(3)
        card = story.visible(self.table)
        self.pick("loss")
        stale = story.choose(self.table, self.seat, {"scene": card["id"], "choice": "loss"})
        self.assertFalse(stale["ok"])
        self.assertFalse(story.visible(self.table)["choices"])
        self.go(5)
        self.pick("wall")
        self.pick("hidden")
        self.go(6)
        self.pick("arrive")
        self.assertEqual([5], [t["zone"] for t in self.table["scene"]["tokens"] if t["kind"] == "foe"])
        for _ in range(2):
            self.play("round")
            story.siege_wave(self.table, self.seat)
        story.siege_wave(self.table, self.seat)
        self.assertEqual([5, 6], [t["zone"] for t in self.table["scene"]["tokens"] if t["kind"] == "foe"])
        self.pick("lada")
        self.assertIn("свидетельство Лады", self.table["party"]["clues"])
        self.go(5, 3, 1)
        self.pick("enter")

    def test_prologue_and_surprises(self):
        self.assertEqual(set(E.HERO_BY), set(story.PERSONAL))
        self.assertEqual({2,3,4,5,7,8,9,10}, set(story.WITNESSES))
        payload = json.dumps(story.visible(self.table), ensure_ascii=False)
        self.assertNotIn("казначеи впервые", payload)
        for realm in E.realms:
            self.assertNotIn(realm[11], payload)
        before = E.serial(self.table).copy()
        denied = story.choose(self.table, self.seat, {"scene":"verdict","choice":"seal"})
        self.assertFalse(denied["ok"])
        self.assertEqual(before, E.serial(self.table))

    def test_decisions_reappear_after_reconnect(self):
        self.play("fork", side="a")
        self.reach_court()
        card = story.visible(self.table)
        self.assertIn(story.CALLBACKS["lada"], card["echoes"])
        self.assertIn(story.PERSONAL["H01"][0], card["echoes"])
        restored = E.restore(json.loads(json.dumps(E.serial(self.table))))
        self.assertEqual(card, story.visible(restored))
        self.pick("council")
        self.pick("trial")
        self.pick("keep")
        self.pick("descend")
        self.assertEqual("B001", self.table["scene"]["tokens"][-1]["ref"])
        self.assertEqual(6, self.table["scene"]["tokens"][-1]["zone"])
        self.assertFalse(self.table["scene"]["door"])
        self.pick("altar")
        self.assertFalse(self.table["scene"]["keeperBound"])
        self.pick("cancel")
        self.assertFalse(any(c["id"] == "cancel" for c in story.visible(self.table)["choices"]))
        self.pick("retreat")
        self.table["party"]["supplies"] = self.table["party"]["silver"] = 0
        self.pick("work")
        day = self.table["party"]["day"]
        self.pick("return")
        self.assertEqual(day + 1, self.table["party"]["day"])
        self.pick("treaty")
        self.table["party"].update(scars=3, debts=1)
        self.pick("rule")
        end = story.visible(self.table)
        self.assertTrue(end["ending"])
        self.assertEqual(E.endings[7][0], end["title"])
        for memory in ("обвинитель", "деревню", "долга", "переплётчиком"):
            self.assertIn(memory, end["text"])
        self.assertIn(story.CALLBACKS["spoon"], end["echoes"])

    def test_local_song_cost_and_coincident_rewards(self):
        self.pick("ribbon")
        self.pick("song-H01", paper=True)
        self.assertNotIn("I19", self.table["heroes"]["H01"]["potions"])
        self.assertEqual(1, self.table["party"]["street"])
        self.assertEqual(1, self.table["party"]["seals"])
        self.go(3)
        self.pick("testimony")
        self.assertEqual(2, self.table["party"]["level"])
        self.go(5)
        self.play("seal")  # Players have already recorded the second local quest.
        self.pick("paid")
        self.pick("families")
        self.assertEqual((2, 1), (self.table["party"]["level"], self.table["party"]["seals"]))

    def test_song_resolved_on_screen_is_charged_once(self):
        self.pick("ribbon")
        token = E.hero_token(self.table, "H01")["id"]
        self.play("move", id=token, zone=2)
        self.play("move", id=token, zone=3)
        self.play("bell", do="song", dice=[6, 6])
        self.assertNotIn("I19", self.table["heroes"]["H01"]["potions"])
        self.pick("song")
        self.assertEqual(2, self.table["party"]["chapter"])

    def test_eight_printed_endings(self):
        for index, choice in enumerate(("seal","seal","publish","publish","open","open","rule","rule")):
            with self.subTest(index=index):
                game = E.new_table()
                seat = E.create_seat(game, "Лада", "local-test")
                s = story.initial(game)
                game["story"] = s
                s["page"] = "verdict"
                s["knighted"] = index == 6
                if index == 0:
                    s["decisions"]["original"] = "crown"
                if index == 2:
                    game["party"]["street"] = 1
                if index == 4:
                    game["party"]["portals"][:2] = ["open", "open"]
                result = story.choose(game, seat, {"scene":"verdict","choice":choice})
                self.assertTrue(result["ok"])
                self.assertEqual(E.endings[index][0], story.visible(game)["title"])
                receipt = story.visible(game)["verdictReceipt"]
                self.assertEqual((E.endings[index][0], "Лада"), (receipt["title"], receipt["when"]["player"]))
                self.assertTrue(receipt["reason"])


if __name__ == "__main__":
    unittest.main()
