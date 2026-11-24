import json
import unittest

import checkpoints
import engine as E
import service


# A 4 × 3 JPEG generated locally. The shipped engine has no image-library dependency.
JPEG = ("/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAx"
        "NDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
        "MjIyMjIyMjL/wAARCAADAAQDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QA"
        "FQEBAQAAAAAAAAAAAAAAAAAABgf/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCLAGVxf//Z")


class CheckpointTest(unittest.TestCase):
    def setUp(self):
        self.t = E.new_table()
        self.h = E.create_seat(self.t, "Мария", "host-ticket")
        self.g = E.create_seat(self.t, "Алексей", "guest-ticket")
        self.t["host"] = self.h
        service.act(self.t, self.h, {"op":"claim", "hero":"H01"})

    def save(self, op, who=None, **opts):
        return checkpoints.apply(self.t, who or self.h, {"op": op, "rev": self.t["rev"], **opts})

    def test_photo_is_separate_and_restore_keeps_new_seats_and_future(self):
        service.act(self.t, self.h, {"op":"story","scene":"prologue","choice":"ribbon"})
        self.save("save", self.g, photo=JPEG, note="Фигуры у моста", author="подмена")
        state = service.snapshot(self.t, self.g)
        point, = state["session"]["points"]
        self.assertEqual(("Алексей", 1, True), (point["author"], point["round"], point["hasPhoto"]))
        for private in (JPEG, "snapshot", "host-ticket"):
            self.assertNotIn(private, json.dumps(state))
        self.assertEqual({"photo":JPEG}, self.save("photo", self.g, id=point["id"]))
        self.assertTrue(service.act(self.t, self.h, {"op":"enemies"})["ok"])
        self.assertTrue(service.act(self.t, self.h, {"op":"round"})["ok"])
        later = E.create_seat(self.t, "Варя", "new-ticket")
        service.act(self.t, later, {"op":"claim", "hero":"H06"})
        previous_rev = self.t["rev"]
        self.save("restore", id=point["id"])
        self.assertEqual(1, self.t["scene"]["round"])
        self.assertGreater(self.t["rev"], previous_rev)
        self.assertEqual(self.t["seats"][later]["token"], "new-ticket")
        self.assertIsNone(self.t["seats"][later]["heroId"])
        self.assertEqual("H01", self.t["seats"][self.h]["heroId"])
        self.assertEqual("paused", checkpoints.status(self.t))
        backup = checkpoints.summary(self.t)["points"][0]
        self.assertEqual("before_restore", backup["kind"])
        self.save("restore", id=backup["id"])
        self.assertEqual(2, self.t["scene"]["round"])
        self.assertEqual(JPEG, self.save("photo", id=point["id"])["photo"])

    def test_roles_bad_input_stale_version_and_transitions(self):
        for op in ("pause", "finish", "resume", "restore"):
            with self.assertRaises(PermissionError):
                self.save(op, self.g)
        original = self.t["rev"]
        for args in ({"rev":False}, {"rev":original-1}, {"photo":"text"}, {"photo":JPEG[:-4]}, {"note":"х"*281}):
            with self.assertRaises(ValueError):
                self.save("save", **args)
            self.assertEqual(original, self.t["rev"])
        self.save("pause")
        self.assertFalse(service.act(self.t, self.g, {"op":"note", "text":"не принят"})["ok"])
        self.save("save", self.g)
        self.save("finish")
        self.assertFalse(service.snapshot(self.t, self.h)["story"]["ending"])
        self.t = E.restore(json.loads(json.dumps(E.serial(self.t))))
        self.assertEqual("finished", checkpoints.status(self.t))
        self.save("resume")
        self.assertTrue(service.act(self.t, self.g, {"op":"approach", "scene":"prologue", "way":"talk",
                                                    "text":"Договорились с паромщиком"})["ok"])
        record, = service.snapshot(self.t, self.h)["story"]["approaches"]
        self.assertEqual("Алексей", record["when"]["player"])
