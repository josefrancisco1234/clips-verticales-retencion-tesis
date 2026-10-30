"""Explicación gráfica completa (video largo -> 5 clips -> puntaje -> respaldo de los picos de re-reproducción).
Salidas en F:\\TESISJF\\EXPLICACION_GRAFICA\\: A_flujo_completo.png, B_calculo_del_puntaje.png, C_respaldo_picos.png y EXPLICACION_COMPLETA.pdf.
Los números salen de una corrida real (clips.json del podcast de 54 min) y de models/formula_calor_D045.json."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(r"F:\TESISJF\EXPLICACION_GRAFICA")
OUT.mkdir(exist_ok=True)
RUN = json.loads(Path(r"F:\TESISJF\tesis_data\outputs\YTDown.com_YouTube_Media_O4wPcQ2vcQo_NOS_b7239366\clips.json").read_text(encoding="utf-8"))
W = json.loads((ROOT / "models" / "formula_calor_D045.json").read_text(encoding="utf-8"))["weights"]
NAVY, ORANGE, GREEN, GREY, PURPLE, RED = "#1f4e79", "#e8710a", "#2e7d32", "#6b7280", "#6b3fa0", "#c62828"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
NL = chr(10)


def tx(s):
    """Texto con saltos de línea escritos como '|'."""
    return s.replace("|", NL)


def box(ax, x, y, w, h, title, body, color=NAVY, num=None, fs=9.4):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.01", fc="white", ec=color, lw=1.8))
    ax.add_patch(FancyBboxPatch((x, y + h - 0.05), w, 0.05, boxstyle="round,pad=0.0,rounding_size=0.01", fc=color, ec=color, lw=1.8))
    ax.text(x + 0.010, y + h - 0.025, (f"{num}  " if num else "") + title, color="white", fontsize=fs + 1.6, fontweight="bold", va="center")
    ax.text(x + 0.010, y + h - 0.062, tx(body), color="#222222", fontsize=fs, va="top", linespacing=1.4)


def arrow(ax, a, b, color=GREY):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=18, lw=2.2, color=color))


# ------------------------------------------------------------------ A. flujo completo
def fig_a():
    fig = plt.figure(figsize=(17, 10.5), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.968, "De un video largo a 5 clips verticales con puntaje: todo el proceso", ha="center", fontsize=21, fontweight="bold", color=NAVY)
    ax.text(0.5, 0.936, "Entra solo audio y texto del video; la curva de re-reproducción de YouTube nunca entra al sistema, solo sirve para calificarlo.", ha="center", fontsize=11.5, color=GREY)
    dur = RUN["duration_s"]
    tl_x0, tl_x1, tl_y = 0.06, 0.94, 0.835
    ax.text(0.06, 0.912, f"Ejemplo real: podcast de {dur / 60:.0f} min  ->  {RUN['n_candidates']:,} candidatos evaluados  ->  5 clips elegidos".replace(",", " "), fontsize=12.5, fontweight="bold", color="#222222")
    ax.add_patch(FancyBboxPatch((tl_x0, tl_y - 0.012), tl_x1 - tl_x0, 0.024, boxstyle="round,pad=0,rounding_size=0.006", fc="#e5e7eb", ec="#9ca3af"))
    for t in range(0, int(dur // 600) + 1):
        x = tl_x0 + (tl_x1 - tl_x0) * (t * 600) / dur
        ax.plot([x, x], [tl_y - 0.012, tl_y - 0.022], color="#9ca3af", lw=1)
        ax.text(x, tl_y - 0.036, f"{t * 10} min", fontsize=8.5, ha="center", color=GREY)
    for c in RUN["clips"]:
        x0 = tl_x0 + (tl_x1 - tl_x0) * c["start"] / dur
        wv = max((tl_x1 - tl_x0) * (c["end"] - c["start"]) / dur, 0.004)
        ax.add_patch(FancyBboxPatch((x0, tl_y - 0.012), wv, 0.024, boxstyle="square,pad=0", fc=GREEN, ec=GREEN))
        ax.text(x0 + wv / 2, tl_y + 0.020, f"#{c['rank']}  puntaje {c['score']}", fontsize=9, ha="center", color=GREEN, fontweight="bold")
    steps = [
        ("Entrada", "Archivo de video (mp4, mkv)|o link de YouTube.|Se extrae el audio en mono|a 16 kHz.", NAVY),
        ("Transcribir", "Whisper (red neuronal, GPU):|texto con tiempo por|palabra e idioma|(español o inglés).", NAVY),
        ("Oraciones", "Se corta por puntuación y|por pausas mayores a 0.9 s,|con unas 40 palabras|como máximo por oración.", NAVY),
        ("Candidatos", "Ventanas de 15 a 90 s que|empiezan y terminan en el|límite de una oración|(versión final: hasta 45 s).", NAVY),
        ("Variables", "71 por candidato: audio|(pausas, volumen, tono),|eventos (risa, música),|palabras clave, preguntas,|gancho y fluidez.", PURPLE),
        ("Percentil", "Cada variable se compara|solo con los demás|candidatos del mismo video|(percentil de 0 a 1).", PURPLE),
        ("Banderas 0/1", "Las 17 variables de la|fórmula valen 1 si el clip|está en el 25 % más alto|del video (percentil|>= 0.75) y 0 si no.", PURPLE),
        ("Puntaje 0 a 99", "Suma de peso x bandera|(pesos ajustados con 121|videos), escalada entre el|mínimo y el máximo|posibles de la fórmula.", ORANGE),
        ("Elegir 5", "De mayor a menor puntaje;|se descarta el clip que|comparte más del 30 % de|su duración con uno elegido.", ORANGE),
        ("Ajustar y recortar", "Los bordes se mueven al|corte de escena o pausa|más cercano (hasta 1.5 s).|Recorte vertical 9:16|siguiendo a quien habla.", GREEN),
        ("Salida", "5 clips mp4 con subtítulos|y palabras clave marcadas,|puntaje 0 a 99, desglose|Hook / Flow / Value y las|variables que lo explican.", GREEN),
    ]
    BW, BH, STEP = 0.137, 0.215, 0.1625
    xs = [0.03 + i * STEP for i in range(6)]
    pos = []
    for i, (t, b, c) in enumerate(steps):
        row, col = (0, i) if i < 6 else (1, i - 6)
        x, y = xs[col], (0.545 if row == 0 else 0.295)
        box(ax, x, y, BW, BH, t, b, c, num=i + 1)
        pos.append((x, y))
    for i in range(10):
        if i == 5:
            continue
        (x0, y0), (x1, y1) = pos[i], pos[i + 1]
        arrow(ax, (x0 + BW + 0.002, y0 + BH / 2), (x1 - 0.002, y1 + BH / 2))
    ax.text(xs[5] + BW / 2, 0.533, "continúa abajo, paso 7", fontsize=9.5, color=GREY, ha="center", va="top", style="italic")
    ax.add_patch(FancyBboxPatch((0.03, 0.05), 0.45, 0.17, boxstyle="round,pad=0.0,rounding_size=0.01", fc="#fff8e1", ec=ORANGE, lw=1.8))
    ax.text(0.042, 0.205, "Dónde entra la curva de re-reproducción (Most Replayed)", fontsize=11.5, fontweight="bold", color=ORANGE, va="top")
    ax.text(0.042, 0.172, tx("Solo al final, para calificar: se mide si al menos 1 de los 5 clips cae sobre un pico real|(acierto@5), el F1 temporal y el NDCG@10. Nunca es una variable de entrada del sistema.|Con 93 videos nuevos: azar 26.9 %, fórmula V0 47.3 %, V1 54.8 %, ranker LightGBM 62.4 %."), fontsize=9.6, va="top", color="#222222", linespacing=1.45)
    ax.add_patch(FancyBboxPatch((0.5, 0.05), 0.47, 0.17, boxstyle="round,pad=0.0,rounding_size=0.01", fc="#eef6ee", ec=GREEN, lw=1.8))
    ax.text(0.512, 0.205, "Qué se genera y dónde se usa", fontsize=11.5, fontweight="bold", color=GREEN, va="top")
    ax.text(0.512, 0.172, tx(f"Este video: {RUN['elapsed_s'] / 60:.1f} min de proceso para {dur / 60:.0f} min de contenido. Los clips se recortan del|video original con ffmpeg. La página web sube el video, muestra los pasos, entrega los 5 clips|y guarda la validación con 5 creadores.|Colores: azul = datos, morado = variables, naranja = puntaje, verde = salida."), fontsize=9.6, va="top", color="#222222", linespacing=1.45)
    fig.savefig(OUT / "A_flujo_completo.png")
    return fig


# ------------------------------------------------------------------ B. cálculo del puntaje
def fig_b():
    c = RUN["clips"][0]
    ex = {v["var"]: v for v in c["explain"]["vars"]}
    order = sorted(W, key=lambda k: -abs(W[k]))
    names = {"a_pause_ratio": "proporción de pausas", "l_silence": "silencio", "a_long_pauses_pm": "pausas largas por minuto", "a_rms_std": "variación del volumen",
             "a_pitch_range": "rango del tono", "a_voiced_ratio": "proporción con voz", "k_keybert_sim": "similitud con palabras clave", "e_speech_mean": "habla (evento), media",
             "k_noun_chunks_ps": "frases nominales por oración", "a_speech_rate": "velocidad del habla", "a_pitch_std": "variación del tono", "e_music_max": "música, máximo",
             "a_rms_mean": "volumen medio", "e_music_mean": "música, media", "f_n_sentences": "número de oraciones", "s_questions_pm": "preguntas por minuto", "s_second_person": "segunda persona (tú, usted)"}
    pos_sum = sum(w for w in W.values() if w > 0)
    neg_sum = sum(w for w in W.values() if w < 0)
    raw = sum(W[k] for k in order if ex[k]["pct"] >= 0.75)
    score = (raw - neg_sum) / (pos_sum - neg_sum) * 99
    n_on = sum(1 for k in order if ex[k]["pct"] >= 0.75)
    fig = plt.figure(figsize=(17, 10.5), dpi=150)
    fig.suptitle("Cómo se calcula el puntaje: ejemplo real del clip #1 (puntaje %d)" % c["score"], fontsize=21, fontweight="bold", color=NAVY, y=0.975)
    fig.text(0.5, 0.925, f"Clip de {c['end'] - c['start']:.0f} s en el minuto {c['start'] / 60:.0f} del podcast; se comparó contra {RUN['n_candidates']:,} candidatos del mismo video.".replace(",", " "), ha="center", fontsize=12, color=GREY)
    ax = fig.add_axes([0.19, 0.10, 0.32, 0.76])
    ys = list(range(len(order)))[::-1]
    for y, k in zip(ys, order):
        p = ex[k]["pct"]
        flag = p >= 0.75
        col = (GREEN if W[k] > 0 else RED) if flag else "#cbd5e1"
        ax.barh(y, p, color=col, height=0.62)
        ax.text(1.03, y, "1" if flag else "0", fontsize=13, fontweight="bold", va="center", color=col if flag else GREY)
        ax.text(1.14, y, f"{W[k]:+.3f}", fontsize=10.5, va="center", color=GREEN if W[k] > 0 else RED)
        ax.text(1.33, y, f"{W[k]:+.3f}" if flag else "0", fontsize=10.5, va="center", fontweight="bold" if flag else "normal", color="#222222")
    ax.axvline(0.75, color=ORANGE, lw=2.2, ls="--")
    ax.text(0.75, len(order) - 0.1, tx("umbral 0.75|(25 % más alto)"), color=ORANGE, fontsize=9.5, ha="center", va="bottom", fontweight="bold")
    ax.set_yticks(ys)
    ax.set_yticklabels([names[k] for k in order], fontsize=10.5)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Percentil de este clip dentro de su video (0 = el más bajo, 1 = el más alto)", fontsize=10.5)
    for t, x in (("bandera", 1.02), ("peso", 1.14), ("peso x bandera", 1.27)):
        ax.text(x, len(order) + 1.15, t, fontsize=9.5, color=GREY, fontweight="bold", va="bottom")
    ax.set_ylim(-0.7, len(order) + 0.4)
    ax2 = fig.add_axes([0.72, 0.10, 0.27, 0.76])
    ax2.axis("off")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.add_patch(FancyBboxPatch((0, 0.0), 1, 1, boxstyle="round,pad=0.0,rounding_size=0.02", fc="#f8fafc", ec=NAVY, lw=1.8))
    lines = [
        ("1  Suma del clip", f"{raw:.3f}", f"suma de peso x bandera|({n_on} variables encendidas)", 0.94),
        ("2  Mínimo posible", f"{neg_sum:.3f}", "todas las variables de peso|negativo encendidas", 0.76),
        ("3  Máximo posible", f"{pos_sum:.3f}", "todas las variables de peso|positivo encendidas", 0.58),
    ]
    for t, v, d, y in lines:
        ax2.text(0.05, y, t, fontsize=12.5, fontweight="bold", color=NAVY, va="top")
        ax2.text(0.95, y, v, fontsize=15, fontweight="bold", ha="right", va="top", color="#222222")
        ax2.text(0.05, y - 0.05, tx(d), fontsize=9.6, color=GREY, va="top", linespacing=1.3)
    ax2.text(0.05, 0.39, "4  Escala 0 a 99", fontsize=12.5, fontweight="bold", color=NAVY, va="top")
    ax2.text(0.05, 0.34, f"( {raw:.3f} - ({neg_sum:.3f}) ){NL}----------------------------  x 99{NL}( {pos_sum:.3f} - ({neg_sum:.3f}) )", fontsize=10.5, family="monospace", va="top", color="#222222", linespacing=1.2)
    ax2.text(0.5, 0.13, f"{score:.0f}", fontsize=46, fontweight="bold", ha="center", va="center", color=ORANGE)
    ax2.text(0.5, 0.045, f"puntaje del clip (en el sistema: {c['score']})", fontsize=10, ha="center", color=GREY)
    fig.text(0.20, 0.035, f"Hook {c['score_breakdown']['hook']}  |  Flow {c['score_breakdown']['flow']}  |  Value {c['score_breakdown']['value']}: resúmenes por grupo de variables (gancho del inicio, fluidez y contenido) para explicar el puntaje; el puntaje total es el de la cuenta.", fontsize=10, color="#222222")
    fig.savefig(OUT / "B_calculo_del_puntaje.png")
    return fig


# ------------------------------------------------------------------ C. respaldo de los picos
def fig_c():
    fig = plt.figure(figsize=(17, 10.5), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.968, "¿Por qué los picos de re-reproducción sirven como \"mejores momentos\"?", ha="center", fontsize=21, fontweight="bold", color=NAVY)
    ax.text(0.5, 0.934, "La curva Most Replayed de YouTube muestra qué partes del video la gente vuelve a ver; la literatura la usa como indicador de momentos destacados.", ha="center", fontsize=11.5, color=GREY)
    img = mpimg.imread(ROOT / "reports" / "ejemplo_heatmap_ranking.png")
    axi = fig.add_axes([0.03, 0.58, 0.50, 0.32])
    axi.imshow(img)
    axi.axis("off")
    ax.text(0.03, 0.912, "Ejemplo de nuestro conjunto: el sistema, sin ver la curva, eligió 4 de 5 clips sobre un pico", fontsize=10, color=GREY)
    axb = fig.add_axes([0.66, 0.60, 0.30, 0.25])
    vals = [64.8, 15.6, 19.6]
    cols = [GREEN, "#9ca3af", RED]
    labs = ["De acuerdo con la etiqueta", "Neutral", "En desacuerdo"]
    axb.barh(labs[::-1], vals[::-1], color=cols[::-1], height=0.6)
    for y, v in enumerate(vals[::-1]):
        axb.text(v + 1, y, f"{v} %", va="center", fontsize=12, fontweight="bold")
    axb.set_xlim(0, 85)
    axb.set_xlabel("% de 250 clips (6 evaluadores por video)", fontsize=10)
    axb.tick_params(labelsize=10.5)
    ax.text(0.56, 0.905, "Estudio con personas en Mr. HiSum (Sul et al., 2023)", fontsize=12.5, fontweight="bold", color=NAVY)
    ax.text(0.56, 0.883, "30 evaluadores juzgaron clips de 5 a 10 s: 5 \"destacados\" y 5 no por video.", fontsize=9.6, color=GREY)
    cards = [
        ("Mr. HiSum  (Sul, Han y Lee, 2023, NeurIPS)", GREEN,
         "31 892 videos con etiquetas de Most Replayed, con al menos 50 000 espectadores por video. Los autores toman esa estadística|como indicador del momento destacado y la validan de dos formas: (1) entrenar con ella y transferir a TVSum y SumMe rinde|igual o mejor que entrenar con las etiquetas propias de esos conjuntos, y (2) el estudio con personas: 64.8 % de acuerdo contra 19.6 % en desacuerdo."),
        ("Rhapsody  (Park, Diwan, Harwath y Choi, 2025)", NAVY,
         "13 000 episodios de podcast con puntajes por segmento derivados de Most Replayed: es el mismo tipo de contenido que este trabajo|y el conjunto cuya receta seguimos para construir YT-MR."),
        ("Picos de re-reproducción en video educativo  (Kim et al., 2014)", PURPLE,
         "862 videos de MOOCs: los picos de re-reproducción señalan puntos de interés (y a veces de confusión) que se pueden explicar,|por ejemplo 61 % coincide con cambios visuales en 80 videos revisados."),
    ]
    y = 0.545
    for t, c, b in cards:
        ax.add_patch(FancyBboxPatch((0.03, y - 0.104), 0.94, 0.108, boxstyle="round,pad=0.0,rounding_size=0.008", fc="white", ec=c, lw=1.8))
        ax.add_patch(FancyBboxPatch((0.03, y - 0.104), 0.006, 0.108, boxstyle="square,pad=0", fc=c, ec=c))
        ax.text(0.045, y - 0.010, t, fontsize=12, fontweight="bold", color=c, va="top")
        ax.text(0.045, y - 0.036, tx(b), fontsize=9.8, va="top", color="#222222", linespacing=1.35)
        y -= 0.122
    ax.text(0.03, 0.025, tx("Referencias verificadas: Sul, J., Han, J., & Lee, J. (2023). Mr. HiSum. NeurIPS 36, 40542-40555. https://doi.org/10.52202/075280-1764  |  Park, Y. et al. (2025). Rhapsody. https://doi.org/10.48550/arXiv.2505.19429|Kim, J. et al. (2014). Understanding in-video dropouts and interaction peaks in online lecture videos. L@S, 31-40. https://doi.org/10.1145/2556325.2566237"), fontsize=8.2, color=GREY, linespacing=1.4)
    fig.savefig(OUT / "C_respaldo_picos.png")
    return fig


if __name__ == "__main__":
    figs = [fig_a(), fig_b(), fig_c()]
    with PdfPages(OUT / "EXPLICACION_COMPLETA.pdf") as pdf:
        for f in figs:
            pdf.savefig(f)
    print("ok", OUT)
