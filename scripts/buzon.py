"""Buzón entre las dos máquinas: laptop (CPU) y pc-gpu. Transporte: carpeta sincronizada por Syncthing.

Cada máquina **sólo escribe su propio archivo**, así que Syncthing nunca genera conflictos:

    <buzon>/de_laptop.jsonl     lo escribe la laptop, lo lee la pc-gpu
    <buzon>/de_pc-gpu.jsonl     lo escribe la pc-gpu, lo lee la laptop

Uso:
    python scripts/buzon.py enviar --soy laptop -m "texto del mensaje"
    python scripts/buzon.py leer   --soy laptop            # mensajes nuevos del otro
    python scripts/buzon.py leer   --soy laptop --todos    # historial completo
    python scripts/buzon.py seguir --soy laptop            # imprime cada mensaje nuevo (para Monitor)

La carpeta por defecto es <data_root>/buzon; se puede cambiar con --buzon o la variable BUZON_TESIS.
El registro de lo ya leído se guarda fuera de la carpeta sincronizada, para que no viaje.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")   # `enviar` por tubería: sin esto Windows usa cp1252
except Exception:
    pass

from src.common.config import load_config  # noqa: E402

MAQUINAS = ("laptop", "pc-gpu")


def carpeta(cfg, explicita: str | None) -> Path:
    d = Path(explicita or os.environ.get("BUZON_TESIS") or (cfg.path("raw").parents[1] / "buzon"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def archivo(buzon: Path, maquina: str) -> Path:
    return buzon / f"de_{maquina}.jsonl"


def estado(cfg, maquina: str) -> Path:
    p = cfg.path("raw").parents[1] / f"buzon_estado_{maquina}.json"   # fuera del buzón: no se sincroniza
    return p


def otra(maquina: str) -> str:
    return MAQUINAS[1] if maquina == MAQUINAS[0] else MAQUINAS[0]


def enviar(buzon: Path, maquina: str, texto: str) -> dict:
    msg = {"de": maquina, "ts": datetime.now().isoformat(timespec="seconds"), "texto": texto}
    with open(archivo(buzon, maquina), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(msg, ensure_ascii=False) + "\n")
    return msg


def leer_todos(buzon: Path, maquina: str) -> list[dict]:
    f = archivo(buzon, otra(maquina))
    if not f.exists():
        return []
    out = []
    for linea in f.read_text(encoding="utf-8", errors="replace").splitlines():
        linea = linea.strip()
        if linea:
            try:
                out.append(json.loads(linea))
            except json.JSONDecodeError:      # línea a medio sincronizar: se ignora hasta la próxima lectura
                continue
    return out


def imprimir(msgs: list[dict]) -> None:
    for m in msgs:
        print(f"[{m['ts']}] {m['de']}: {m['texto']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Buzón entre laptop y pc-gpu (transporte: Syncthing)")
    ap.add_argument("accion", choices=["enviar", "leer", "seguir"])
    ap.add_argument("texto", nargs="*", help="texto del mensaje (también admite -m, o por entrada estándar)")
    ap.add_argument("-m", "--mensaje", default=None, help="texto del mensaje")
    ap.add_argument("--soy", required=True, choices=list(MAQUINAS))
    ap.add_argument("--buzon", default=None)
    ap.add_argument("--todos", action="store_true", help="al leer, mostrar el historial completo")
    ap.add_argument("--intervalo", type=float, default=5.0, help="segundos entre comprobaciones en 'seguir'")
    args = ap.parse_args()

    cfg = load_config()
    buzon = carpeta(cfg, args.buzon)
    est = estado(cfg, args.soy)

    if args.accion == "enviar":
        texto = (args.mensaje or " ".join(args.texto)).strip()
        if not texto:
            texto = sys.stdin.read().strip()            # permite: echo "…" | buzon.py enviar --soy laptop
        if not texto:
            raise SystemExit("mensaje vacío")
        m = enviar(buzon, args.soy, texto)
        print(f"enviado a {otra(args.soy)}: {m['ts']}")
        return

    vistos = json.loads(est.read_text(encoding="utf-8"))["vistos"] if est.exists() else 0

    if args.accion == "leer":
        msgs = leer_todos(buzon, args.soy)
        nuevos = msgs if args.todos else msgs[vistos:]
        if not nuevos:
            print(f"sin mensajes nuevos de {otra(args.soy)}")
        imprimir(nuevos)
        est.write_text(json.dumps({"vistos": len(msgs)}), encoding="utf-8")
        return

    # seguir: una línea por mensaje nuevo, pensado para la herramienta Monitor
    print(f"escuchando mensajes de {otra(args.soy)} en {buzon} …", flush=True)
    while True:
        msgs = leer_todos(buzon, args.soy)
        if len(msgs) > vistos:
            imprimir(msgs[vistos:])
            sys.stdout.flush()
            vistos = len(msgs)
            est.write_text(json.dumps({"vistos": vistos}), encoding="utf-8")
        time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
