"""Exercise road stories through the shared LAN and browser room actions."""
import json
import unittest
from unittest.mock import patch

import engine as E
import roadside
import service
import story


class RoadStories(unittest.TestCase):
    def start(self, realm=1, chapter=1):
        self.table = E.new_table()
        self.host = E.create_seat(self.table, "Ведущий", "host")
        self.guest = E.create_seat(self.table, "Друг", "guest")
        self.table["host"] = self.host
        self.table["party"].update(realm=realm, chapter=chapter)
        self.party = self.table["party"]

    def act(self, op, **fields):
        result = service.act(self.table, self.host, {"op": op, **fields})
        self.assertTrue(result["ok"], result)
        return result

    def meet(self, choice):
        self.act("meeting", realm=self.party["realm"], chapter=self.party["chapter"], choice=choice)

    def view(self):
        return service.snapshot(self.table, self.guest)["story"]

    def pick(self, key):
        self.act("story", scene=self.view()["id"], choice=key)

    def test_every_kingdom_hero_and_choice_through_the_next_chapter(self):
        self.assertEqual(set(range(1, len(E.realms) + 1)), set(roadside.MEETINGS))
        self.assertEqual(set(E.HERO_BY), {hero for m in roadside.MEETINGS.values() for hero in m.voices})
        for realm, meeting in roadside.MEETINGS.items():
            self.assertEqual(2, len(meeting.paths))
            for choice, path in meeting.paths.items():
                with self.subTest(realm=realm, choice=choice):
                    self.start(realm)
                    hero, other = meeting.voices
                    self.act("claim", hero=hero)
                    self.assertEqual("rumour", self.view()["meeting"]["stage"])
                    self.assertNotIn(meeting.secret, json.dumps(self.view(), ensure_ascii=False))
                    self.meet("listen")
                    self.assertEqual([meeting.voices[hero]], self.view()["meeting"]["voices"])
                    self.assertTrue(service.act(self.table, self.guest, {"op": "claim", "hero": other})["ok"])
                    opening = self.view()["meeting"]
                    self.assertEqual(meeting.secret, opening["text"])
                    self.assertEqual(list(meeting.voices.values()), opening["voices"])
                    self.assertEqual(set(meeting.paths), {c["id"] for c in opening["choices"]})
                    self.meet(choice)
                    self.assertEqual(path.immediate, self.view()["meeting"]["text"])
                    self.assertEqual("", self.view()["roadJournal"][0]["news"])
                    self.assertNotIn(path.news, service.narration(self.table, "Какие вести?"))
                    self.table["story"]["page"] = "bell"
                    self.pick("empty")
                    view = self.view()
                    entry, = view["roadJournal"]
                    self.assertEqual([E.HERO_BY[h]["name"] for h in (hero, other)], entry["witnesses"])
                    self.assertEqual("Глава 2", entry["arrival"])
                    self.assertIn(path.news, entry["news"])
                    self.assertEqual([entry["news"]], view["news"])
                    self.assertIn(path.news, service.narration(self.table, "Какие вести?"))
                    alternative = next(p for k, p in meeting.paths.items() if k != choice)
                    self.assertNotIn(alternative.news, json.dumps(view, ensure_ascii=False))
                    before = json.dumps(E.serial(self.table))
                    roadside.deliver(self.table, self.host, self.table["story"])
                    self.assertEqual(before, json.dumps(E.serial(self.table)))
                    restored = E.restore(json.loads(before))
                    self.assertEqual(view, service.snapshot(restored, self.guest)["story"])

    def test_permissions_blockers_stale_choice_and_return(self):
        self.start()
        self.assertIsNone(self.view()["meeting"])
        self.act("claim", hero="H01")
        args = {"op": "meeting", "realm": 1, "chapter": 1, "choice": "listen"}
        for key in ("weatherDue", "fightDue"):
            self.party[key] = True
            self.assertIsNone(self.view()["meeting"])
            self.assertFalse(service.act(self.table, self.host, args)["ok"])
            self.party[key] = False
        self.act("scene", kind="bell")
        self.assertIsNone(self.view()["meeting"])
        self.act("end")
        self.assertFalse(service.act(self.table, self.guest, args)["ok"])
        for change in ({"realm": 2}, {"chapter": 2}, {"rev": -1}, {"choice": "supper"}):
            self.assertFalse(service.act(self.table, self.host, {**args, **change})["ok"])
        self.meet("listen")
        self.meet("supper")
        self.assertFalse(service.act(self.table, self.host, {**args, "choice": "tablecloth"})["ok"])
        with patch.object(self.table["rng"], "randint", return_value=2):
            self.act("travel", dest=3)
            self.assertEqual("open", self.view()["meeting"]["stage"])
            self.assertEqual([], self.view()["meeting"]["voices"])
            self.act("travel", dest=1)
            self.assertEqual("settled", self.view()["meeting"]["stage"])
        self.party["flags"].append("calmRoad")
        self.act("travel", dest=8)
        self.assertEqual("rumour", self.view()["meeting"]["stage"])

    def test_three_new_choices_change_the_main_scenes(self):
        for realm, decision, chapter, page, added in (
                (2, "testify", 4, "hearing", "widows"), (4, "pilots", 3, "gate", "boats"),
                (9, "rest", 5, "heart", "silence")):
            with self.subTest(added=added):
                self.start(realm, chapter - 1)
                self.act("claim", hero="H01")
                self.meet("listen")
                self.meet(decision)
                history = self.table["story"]
                history["page"] = page
                self.assertNotIn(added, [c["id"] for c in self.view()["choices"]])
                self.party["chapter"] = chapter
                roadside.deliver(self.table, self.host, history)
                day = self.party["day"]
                self.party["supplies"] = 0
                self.pick(added)
                if added == "boats":
                    self.assertEqual(3, self.party["supplies"])
                    self.assertIn("свидетельство Лады", self.party["clues"])
                    history["page"] = "hearing"
                    self.assertIn(story.CALLBACKS["boats"], self.view()["echoes"])
                elif added == "widows":
                    self.assertEqual((day, 1, "original"), (self.party["day"], self.party["street"], history["page"]))
                else:
                    self.assertTrue(history["usedSilence"])
                    self.assertNotIn(added, [c["id"] for c in self.view()["choices"]])

    def test_late_delivery_and_last_voice_count_before_the_ending(self):
        self.start(4, 5)
        self.act("claim", hero="H04")
        self.meet("listen")
        self.meet("pilots")
        self.party.update(realm=8, supplies=6)
        self.meet("listen")
        self.meet("commons")
        self.table["story"]["page"] = "verdict"
        self.pick("publish")
        final = self.view()
        self.assertEqual(E.endings[2][0], final["title"])
        self.assertIsNone(final["meeting"])
        self.assertEqual(["Эпилог", "Эпилог"], [r["arrival"] for r in final["roadJournal"]])
        self.assertIn(roadside.LATE_NEWS[4, "pilots"][1], final["news"][0])
        self.assertEqual(6, self.party["supplies"])
        self.assertEqual(1, self.party["street"])


if __name__ == "__main__":
    unittest.main()
