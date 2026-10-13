"""QuantConnect / LEAN custom data class backed by FinzData CSV exports.

This is a template for LEAN users who want FinzData's long, survivorship-free
daily history inside a QuantConnect algorithm. ``FinzDataBars`` is a
``PythonData`` custom data type: ``GetSource`` points LEAN at the FinzData
CSV export endpoint and ``Reader`` parses one CSV line
(date,open,high,low,close,volume) into a bar.

Deploy the CSV behind LEAN's remote-file transport (or mirror it to object
storage) and reference the custom data symbol in your algorithm. The API key
is read from the FINZDATA_API_KEY environment variable, never hard-coded.

Requires the QuantConnect LEAN engine (this file is a template; it runs
inside LEAN, not standalone).
"""

import os
from datetime import datetime

from AlgorithmImports import PythonData, QCAlgorithm, Resolution, SubscriptionDataConfig, SubscriptionTransportMedium


class FinzDataBars(PythonData):
    """Custom LEAN data type reading FinzData daily bars as CSV."""

    def GetSource(self, config: SubscriptionDataConfig, date: datetime, isLiveMode: bool):
        key = os.environ.get("FINZDATA_API_KEY", "")
        symbol = config.Symbol.Value
        url = (
            "https://api.finzdata.com/v1/prices"
            f"?symbol={symbol}&format=csv&api_key={key}"
        )
        return SubscriptionDataSource(
            url,
            SubscriptionTransportMedium.RemoteFile,
        )

    def Reader(self, config: SubscriptionDataConfig, line: str, date: datetime, isLiveMode: bool):
        if not line.strip() or line.startswith("date"):
            return None

        parts = line.split(",")
        bar = FinzDataBars()
        bar.Symbol = config.Symbol
        bar.Time = datetime.strptime(parts[0], "%Y-%m-%d")
        bar.EndTime = bar.Time + timedelta(days=1)
        bar["Open"] = float(parts[1])
        bar["High"] = float(parts[2])
        bar["Low"] = float(parts[3])
        bar["Close"] = float(parts[4])
        bar["Volume"] = float(parts[5])
        bar.Value = bar["Close"]
        return bar


class FinzDataMomentumAlgorithm(QCAlgorithm):
    """Minimal example: buy SPY when its FinzData close crosses above its SMA."""

    def Initialize(self):
        self.SetStartDate(2015, 1, 1)
        self.SetEndDate(2024, 1, 1)
        self.SetCash(100_000)

        self.symbol = self.AddData(FinzDataBars, "SPY", Resolution.Daily).Symbol
        self.sma = self.SMA(self.symbol, 50)

    def OnData(self, data):
        if not self.sma.IsReady or not data.ContainsKey(self.symbol):
            return
        close = data[self.symbol].Close
        if close > self.sma.Current.Value and not self.Portfolio.Invested:
            self.SetHoldings(self.symbol, 1.0)
        elif close < self.sma.Current.Value and self.Portfolio.Invested:
            self.Liquidate(self.symbol)
