import unittest
from unittest.mock import Mock

import engine as E
import service
import story


class FirstChapterTest(unittest.TestCase):
    def setUp(self):
        self.table = E.new_table()
        self.host = E.create_seat(self.table, "Анна", "host")
        self.guest = E.create_seat(self.table, "Глеб", "guest")
        self.table["host"] = self.host
        self.act(self.host, "claim", hero="H01")
        self.act(self.guest, "claim", hero="H16")
        self.act(self.host, "story", scene="prologue", choice="ribbon")
        self.scene = self.table["scene"]
        self.party = self.table["party"]
        self.hound = self.scene["tokens"][-1]

    def act(self, seat, op, ok=True, **fields):
        result = service.act(self.table, seat, {"op":op, **fields})
        self.assertEqual(ok, result["ok"], result)

    def move(self, seat, hero, zone, **fields):
        self.act(seat, "move", id=E.hero_token(self.table,hero)["id"], zone=zone, **fields)

    def advance(self, dice=(1,1)):
        self.table["rng"] = Mock()
        self.table["rng"].randint.side_effect = list(dice)
        self.act(self.host, "enemies")
        self.act(self.host, "enemies", ok=False)
        self.act(self.host, "round")

    def test_printed_victory(self):
        self.assertEqual((8,3),(self.party["silver"],self.party["supplies"]))
        self.act(self.host,"story",ok=False,scene="bell",choice="tongue")
        self.act(self.host,"round",ok=False)
        self.move(self.host,"H01",2)
        self.move(self.guest,"H16",2)
        self.act(self.host,"roll",ok=False,kind="attack",target=self.hound["id"],source="table",faces=[3,5])
        self.assertFalse(self.hound.get("attacked",False))
        self.act(self.host,"roll",kind="attack",target=self.hound["id"],source="table",faces=[2,3,5])
        self.assertEqual(1,self.hound["hp"])
        self.act(self.guest,"bell",do="shield")
        self.move(self.guest,"H16",3,run=True,ok=False)
        self.advance((4,4))
        h = self.table["heroes"]["H01"]
        self.assertEqual((6,["надлом"]),(h["hp"],h["conditions"]))
        self.act(self.host,"roll",kind="attack",target=self.hound["id"],source="table",faces=[2,3])
        self.act(self.guest,"roll",kind="attack",target=self.hound["id"],source="table",faces=[3,4])
        self.move(self.guest,"H16",4)
        self.act(self.guest,"bell",do="tongue",ok=False)
        self.advance(())
        self.act(self.guest,"bell",do="tongue")
        self.act(self.host,"story",scene="bell",choice="tongue")
        self.act(self.host,"story",scene="bell",choice="tongue",ok=False)
        self.assertEqual((2,11,1,"trace"),(self.party["chapter"],self.party["silver"],self.party["seals"],self.party["portals"][0]))
        self.assertEqual(["медь"],self.party["clues"])

    def test_third_round_timeout(self):
        self.act(self.host,"story",ok=False,scene="bell",choice="empty")
        for _ in range(3):
            self.advance()
        self.assertEqual(["empty"],[c["id"] for c in story.visible(self.table)["choices"]])
        self.act(self.guest,"bell",do="hold",ok=False)
        self.act(self.host,"story",scene="bell",choice="empty")
        self.assertEqual((2,8,0,1),(self.party["chapter"],self.party["silver"],self.party["seals"],self.party["tide"]))
        self.assertEqual(["медная крошка"],self.party["clues"])

    def test_hold_requires_position_and_two_actions(self):
        self.act(self.guest,"bell",do="hold",ok=False,source="table",faces=[4,4])
        self.move(self.guest,"H16",2)
        self.move(self.guest,"H16",3,run=True)
        self.act(self.guest,"bell",do="hold",ok=False,source="table",faces=[4,4])
        self.advance(())
        self.act(self.guest,"bell",do="hold",source="table",faces=[2,3])
        self.act(self.guest,"bell",do="hold",ok=False,source="table",faces=[2,3])
        self.advance((1,1))
        self.act(self.guest,"bell",do="hold",source="table",faces=[2,3])
        self.assertEqual("коромысло",self.scene["goal"])
        self.act(self.host,"story",scene="bell",choice="hold")
        self.assertEqual(1,self.party["street"])
