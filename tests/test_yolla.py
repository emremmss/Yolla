"""Uctan uca testler: yolla.py'yi gercek bir sureç olarak baslatir, terminal
onaylarini stdin'den verir ve HTTP uzerinden yukleme yapar."""

import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class YollaTest(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())
        port = free_port()
        self.base = f"http://127.0.0.1:{port}"
        self.proc = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "yolla.py"), "--port", str(port), "--dir", str(self.out)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        self.token = (ROOT / "token.txt").read_text().strip()

    def tearDown(self):
        self.proc.kill()
        self.proc.wait()
        self.proc.stdin.close()
        shutil.rmtree(self.out, ignore_errors=True)

    def answer(self, text):
        # Yanit onceden yazilir; sunucu soruyu sordugunda stdin'den okur.
        self.proc.stdin.write(text + "\n")
        self.proc.stdin.flush()

    def call(self, method, path, body=b""):
        req = urllib.request.Request(self.base + path, data=body, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, b""

    def request(self, files):
        body = json.dumps({"files": [{"name": n, "size": s} for n, s in files]}).encode()
        return self.call("POST", f"/request?k={self.token}", body)

    def saved(self):
        return sorted(p.name for p in self.out.iterdir())

    def test_sayfa_anahtar_ister(self):
        self.assertEqual(self.call("GET", "/")[0], 403)
        self.assertEqual(self.call("GET", "/?k=yanlis")[0], 403)
        self.assertEqual(self.call("GET", f"/?k={self.token}")[0], 200)

    def test_onaylanan_istek_yalnizca_listedeki_dosyalari_kabul_eder(self):
        self.answer("e")
        status, body = self.request([("IMG_1.HEIC", 3), ("IMG_2.MOV", 5)])
        self.assertEqual(status, 200)
        g = json.loads(body)["grant"]
        up = lambda name, data: self.call("PUT", f"/upload/{name}?k={self.token}&g={g}", data)[0]

        self.assertEqual(up("IMG_1.HEIC", b"abc"), 200)
        self.assertEqual(up("evil.exe", b"abcde"), 403)      # listede yok
        self.assertEqual(up("IMG_2.MOV", b"abcdefgh"), 403)  # boyut farkli
        self.assertEqual(up("IMG_2.MOV", b"abcde"), 200)
        self.assertEqual(up("IMG_1.HEIC", b"abc"), 403)      # ikinci kez
        self.assertEqual(self.saved(), ["IMG_1.HEIC", "IMG_2.MOV"])

    def test_reddedilen_istek_dosya_yazmaz(self):
        self.answer("h")
        self.assertEqual(self.request([("a.jpg", 1)])[0], 403)
        self.assertEqual(self.saved(), [])

    def test_kestirme_tumu_secenegi(self):
        self.answer("t")
        self.assertEqual(self.call("PUT", f"/upload/S1.jpg?k={self.token}", b"x")[0], 200)
        self.assertEqual(self.call("PUT", f"/upload/S2.jpg?k={self.token}", b"y")[0], 200)
        self.assertEqual(self.saved(), ["S1.jpg", "S2.jpg"])

    def test_zararli_dosya_adi_klasor_disina_cikamaz(self):
        self.answer("e")
        self.assertEqual(self.call("PUT", f"/upload/..%2F..%2Fkotu.txt?k={self.token}", b"x")[0], 200)
        self.assertEqual(self.saved(), ["kotu.txt"])


if __name__ == "__main__":
    unittest.main()
