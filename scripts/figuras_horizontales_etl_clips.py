"""Figuras 2 (ETL del conjunto de datos) y 3 (de un video crudo a cinco clips) en el mismo arte que la Figura 1: bloques que avanzan hacia la derecha.
Salidas: reports/etl_horizontal_D099.png y reports/video_a_clips_horizontal_D099.png"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
NL = chr(10)
plt.rcParams.update({"font.family": "DejaVu Sans"})
T = lambda s: s.replace("|", NL)
GRIS = ("#ececec", "#8a8f98")
AZUL = ("#dbe7f5", "#7aa0cf")
VERDE = ("#dcefdc", "#7cb87c")
AMAR = ("#fbf0c8", "#d6b84e")
SAL = ("#fde6cf", "#e8a05a")
ROSA = ("#f8dfe6", "#d489a2")
MORADO = ("#e6dcf3", "#9b7fc7")


class Lienzo:
    def __init__(self, w, h, titulo):
        self.fig = plt.figure(figsize=(w, h), dpi=300)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, 1); self.ax.set_ylim(0, 1); self.ax.axis("off")
        self.ax.text(0.005, 0.975, titulo, fontsize=6.4, style="italic", va="top", color="#111827")

    def panel(self, x, y, w, h, col, titulo, cuerpo="", pie="", tfs=5.4, bfs=4.5):
        fc, ec = col
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.008", fc=fc, ec=ec, lw=0.7))
        self.ax.text(x + w / 2, y + h - 0.035, T(titulo), ha="center", va="top", fontsize=tfs, fontweight="bold", color="#1f2937", linespacing=1.15)
        nt = titulo.count("|") + 1
        if cuerpo:
            self.ax.text(x + w / 2, y + h - 0.035 - 0.085 * nt - 0.03, T(cuerpo), ha="center", va="top", fontsize=bfs, color="#374151", linespacing=1.3)
        if pie:
            self.ax.text(x + w / 2, y + 0.04, T(pie), ha="center", va="bottom", fontsize=bfs - 0.3, style="italic", color="#7c2d12", linespacing=1.25)

    def flecha(self, a, b):
        self.ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5.5, lw=0.7, color="#4b5563"))

    def guardar(self, ruta):
        self.fig.savefig(ruta, facecolor="white"); plt.close(self.fig)


# ---------------------------------------------------------------- Figura 2: ETL (mismo arte que la Figura 1)
BLANCO = ("#ffffff", "#9ca3af")
L = Lienzo(7.6, 3.3, "ETL del conjunto de datos")
TOP, BOT = (0.55, 0.37), (0.07, 0.37)
ax = L.ax
ax.text(0.0525, 0.54, "Búsqueda", ha="center", va="center", fontsize=5.0, fontweight="bold", color="#1f4e79")
ax.text(0.0525, 0.465, T("50 consultas|(26 ES, 24 EN)|máx. 2 por canal|≈ 770 videos"), ha="center", va="center", fontsize=4.1, color="#6b7280", linespacing=1.3)
# entradas
L.panel(0.105, TOP[0], 0.115, TOP[1], BLANCO, "Curva", "yt-dlp descarga el|heatmap: 100 tramos|con valor 0 a 1", "un JSON por video")
L.panel(0.105, BOT[0], 0.115, BOT[1], BLANCO, "Audio", "se descarga solo el|audio (WAV), no el|video completo", "≈ 765 archivos · 66 GB")
# procesamiento
L.panel(0.245, TOP[0], 0.135, TOP[1], AZUL, "Preprocesamiento", "se corrige el primer|tramo (igual al|segundo)", "curva limpia")
L.panel(0.245, BOT[0], 0.135, BOT[1], AZUL, "Transcripción", "Whisper local en GPU:|palabra con inicio, fin|y confianza; detecta|el idioma", "765 transcripciones")
# etiquetas y variables
L.panel(0.405, TOP[0], 0.145, TOP[1], SAL, "Etiquetas", "calor medio del tramo,|grado 0 a 4 por cuantiles|y marca de momento|caliente (> 0.5)", "no entran al sistema")
L.panel(0.405, BOT[0], 0.145, BOT[1], VERDE, "Variables", "71 variables por ventana|(audio, texto y eventos)", "tabla por ventana")
# tabla por video y división
L.panel(0.575, 0.07, 0.15, 0.84, AMAR, "Percentil y|división de datos", "", "")
ax.text(0.65, 0.76, T("cada variable pasa a|percentil dentro de|su propio video"), ha="center", va="top", fontsize=4.5, color="#374151", linespacing=1.3)
ax.text(0.65, 0.52, T("tabla por video:|678 videos con las|71 variables"), ha="center", va="top", fontsize=4.5, color="#374151", linespacing=1.3)
ax.text(0.65, 0.36, T("Conjuntos agrupados|por canal:"), ha="center", va="top", fontsize=4.5, color="#374151", linespacing=1.3)
for i, lab in enumerate(("Desarrollo", "Confirmación", "Cohortes frescas")):
    ax.add_patch(FancyBboxPatch((0.59, 0.22 - i * 0.06), 0.12, 0.045, boxstyle="round,pad=0,rounding_size=0.006", fc="#fff8e1", ec="#d6b84e", lw=0.5))
    ax.text(0.65, 0.2425 - i * 0.06, lab, ha="center", va="center", fontsize=4.4, color="#374151")
# destino
L.panel(0.75, TOP[0], 0.15, TOP[1], ROSA, "Califican", "las etiquetas solo|entrenan y califican;|nunca son entrada", "")
L.panel(0.75, BOT[0], 0.15, BOT[1], ROSA, "Alimentan", "las variables son la|entrada de la fórmula|y del ranking", "")
L.panel(0.925, 0.07, 0.07, 0.84, MORADO, "", "", "")
ax.text(0.96, 0.49, T("Uso en el sistema"), ha="center", va="center", fontsize=4.9, fontweight="bold", color="#1f2937", rotation=90)
# flechas
for y in (TOP[0] + TOP[1] / 2, BOT[0] + BOT[1] / 2):
    L.flecha((0.092, 0.5), (0.103, y))
    L.flecha((0.222, y), (0.243, y))
    L.flecha((0.382, y), (0.403, y))
L.flecha((0.552, TOP[0] + TOP[1] / 2), (0.573, 0.7))
L.flecha((0.552, BOT[0] + BOT[1] / 2), (0.573, 0.3))
L.flecha((0.727, 0.7), (0.748, TOP[0] + TOP[1] / 2))
L.flecha((0.727, 0.3), (0.748, BOT[0] + BOT[1] / 2))
L.flecha((0.902, TOP[0] + TOP[1] / 2), (0.923, 0.7))
L.flecha((0.902, BOT[0] + BOT[1] / 2), (0.923, 0.3))
L.guardar(ROOT / "reports" / "etl_horizontal_D099.png")

# ---------------------------------------------------------------- Figura 3: de un video crudo a cinco clips
L = Lienzo(7.6, 2.7, "De un video crudo a cinco clips verticales")
ancho, gap, x0 = 0.1265, 0.0175, 0.005
pasos = [
    (BLANCO, "1 · Video|crudo", "URL o archivo.|Se extrae el audio|y se transcribe|con Whisper.", "palabras con tiempo"),
    (AZUL, "2 · Oraciones|y candidatos", "Corte por puntuación,|pausas > 0.9 s o|40 palabras; ventanas|de 15 a 90 s.", "708 candidatos|(video de 50 min)"),
    (VERDE, "3 · Variables", "71 variables por|candidato; cada una|se vuelve percentil|dentro del video.", "tabla de variables"),
    (AMAR, "4 · Puntaje", "Fórmula de 17 pesos:|suma de peso x bandera.|Score de 0 a 99.", "345 candidatos|≤ 45 s"),
    (ROSA, "5 · Elegir 5", "Se ordena por puntaje;|se descarta lo que|se solape más|de 30 %.", "5 clips"),
    (SAL, "6 · Ajuste|y recorte", "Corte de escena en una|pausa (margen 0.15 s);|reencuadre 9:16 al|hablante y subtítulos.", "mp4 vertical"),
    (MORADO, "7 · Explicación", "Aporte de cada variable|y desglose en|Hook, Flow y Value.", "tabla por clip"),
]
for n, (col, t, b, pie) in enumerate(pasos):
    x = x0 + n * (ancho + gap)
    L.panel(x, 0.17, ancho, 0.70, col, t, b, pie, tfs=5.4, bfs=4.6)
    if n:
        L.flecha((x - gap + 0.002, 0.52), (x - 0.002, 0.52))
for x, col, txt in ((0.005, AMAR, "amarillo: puntúa todos los candidatos"), (0.30, ROSA, "rosa y siguientes: solo los clips elegidos")):
    L.ax.add_patch(plt.Rectangle((x, 0.04), 0.015, 0.05, fc=col[0], ec=col[1], lw=0.5))
    L.ax.text(x + 0.02, 0.065, txt, fontsize=4.3, va="center", color="#374151")
L.guardar(ROOT / "reports" / "video_a_clips_horizontal_D099.png")
print("ok")
