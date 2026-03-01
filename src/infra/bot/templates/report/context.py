import typing
from datetime import datetime
from datetime import timezone
from typing import Optional

from utils.binance.types import BinanceWSEventType


def f(x: typing.Any, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def get_closed_event_context(msg: BinanceWSEventType) -> BinanceWSEventType:
    o = msg.get("o", {})
    symbol = o.get("s", "UNKNOWN")
    quote_asset = symbol[-4:] if symbol and symbol.endswith(("USDT", "BUSD", "USDC")) else "USDT"  # rough heuristic
    base_asset = symbol.replace(quote_asset, "") if symbol and quote_asset in symbol else "BASE"

    fees_quote_value = 0.0
    if "n" in o and "N" in o and str(o.get("N")).upper() == quote_asset:
        fees_quote_value = f(o.get("n"), 0.0)

    # Event time
    t_ms = msg.get("E")
    event_time_str = (
        datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        if isinstance(t_ms, int)
        else None
    )

    ctx = {
        # Market info
        "market": "Futures",
        "symbol": symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "status": o.get("X"),
        "order_type": o.get("ot") or o.get("o"),
        "side": o.get("S"),
        "position_side": o.get("ps"),
        "leverage": msg.get("l"),  # may not be present in this event
        "margin_mode": msg.get("m"),  # may also be missing
        "executed_qty": f(o.get("z")),
        "avg_price": f(o.get("ap") or o.get("p")),
        "realized_pnl": f(o.get("rp")),  # total realized PnL for this update
        "fees_quote_value": fees_quote_value,  # if fee is received and it's quote currency
        "funding_paid": 0.0,  # funding does not come here — keep as 0
        "initial_margin": None,  # can be fetched separately if ROI is needed
        "order_id": o.get("i"),
        "client_order_id": o.get("c"),
        "event_time_str": event_time_str,
        "qty_prec": 4,
        "price_prec": 2,
        "money_prec": 2,
        "notional_prec": 2,
    }

    return ctx


def get_opened_event_context(
    msg: BinanceWSEventType,
    *,
    maker_fee_rate: Optional[float] = None,
    taker_fee_rate: Optional[float] = None,
    fee_mode: str = "taker",  # "maker" | "taker"
    leverage: Optional[int] = None,
    margin_mode: Optional[str] = None,  # "isolated" | "cross"
) -> BinanceWSEventType:
    """
    Builds context for order 'opening' from raw ORDER_TRADE_UPDATE data (X=='NEW').

    Key Futures fields in msg['o']:
      S (side), ps (position side), ot (order type), q (original quantity), p (price), i (order id),
      c (client order id), R (reduce only, bool), X (status='NEW').
    """
    o = msg.get("o", {})
    symbol: str = o.get("s", "UNKNOWN")
    known_quotes = ("USDT", "BUSD", "USDC", "FDUSD", "TUSD")
    quote_asset = next((q for q in known_quotes if symbol.endswith(q)), "USDT")
    base_asset = symbol[: -len(quote_asset)] if symbol.endswith(quote_asset) else "BASE"

    qty = f(o.get("q"))
    price = f(o.get("p"))  # For MARKET orders, the price can be 0 — this is normal at the moment of NEW.
    notional = qty * price if price > 0 else 0.0

    # Commission estimation in quote currency (if rate is provided)
    fee_rate = maker_fee_rate if fee_mode.lower() == "maker" else taker_fee_rate
    est_fee_quote = (notional * fee_rate) if (fee_rate and notional > 0) else None

    # Approximate estimation of Initial Margin (if leverage is provided)
    initial_margin = (notional / leverage) if (leverage and leverage > 0 and notional > 0) else None

    # Human-readable event time
    t_ms = msg.get("E")
    event_time_str = (
        datetime.fromtimestamp(t_ms / 1000, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        if isinstance(t_ms, int)
        else None
    )

    ctx = {
        "market": "Futures",
        "symbol": symbol,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "status": "NEW",
        "order_type": o.get("ot") or o.get("o"),
        "side": o.get("S"),
        "position_side": o.get("ps"),
        "reduce_only": bool(o.get("R")) if o.get("R") is not None else None,
        "orig_qty": qty,
        "price": price,
        "leverage": leverage,
        "margin_mode": margin_mode,  # "isolated" / "cross" / None
        "initial_margin": initial_margin,
        # commission & notional
        "est_fee_quote": est_fee_quote,
        # мета
        "order_id": o.get("i"),
        "client_order_id": o.get("c"),
        "event_time_str": event_time_str,
        # format settings (optional)
        "qty_prec": 4,
        "price_prec": 2,
        "money_prec": 2,
        "notional_prec": 2,
    }

    return ctx
