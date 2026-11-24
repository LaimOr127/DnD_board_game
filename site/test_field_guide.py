import unittest

import engine as E


class FieldGuideTest(unittest.TestCase):
    def test_atlas_exposes_people_and_card_ranges_with_earned_cave_details(self):
        table = E.new_table()
        public = E.compendium(None)
        heads = set()
        for r in public["realms"]:
            i = r["id"]
            with self.subTest(kingdom=i):
                guide = r["fieldGuide"]
                self.assertEqual(3, len(guide["residents"]))
                self.assertTrue(all(p["name"] and p["role"] and p["hook"] for p in guide["residents"]))
                self.assertTrue(all(guide[k] for k in ("head", "request", "crown", "terrain", "cave", "tracks")))
                heads.add(guide["head"])
                self.assertEqual(30, sum(m["area"] == i-1 for m in public["mobs"]))
                self.assertEqual(10, sum(b["area"] == i-1 for b in public["bosses"]))
                for key in ("dungeon", "floors", "pact", "portalHint"):
                    self.assertNotIn(key, r)
                self.assertNotIn(E.realms[i-1][8].casefold(), str(guide).casefold())
                table["party"]["deeds"] = [i]
                earned = E.compendium(table)["realms"][i-1]
                self.assertEqual(5, len(earned["floors"]))
                self.assertEqual(E.realms[i-1][8], earned["dungeon"])
                self.assertNotIn("portalHint", earned)
        self.assertEqual(10, len(heads))
