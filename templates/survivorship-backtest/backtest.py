"""Survivorship-bias check for any strategy, run on the FinzData server (no data download, no key needed for a
6-month preview; set FINZDATA_API_KEY for more history).

    python backtest.py                      # 3-month momentum on the 500 most-traded US stocks
    python backtest.py --universe top1000 --start 2010-01-01 --lookback 252 --skip 21   # needs full history

survivorship_audit runs your spec twice: on the point-in-time universe (delisted names included while they traded)
and on today's survivors only, and reports how much CAGR and Sharpe the survivor list adds.
"""
import argparse, datetime, json, os, urllib.request

MCP = "https://api.finzdata.com/mcp"


def call(tool, args):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if os.environ.get("FINZDATA_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["FINZDATA_API_KEY"]
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    req = urllib.request.Request(MCP, data=body, headers=headers)
    res = json.loads(urllib.request.urlopen(req, timeout=300).read())["result"]
    return res.get("structuredContent") or res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--universe", default="top500", help="top500 | top1000 | top3000 or comma-separated tickers")
    p.add_argument("--start", default="2026-06-01")
    p.add_argument("--end", default=None)
    p.add_argument("--lookback", type=int, default=63, help="momentum lookback in trading days")
    p.add_argument("--skip", type=int, default=5, help="most recent days skipped")
    p.add_argument("--top", type=int, default=50, help="names held")
    a = p.parse_args()
    universe = a.universe.split(",") if "," in a.universe else a.universe
    spec = {"universe": universe, "start": a.start, "rebalance": "M", "top_n": a.top, "costs_bps": 10,
            "signal": {"type": "momentum", "lookback": a.lookback, "skip": a.skip}}
    spec["end"] = a.end or (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    out = call("survivorship_audit", {"spec": spec})
    if not out.get("ok", True) or "error" in out:
        print(json.dumps(out, indent=1)); return
    r = out.get("result", out)
    pit, surv = r["point_in_time"]["stats"], r["survivors_only"]["stats"]
    print(f"{'':22}{'point in time':>16}{'survivors only':>16}")
    for k in ("cagr", "sharpe", "max_drawdown"):
        print(f"{k:22}{pit[k]:>16.3f}{surv[k]:>16.3f}")
    print(f"names a survivor list leaves out: {r['survivors_only'].get('names_excluded')}")
    print(f"CAGR added by survivorship bias: {r['inflation']['cagr']:+.3f}   Sharpe added: {r['inflation']['sharpe']:+.3f}")
    print(f"snapshot: {r.get('snapshot')}  (cite it to reproduce this result)")


if __name__ == "__main__":
    main()
