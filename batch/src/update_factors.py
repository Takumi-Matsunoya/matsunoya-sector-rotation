import os
import sys
import datetime as dt

import pandas as pd
import yfinance as yf
from sqlalchemy import text

# /batch を sys.path に追加して src を見えるようにする
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.db import engine


FACTOR_SYMBOLS = {
    "VIX": "^VIX",
    "WTI": "CL=F",
    "GOLD": "GC=F",
    "US10Y": "^TNX",
    "USDJPY": "JPY=X",
}


def fetch_and_store_factor(
    name: str, ticker: str, start: dt.date, end: dt.date
) -> None:
    print(f"Fetching factor {name} ({ticker}) ...")
    df = yf.download(ticker, start=start, end=end)
    if df.empty:
        print(f"No data for {name}")
        return

    df = df.reset_index()
    # 終値を使う（Close）
    df = df[["Date", "Close"]]
    df.columns = ["date", "value"]  # 列名を固定

    with engine.begin() as conn:
        for row in df.itertuples(index=False, name="FactorRow"):
            conn.execute(
                text(
                    """
                    INSERT INTO factors (name, date, value)
                    VALUES (:name, :date, :value)
                    ON CONFLICT (name, date) DO UPDATE SET
                      value = EXCLUDED.value
                    """
                ),
                {
                    "name": name,
                    "date": row.date,  # ← name="FactorRow" で必ず .date になる
                    "value": float(row.value) if not pd.isna(row.value) else None,
                },
            )


def main() -> None:
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * 10)

    for name, ticker in FACTOR_SYMBOLS.items():
        fetch_and_store_factor(name, ticker, start, end)


if __name__ == "__main__":
    main()
