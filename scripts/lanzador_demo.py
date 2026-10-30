"""Lanzador de la demo: sirve la interfaz 'Generador de clips' con los 3 videos de ejemplo y abre el navegador. No requiere Python ni internet."""
import os, re, socket, sys, threading, time, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "demo"


class H(SimpleHTTPRequestHandler):
    """Servidor estático con soporte de Range para poder adelantar los videos."""
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(BASE), **k)

    def log_message(self, *a):
        pass

    def guess_type(self, path):
        """Declara UTF-8 en los textos: sin esto algunos navegadores muestran 'Ã³' en vez de 'ó'."""
        t = super().guess_type(path)
        return t + "; charset=utf-8" if t.startswith("text/") or t in ("application/javascript", "application/json") else t

    def send_head(self):
        rng = self.headers.get("Range")
        path = Path(self.translate_path(self.path))
        if not rng or not path.is_file():
            return super().send_head()
        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        size = path.stat().st_size
        a = int(m.group(1)) if m and m.group(1) else 0
        b = int(m.group(2)) if m and m.group(2) else size - 1
        b = min(b, size - 1)
        f = open(path, "rb"); f.seek(a)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        self.send_header("Content-Length", str(b - a + 1)); self.send_header("Accept-Ranges", "bytes"); self.end_headers()
        self._left = b - a + 1
        return f

    def copyfile(self, src, dst):
        left = getattr(self, "_left", None)
        try:
            if left is None:
                return super().copyfile(src, dst)
            while left > 0:
                buf = src.read(min(65536, left))
                if not buf: break
                dst.write(buf); left -= len(buf)
        except (ConnectionResetError, BrokenPipeError):
            pass


def libre(p=8770):
    for q in range(p, p + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", q)) != 0:
                return q
    return p


if __name__ == "__main__":
    if not (BASE / "index.html").exists():
        print("No se encontró la demo:", BASE); input("Enter para salir"); sys.exit(1)
    port = libre()
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    url = f"http://localhost:{port}/index.html"
    print("=" * 62, "\n  Generador de clips - demo de la tesis (3 videos de ejemplo)\n", "=" * 62)
    print(f"\n  Abriendo {url}\n  Cierra esta ventana para terminar.\n")
    threading.Thread(target=lambda: (time.sleep(0.8), webbrowser.open(url)), daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
