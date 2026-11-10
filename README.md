<p align="center"><a href="https://finzdata.com"><img src="https://finzdata.com/assets/brand/finzdata-logo-full.png" alt="FinzData" width="360"></a></p>

# finzdata

Python client for the [FinzData](https://finzdata.com) market data API. It works like yfinance and adds
the datasets yfinance doesn't have.

```
pip install finzdata
```

Get a free API key at https://api.finzdata.com/ and set `FINZDATA_API_KEY`.

```python
import finzdata as yf

msft = yf.Ticker("MSFT")
daily = msft.history(start="2020-01-01")                  # daily bars, split and dividend adjusted
bars = msft.history(interval="5m", start="2026-10-01")    # 1m, 5m, 1h bars (Researcher+)
both = yf.download(["SPY", "QQQ"], period="max")

c = yf.Client()
gold = c.cot(report="legacy_fo", code="088691")            # CFTC Commitments of Traders (COMEX gold)
rev = c.fundamentals(ticker="AAPL", concept="Revenues", as_of="2025-06-30")   # SEC, point-in-time
cpi = c.macro("CPIAUCSL", as_of="2022-06-30")             # US macro, as known on that date
regime = c.model("latest")                                # FinzData Quantitative Model (Researcher+)
hy = c.licensed("BAMLH0A0HYM2")                           # licensed third-party series (Researcher+)
liq = c.liquidity("FED_NET_LIQUIDITY")                   # Fed assets - TGA - reverse repo (Researcher+)
money = c.liquidity(["US_M2", "US_M3_ESTIMATE"], transform="yoy", wide=True)  # money supply growth
flows = c.tic(country="Japan", asset="treasuries")       # TIC foreign holdings and net purchases
```

## Also in the client (0.1.4)

```python
t = yf.Ticker("AAPL")
t.info                      # name, exchange, sector, industry, IPO date
t.income_stmt               # annual; also quarterly_income_stmt, ttm_income_stmt
t.balance_sheet, t.cashflow
t.insider_transactions      # SEC Forms 4/5 since 2006
t.short_interest            # FINRA, twice a month since 2017
t.mutualfund_holders        # SEC N-PORT fund holdings
t.earnings_dates            # SEC 8-K Item 2.02 since 2004
```

## Coverage

FinzData is point-in-time market data for AI, quants, data scientists and financial analysts:

- 16,000+ US stocks traded since 2000, delisted included, and 5,100+ ETFs: tick trades and 1-minute to daily bars
- Point-in-time options gamma (GEX) for 11,200+ stocks, ETFs and indexes since 2010, plus options chains
- 139 futures markets with every contract since 2007; CFTC COT since 1986
- 512 crypto pairs, 79 FX pairs and 123 indexes
- SEC fundamentals as filed, 13F holdings, insider trades and short interest
- 22,700+ macro series with every vintage, including electricity use, prices and power demand
- Global Macro Pulse: ship transits through 28 chokepoints, port calls for 2,000+ ports, flights by airport and airline, and toll and congestion traffic

Free API key: https://finzdata.com · MCP server for Claude and other AI assistants: https://api.finzdata.com/mcp · Docs: https://finzdata.com/docs

## Datasets

- US equity bars, daily (incl. delisted names) and intraday 1-minute, 5-minute and hourly
- Splits and dividends
- CFTC Commitments of Traders, all reports, since 1986
- SEC XBRL fundamentals, as reported and point-in-time
- US macro series with every vintage (FRED/ALFRED), plus a release calendar
- FinzData Quantitative Model: macro regime labels, a nowcast and a market-stress probability
- Futures: 142 markets, every contract since 2007, daily and 1-minute to hourly bars, continuous series: `c.futures("ES", continuous=True)`
- Licensed series: Moody's, University of Michigan, Case-Shiller, ICE BofA, Cboe (incl. the VIX futures curve)

Guides (13F, COT, macro vintages, intraday, delisted stocks): https://finzdata.com/guides ·
Free samples and the full file specification: https://finzdata.com/samples ·
Pricing: https://finzdata.com/pricing · Data status: https://finzdata.com/status ·
API reference: https://api.finzdata.com/docs

Bulk downloads (Researcher and above): `POST /v1/batch`, then fetch the `download_url`.
Full-history bundles and nightly updates: `GET /v1/bundles`.

Data is provided under the FinzData subscriber licence; redistribution is prohibited.

## Examples

| Notebook | What it shows |
|---|---|
| [examples/13f_holdings.ipynb](examples/13f_holdings.ipynb) | 13F manager books, holders of a stock, ownership flows |
| [examples/cot_positioning.ipynb](examples/cot_positioning.ipynb) | COT net speculative positioning and its percentile |
| [examples/macro_vintages.ipynb](examples/macro_vintages.ipynb) | First release vs revised macro data, as-of queries |

More guides: https://finzdata.com/guides
