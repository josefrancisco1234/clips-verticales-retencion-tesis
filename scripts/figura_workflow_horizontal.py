"""Metodología completa del sistema en el arte de la Figura 1, en cuatro carriles que avanzan hacia la derecha:
A construir los datos, B modelar y evaluar, C usar el sistema con un video nuevo y validar con creadores, D mejorar solo (campeón/retador).
Cifras tomadas del artículo (secciones 4 a 6). Salida: reports/workflow_horizontal_D099.png"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
NL = chr(10)
T = lambda s: s.replace("|", NL)
plt.rcParams.update({"font.family": "DejaVu Sans"})
BL, AZ, VE, AM, RO, NA, MO = ("#ffffff", "#9ca3af"), ("#dbe7f5", "#7aa0cf"), ("#dcefdc", "#7cb87c"), ("#fbf0c8", "#d6b84e"), ("#f8dfe6", "#d489a2"), ("#fde6cf", "#e8a05a"), ("#e6dcf3", "#9b7fc7")
fig = plt.figure(figsize=(7.6, 5.9), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")


def bloque(x, y, w, h, col, titulo, cuerpo, pie="", tfs=4.7, bfs=3.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.006", fc=col[0], ec=col[1], lw=0.6))
    ax.text(x + w / 2, y + h - 0.009, T(titulo), ha="center", va="top", fontsize=tfs, fontweight="bold", color="#1f2937", linespacing=1.1)
    ax.text(x + w / 2, y + h - 0.009 - 0.0185 * (titulo.count("|") + 1) - 0.008, T(cuerpo), ha="center", va="top", fontsize=bfs, color="#374151", linespacing=1.28)
    if pie:
        ax.text(x + w / 2, y + 0.007, T(pie), ha="center", va="bottom", fontsize=bfs - 0.2, style="italic", color="#7c2d12", linespacing=1.2)


def flecha(a, b, c="#4b5563", ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=5, lw=0.6, color=c, linestyle=ls))


H, GAP = 0.2, 0.027
N = 7
ANCHO = 0.116
GX = (0.98 - N * ANCHO) / (N - 1)
XS = [0.01 + i * (ANCHO + GX) for i in range(N)]


def carril(y, titulo, bloques):
    ax.add_patch(FancyBboxPatch((0.003, y), 0.994, H, boxstyle="round,pad=0,rounding_size=0.008", fc="#f6f7fa", ec="#d5dae3", lw=0.7))
    ax.text(0.012, y + H - 0.008, titulo, fontsize=5.3, fontweight="bold", color="#14213d", va="top")
    bh = H - 0.052
    for i, (col, t, b, pie) in enumerate(bloques):
        bloque(XS[i], y + 0.012, ANCHO, bh, col, t, b, pie)
        if i:
            flecha((XS[i] - GX + 0.002, y + 0.012 + bh / 2), (XS[i] - 0.002, y + 0.012 + bh / 2))


yA, yB, yC, yD = 0.79, 0.563, 0.336, 0.109
carril(yA, "A · CONSTRUIR LOS DATOS (ETL → base de datos)", [
    (BL, "1 · Búsqueda", "50 consultas (26 ES,|24 EN); solo videos|con curva; máx. 2|por canal", "≈ 770 videos"),
    (AZ, "2 · Descarga", "yt-dlp: audio WAV|16 kHz y curva Most|Replayed (100 tramos)", "un JSON por video"),
    (AZ, "3 · Transcripción", "Whisper en GPU: cada|palabra con inicio, fin|y confianza; idioma", "765 transcripciones"),
    (VE, "4 · Variables", "71 por ventana: audio,|texto, gancho, fluidez|y eventos de sonido", "tabla por ventana"),
    (AM, "5 · Percentil", "cada variable pasa a|percentil dentro de|su propio video", "678 videos"),
    (NA, "6 · Etiquetas", "calor medio, grado 0 a 4|y momento caliente|(> 0.5); solo para|entrenar y calificar", "no son entrada"),
    (MO, "7 · Base de datos", "BD_TESIS con partición|por canal: desarrollo,|confirmación y grupos de|videos nuevos congelados", "antes de mirar"),
])
carril(yB, "B · MODELAR Y EVALUAR", [
    (BL, "1 · Datos", "percentiles dentro del|video; desarrollo 444,|confirmación 352; dos|grupos nuevos: 93 y 63", ""),
    (RO, "2 · Base", "azar; fórmula V0 de 17|variables (pesos de la|correlación parcial); V1|con clips de hasta 45 s", ""),
    (RO, "3 · Aprendizaje", "R0: LightGBM LambdaRank|(un video = un grupo)|con validación cruzada|por canal", ""),
    (RO, "4 · Redes", "BiGRU, TCN, Transformer|y red de ecuaciones|(EQL) frente a la|fórmula", ""),
    (NA, "5 · Métricas", "acierto@5, F1 temporal|y NDCG@10; matriz de|confusión por ventana", ""),
    (NA, "6 · Pruebas", "Wilcoxon y McNemar;|Bonferroni; hipótesis|previa y una sola|corrida por grupo nuevo", ""),
    (MO, "7 · Decisión", "se adopta V1 en banderas|0/1 por su explicabilidad;|R0 queda como|referencia", ""),
])
carril(yC, "C · USAR EL SISTEMA (video nuevo → clips) Y VALIDAR CON CREADORES", [
    (BL, "1 · Video largo", "archivo o URL; no|necesita la curva|de YouTube", ""),
    (AZ, "2 · Audio y|transcripción", "mismo ETL: Whisper y|eventos de sonido", ""),
    (VE, "3 · Candidatos|y variables", "ventanas de 15 a 90 s|por oración; 71|variables en percentil", ""),
    (RO, "4 · Puntaje", "campeón vigente:|fórmula V1 con 17|banderas 0/1;|escala de 0 a 99", ""),
    (NA, "5 · Selección", "top 5; dos clips no|comparten más de 30 %;|corte de escena", ""),
    (MO, "6 · Clips 9:16", "seguimiento del hablante,|subtítulos, puntaje y|aporte por variable|(Hook, Flow, Value)", ""),
    (BL, "7 · Validación", "página web con 5|creadores de podcast:|utilidad y SUS|(meta > 70)", ""),
])
carril(yD, "D · MEJORAR SOLO (ciclo campeón / retador, en GPU)", [
    (AZ, "1 · Minero|de papers", "OpenAlex, 15 consultas,|trabajos desde 2020:|señales que las 71|variables no cubren", ""),
    (VE, "2 · Variables|candidatas", "se calculan con el audio|y la transcripción|ya existentes", ""),
    (AM, "3 · Explorador", "lee BD_TESIS; red de|ecuaciones (EQL) con L1;|17 y 68 variables;|validación por canal", ""),
    (RO, "4 · Campeón|contra retador", "Wilcoxon unilateral|p < 0.05 en el conjunto|reservado; Bonferroni", ""),
    (NA, "5 · Confirmación", "una sola vez en un|grupo de videos nuevos;|la hipótesis se escribe|antes de mirar", ""),
    (MO, "6 · Nuevo campeón", "si se confirma, reemplaza|al puntaje de C y se|reentrena; si no, se|descarta", ""),
    (BL, "7 · Bitácora", "DECISIONES.md: 87|entradas, también los|resultados negativos", ""),
])


def codo(x0, y0, x1, y1, ymid, c, etiqueta, xe, ls="-"):
    ax.plot([x0, x0, x1], [y0, ymid, ymid], color=c, lw=0.7, ls=ls, solid_capstyle="round")
    flecha((x1, ymid), (x1, y1), c=c, ls=ls)
    ax.text(xe, ymid + 0.0035, etiqueta, fontsize=3.7, color=c, ha="left", va="bottom")


cx = lambda i: XS[i] + ANCHO / 2
codo(cx(6), yA, cx(0), yB + H, yA - GAP / 2, "#6b7280", "la base alimenta el modelado y la evaluación", cx(0) + 0.015, ":")
codo(cx(6), yB, cx(3), yC + H, yB - GAP / 2, "#6b7280", "el modelo elegido puntúa los videos nuevos", cx(3) + 0.015, ":")
codo(cx(5), yD + H, cx(3), yC, yC - GAP / 2, "#7c3aed", "si se confirma, el nuevo campeón reemplaza al puntaje", cx(3) + 0.015)
ax.text(0.5, 0.10, "BACKEND: la página web solo hace llamadas (peticiones) al servidor; todo lo que muestran los carriles A a D (descarga, transcripción, variables, puntaje, selección, clips y mejora) se ejecuta en el servidor.",
        ha="center", va="center", fontsize=4.2, fontweight="bold", color="#14213d")
ax.text(0.5, 0.06, "La curva Most Replayed solo califica (acierto@5, F1 temporal, NDCG@10); nunca entra como variable del sistema, y el reservado y los grupos de videos nuevos no se mezclan con el entrenamiento.",
        ha="center", va="center", fontsize=3.8, style="italic", color="#555555")
fig.savefig(ROOT / "reports" / "workflow_horizontal_D099.png", facecolor="white", bbox_inches="tight", pad_inches=0.04)
print("ok")
