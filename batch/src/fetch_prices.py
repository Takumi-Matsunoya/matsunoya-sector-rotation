import datetime as dt

import pandas as pd
import yfinance as yf
from sqlalchemy import text

from src.db import engine


US_SYMBOLS = [
    "XLK",
    "XLY",
    "XLF",
    "XLE",
    "XLV",
    "XLI",
    "XLB",
    "XLP",
    "XLU",
    "XLC",
    "^GSPC",
]


def fetch_and_store(symbol: str, start: dt.date, end: dt.date) -> None:
    print(f"Fetching {symbol} ...")
    df = yf.download(symbol, start=start, end=end)
    if df.empty:
        print(f"No data for {symbol}")
        return

    df = df.reset_index()
    df["symbol"] = symbol

    # 列名を小文字に統一（MultiIndex 対応）
    new_cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            # ('Open', 'XLK') → 'open'
            name = c[0]
        else:
            name = c
        new_cols.append(str(name).lower())

    df.columns = new_cols  # date, open, high, low, close, volume, symbol 想定

    with engine.begin() as conn:
        for row in df.itertuples(index=False):
            volume = None
            if getattr(row, "volume", None) is not None and not pd.isna(row.volume):
                volume = int(row.volume)

            conn.execute(
                text(
                    """
                    INSERT INTO prices (symbol, date, open, high, low, close, volume)
                    VALUES (:symbol, :date, :open, :high, :low, :close, :volume)
                    ON CONFLICT (symbol, date) DO UPDATE SET
                      open = EXCLUDED.open,
                      high = EXCLUDED.high,
                      low = EXCLUDED.low,
                      close = EXCLUDED.close,
                      volume = EXCLUDED.volume
                    """
                ),
                {
                    "symbol": row.symbol,
                    "date": row.date,  # pandas.Timestamp のままでOK
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": volume,
                },
            )


def main() -> None:
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * 10)

    for symbol in US_SYMBOLS:
        fetch_and_store(symbol, start, end)


if __name__ == "__main__":
    main()
