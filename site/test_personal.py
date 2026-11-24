import json
import unittest

import engine as E
import personal
import service
import story


class PersonalPromiseTest(unittest.TestCase):
    def prepare(self, hid):
        self.table = E.new_table()
        self.host = E.create_seat(self.table, "Алексей", "host")
        self.friend = E.create_seat(self.table, "Лея", "guest")
        self.table["host"] = self.host
        self.hid = hid
        self.quest = personal.QUESTS[hid]
        for sid, hero in [(self.host, hid), (self.friend, "H02" if hid == "H01" else "H01")]:
            self.assertTrue(service.act(self.table, sid, {"op": "claim", "hero": hero})["ok"])
        self.party = self.table["party"]

    def sign(self, sid, choice, ok=True):
        cmd = {"op": "promise", "hero": self.table["seats"][sid]["heroId"], "realm": self.party["realm"],
               "chapter": self.party["chapter"], "parcel": self.hid, "choice": choice}
        before = json.dumps(E.serial(self.table))
        result = service.act(self.table, sid, cmd)
        self.assertEqual(ok, result["ok"], result)
        if not ok:
            self.assertEqual(before, json.dumps(E.serial(self.table)))

    def end(self):
        self.table.setdefault("story", story.initial(self.table))["page"] = "verdict"
        self.party["chapter"] = 5
        self.assertTrue(story.choose(self.table, self.host, {"scene": "verdict", "choice": "open"})["ok"])
        return story.visible(self.table)["echoes"]

    def test_every_owner_both_decisions_receipt_and_finale(self):
        self.assertEqual(set(personal.QUESTS), set(E.HERO_BY))
        self.assertEqual(set(range(1, 11)), {q.reply_realm for q in personal.QUESTS.values()})
        for hid, quest in personal.QUESTS.items():
            self.assertNotEqual(quest.realm, quest.reply_realm)
            self.assertEqual(2, len(quest.paths))
            for branch, path in quest.paths.items():
                with self.subTest(hero=hid, choice=branch):
                    self.prepare(hid)
                    self.assertNotIn(quest.title, str(service.snapshot(self.table, self.friend)["story"]))
                    self.sign(self.friend, "take", False)
                    self.sign(self.host, "take")
                    self.party["realm"] = quest.reply_realm
                    self.sign(self.host, branch, False)
                    self.party["realm"] = quest.realm
                    self.sign(self.friend, branch, False)
                    self.sign(self.host, branch)
                    self.sign(self.host, "receive", False)
                    self.party["realm"] = quest.reply_realm
                    self.party["glory"][quest.reply_realm - 1] = 3 if branch == "a" else 4
                    self.sign(self.friend, "receive")
                    self.sign(self.host, "receive", False)
                    record = self.table["story"]["personalPromises"][hid]
                    receipt = record["receipt"]
                    self.assertEqual(("Алексей", "Лея", path.scene, path.reply, 4),
                                     (record["closed"]["player"], receipt["when"]["player"], record["scene"],
                                      receipt["text"], self.party["glory"][quest.reply_realm - 1]))
                    self.assertIn(path.epilogue, self.end())

    def test_missed_answers_and_unfinished_words(self):
        self.prepare("H01")
        self.sign(self.host, "take")
        self.table["party"]["fightDue"] = True
        self.table["party"]["realm"] = self.quest.realm
        self.sign(self.host, "a", False)
        self.table["party"]["fightDue"] = False
        self.assertIn(self.quest.unfinished, self.end())
        self.assertNotIn("receipt", self.table["story"]["personalPromises"]["H01"])
        self.prepare("H01")
        self.sign(self.host, "take")
        self.party["realm"] = self.quest.realm
        self.sign(self.host, "b")
        self.assertIn(self.quest.paths["b"].epilogue, self.end())
        receipt = self.table["story"]["personalPromises"]["H01"]["receipt"]
        self.assertEqual(("courier", [], self.quest.paths["b"].reply), (receipt["mode"], receipt["changes"], receipt["text"]))
        self.assertEqual([0]*10, self.party["glory"])
        self.assertNotIn(personal.QUESTS["H02"].unfinished, story.visible(self.table)["echoes"])
