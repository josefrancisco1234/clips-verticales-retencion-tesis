"""Construye F:\\TESISJF\\BD_TESIS: una carpeta autocontenida (tipo base de datos) con todo lo que analiza el audio y la transcripcion.

Copia (no mueve) los datos derivados de tesis_data y genera un indice por video, un consolidado de variables y un LEEME.md.
No incluye los audios .wav originales (unos 66 GB).
"""
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
D = Path(r"F:\TESISJF\tesis_data\data")
OUT = Path(r"F:\TESISJF\BD_TESIS")
OUT.mkdir(exist_ok=True)

CARPETAS = {
    "01_transcripciones": (D / "interim" / "transcripts" / "base", "*.json"),
    "02_audio_cuadros": (D / "interim" / "audio_frames", "*.npz"),
    "03_eventos_sonido": (D / "interim" / "audio_events", "*.parquet"),
    "04_embeddings_habla": (D / "interim" / "speech_emb", "*"),
    "05_curvas_retencion": (D / "interim" / "heatmaps", "*.json"),
    "06_variables/bin": (D / "processed" / "features" / "bin", "*.parquet"),
    "06_variables/sentence": (D / "processed" / "features" / "sentence", "*.parquet"),
    "06_variables/fixed": (D / "processed" / "features" / "fixed", "*.parquet"),
    "08_clips_humanos": (D / "interim" / "human_clips", "*"),
}
for nombre, (src, pat) in CARPETAS.items():
    dst = OUT / nombre
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in src.glob(pat):
        if f.is_file():
            if not (dst / f.name).exists():
                shutil.copy2(f, dst / f.name)
            n += 1
    print(f"{nombre:28s} {n:5d} archivos")

# Audio en crudo (wav 16 kHz mono, sin perdida): enlaces duros NTFS al original en data/raw/wav, para que BD_TESIS lo contenga sin duplicar 84 GB.
wav_dst = OUT / "10_audio_crudo_wav"
wav_dst.mkdir(exist_ok=True)
n_wav = 0
for f in (D / "raw" / "wav").glob("*.wav"):
    if not (wav_dst / f.name).exists():
        try:
            os.link(f, wav_dst / f.name)
        except OSError:
            shutil.copy2(f, wav_dst / f.name)   # si no es el mismo volumen, se copia
    n_wav += 1
print(f"{'10_audio_crudo_wav':28s} {n_wav:5d} archivos")

(OUT / "07_manifiestos").mkdir(exist_ok=True)
for f in (ROOT / "data" / "manifests").glob("*.csv"):
    shutil.copy2(f, OUT / "07_manifiestos" / f.name)

# ---------------------------------------------------------------- indice por video
J = lambda f: set(json.loads((ROOT / "reports" / f).read_text(encoding="utf-8"))["video_ids"]) if (ROOT / "reports" / f).exists() else set()  # noqa: E731
dev = {str(v) for v in np.load(ROOT / "reports" / "dl_secuencia_D054" / "oof.npz", allow_pickle=True)["vids"]}
grupos = [("desarrollo_444", dev), ("cohorte_fresca_1_D050", J("conjunto_confirmacion_fresca_D050.json")),
          ("cohorte_fresca_2_D065", J("conjunto_confirmacion_fresca2_D065.json")), ("ampliacion_D071", J("conjunto_entrenamiento_extra_D071.json")),
          ("libres_D078", J("conjunto_libres_D078.json")), ("cohorte_fresca_3_D091", J("conjunto_confirmacion_fresca3_D091.json"))]
rep = set(pd.read_csv(ROOT / "data" / "manifests" / "youtube_mr_repurpose.csv")["video_id"])
man = pd.concat([pd.read_csv(f) for f in sorted((ROOT / "data" / "manifests").glob("youtube_mr*.csv")) if "status" not in f.name]).drop_duplicates("video_id")
man = man.set_index("video_id")
ids = sorted({p.stem for p in (OUT / "05_curvas_retencion").glob("*.json")} | {p.stem for p in (OUT / "01_transcripciones").glob("*.json")})
filas = []
for v in ids:
    grupo = next((g for g, s in grupos if v in s), "repurpose_humanos" if v in rep else "otros")
    tp, hp = OUT / "01_transcripciones" / f"{v}.json", OUT / "05_curvas_retencion" / f"{v}.json"
    nw, idioma = None, None
    if tp.exists():
        t = json.loads(tp.read_text(encoding="utf-8"))
        nw, idioma = len(t.get("words", [])), t.get("language")
    meta = json.loads(hp.read_text(encoding="utf-8")) if hp.exists() else {}
    m = man.loc[v] if v in man.index else None
    filas.append({
        "video_id": v, "grupo": grupo, "titulo": meta.get("title") or (m["title"] if m is not None else None),
        "canal": meta.get("channel") or (m["channel"] if m is not None else None), "canal_id": meta.get("channel_id"),
        "idioma_consulta": m["query_lang"] if m is not None else None, "idioma_detectado": idioma,
        "duracion_s": meta.get("duration"), "n_palabras": nw,
        "tiene_transcripcion": tp.exists(), "tiene_audio_cuadros": (OUT / "02_audio_cuadros" / f"{v}.npz").exists(),
        "tiene_audio_crudo_wav": (OUT / "10_audio_crudo_wav" / f"{v}.wav").exists(),
        "tiene_audio_mp3": (OUT / "09_audio_mp3" / f"{v}.mp3").exists(),
        "tiene_eventos_sonido": (OUT / "03_eventos_sonido" / f"{v}.parquet").exists(),
        "tiene_curva": hp.exists(), "tiene_variables_bin": (OUT / "06_variables/bin" / f"{v}.parquet").exists()})
idx = pd.DataFrame(filas)
idx.to_csv(OUT / "indice_videos.csv", index=False, encoding="utf-8-sig")
idx.to_excel(OUT / "indice_videos.xlsx", index=False)
print("indice:", len(idx), "videos |", idx["grupo"].value_counts().to_dict())

# ---------------------------------------------------------------- consolidado de variables por tramo
cons = OUT / "consolidado"
cons.mkdir(exist_ok=True)
partes = []
for p in sorted((OUT / "06_variables/bin").glob("*.parquet")):
    d = pd.read_parquet(p)
    d.insert(0, "video_id_tabla", p.stem)
    partes.append(d)
if partes:
    big = pd.concat(partes, ignore_index=True)
    big.to_parquet(cons / "variables_por_tramo_todos.parquet", index=False)
    print("consolidado:", big.shape)
ncols = len(pd.read_parquet(next((OUT / "06_variables/bin").glob("*.parquet"))).columns)

# ---------------------------------------------------------------- esquemas para el LEEME
ej_ev = next((OUT / "03_eventos_sonido").glob("*.parquet"), None)
cols_ev = list(pd.read_parquet(ej_ev).columns)[:6] if ej_ev else []
ej_h = next((OUT / "05_curvas_retencion").glob("*.json"), None)
claves_h = list(json.loads(ej_h.read_text(encoding="utf-8")).keys()) if ej_h else []
ej_a = next((OUT / "02_audio_cuadros").glob("*.npz"), None)
claves_a = list(np.load(ej_a).files) if ej_a else []

LEEME = f"""# BD_TESIS: base de datos derivada del audio y la transcripcion

Tesis: seleccion automatica de clips con alto potencial de retencion en videos conversacionales (J. F. Nunez del Prado, U. de Lima).
Generada con `scripts/construir_bd_tesis.py`. Contiene {len(idx)} videos de YouTube (podcast, entrevistas, charlas) en espanol e ingles.
**Audios:** `10_audio_crudo_wav/` trae el audio en crudo de cada video (wav 16 kHz mono, sin perdida, ~84 GB, enlazado al original de `data/raw/wav`) y `09_audio_mp3/` el mismo audio en mp3 liviano (voz, 32 kbps). El archivo original que baja YouTube (webm/m4a) se borra a proposito tras extraer el wav (`src/data/youtube_dataset.py:124`), asi que el wav es el audio crudo que existe.

## Transparencia: que cubre y que no cubre esta base de datos
- Videos en el indice: {len(idx)}. Con transcripcion: {int(idx['tiene_transcripcion'].sum())}. Con audio crudo (wav): {int(idx['tiene_audio_crudo_wav'].sum())}. Con audio mp3: {int(idx['tiene_audio_mp3'].sum())}. Con tabla de variables: {int(idx['tiene_variables_bin'].sum())}.
- Los videos sin transcripcion o sin audio figuran en el indice con `False`; no se completaron ni se inventaron. En particular, la `cohorte_fresca_3_D091` quedo incompleta (descarga y transcripcion a medias), por lo que su confirmacion sigue pendiente.
- Los `repurpose_humanos` traen los clips elegidos por editores humanos (`08_clips_humanos/`), para contrastar con la curva.
- Los videos originales de YouTube no se redistribuyen: la base conserva identificadores, audio derivado, transcripciones y variables.

## Que hay en cada carpeta (un archivo por video, nombrado con el ID de YouTube)

| Carpeta | Formato | Que contiene |
|---|---|---|
| `01_transcripciones/` | JSON | Transcripcion en crudo, salida directa de Whisper (`src/transcribe/whisper.py:68`): `language`, `duration`, `model` y `words` = lista de `[texto, inicio_s, fin_s, confianza]` por palabra |
| `02_audio_cuadros/` | NPZ | Cuadros de audio: {', '.join(claves_a)} (`rms_z` = volumen estandarizado, `f0_st` = tono en semitonos, `voiced` = hay voz, `hop_s` = segundos por cuadro) |
| `03_eventos_sonido/` | Parquet | Probabilidad de eventos de sonido con PANNs CNN14 (habla, musica, risa, aplauso...) por segundo. Columnas de ejemplo: {', '.join(cols_ev)} |
| `04_embeddings_habla/` | NPY/NPZ | Representaciones HuBERT del habla por trozo de 10 s (usadas en pruebas D-056/D-062) |
| `05_curvas_retencion/` | JSON | Curva "Most Replayed" de YouTube (100 tramos) y metadatos: {', '.join(claves_h)}. **Solo sirve para calificar, nunca como entrada del sistema.** |
| `06_variables/bin/` | Parquet | 100 tramos por video x {ncols} columnas: variables de contenido por grupo (K texto/tema, S sentimiento, A audio/prosodia, H gancho, F fluidez, L linguisticas, E eventos de sonido, U habla), posicion (`p_*`) y etiquetas (`y_mr`, `y_relevant`, `y_grade`) |
| `06_variables/sentence/` | Parquet | Ventanas candidatas alineadas a oracion (20, 40 y 60 s) con las mismas variables y etiquetas |
| `06_variables/fixed/` | Parquet | Ventanas fijas de 20 s (linea base) |
| `07_manifiestos/` | CSV | Listas de videos (consulta, titulo, canal, duracion, idioma) y su estado de descarga |
| `08_clips_humanos/` | JSON | Clips elegidos por editores humanos (Repurpose-10K), para contrastar con la curva |
| `10_audio_crudo_wav/` | WAV | Audio en crudo: wav 16 kHz mono sin perdida, tal como lo usa Whisper y el calculo de variables (`data/raw/wav`) |
| `09_audio_mp3/` | MP3 | Audio de cada video (voz, mono, 16 kHz, 32 kbps), derivado de los wav de `data/raw/wav` con `scripts/convertir_audio_mp3_bd.py` |
| `consolidado/` | Parquet | `variables_por_tramo_todos.parquet`: todas las tablas de `06_variables/bin` en una sola, con la columna `video_id_tabla` |

## Indice
`indice_videos.csv` lista cada video con su `grupo` (desarrollo_444, cohorte_fresca_1_D050, cohorte_fresca_2_D065, ampliacion_D071, libres_D078,
cohorte_fresca_3_D091, repurpose_humanos u otros), titulo, canal, idioma, duracion, numero de palabras y que archivos existen.

## Como leerlo (Python)
```python
import json, numpy as np, pandas as pd
v = "ID_DEL_VIDEO"
palabras = json.load(open(f"01_transcripciones/{{v}}.json", encoding="utf-8"))["words"]   # [texto, inicio, fin, confianza]
audio = np.load(f"02_audio_cuadros/{{v}}.npz")                                            # rms_z, f0_st, voiced, hop_s
tramos = pd.read_parquet(f"06_variables/bin/{{v}}.parquet")                               # 100 tramos con variables y etiquetas
```

## Reglas de uso (de la tesis)
- Los grupos `cohorte_fresca_*` y `libres_D078` son de **confirmacion**: no se usan para entrenar ni elegir variantes.
- La curva de retencion nunca entra como variable del modelo; solo califica.
- Los divisiones se agrupan por canal para evitar fugas.
"""
(OUT / "LEEME.md").write_text(LEEME, encoding="utf-8")
tam = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e9
print(f"listo: {OUT} | {tam:.2f} GB")
