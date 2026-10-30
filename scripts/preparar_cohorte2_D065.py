"""Prepara la segunda cohorte fresca (D-065): config con consultas nuevas y copias de los scripts de ampliacion."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
cfg = yaml.safe_load((ROOT / "configs" / "ampliacion_D050.yaml").read_text(encoding="utf-8"))
cfg["dataset_youtube"]["target_videos"] = {"es": 350, "en": 346}   # ~50 nuevos por idioma sobre D-050
cfg["dataset_youtube"]["queries"] = {
    "es": ["podcast de emprendimiento digital y marketing", "entrevista completa a actor",
           "podcast de salud mental y ansiedad", "podcast de finanzas e inversiones en espanol",
           "conversacion completa con escritor", "podcast de ciencia y divulgacion episodio completo",
           "debate politico completo", "podcast de maternidad y crianza", "entrevista completa a futbolista",
           "podcast de filosofia episodio completo", "stand up comedy completo mexicano", "charla completa de liderazgo",
           "podcast de crimen real latinoamericano", "podcast de tecnologia e inteligencia artificial",
           "entrevista completa a influencer", "podcast de historia de latinoamerica"],
    "en": ["mental health podcast full episode", "interview with actor full episode",
           "business strategy podcast full episode", "science communication podcast full episode",
           "political debate full length", "parenting advice podcast full episode",
           "football player interview full length", "philosophy lecture full", "stand up special full length",
           "leadership talk full", "true crime podcast long form", "AI and technology podcast long form",
           "influencer interview full podcast", "history documentary podcast long",
           "fitness and nutrition podcast full episode", "relationships and dating podcast full"],
}
header = "# Ampliacion D-065: cohorte fresca 2 (consultas nuevas respecto a D-050).\n"
(ROOT / "configs" / "ampliacion_D065.yaml").write_text(header + yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
                                                       encoding="utf-8")
for src, dst in (("ampliar_dataset_D050.py", "ampliar_dataset_D065.py"), ("acquire_worker_D050.py", "acquire_worker_D065.py")):
    t = (ROOT / "scripts" / src).read_text(encoding="utf-8")
    t = t.replace("D050", "D065").replace("D-050", "D-065").replace("conjunto_confirmacion_fresca_", "conjunto_confirmacion_fresca2_")
    (ROOT / "scripts" / dst).write_text(t, encoding="utf-8")
print("listo: configs/ampliacion_D065.yaml, scripts/ampliar_dataset_D065.py, scripts/acquire_worker_D065.py")
