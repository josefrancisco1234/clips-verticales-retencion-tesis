"""Lanzador de la web de clips (se empaqueta como Clips_Web.exe). Arranca el servidor en esta PC y lo deja accesible en la red local.

Uso: Clips_Web.exe [CLAVE] [--internet]
  CLAVE       clave de acceso (se pide como ?k=CLAVE); si no se da, se usa la de CLAVE_WEB.txt o se genera una.
  --internet  además abre un túnel de Cloudflare (requiere cloudflared) para usarla fuera de la red local.
La carpeta del exe debe contener tesis/desarrollo, tesis_data (con .venv; crear con INSTALAR_ENTORNO.bat) y, opcionalmente, MIS_VIDEOS."""
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

HOME = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent.parent.parent
SERVER = HOME / "tesis" / "desarrollo" / "scripts" / "web_clips.py"
PORT = int(os.environ.get("PORT", "8765"))


def ips() -> list[str]:
    out = set()
    try:
        for r in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            if not r[4][0].startswith("127."):
                out.add(r[4][0])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            out.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(out)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    key_file = HOME / "CLAVE_WEB.txt"
    key = args[0] if args else (key_file.read_text(encoding="utf-8").strip() if key_file.is_file() else secrets.token_urlsafe(6))
    key_file.write_text(key, encoding="utf-8")
    data = HOME / "tesis_data"
    py = data / ".venv" / "Scripts" / "python.exe"
    if not SERVER.is_file():
        print("No encuentro tesis\desarrollo\scripts\web_clips.py junto al exe."); input("Enter para salir"); return 1
    if not py.is_file():
        print("Falta el entorno de Python. Ejecuta primero INSTALAR_ENTORNO.bat (una sola vez, necesita internet)."); input("Enter para salir"); return 1
    env = dict(os.environ, TESIS_HOME=str(HOME), TESIS_DATA=str(data), TESIS_PYTHON=str(py), HOST="0.0.0.0", ACCESS_KEY=key,
               PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    (HOME / "MIS_VIDEOS").mkdir(exist_ok=True)
    srv = subprocess.Popen([str(py), "-u", str(SERVER)], cwd=str(SERVER.parent.parent), env=env)
    time.sleep(3)
    print("\n=== Generador de clips ===")
    print(f"En esta PC:       http://localhost:{PORT}/?k={key}")
    for ip in ips():
        print(f"En tu red (wifi): http://{ip}:{PORT}/?k={key}")
    print("Si otra PC no abre el enlace, permite el puerto en el Firewall de Windows (aviso que aparece la primera vez).")
    tunnel = None
    if "--internet" in sys.argv:
        cf = shutil.which("cloudflared")
        if cf:
            print("Túnel a internet: busca abajo el enlace https://....trycloudflare.com y agrega /?k=" + key)
            tunnel = subprocess.Popen([cf, "tunnel", "--url", f"http://localhost:{PORT}"])
        else:
            print("Para internet instala cloudflared: winget install Cloudflare.cloudflared")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}/?k={key}")).start()
    try:
        srv.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (srv, tunnel):
            if p and p.poll() is None:
                p.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
