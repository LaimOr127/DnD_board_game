import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from server import GameServer


class SharedTableTest(unittest.TestCase):
    def test_two_devices_rejoin_and_keep_physical_roll_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "rooms.db"
            host, guest = (urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())) for _ in range(2))
            def serve():
                server = GameServer(("127.0.0.1", 0), db)
                server.ai_key = server.local_model = None
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                return server

            def api(client, path, **body):
                payload = json.dumps(body).encode() if body else None
                url = f"http://127.0.0.1:{server.server_port}/api/" + path
                req = urllib.request.Request(url, payload, {"Content-Type": "application/json"})
                with client.open(req, timeout=5) as response:
                    return json.load(response)["state"]

            server = serve()
            try:
                first = api(host, "create", name="Вера")
                code = first["code"]
                second = api(guest, "join", name="Юра", code=code)
                api(host, "action", op="claim", hero="H01")
                api(host, "action", op="deal")
                api(guest, "action", op="claim", hero="H07")
                with self.assertRaises(urllib.error.HTTPError):
                    api(guest, "action", op="seal")
                api(guest, "action", op="roll", kind="check", stat="will", dc=9, source="table", faces=[4, 5])
                api(guest, "action", op="pencil", text="Мой секрет")
                state = api(host, "state")
                self.assertNotIn("Мой секрет", str(state))
                self.assertEqual(state["party"]["silver"], 8)
                rolled = next(x["dice"] for x in reversed(state["log"]) if x["dice"])
                self.assertEqual((rolled["faces"], rolled["source"]), ([4, 5], "table"))
                with self.assertRaises(urllib.error.HTTPError):
                    api(guest, "action", op="roll", kind="check", source="table", faces=[4, 8], spark=True)
                self.assertEqual(api(guest, "state")["heroes"]["H07"]["sparks"], 3)
                api(host, "action", op="story", scene="prologue", choice="ribbon")
                seen = api(guest, "state")
                self.assertTrue(any(t["ref"] == "M001" for t in seen["scene"]["tokens"]))
                self.assertEqual(seen["story"]["id"], "bell")
                api(guest, "gm", question="Зачитай текущую сцену")
                self.assertIn("Сказитель", api(host, "state")["log"][-1]["text"])
                with self.assertRaises(urllib.error.HTTPError):
                    api(host, "action", op="round", rev=first["rev"])
                self.assertEqual(second["you"]["id"], api(guest, "join", name="Юра", code=code)["you"]["id"])
            finally:
                server.shutdown()
                server.server_close()
            server = serve()
            try:
                again = api(guest, "state")
                self.assertEqual(again["you"]["heroId"], "H07")
                self.assertEqual(again["heroes"]["H07"]["pencil"], "Мой секрет")
                self.assertEqual(again["story"]["id"], "bell")
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
