from __future__ import annotations

import datetime as dt
import io
import os
from typing import Any, Optional

import httpx
import pandas as pd

__version__ = "0.1.4"

_DATE_COLUMNS = ("date", "ts", "start", "end", "filed")
_DATE_COLUMNS = tuple(dict.fromkeys(tuple(_DATE_COLUMNS) + ("realtime_start",)))
_DATE_COLUMNS = tuple(dict.fromkeys(tuple(_DATE_COLUMNS) + ("trade_date",)))
# realtime_end stays text: the open vintage is 9999-12-31, outside pandas timestamp range


class FinzError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"{status}: {detail}")
        self.status = int(status)
        self.detail = str(detail)


def _iso(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _clean(params: dict) -> dict:
    out = {}
    for key, value in params.items():
        if value is None:
            continue
        out[key] = _iso(value)
    return out


class Client:
    def __init__(self, api_key=None, base_url=None, http=None, timeout=60):
        self.api_key = api_key if api_key is not None else os.environ.get("FINZDATA_API_KEY")
        self.base_url = base_url if base_url is not None else (
            os.environ.get("FINZDATA_URL") or "https://api.finzdata.com"
        )
        self.timeout = timeout
        if http is not None:
            self.http = http
        else:
            self.http = httpx.Client(base_url=self.base_url, timeout=timeout)

    def _get(self, path: str, params: Optional[dict] = None):
        response = self.http.get(
            path,
            params=_clean(params or {}),
            headers={"X-API-Key": self.api_key},
        )
        if not (200 <= response.status_code < 300):
            detail = None
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    detail = payload.get("detail")
            except Exception:
                detail = None
            if detail is None:
                detail = response.text
            if not isinstance(detail, str):
                detail = str(detail)
            raise FinzError(response.status_code, detail)
        return response.json()

    def _frame(self, path: str, params: Optional[dict] = None) -> pd.DataFrame:
        payload = self._get(path, params)
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        frame = pd.DataFrame(rows)
        for column in _DATE_COLUMNS:
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column])
        return frame

    def me(self) -> dict:
        return self._get("/v1/me")

    def datasets(self):
        return self._frame("/v1/datasets", {})

    def cot(self, report=None, code=None, market=None, start=None, end=None) -> pd.DataFrame:
        return self._frame(
            "/v1/cot",
            {"report": report, "code": code, "market": market, "start": start, "end": end},
        )

    def cot_markets(self, report="legacy_fo"):
        return self._frame("/v1/cot/markets", {"report": report})

    def prices(self, symbol, start=None, end=None, adjust="splits") -> pd.DataFrame:
        return self._frame(
            "/v1/prices/daily",
            {"symbol": symbol, "start": start, "end": end, "adjust": adjust},
        )

    def minutes(self, symbol, start=None, end=None, interval="1min", adjust="none") -> pd.DataFrame:
        """Intraday bars. interval: 1min | 5min | 1hour. adjust: none | all (splits + dividends)."""
        return self._frame(
            "/v1/prices/minute",
            {"symbol": symbol, "start": start, "end": end, "interval": interval, "adjust": adjust},
        )

    def actions(self, symbol) -> pd.DataFrame:
        return self._frame("/v1/actions", {"symbol": symbol})

    def statements(self, ticker, statement="income", freq="quarterly", as_of=None) -> pd.DataFrame:
        """Standardised statement from SEC XBRL: statement = income | balance | cashflow; freq = quarterly | annual | ttm.
        as_of='YYYY-MM-DD' returns only what had been filed by then (look-back plans)."""
        df = self._frame("/v1/statements", {"ticker": ticker, "statement": statement, "freq": freq, "as_of": as_of})
        if "period_end" in df.columns:
            df["period_end"] = pd.to_datetime(df["period_end"])
            df = df.set_index("period_end")
        return df

    def fund_holders(self, ticker, limit=1000) -> pd.DataFrame:
        """Mutual funds and ETFs holding a stock, from their latest SEC Form N-PORT (look-back plans)."""
        return self._frame("/v1/fund_holdings", {"ticker": ticker, "limit": limit})

    def fund_holdings(self, series_id, limit=10000) -> pd.DataFrame:
        """One fund's equity book (N-PORT series id, e.g. from fund_holders)."""
        return self._frame("/v1/fund_holdings", {"series_id": series_id, "limit": limit})

    def earnings_dates(self, ticker) -> pd.DataFrame:
        """Past earnings releases from SEC 8-K Item 2.02 filings since 2004, with timing (before_open / after_close)."""
        return self._frame("/v1/earnings_dates", {"ticker": ticker})

    def short_interest(self, ticker, start=None, end=None) -> pd.DataFrame:
        """FINRA short interest twice a month since 2017: short_shares, change, avg_daily_volume, days_to_cover."""
        return self._frame("/v1/short_interest", {"ticker": ticker, "start": start, "end": end})

    def insider_transactions(self, ticker=None, owner=None, code=None, start=None, end=None, limit=10000) -> pd.DataFrame:
        """SEC Form 4/5 insider transactions since 2006 (code P = open-market buy, S = sale). Free: last 12 months."""
        return self._frame("/v1/insiders", {"ticker": ticker, "owner": owner, "code": code, "start": start,
                                            "end": end, "limit": limit})

    def profile(self, symbol=None, sector=None) -> pd.DataFrame:
        """Name, exchange, sector, industry, country, IPO date and history range; symbol may be a comma list."""
        return self._frame("/v1/profile", {"symbol": symbol, "sector": sector})

    def fundamentals(self, ticker=None, cik=None, concept=None, as_of=None) -> pd.DataFrame:
        return self._frame(
            "/v1/fundamentals",
            {"ticker": ticker, "cik": cik, "concept": concept, "as_of": as_of},
        )


_default: Optional[Client] = None


def set_default_client(client: Optional[Client]) -> None:
    global _default
    _default = client


def get_client() -> Client:
    global _default
    if _default is None:
        _default = Client()
    return _default


def period_start(period, today=None):
    if today is None:
        today = dt.date.today()
    if isinstance(today, dt.datetime):
        today = today.date()
    if period is None:
        raise ValueError(f"invalid period: {period!r}")
    text = str(period).strip().lower()
    if text == "max":
        return None
    if text == "ytd":
        return dt.date(today.year, 1, 1)
    for suffix, days in (("wk", 7), ("mo", 31), ("d", 1), ("y", 366)):
        if text.endswith(suffix):
            number = text[: -len(suffix)]
            if number.isdigit():
                return today - dt.timedelta(days=days * int(number))
    raise ValueError(f"invalid period: {period!r}")


_HISTORY_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _empty_history(index_name: str = "Date") -> pd.DataFrame:
    index = pd.DatetimeIndex([], name=index_name)
    return pd.DataFrame(columns=_HISTORY_COLUMNS, index=index)


class Ticker:
    def __init__(self, symbol, client=None):
        self.ticker = str(symbol).upper()
        self.client = client if client is not None else get_client()

    def _stmt(self, statement, freq):
        df = self.client.statements(self.ticker, statement, freq)
        if df.empty:
            return df
        special = {"sga": "SGA", "eps_basic": "EPS Basic", "eps_diluted": "EPS Diluted"}
        t = df.sort_index(ascending=False).T
        t.index = [special.get(c, c.replace("_", " ").title()) for c in t.index]
        return t

    # yfinance-style statements: line items as rows, newest period first
    income_stmt = property(lambda self: self._stmt("income", "annual"))
    financials = income_stmt
    quarterly_income_stmt = property(lambda self: self._stmt("income", "quarterly"))
    quarterly_financials = quarterly_income_stmt
    ttm_income_stmt = property(lambda self: self._stmt("income", "ttm"))
    balance_sheet = property(lambda self: self._stmt("balance", "annual"))
    quarterly_balance_sheet = property(lambda self: self._stmt("balance", "quarterly"))
    cashflow = property(lambda self: self._stmt("cashflow", "annual"))
    quarterly_cashflow = property(lambda self: self._stmt("cashflow", "quarterly"))
    ttm_cashflow = property(lambda self: self._stmt("cashflow", "ttm"))

    @property
    def mutualfund_holders(self) -> pd.DataFrame:
        return self.client.fund_holders(self.ticker)

    @property
    def earnings_dates(self) -> pd.DataFrame:
        return self.client.earnings_dates(self.ticker)

    @property
    def short_interest(self) -> pd.DataFrame:
        return self.client.short_interest(self.ticker)

    @property
    def insider_transactions(self) -> pd.DataFrame:
        return self.client.insider_transactions(self.ticker)

    @property
    def info(self) -> dict:
        """Company profile like yfinance's Ticker.info: name, exchange, sector, industry, country, IPO date."""
        df = self.client.profile(self.ticker)
        if df.empty:
            return {"symbol": self.ticker}
        r = df.iloc[0].to_dict()
        return {"symbol": r.get("symbol"), "longName": r.get("name"), "shortName": r.get("name"),
                "exchange": r.get("exchange"), "sector": r.get("sector"), "industry": r.get("industry"),
                "country": r.get("country"), "state": r.get("state"), "ipoDate": r.get("ipo_date"),
                "firstTradeDate": r.get("first_date"), "lastTradeDate": r.get("last_date"),
                "delisted": bool(r.get("delisted"))}

    def history(self, period="1mo", interval="1d", start=None, end=None, auto_adjust=True) -> pd.DataFrame:
        if start is None:
            start = period_start(period)
        if interval == "1d":
            frame = self.client.prices(
                self.ticker,
                start=start,
                end=end,
                adjust="all" if auto_adjust else "none",
            )
            index_name = "Date"
        elif interval in _INTRADAY:
            frame = self.client.minutes(
                self.ticker,
                start=start,
                end=end,
                interval=_INTRADAY[interval],
                adjust="all" if auto_adjust else "none",
            )
            index_name = "Datetime"
        else:
            raise ValueError(f"invalid interval: {interval!r}")
        return _normalize_history(frame, index_name)

    @property
    def dividends(self) -> pd.Series:
        return self._action_series("dividend", "Dividends")

    @property
    def splits(self) -> pd.Series:
        return self._action_series("split", "Stock Splits")

    def _action_series(self, kind: str, name: str) -> pd.Series:
        frame = self.client.actions(self.ticker)
        index = pd.DatetimeIndex([], name="Date")
        series = pd.Series([], dtype="float64", index=index, name=name)
        if frame is None or frame.empty or "type" not in frame.columns:
            return series
        mask = frame["type"].astype(str).str.lower().str.contains(kind)
        subset = frame[mask]
        if subset.empty:
            return series
        dates = None
        for column in ("date", "ts"):
            if column in subset.columns:
                dates = pd.to_datetime(subset[column])
                break
        if dates is None:
            dates = pd.to_datetime(subset.index)
        values = None
        for column in ("value", "amount", "dividend", "split"):
            if column in subset.columns:
                values = subset[column]
                break
        if values is None:
            numeric = [c for c in subset.columns if c not in ("type", "date", "ts")]
            values = subset[numeric[0]] if numeric else pd.Series([1.0] * len(subset))
        series = pd.Series(
            pd.to_numeric(values, errors="coerce").to_numpy(),
            index=pd.DatetimeIndex(dates, name="Date"),
            name=name,
        )
        return series.sort_index()

    @property
    def actions(self) -> pd.DataFrame:
        dividends = self.dividends
        splits = self.splits
        frame = pd.DataFrame({"Dividends": dividends, "Stock Splits": splits})
        frame = frame.fillna(0.0)
        frame.index = pd.DatetimeIndex(frame.index, name="Date")
        return frame

    def facts(self, concept=None, as_of=None) -> pd.DataFrame:
        return self.client.fundamentals(ticker=self.ticker, concept=concept, as_of=as_of)


def _normalize_history(frame: pd.DataFrame, index_name: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_history(index_name)
    frame = frame.copy()
    date_column = None
    for column in ("date", "ts"):
        if column in frame.columns:
            date_column = column
            break
    if date_column is not None:
        frame.index = pd.DatetimeIndex(pd.to_datetime(frame[date_column]), name=index_name)
        frame = frame.drop(columns=[date_column])
    else:
        frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index), name=index_name)
    rename = {}
    for column in frame.columns:
        lowered = str(column).lower()
        for target in _HISTORY_COLUMNS:
            if lowered == target.lower():
                rename[column] = target
    frame = frame.rename(columns=rename)
    for column in _HISTORY_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.Series(dtype="float64")
    frame = frame[_HISTORY_COLUMNS]
    return frame.sort_index()


def _parse_tickers(tickers) -> list:
    if isinstance(tickers, str):
        parts = tickers.replace(",", " ").split()
        return [part.upper() for part in parts]
    return [str(ticker).upper() for ticker in tickers]


_INTRADAY = {"1m": "1min", "5m": "5min", "60m": "1hour", "1h": "1hour"}


def download(tickers, start=None, end=None, period="1mo", interval="1d", auto_adjust=True, client=None) -> pd.DataFrame:
    symbols = _parse_tickers(tickers)
    frames = {}
    for symbol in symbols:
        ticker = Ticker(symbol, client=client)
        frames[symbol] = ticker.history(
            period=period,
            interval=interval,
            start=start,
            end=end,
            auto_adjust=auto_adjust,
        )
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, axis=1)
    combined.columns = combined.columns.swaplevel(0, 1)
    combined = combined.sort_index(axis=1, level=0)
    return combined.sort_index()


def cot(**kw) -> pd.DataFrame:
    return get_client().cot(**kw)


# --- macro data (FRED/ALFRED, point-in-time) -------------------------------------------
def _clean(params: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in params.items() if v is not None}


def _macro(self, series, start=None, end=None, vintage="latest", as_of=None) -> pd.DataFrame:
    """Macro series. vintage: 'latest' (current values), 'first' (as first released) or 'all';
    as_of='YYYY-MM-DD' returns only what was known on that date (point-in-time, Researcher+)."""
    return self._frame("/v1/macro", _clean({"series": series, "start": start, "end": end, "vintage": vintage, "as_of": as_of}))


def _macro_series(self, category=None) -> pd.DataFrame:
    """Catalog of available macro series (id, title, units, frequency, category, ...)."""
    return self._frame("/v1/macro/series", _clean({"category": category}))


def _macro_calendar(self, start=None, end=None) -> pd.DataFrame:
    """Upcoming and recent economic release dates."""
    return self._frame("/v1/macro/calendar", _clean({"start": start, "end": end}))


Client.macro = _macro
Client.macro_series = _macro_series
Client.macro_calendar = _macro_calendar


def macro(series, **kw):
    return get_client().macro(series, **kw)


def _licensed(self, series_id, start=None, end=None) -> pd.DataFrame:
    """Third-party licensed series (paid plans). Each row carries its `source` citation."""
    return self._frame("/v1/licensed/series", _clean({"id": series_id, "start": start, "end": end}))


def _licensed_catalog(self) -> pd.DataFrame:
    """Licensed series, their owners, citations and availability."""
    return self._frame("/v1/licensed/catalog", {})


def _vix_futures(self, start=None, end=None) -> pd.DataFrame:
    """Daily VIX futures settlements by expiry (paid plans)."""
    return self._frame("/v1/licensed/vix-futures", _clean({"start": start, "end": end}))


Client.licensed = _licensed
Client.licensed_catalog = _licensed_catalog
Client.vix_futures = _vix_futures


def _model(self, what="latest", series=None, start=None, end=None):
    """FinzData Quantitative Model (paid plans): what = latest | labels | nowcast | stress | catalog."""
    if what not in ("latest", "labels", "nowcast", "stress", "catalog"):
        raise ValueError("what must be latest, labels, nowcast, stress or catalog")
    if what == "latest":
        return self._get("/v1/model/latest", {})
    return self._frame(f"/v1/model/{what}", _clean({"series": series, "start": start, "end": end}))


Client.model = _model


def _liquidity(self, series, start=None, end=None, transform="level", wide=False) -> pd.DataFrame:
    """Money, Liquidity & Capital Flows (paid plans).

    series: one id or a list, e.g. "FED_NET_LIQUIDITY" or ["US_M2", "US_M3_ESTIMATE", "G4_BROAD_MONEY_USD"].
    transform: level | yoy (% over a year) | mom (% over one period) | diff | diff_yoy.
    wide=True returns one column per series indexed by date. The source credit is in frame.attrs["source"].
    """
    ids = series if isinstance(series, str) else ",".join(series)
    payload = self._get("/v1/liquidity", _clean({"series": ids, "start": start, "end": end, "transform": transform}))
    frame = pd.DataFrame(payload.get("data", []))
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"])
    if wide and len(frame):
        frame = frame.pivot(index="date", columns="series_id", values="value").sort_index()
        frame.columns.name = None
    frame.attrs["source"] = payload.get("citation")
    return frame


def _liquidity_catalog(self, group=None) -> pd.DataFrame:
    """Series available in Money, Liquidity & Capital Flows (group: money_supply | liquidity | capital_flows)."""
    return self._frame("/v1/liquidity/catalog", _clean({"group": group}))


def _tic(self, country=None, asset=None, start=None, end=None) -> pd.DataFrame:
    """Treasury TIC: foreign holdings, net purchases and valuation changes of US securities (USD bn), paid plans.

    country: a country name, or "All", "Official", "Private". asset: total | treasuries | agencies | corporate_bonds | equities.
    """
    return self._frame("/v1/liquidity/tic", _clean({"country": country, "asset": asset, "start": start, "end": end}))


Client.liquidity = _liquidity
Client.liquidity_catalog = _liquidity_catalog
Client.tic = _tic


# --- 13F institutional holdings (SEC filings, every manager, 2013 onward) ---------------
def _f13_ownership(self, ticker=None, cusip=None, start=None, end=None) -> pd.DataFrame:
    """Institutional ownership of one security by quarter: holders, shares, value and the quarter's flows
    (new, closed, increased, decreased positions). Free: latest quarter; look-back bundles: the years you bought."""
    return self._frame("/v1/13f/ownership", _clean({"ticker": ticker, "cusip": cusip, "start": start, "end": end}))


def _f13_holders(self, ticker=None, cusip=None, period=None, limit=1000) -> pd.DataFrame:
    """Every manager that reported the security for a quarter (e.g. period='2026Q2'; latest by default)."""
    return self._frame("/v1/13f/holders", _clean({"ticker": ticker, "cusip": cusip, "period": period, "limit": limit}))


def _f13_manager(self, cik, period=None) -> pd.DataFrame:
    """A manager's full 13F book for a quarter, with portfolio weights."""
    return self._frame("/v1/13f/manager", _clean({"cik": cik, "period": period}))


def _f13_managers(self, q=None, period=None, limit=500) -> pd.DataFrame:
    """Managers that filed for a quarter, largest first; q filters by name (e.g. q='berkshire')."""
    return self._frame("/v1/13f/managers", _clean({"q": q, "period": period, "limit": limit}))


Client.institutional_ownership = _f13_ownership
Client.holders = _f13_holders
Client.manager_holdings = _f13_manager
Client.managers = _f13_managers
