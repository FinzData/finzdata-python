"""A LangGraph research agent on FinzData point-in-time market data.

    pip install langchain-finzdata langgraph langchain-anthropic   # or langchain-openai
    export ANTHROPIC_API_KEY=...          # your model provider's key
    export FINZDATA_API_KEY=...           # optional: free key (email only) for 12 months; none = 6-month preview
    python agent.py "Is SPX in positive or negative gamma today?"

MODEL picks the chat model, e.g. MODEL=openai:gpt-4.1 (any LangChain chat model with tool calling works).
"""
import os
import sys

from langchain_finzdata import load_finzdata_tools
from langgraph.prebuilt import create_react_agent

MODEL = os.environ.get("MODEL", "anthropic:claude-sonnet-4-5")
SYSTEM = (
    "You are a quantitative research assistant. Get every number from the FinzData tools; never guess data. "
    "Prefer server-side run_backtest and survivorship_audit over pulling raw bars. "
    "State the as_of date and the snapshot id behind each result, and report the deflated Sharpe ratio with any backtest. "
    "If a tool says the data is beyond the free window, say so and pass on the links it gives."
)


def main():
    question = " ".join(sys.argv[1:]) or "Is SPX in positive or negative dealer gamma today, and how far is it from the gamma flip?"
    agent = create_react_agent(MODEL, load_finzdata_tools(), prompt=SYSTEM)
    result = agent.invoke({"messages": [("user", question)]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
