"""Yolla: telefondan Windows'a yerel ag uzerinden fotograf/video aktarimi.

Kullanim:
    python yolla.py [--port 8765] [--dir "D:\\Fotolar"]

Telefon ayni Wi-Fi'ye bagliyken terminaldeki QR kodu okut, dosyalari sec.
Her gonderim istegi terminalde onaylanmadan bilgisayara hicbir sey yazilmaz.
"""

import argparse
import hmac
import html
import io
import json
import os
import queue
import re
import secrets
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs

__version__ = "0.1.0"

CHUNK = 1024 * 1024
TOKEN_FILE = Path(__file__).with_name("token.txt")
APPROVAL_TIMEOUT = 300      # terminal yanit vermezse istek bu kadar saniye sonra reddedilir
DEVICE_GRANT_SECONDS = 600  # "tumu" yaniti bir cihaza bu kadar sure izin verir
MAX_FILES = 2000

PAGE = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Yolla</title>
<style>
  :root { color-scheme: light dark; --accent: #0a84ff; }
  body { font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 24px 16px;
         max-width: 520px; margin-inline: auto; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  p.sub { margin: 0 0 24px; opacity: .65; font-size: 15px; }
  label.pick { display: block; text-align: center; padding: 22px; border-radius: 14px;
               background: var(--accent); color: #fff; font-size: 18px; font-weight: 600; }
  label.pick.busy { opacity: .4; pointer-events: none; }
  input[type=file] { display: none; }
  ul { list-style: none; padding: 0; margin: 20px 0 0; }
  li { padding: 10px 0; border-bottom: 1px solid #8884; font-size: 14px; }
  .name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  progress { width: 100%; height: 6px; margin-top: 6px; }
  .ok { color: #30d158; } .err { color: #ff453a; }
  #summary { margin-top: 16px; font-weight: 600; }
</style>
</head>
<body>
<h1>Yolla</h1>
<p class="sub">Dosyalar bilgisayarda onaylandiktan sonra aktarilir.</p>
<label class="pick" id="pick">Fotograf / Video Sec
  <input id="f" type="file" multiple>
</label>
<div id="summary"></div>
<ul id="list"></ul>
<script>
const input = document.getElementById('f');
const pick = document.getElementById('pick');
const list = document.getElementById('list');
const summary = document.getElementById('summary');
const key = new URLSearchParams(location.search).get('k') || '';

function setStatus(row, text, cls) {
  const st = row.querySelector('.st');
  st.textContent = text;
  st.className = 'st ' + (cls || '');
}

function askApproval(files) {
  return fetch('/request?k=' + encodeURIComponent(key), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files: files.map(f => ({ name: f.name, size: f.size })) }),
  }).then(r => r.ok ? r.json() : null).catch(() => null);
}

function upload(file, row, grant) {
  return new Promise(resolve => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', '/upload/' + encodeURIComponent(file.name) +
             '?k=' + encodeURIComponent(key) + '&g=' + encodeURIComponent(grant));
    xhr.setRequestHeader('X-Last-Modified', String(file.lastModified || ''));
    const bar = row.querySelector('progress');
    xhr.upload.onprogress = e => { if (e.lengthComputable) bar.value = e.loaded / e.total; };
    xhr.onload = () => {
      const ok = xhr.status === 200;
      setStatus(row, ok ? 'Tamam' : 'Hata ' + xhr.status, ok ? 'ok' : 'err');
      bar.value = ok ? 1 : 0;
      resolve(ok);
    };
    xhr.onerror = () => { setStatus(row, 'Baglanti hatasi', 'err'); resolve(false); };
    xhr.send(file);
  });
}

input.addEventListener('change', async () => {
  const files = [...input.files];
  input.value = '';
  if (!files.length) return;
  pick.classList.add('busy');
  list.innerHTML = '';
  const rows = files.map(file => {
    const li = document.createElement('li');
    li.innerHTML = '<span class="name"></span><span class="st">Onay bekleniyor</span><progress max="1" value="0"></progress>';
    li.querySelector('.name').textContent = file.name + ' (' + (file.size / 1048576).toFixed(1) + ' MB)';
    list.appendChild(li);
    return li;
  });

  summary.textContent = 'Bilgisayarda onay bekleniyor...';
  const res = await askApproval(files);
  if (!res || !res.grant) {
    summary.textContent = 'Istek reddedildi.';
    summary.className = 'err';
    rows.forEach(r => setStatus(r, 'Reddedildi', 'err'));
    pick.classList.remove('busy');
    return;
  }
  summary.className = '';
  let done = 0;
  for (let i = 0; i < files.length; i++) {
    summary.textContent = (i + 1) + ' / ' + files.length + ' gonderiliyor...';
    if (await upload(files[i], rows[i], res.grant)) done++;
  }
  summary.textContent = done + ' / ' + files.length + ' dosya aktarildi.';
  pick.classList.remove('busy');
});
</script>
</body>
</html>
"""


class Approval:
    """Telefondan gelen, terminalde yanit bekleyen bir gonderim istegi."""

    def __init__(self, ip, files, single):
        self.ip = ip
        self.files = files      # [(ad, boyut), ...]
        self.single = single    # True: kestirmeden gelen tek dosya ("tumu" secenegi sunulur)
        self.answer = None      # "yes", "no" veya "all"
        self.done = threading.Event()
        self.abandoned = False


class Grants:
    """Onaylanmis istekler: hangi cihaz hangi dosyalari gonderebilir."""

    def __init__(self):
        self.lock = threading.Lock()
        self.batches = {}   # grant id -> (ip, {ad: [boyut, ...]})
        self.devices = {}   # ip -> izin bitis zamani

    def add_batch(self, ip, files):
        allowed = {}
        for name, size in files:
            allowed.setdefault(name, []).append(size)
        gid = secrets.token_urlsafe(12)
        with self.lock:
            self.batches[gid] = (ip, allowed)
        return gid

    def allow_device(self, ip):
        with self.lock:
            self.devices[ip] = time.time() + DEVICE_GRANT_SECONDS

    def device_allowed(self, ip):
        with self.lock:
            return self.devices.get(ip, 0) > time.time()

    def take(self, gid, ip, name, size):
        """Onayli listede varsa dosyayi listeden dus ve True don."""
        with self.lock:
            batch = self.batches.get(gid)
            if not batch or batch[0] != ip:
                return False
            sizes = batch[1].get(name)
            if not sizes or size not in sizes:
                return False
            sizes.remove(size)
            if not sizes:
                del batch[1][name]
            if not batch[1]:
                del self.batches[gid]
            return True


def pictures_dir():
    """Windows'ta OneDrive'a tasinmis olsa bile gercek Resimler klasoru."""
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD),
                            ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]

            folderid_pictures = GUID(0x33E28130, 0x4E1E, 0x4676,
                                     (ctypes.c_ubyte * 8)(0x83, 0x5A, 0x98, 0x39, 0x5C, 0x3B, 0xC3, 0xBB))
            buf = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folderid_pictures), 0, None,
                                                          ctypes.byref(buf)) == 0:
                path = Path(buf.value)
                ctypes.windll.ole32.CoTaskMemFree(buf)
                return path
        except Exception:
            pass
    return Path.home() / "Pictures"


def local_ip():
    """Varsayilan agdaki yerel IP adresini bul (paket gondermeden)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def load_token():
    """Kalici erisim anahtari: QR/adres bunu icerir, bilmeyen istek bile gonderemez."""
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="ascii").strip()
        if token:
            return token
    token = secrets.token_urlsafe(16)
    TOKEN_FILE.write_text(token, encoding="ascii")
    return token


def safe_name(raw):
    name = os.path.basename(raw.replace("\\", "/"))
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or f"dosya_{int(time.time())}"


def unique_path(dest, name):
    path = dest / name
    stem, suffix = path.stem, path.suffix
    n = 1
    while path.exists():
        path = dest / f"{stem} ({n}){suffix}"
        n += 1
    return path


def mb(n):
    return f"{n / 1048576:.1f} MB"


def make_handler(dest, token, approvals, grants):
    page = PAGE.encode("utf-8")

    def wait_for_answer(req):
        approvals.put(req)
        if not req.done.wait(APPROVAL_TIMEOUT):
            req.abandoned = True
            return "no"
        return req.answer

    class Handler(BaseHTTPRequestHandler):
        def authorized(self):
            given = parse_qs(urlsplit(self.path).query).get("k", [""])[0]
            if hmac.compare_digest(given.encode(), token.encode()):
                return True
            print(f"  !  anahtarsiz istek reddedildi <- {self.client_address[0]}")
            self.send_error(403)
            return False

        def reply(self, status, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if urlsplit(self.path).path not in ("/", "/index.html"):
                self.send_error(404)
                return
            if not self.authorized():
                return
            self.reply(200, page, "text/html; charset=utf-8")

        def do_POST(self):
            path = urlsplit(self.path).path
            if path.startswith("/upload/"):
                return self.do_PUT()
            if path != "/request":
                self.send_error(404)
                return
            if not self.authorized():
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    raise ValueError
                data = json.loads(self.rfile.read(length))
                files = [(str(f["name"]), int(f["size"])) for f in data["files"]]
                if not 0 < len(files) <= MAX_FILES or any(s < 0 for _, s in files):
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                self.send_error(400)
                return

            ip = self.client_address[0]
            if wait_for_answer(Approval(ip, files, single=False)) == "no":
                self.reply(403, {"rejected": True})
                return
            self.reply(200, {"grant": grants.add_batch(ip, files)})

        def do_PUT(self):
            parts = urlsplit(self.path)
            if not parts.path.startswith("/upload/"):
                self.send_error(404)
                return
            if not self.authorized():
                return
            length = self.headers.get("Content-Length")
            if length is None:
                self.send_error(411)
                return
            size = int(length)
            ip = self.client_address[0]
            raw_name = unquote(parts.path[len("/upload/"):])
            gid = parse_qs(parts.query).get("g", [""])[0]

            if gid:
                allowed = grants.take(gid, ip, raw_name, size)
            elif grants.device_allowed(ip):
                allowed = True
            else:
                # Kestirme gibi istemciler dosyalari tek tek, listesiz gonderir.
                answer = wait_for_answer(Approval(ip, [(raw_name, size)], single=True))
                if answer == "all":
                    grants.allow_device(ip)
                allowed = answer in ("yes", "all")
            if not allowed:
                print(f"  -  {raw_name} reddedildi <- {ip}")
                self.send_error(403)
                return

            target = unique_path(dest, safe_name(raw_name))
            tmp = target.with_name(target.name + ".part")
            remaining = size
            try:
                with open(tmp, "wb") as f:
                    while remaining > 0:
                        chunk = self.rfile.read(min(CHUNK, remaining))
                        if not chunk:
                            raise ConnectionError("baglanti erken kapandi")
                        f.write(chunk)
                        remaining -= len(chunk)
                tmp.replace(target)
            except Exception as e:
                tmp.unlink(missing_ok=True)
                print(f"  HATA  {target.name}: {e}")
                self.send_error(500)
                return

            mtime = self.headers.get("X-Last-Modified", "")
            if mtime.isdigit():
                ts = int(mtime) / 1000
                os.utime(target, (ts, ts))

            print(f"  +  {target.name}  ({mb(size)})")
            self.reply(200, b"OK\n", "text/plain")

        def log_message(self, *args):
            pass

    return Handler


def ask(req):
    """Terminalde onay sor; yaniti "yes", "no" veya "all" olarak dondur."""
    total = sum(s for _, s in req.files)
    print()
    print(f"  >> {req.ip} {len(req.files)} dosya gondermek istiyor ({mb(total)}):")
    for name, size in req.files[:10]:
        print(f"       {name}  ({mb(size)})")
    if len(req.files) > 10:
        print(f"       ... ve {len(req.files) - 10} dosya daha")

    if req.single:
        prompt = f"  Kabul edilsin mi? [e]vet / [h]ayir / [t]umu ({DEVICE_GRANT_SECONDS // 60} dk bu cihazdan hepsi): "
    else:
        prompt = "  Kabul edilsin mi? [e/H]: "
    reply = input(prompt).strip().lower()
    if reply in ("e", "evet", "y", "yes"):
        return "yes"
    if req.single and reply in ("t", "tumu", "tümü", "a", "all"):
        return "all"
    return "no"


def main():
    # Telefondan gelen dosya adlarinda emoji vb. olabilir; yazdirirken cokmesin.
    sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Telefondan Windows'a fotograf aktarimi")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--dir", type=Path, default=pictures_dir() / "Yolla")
    parser.add_argument("--version", action="version", version=f"Yolla {__version__}")
    args = parser.parse_args()

    dest = args.dir.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    token = load_token()
    url = f"http://{local_ip()}:{args.port}/?k={token}"
    approvals = queue.Queue()
    handler = make_handler(dest, token, approvals, Grants())
    server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print()
    print(f"  Yolla {__version__} calisiyor")
    print(f"  Telefonda ac:   {url}")
    print(f"  Kayit klasoru:  {dest}")
    print()
    print_qr(url)
    print("  Gelen istekler burada onayina sunulacak. Durdurmak icin Ctrl+C\n")

    # Onay sorulari ana thread'de sirayla sorulur; boylece Ctrl+C her an calisir.
    try:
        while True:
            try:
                req = approvals.get(timeout=0.5)
            except queue.Empty:
                continue
            answer = ask(req)
            if req.abandoned:
                print("  (Sure dolmustu, istek zaten iptal edildi.)")
            else:
                req.answer = answer
                req.done.set()
                print("  Onaylandi." if answer != "no" else "  Reddedildi.")
    except (KeyboardInterrupt, EOFError):
        print("\n  Kapatildi.")
    finally:
        server.shutdown()


def print_qr(url):
    try:
        import qrcode
    except ImportError:
        print("  (QR kod icin: pip install qrcode)")
        return
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    out = io.StringIO()
    qr.print_ascii(out=out, invert=True)
    try:
        "█▀▄".encode(sys.stdout.encoding or "ascii")
    except UnicodeEncodeError:
        # Cikti dosyaya/boruya yonlendirilmisse blok karakterler yazilamayabilir.
        print("  (QR kod bu ciktida gosterilemiyor, adresi elle ac.)")
        return
    print(out.getvalue(), end="")


if __name__ == "__main__":
    main()
