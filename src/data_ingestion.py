"""Read a Hudl upload and map its headers to FormationIQ names."""
from __future__ import annotations

import re
import pandas as pd

from src.config import HUDL_COLUMN_ALIASES, REQUIRED_COLUMNS


def _key(name) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(name).upper())


def read_upload(file) -> dict[str, pd.DataFrame]:
    """Return {sheet_name: DataFrame}. CSV becomes a single 'CSV' sheet.
    Each Excel sheet is kept separate so multi-game workbooks get a Game_ID per sheet."""
    name = getattr(file, "name", str(file)).lower()
    if name.endswith(".csv"):
        return {"CSV": pd.read_csv(file)}
    sheets = pd.read_excel(file, sheet_name=None)
    return {k: v for k, v in sheets.items() if not v.dropna(how="all").empty}


def read_uploads(files) -> dict[str, pd.DataFrame]:
    """Multiple files, one game each. Game_ID = file name (e.g. 'Oside')."""
    out = {}
    for f in files:
        stem = getattr(f, "name", str(f)).rsplit("/", 1)[-1].rsplit(".", 1)[0]
        base, n = stem, 2
        while stem in out or any(k.startswith(stem + " - ") for k in out):
            stem = f"{base} ({n})"   # same file name uploaded twice: keep both so the duplicate check can see them
            n += 1
        sheets = read_upload(f)
        if len(sheets) == 1:
            out[stem] = next(iter(sheets.values()))
        else:
            for k, v in sheets.items():
                out[f"{stem} - {k}"] = v
    return out


def normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Rename known Hudl headers. Returns (df, list of unmapped original columns)."""
    rename, unmapped, used = {}, [], set()
    for col in df.columns:
        target = HUDL_COLUMN_ALIASES.get(_key(col))
        if target and target not in used:
            rename[col] = target
            used.add(target)
        else:
            unmapped.append(str(col))
    return df.rename(columns=rename), unmapped


def missing_required(df: pd.DataFrame) -> list[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]
