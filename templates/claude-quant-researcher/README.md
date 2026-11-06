# Claude quant researcher (FinzData)

A ready-made Claude Code project for point-in-time market research: survivorship-free US stocks, ETFs, futures, options gamma (GEX), COT, SEC fundamentals as filed and 22,700+ macro series with every vintage, plus server-side backtests.

## Use it

```
cp -r templates/claude-quant-researcher my-research && cd my-research
mv mcp.json .mcp.json        # Claude Code picks up the FinzData MCP server
claude
```

Or add the server once, anywhere: `claude mcp add --transport http finzdata https://api.finzdata.com/mcp`

`CLAUDE.md` holds the research rules (point-in-time, snapshot ids, survivorship audit, deflated Sharpe). Cursor and other MCP clients: point them at `https://api.finzdata.com/mcp`.

## Try

- "Is SPX in positive or negative dealer gamma today, and where are the walls?"
- "Show speculator positioning in crude oil from COT over the last year, next to /CL prices."
- "What was CPI year over year as known on 2025-01-15, and what is it after revisions?"
- "Backtest 12-1 momentum on the 1000 most-traded US stocks, monthly, then run survivorship_audit on it."

No key needed for a 6-month preview. A free key (email only, https://finzdata.com/agents) gives 12 months; full history at https://finzdata.com/shop.
