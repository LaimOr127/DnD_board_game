import unittest

import engine as E
from service import act


class PlayableMapTest(unittest.TestCase):
    def setUp(self):
        self.t = E.new_table()
        self.host = E.create_seat(self.t, "Лада", "host")
        self.guest = E.create_seat(self.t, "Лиор", "guest")
        self.t["host"] = self.host
        self.p = self.t["party"]

    def test_road_price_and_physical_die_use_one_shared_turn(self):
        cmd = {"op":"travel", "dest":4, "pay":"supply", "faces":[3]}
        self.assertFalse(act(self.t,self.guest,cmd)["ok"])
        self.assertFalse(act(self.t,self.host,{**cmd,"faces":[7]})["ok"])
        self.assertEqual((1,0,3),(self.p["realm"],self.p["day"],self.p["supplies"]))
        self.assertTrue(act(self.t,self.host,cmd)["ok"])
        self.assertEqual((4,1,3),(self.p["realm"],self.p["day"],self.p["supplies"]))
        self.assertIn("Настольный d6=3",self.t["log"][-1]["text"])

    def test_arcs_need_two_open_ends_and_do_not_roll_or_advance_day(self):
        cmd={"op":"travel","via":"portal","dest":10,"pay":"supply"}
        for state in ("unknown","trace"):
            self.p["portals"][0]="open"
            self.p["portals"][9]=state
            self.assertFalse(act(self.t,self.host,cmd)["ok"])
        self.p["portals"][9]="open"
        self.assertTrue(act(self.t,self.host,cmd)["ok"])
        self.assertEqual((10,0,2,None),(self.p["realm"],self.p["day"],self.p["supplies"],self.p["lastRoad"]))
        self.p["fightDue"]=True
        self.assertFalse(act(self.t,self.host,{**cmd,"dest":1,"pay":"tide"})["ok"])
        self.p["fightDue"]=False
        self.assertTrue(act(self.t,self.host,{**cmd,"dest":1,"pay":"tide"})["ok"])
        self.assertEqual((1,0,1),(self.p["realm"],self.p["day"],self.p["tide"]))

    def test_tactical_step_checks_owner_edges_and_closed_door(self):
        self.assertTrue(act(self.t,self.guest,{"op":"claim","hero":"H01"})["ok"])
        self.assertTrue(act(self.t,self.host,{"op":"scene","kind":"dungeon"})["ok"])
        token=E.hero_token(self.t,"H01")
        token["zone"]=5
        cmd={"op":"move","id":token["id"],"zone":4}
        self.assertFalse(act(self.t,self.host,cmd)["ok"])
        self.assertFalse(act(self.t,self.guest,{**cmd,"zone":1})["ok"])
        self.assertFalse(act(self.t,self.guest,{**cmd,"zone":6})["ok"])
        self.assertTrue(act(self.t,self.guest,cmd)["ok"])
        self.assertEqual(4,token["zone"])

    def test_all_character_cards_share_printed_profiles(self):
        cards=E.HERO_CARDS + E.BESTIARY_MOBS + E.BESTIARY_BOSSES
        self.assertEqual(418,len({c["id"] for c in cards}))
        for c in cards:
            with self.subTest(c=c["id"]):
                p=c["profile"]
                self.assertTrue(p["story"] and p["passive_name"] and p["passive"] and p["counter"])
                if c["id"][0]!="H":
                    self.assertEqual(c["loss"],p["defeat"])
