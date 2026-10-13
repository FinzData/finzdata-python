# FinzData integration examples

Short, runnable examples showing how to plug FinzData's long, survivorship-free
price history into the backtesting tools you already use. Set
`FINZDATA_API_KEY` in your environment before running any of them.

| Example | What it shows |
| --- | --- |
| `vectorbt_momentum.py` | 12-1 month momentum on 20 large caps, monthly top-5 portfolio with vectorbt. |
| `backtrader_feed.py` | SPY daily bars into `bt.feeds.PandasData`, 50/200 SMA crossover strategy. |
| `nautilus_bars.py` | 1-minute bars converted to NautilusTrader `Bar` objects and written to a `ParquetDataCatalog`. |
| `quantconnect_custom_data.py` | A LEAN `PythonData` custom data class reading FinzData CSV exports. |

## Install

```bash
pip install finzdata vectorbt backtrader nautilus_trader
```

Each example only needs `finzdata` plus the one library it demonstrates.

## More

- Building an AI agent on FinzData? See https://finzdata.com/agents
- Choosing data for backtests: https://finzdata.com/learn/backtesting-data
