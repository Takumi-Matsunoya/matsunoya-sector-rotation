import os
import sys
import datetime as dt

import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.db import engine


HORIZONS = [5, 20]  # 5営業日, 20営業日


def load_prices() -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT date, symbol, close
                FROM prices
                ORDER BY date, symbol
                """
            ),
            conn,
            parse_dates=["date"],
        )
    return df


def load_regimes() -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT date, regime_name
                FROM regimes
                ORDER BY date
                """
            ),
            conn,
            parse_dates=["date"],
        )
    return df


def build_stats() -> pd.DataFrame:
    prices = load_prices()
    regimes = load_regimes()

    if prices.empty or regimes.empty:
        raise RuntimeError("prices または regimes が空です")

    # pivot: rows=date, cols=symbol, values=close
    price_wide = prices.pivot(
        index="date", columns="symbol", values="close"
    ).sort_index()
    # regimes をマージ
    df = regimes.merge(price_wide, on="date", how="inner")

    records = []

    symbols = [c for c in df.columns if c not in ("date", "regime_name")]

    for horizon in HORIZONS:
        # 各シンボルの将来リターンを計算
        fwd = df[symbols].shift(-horizon) / df[symbols] - 1.0  # 単純リターン
        fwd.columns = [f"{c}_fwd_{horizon}" for c in symbols]

        tmp = pd.concat([df[["date", "regime_name"]], fwd], axis=1)
        # horizon 日先の価格がない行は落とす
        tmp = tmp.dropna()

        for symbol in symbols:
            col = f"{symbol}_fwd_{horizon}"
            for regime_name, grp in tmp.groupby("regime_name"):
                rets = grp[col].dropna()
                if rets.empty:
                    continue
                n = len(rets)
                avg_ret = rets.mean() * 100.0  # %
                win_rate = (rets > 0).mean()

                records.append(
                    {
                        "regime_name": regime_name,
                        "symbol": symbol,
                        "horizon_days": horizon,
                        "start_date": grp["date"].min().date(),
                        "end_date": grp["date"].max().date(),
                        "n_trades": n,
                        "avg_return": avg_ret,
                        "win_rate": win_rate,
                    }
                )

    return pd.DataFrame.from_records(records)


def upsert_stats(df: pd.DataFrame) -> None:
    if df.empty:
        print("no stats to upsert")
        return

    with engine.begin() as conn:
        # とりあえず全削除してから入れ直す（集計テーブルなのでこれで十分）
        conn.execute(text("TRUNCATE TABLE regime_stats"))

        for row in df.itertuples(index=False, name="StatRow"):
            conn.execute(
                text(
                    """
                    INSERT INTO regime_stats (
                        regime_name,
                        symbol,
                        horizon_days,
                        start_date,
                        end_date,
                        n_trades,
                        avg_return,
                        win_rate
                    )
                    VALUES (
                        :regime_name,
                        :symbol,
                        :horizon_days,
                        :start_date,
                        :end_date,
                        :n_trades,
                        :avg_return,
                        :win_rate
                    )
                    """
                ),
                {
                    "regime_name": row.regime_name,
                    "symbol": row.symbol,
                    "horizon_days": int(row.horizon_days),
                    "start_date": row.start_date,
                    "end_date": row.end_date,
                    "n_trades": int(row.n_trades),
                    "avg_return": float(row.avg_return),
                    "win_rate": float(row.win_rate),
                },
            )


def main() -> None:
    df = build_stats()
    upsert_stats(df)
    print(f"inserted {len(df)} stats rows")


if __name__ == "__main__":
    main()
