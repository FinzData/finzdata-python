"""
FinzData adapters for popular backtesting frameworks.

Usage examples:
bt.feeds.PandasData(dataname=adapters.to_backtrader(fd.download("SPY")))
Backtest(adapters.to_backtesting_py(fd.download("SPY")))
vectorbt.Portfolio.from_historical_data(adapters.to_vectorbt({"SPY": fd.download("SPY")}))
BarDataWrangler(adapters.to_nautilus(fd.download("SPY")))
zipline bundle via adapters.write_zipline_csvdir(...)
LEAN data via adapters.write_lean_daily(...)
freqtrade data via adapters.write_freqtrade_json(...)
qlib data via adapters.write_qlib_csv(...)
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Dict

import pandas as pd

FORMATS = {"backtrader", "backtesting_py", "vectorbt", "nautilus", "zipline", "lean", "freqtrade", "qlib"}


def _find_column(columns, names):
    lower_map = {c.lower(): c for c in columns}
    for n in names:
        if n.lower() in lower_map:
            return lower_map[n.lower()]
    return None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {}
    for std in ["open", "high", "low", "close", "volume"]:
        found = _find_column(df.columns, [std])
        if found:
            col_map[found] = std
    for opt in ["dividend", "split"]:
        found = _find_column(df.columns, [opt])
        if found:
            col_map[found] = opt
    if col_map:
        df = df.rename(columns=col_map)
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")

    df = df.copy()
    df = _normalize_columns(df)

    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = _find_column(df.columns, ["date", "datetime"])
        if date_col is None:
            raise ValueError("DataFrame must have DatetimeIndex or a date/datetime column")
        df[date_col] = pd.to_datetime(df[date_col], errors="raise")
        df = df.set_index(date_col)
        df.index.name = None

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="raise")

    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    out = df[required].astype(float).copy()
    out.index = pd.DatetimeIndex(out.index)
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.index.name = "datetime"
    return out


def to_backtrader(df: pd.DataFrame) -> pd.DataFrame:
    n = normalize(df)
    n = n.copy()
    n["openinterest"] = 0.0
    return n


def to_backtesting_py(df: pd.DataFrame) -> pd.DataFrame:
    n = normalize(df)
    n = n.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    })
    n.index.name = None
    return n


def to_vectorbt(frames: Dict[str, pd.DataFrame], field: str = "close") -> pd.DataFrame:
    field_l = field.lower()
    data = {}
    for symbol, df in frames.items():
        n = normalize(df)
        if field_l not in n.columns:
            raise ValueError(f"Field {field} not found for {symbol}")
        data[symbol] = n[field_l]
    out = pd.DataFrame(data)
    out = out.sort_index()
    return out


def to_nautilus(df: pd.DataFrame) -> pd.DataFrame:
    n = normalize(df)
    n.index = n.index.tz_localize("UTC")
    n.index.name = "timestamp"
    return n


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def write_zipline_csvdir(frames: Dict, root) -> list[Path]:
    root = Path(root)
    daily_dir = root / "daily"
    _ensure_dir(daily_dir)
    paths = []
    for symbol, df in frames.items():
        n = normalize(df)
        df_normed = _normalize_columns(df.copy())
        if "dividend" in df_normed.columns:
            dividend_series = pd.to_numeric(df_normed["dividend"], errors="coerce").fillna(0.0).reindex(n.index)
        else:
            dividend_series = pd.Series(0.0, index=n.index, dtype=float)
        if "split" in df_normed.columns:
            split_series = pd.to_numeric(df_normed["split"], errors="coerce").fillna(1.0).reindex(n.index)
        else:
            split_series = pd.Series(1.0, index=n.index, dtype=float)

        out_df = pd.DataFrame({
            "date": n.index.strftime("%Y-%m-%d"),
            "open": n["open"],
            "high": n["high"],
            "low": n["low"],
            "close": n["close"],
            "volume": n["volume"],
            "dividend": dividend_series,
            "split": split_series,
        })
        path = daily_dir / f"{symbol}.csv"
        out_df.to_csv(path, index=False)
        paths.append(path)
    return paths


def write_lean_daily(frames: Dict, root) -> list[Path]:
    root = Path(root)
    base = root / "equity" / "usa" / "daily"
    _ensure_dir(base)
    paths = []
    for symbol, df in frames.items():
        n = normalize(df)
        sym_low = symbol.lower()
        lines = []
        for ts, row in n.iterrows():
            date_str = ts.strftime("%Y%m%d")
            o = int(round(row["open"] * 10000))
            h = int(round(row["high"] * 10000))
            l = int(round(row["low"] * 10000))
            c = int(round(row["close"] * 10000))
            v = int(row["volume"])
            lines.append(f"{date_str} 00:00,{o},{h},{l},{c},{v}")
        csv_content = "\n".join(lines) + ("\n" if lines else "")
        zip_path = base / f"{sym_low}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{sym_low}.csv", csv_content)
        paths.append(zip_path)
    return paths


def write_freqtrade_json(frames: Dict, root, timeframe: str = "1d") -> list[Path]:
    root = Path(root)
    _ensure_dir(root)
    paths = []
    for symbol, df in frames.items():
        n = normalize(df)
        pair = symbol.replace("/", "_").replace("-", "_")
        rows = []
        for ts, row in n.iterrows():
            epoch_ms = int(ts.value // 10**6)
            rows.append([
                epoch_ms,
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(row["volume"]),
            ])
        path = root / f"{pair}-{timeframe}.json"
        with open(path, "w") as f:
            json.dump(rows, f)
        paths.append(path)
    return paths


def write_qlib_csv(frames: Dict, root) -> list[Path]:
    root = Path(root)
    _ensure_dir(root)
    paths = []
    for symbol, df in frames.items():
        n = normalize(df)
        out_df = pd.DataFrame({
            "date": n.index.strftime("%Y-%m-%d"),
            "open": n["open"],
            "high": n["high"],
            "low": n["low"],
            "close": n["close"],
            "volume": n["volume"],
            "factor": 1.0,
        })
        path = root / f"{symbol}.csv"
        out_df.to_csv(path, index=False)
        paths.append(path)
    return paths
