"""Gate for finzdata/adapters.py (plain python, by path, pandas only)."""
import importlib.util, json, sys, tempfile, zipfile
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sp = importlib.util.spec_from_file_location("adapters", ROOT / "finzdata/adapters.py"); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
F = []
def ok(c, msg):
    if not c: F.append(msg)
src = open(ROOT / "finzdata/adapters.py").read()
for bad in ("import backtrader", "import vectorbt", "import zipline", "import nautilus", "import freqtrade", "import qlib"):
    ok(bad not in src, f"must not {bad}")
idx = pd.to_datetime(["2026-10-14", "2026-10-13", "2026-10-15", "2026-10-15"])
yf = pd.DataFrame({"Open": [101, 100, 102, 102.5], "High": [102, 101, 103, 103.5], "Low": [100, 99, 101, 101.5],
                   "Close": [101.5, 100.5, 102.5, 103.25], "Volume": [10, 20, 30, 35], "Extra": 1}, index=idx)
n = m.normalize(yf)
ok(list(n.columns) == ["open", "high", "low", "close", "volume"] and n.index.name == "datetime", f"normalize cols {list(n.columns)} {n.index.name}")
ok(list(n.index.strftime("%Y-%m-%d")) == ["2026-10-13", "2026-10-14", "2026-10-15"] and n.close.iloc[-1] == 103.25, "sorted + dedupe keep last")
c = pd.DataFrame({"date": ["2026-10-13", "2026-10-14"], "open": [1, 2], "high": [1, 2], "low": [1, 2], "close": [1, 2], "volume": [5, 6]})
ok(len(m.normalize(c)) == 2, "date column accepted")
try:
    m.normalize(yf.drop(columns=["Volume"])); ok(False, "missing volume should raise")
except ValueError as e:
    ok("volume" in str(e).lower(), "error names missing column")
b = m.to_backtrader(yf); ok("openinterest" in b.columns and (b.openinterest == 0).all(), "backtrader openinterest")
p = m.to_backtesting_py(yf); ok(list(p.columns) == ["Open", "High", "Low", "Close", "Volume"], "backtesting.py cols")
w = m.to_vectorbt({"SPY": yf, "QQQ": yf.iloc[:2]})
ok(list(w.columns) == ["SPY", "QQQ"] and len(w) == 3 and pd.isna(w.QQQ.iloc[-1]), f"vectorbt wide {w.shape}")
nt = m.to_nautilus(yf); ok(nt.index.name == "timestamp" and str(nt.index.tz) == "UTC", "nautilus utc index")
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    z = m.write_zipline_csvdir({"SPY": yf}, t / "zl")
    txt = z[0].read_text().splitlines()
    ok(z[0] == t / "zl/daily/SPY.csv" and txt[0] == "date,open,high,low,close,volume,dividend,split" and txt[1].startswith("2026-10-13,100"), f"zipline {txt[:2]}")
    ok(txt[1].split(",")[-2:] in (["0.0", "1.0"], ["0", "1"]), f"zipline defaults {txt[1]}")
    L = m.write_lean_daily({"SPY": yf}, str(t / "lean"))
    ok(L[0] == t / "lean/equity/usa/daily/spy.zip", f"lean path {L}")
    line = zipfile.ZipFile(L[0]).read("spy.csv").decode().splitlines()[0]
    ok(line == "20261013 00:00,1000000,1010000,990000,1005000,20", f"lean line {line}")
    fr = m.write_freqtrade_json({"BTC/USD": yf}, t / "ft")
    ok(fr[0].name == "BTC_USD-1d.json", f"freqtrade name {fr[0].name}")
    rows = json.loads(fr[0].read_text())
    ok(rows[0][0] == int(pd.Timestamp("2026-10-13").value // 10**6) and rows[0][4] == 100.5 and len(rows) == 3, f"freqtrade rows {rows[:1]}")
    q = m.write_qlib_csv({"SPY": yf}, t / "qlib")
    ql = q[0].read_text().splitlines()
    ok(ql[0] == "date,open,high,low,close,volume,factor" and ql[1].endswith(",1.0"), f"qlib {ql[:2]}")
ok(set(m.FORMATS) == {"backtrader", "backtesting_py", "vectorbt", "nautilus", "zipline", "lean", "freqtrade", "qlib"}, "FORMATS")
print("PASS gate_adapters" if not F else "FAIL gate_adapters\n  " + "\n  ".join(F)); sys.exit(1 if F else 0)
