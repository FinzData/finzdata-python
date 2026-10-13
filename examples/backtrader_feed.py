"""Feed FinzData daily bars into Backtrader and run a 50/200 SMA crossover.

Loads SPY daily history since 2005 with the yfinance-style FinzData client,
wraps the DataFrame in ``bt.feeds.PandasData``, and runs a simple golden-cross
/ death-cross strategy: long when the 50-day SMA is above the 200-day SMA,
flat otherwise. Prints the final portfolio value.

Requires: pip install finzdata backtrader
Set FINZDATA_API_KEY in your environment before running.
"""

import backtrader as bt

import finzdata as fd


class SmaCross(bt.Strategy):
    params = dict(fast=50, slow=200)

    def __init__(self):
        sma_fast = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.fast)
        sma_slow = bt.indicators.SimpleMovingAverage(self.data.close, period=self.p.slow)
        self.crossover = bt.indicators.CrossOver(sma_fast, sma_slow)

    def next(self):
        if not self.position and self.crossover > 0:
            self.buy()
        elif self.position and self.crossover < 0:
            self.close()


def main() -> None:
    # yfinance-style columns: Open, High, Low, Close, Volume, DatetimeIndex.
    frame = fd.Ticker("SPY").history(interval="1d", start="2005-01-01")

    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=frame))
    cerebro.addstrategy(SmaCross)
    cerebro.broker.setcash(100_000.0)
    cerebro.broker.setcommission(commission=0.0005)

    cerebro.run()
    print(f"Final portfolio value: {cerebro.broker.getvalue():,.2f}")


if __name__ == "__main__":
    main()
