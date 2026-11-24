import itertools
import unittest

import checkpoints
import engine as E
import freeplay
import service


class FreeplayTest(unittest.TestCase):
    def test_exact_dice_chances_against_enumeration_and_extremes(self):
        self.assertAlmostEqual(freeplay.chance(2, 6, 1, 9), 100*15/36)
        for count in (1, 2, 3):
            totals = [sum(f) for f in itertools.product(range(1, 5), repeat=count)]
            for target in range(-2, 16):
                self.assertAlmostEqual(freeplay.chance(count, 4, -1, target),
                                       100*sum(t-1 >= target for t in totals)/len(totals))
        self.assertEqual(0, freeplay.chance(10, 100, -1, 1000))
        self.assertAlmostEqual(1e-18, freeplay.chance(10, 100, 0, 1000), delta=1e-28)

    def test_sheet_and_physical_dice_belong_to_their_room_and_snapshot(self):
        t = E.new_table()
        service.configure_table(t, {"mode":"free", "title":"Поход за светом"})
        a = E.create_seat(t, "Роман", "key")
        b = E.create_seat(t, "Маша", "friend")
        t["host"] = a
        def play(op, **kw):
            return service.act(t, b, {"op":op, "rev":t["rev"], **kw})["ok"]
        self.assertTrue(play("freeSheet", name="Мышка", hp=14, maxHp=25, energy=3, maxEnergy=9, power=4))
        roll = {"count":2, "sides":6, "modifier":1, "target":9}
        for faces in ([1], [True,5], [5,7], None):
            self.assertFalse(play("freeRoll", faces=faces, **roll))
        self.assertTrue(play("freeRoll", faces=[5,3], **roll))
        self.assertFalse(play("story", scene="prologue", choice="ribbon"))
        view = service.snapshot(t, a)
        self.assertEqual("Роман", view["freeplay"]["sheets"][a]["name"])
        row, = view["freeplay"]["rolls"]
        self.assertEqual(("Маша", True, 9, "table"), (row["player"], row["success"], row["total"], row["source"]))
        self.assertIsNone(view["story"])
        checkpoints.apply(t, b, {"op":"save", "rev":t["rev"]})
        self.assertTrue(play("freeRoll", **roll))
        checkpoints.apply(t, a, {"op":"restore", "rev":t["rev"], "id":1})
        self.assertEqual(view["freeplay"], service.snapshot(t, a)["freeplay"])
        self.assertFalse(play("freeRoll", **roll))
