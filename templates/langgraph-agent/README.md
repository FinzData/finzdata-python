# LangGraph agent on FinzData

A research agent that answers market questions with point-in-time, survivorship-free data and server-side backtests, using the 39 FinzData tools from `langchain-finzdata`.

```
pip install langchain-finzdata langgraph langchain-anthropic
export ANTHROPIC_API_KEY=...
python agent.py "Backtest 12-1 momentum on the top 1000 US stocks and run survivorship_audit on it"
```

Any LangChain chat model with tool calling works: `MODEL=openai:gpt-4.1 python agent.py "..."`.
FinzData needs no key for a 6-month preview; set `FINZDATA_API_KEY` (free, email only: https://finzdata.com/agents) for 12 months, and buy full history at https://finzdata.com/shop.
