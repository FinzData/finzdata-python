# Survivorship-bias check for a backtest

`backtest.py` sends a strategy spec to the FinzData server and runs it twice: on the point-in-time universe (delisted companies included while they traded) and on only the names still trading today, the way a backtest on a current ticker list works. It prints both results and how much CAGR and Sharpe the survivor list adds. No data download, no dependencies beyond Python.

```
python backtest.py                                     # 6-month preview, no key
export FINZDATA_API_KEY=...                            # free key: 12 months
python backtest.py --universe top1000 --start 2005-01-01 --lookback 252 --skip 21   # full history (purchase)
python backtest.py --universe SPY,QQQ,IWM,TLT,GLD --top 2
```

Change the signal in the `spec` dict: `momentum`, `ma_cross`, `factor` (point-in-time fundamentals such as book_to_market, earnings_yield, roe) or an `expr` formula like `rank(ret(252)) - rank(vol(60))`. Every result carries a snapshot id so it can be reproduced.
