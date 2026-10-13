"""Cross-sectional momentum backtest with vectorbt and FinzData.

Downloads 20 large-cap US stocks with daily history since 2010, computes the
classic 12-1 month momentum signal (return over the past 12 months, skipping
the most recent month), and rebalances monthly into an equal-weighted top-5
portfolio using vectorbt.

FinzData history is survivorship-free: symbols that were delisted keep their
full price history instead of silently disappearing. To include delisted
names in your universe, append ``-DELISTED`` to the symbol, e.g.
``fd.download(["AAPL", "LEH-DELISTED"], start="2005-01-01")``. This matters
for momentum studies, where dropping the losers biases results upward.

Requires: pip install finzdata vectorbt
Set FINZDATA_API_KEY in your environment before running.
"""

import finzdata as fd
import vectorbt as vbt

# 20 large caps; add "-DELISTED" symbols here to include dead names.
TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META",
    "NVDA", "JPM", "V", "JNJ", "WMT",
    "PG", "XOM", "HD", "MA", "BAC",
    "PFE", "KO", "PEP", "CSCO", "INTC",
]

START = "2010-01-01"
TOP_N = 5


def main() -> None:
    # Multi-index columns like yfinance: (field, ticker).
    data = fd.download(TICKERS, start=START, interval="1d")
    close = data["Close"].dropna(how="all")

    # Resample to month-end prices for the momentum signal.
    monthly = close.resample("ME").last()

    # 12-1 momentum: total return from t-12 to t-1 (skip the last month).
    momentum = monthly.shift(1) / monthly.shift(12) - 1.0

    # Rank each month; trade the top N names, equal weight.
    ranks = momentum.rank(axis=1, ascending=False)
    entries = ranks <= TOP_N

    # Hold from the month after the signal until the next rebalance.
    entries = entries.reindex(close.index).ffill().fillna(False)

    size = entries.astype(float).div(entries.sum(axis=1).replace(0, pd.NA), axis=0)
    size = size.fillna(0.0)

    portfolio = vbt.Portfolio.from_orders(
        close=close,
        size=size,
        size_type="targetpercent",
        freq="1D",
        init_cash=100_000,
        fees=0.0005,
    )

    print(portfolio.stats())


if __name__ == "__main__":
    import pandas as pd  # noqa: F401  (used for pd.NA above)

    main()
