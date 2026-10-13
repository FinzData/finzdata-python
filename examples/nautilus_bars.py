"""Convert FinzData 1-minute bars into NautilusTrader Bar objects and persist them.

FinzData provides long intraday bar history back to 2000, which pairs well
with tick-level feeds: many users consume Databento for real-time ticks and
need deep historical bars for research and backtests. This example pulls
1-minute AAPL bars from FinzData, converts them into NautilusTrader ``Bar``
objects with ``BarDataWrangler``, and writes them to a ``ParquetDataCatalog``
so a Nautilus backtest can load them later.

Requires: pip install finzdata nautilus_trader
Set FINZDATA_API_KEY in your environment before running.
"""

import pandas as pd

import finzdata as fd

from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider

CATALOG_PATH = "./catalog"
START = "2024-01-01"
END = "2024-02-01"


def main() -> None:
    # yfinance-style 1-minute bars with a DatetimeIndex.
    frame = fd.Ticker("AAPL").history(interval="1m", start=START, end=END)

    instrument = TestInstrumentProvider.equity("AAPL", "XNAS")
    bar_type = BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-EXTERNAL")

    # BarDataWrangler expects columns: open, high, low, close, volume.
    bars_frame = frame.rename(columns=str.lower)
    bars_frame.index = pd.to_datetime(bars_frame.index, utc=True)

    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    bars: list[Bar] = wrangler.process(bars_frame)

    catalog = ParquetDataCatalog(CATALOG_PATH)
    catalog.write_data([instrument])
    catalog.write_data(bars)

    print(f"Wrote {len(bars)} bars for {instrument.id} to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
