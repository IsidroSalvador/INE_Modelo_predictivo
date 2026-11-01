"""Rutas y constantes del proyecto."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CCPC_DIR = RAW / "ccpc"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_MAP = ROOT / "outputs" / "maps"

YEARS = [2009, 2012, 2015, 2018, 2021, 2024]
TIPO_ELECCION = {2009: "intermedia", 2012: "presidencial", 2015: "intermedia",
                 2018: "presidencial", 2021: "intermedia", 2024: "presidencial"}

EDAD_BINS = [17, 24, 34, 49, 64, 200]
EDAD_LABELS = ["18_24", "25_34", "35_49", "50_64", "65m"]

for p in (INTERIM, PROCESSED, OUT_FIG, OUT_TAB, OUT_MAP):
    p.mkdir(parents=True, exist_ok=True)
