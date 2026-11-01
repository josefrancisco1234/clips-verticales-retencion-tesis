"""Figura: qué variables de la fórmula salen solo del audio, cuáles de los tiempos de las palabras (transcripción con tiempos) y cuáles del contenido del texto,
con su parte del peso total. Mismo arte que la Figura 1. Salida: reports/audio_vs_transcripcion_D099.png"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
W = json.load(open(ROOT / "models" / "formula_calor_D045.json", encoding="utf-8"))["weights"]
AUDIO = ["a_rms_std", "a_pitch_range", "a_voiced_ratio", "a_pitch_std", "a_rms_mean", "e_speech_mean", "e_music_max", "e_music_mean"]
TIEMPOS = ["a_pause_ratio", "a_long_pauses_pm", "l_silence", "a_speech_rate"]
TEXTO = ["k_keybert_sim", "k_noun_chunks_ps", "f_n_sentences", "s_questions_pm", "s_second_person"]
assert sorted(AUDIO + TIEMPOS + TEXTO) == sorted(W), "las 17 variables deben quedar repartidas una sola vez"
tot = sum(abs(v) for v in W.values())
share = [sum(abs(W[k]) for k in g) / tot for g in (AUDIO, TIEMPOS, TEXTO)]
print("participación del peso:", [round(100 * s, 1) for s in share], "| variables:", len(AUDIO), len(TIEMPOS), len(TEXTO))

NL = chr(10)
T = lambda s: s.replace("|", NL)
plt.rcParams.update({"font.family": "DejaVu Sans"})
fig = plt.figure(figsize=(7.6, 3.3), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
BLANCO, VERDE, ROSA, AMAR = ("#ffffff", "#9ca3af"), ("#dcefdc", "#7cb87c"), ("#f8dfe6", "#d489a2"), ("#fbf0c8", "#d6b84e")


def panel(x, y, w, h, col, titulo, cuerpo="", tfs=5.3, bfs=4.4):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008", fc=col[0], ec=col[1], lw=0.7))
    ax.text(x + w / 2, y + h - 0.025, T(titulo), ha="center", va="top", fontsize=tfs, fontweight="bold", color="#1f2937", linespacing=1.15)
    if cuerpo:
        ax.text(x + w / 2, y + h - 0.025 - 0.042 * (titulo.count("|") + 1) - 0.02, T(cuerpo), ha="center", va="top", fontsize=bfs, color="#374151", linespacing=1.3)


def flecha(a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, lw=0.7, color="#4b5563"))


ax.text(0.005, 0.985, "Qué sale del audio y qué de la transcripción", fontsize=6.4, style="italic", va="top", color="#111827")
H, ys = 0.235, (0.66, 0.37, 0.08)
filas = [
    ("1 · Solo la señal|de audio", "no necesita la transcripción", "Volumen y tono|(RMS, f0, voz continua)|Eventos de sonido|(habla y música, PANNs)", AUDIO, "variables de volumen,|tono y eventos"),
    ("2 · Tiempos|de las palabras", "Whisper marca inicio y fin|de cada palabra", "Pausas, silencio y ritmo|(huecos entre palabras,|tiempo hablado,|palabras por segundo)", TIEMPOS, "variables de pausas,|silencio y ritmo"),
    ("3 · Contenido|del texto", "las palabras y las oraciones|de la transcripción", "Tema del video, preguntas,|segunda persona, densidad|de sustantivos y n.º|de oraciones", TEXTO, "variables de tema|y estilo del texto"),
]
for (tit, sub, med, grupo, resumen), y, sh in zip(filas, ys, share):
    panel(0.005, y, 0.2, H, BLANCO, tit, sub, 5.2, 4.3)
    panel(0.235, y, 0.255, H, VERDE, "Qué se mide", med, 5.0, 4.3)
    panel(0.52, y, 0.2, H, ROSA, f"{len(grupo)} variables", "", 5.2)
    ax.text(0.62, y + H - 0.085, T(resumen), ha="center", va="top", fontsize=4.2, color="#374151", linespacing=1.25)
    ax.add_patch(plt.Rectangle((0.535, y + 0.025), 0.17, 0.028, fc="#e5e7eb", ec="none"))
    ax.add_patch(plt.Rectangle((0.535, y + 0.025), 0.17 * sh, 0.028, fc="#d489a2", ec="none"))
    ax.text(0.62, y + 0.062, f"{100 * sh:.0f} % del peso", ha="center", va="bottom", fontsize=4.6, fontweight="bold", color="#9d2b57")
    flecha((0.207, y + H / 2), (0.233, y + H / 2))
    flecha((0.492, y + H / 2), (0.518, y + H / 2))
    flecha((0.722, y + H / 2), (0.75, 0.5))
panel(0.75, 0.08, 0.245, 0.815, AMAR, "Puntaje de|17 variables", "")
ax.text(0.8725, 0.72, T("cada variable pasa a|percentil dentro del video|y a bandera 0/1;|se suma peso x bandera|y se lleva a la escala 0 a 99"), ha="center", va="top", fontsize=4.4, color="#374151", linespacing=1.3)
ax.text(0.8725, 0.40, T("Con solo la transcripción|se arman además los|candidatos alineados a|oración, los subtítulos|y las palabras clave|de cada clip"), ha="center", va="top", fontsize=4.2, color="#6b7280", linespacing=1.3)
fig.savefig(ROOT / "reports" / "audio_vs_transcripcion_D099.png", facecolor="white")
