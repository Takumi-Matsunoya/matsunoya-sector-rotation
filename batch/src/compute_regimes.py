import os
import sys
import datetime as dt

import pandas as pd
from sqlalchemy import text

# /batch を sys.path に追加して src を見えるようにする
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.db import engine


def load_factor_series(name: str) -> pd.Series:
    """factors テーブルから指定指標の series を取得（index=date, value）"""
    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT date, value
                FROM factors
                WHERE name = :name
                ORDER BY date
                """
            ),
            conn,
            params={"name": name},
            parse_dates=["date"],
        )
    if df.empty:
        return pd.Series(dtype="float64")
    s = df.set_index("date")["value"].sort_index()
    return s


def build_regimes() -> pd.DataFrame:
    # 各ファクター（US10Y, WTI, VIX）の series を取得
    us10y = load_factor_series("US10Y")
    wti = load_factor_series("WTI")
    vix = load_factor_series("VIX")

    if us10y.empty or wti.empty or vix.empty:
        raise RuntimeError("factors が足りません（US10Y/WTI/VIX を確認してください）")

    # 共通の日付インデックスに揃える
    idx = us10y.index.union(wti.index).union(vix.index)
    df = pd.DataFrame(index=idx)
    df["us10y"] = us10y.reindex(idx)
    df["wti"] = wti.reindex(idx)
    df["vix"] = vix.reindex(idx)

    # 20営業日の変化率
    df["us10y_chg_20d"] = df["us10y"] - df["us10y"].shift(20)
    df["wti_chg_20d"] = (df["wti"] / df["wti"].shift(20) - 1.0) * 100.0
    df["vix_level"] = df["vix"]

    # レジームルール（閾値を少し緩める）
    conditions = []
    names = []

    # rate_up_oil_up
    cond_rate_up_oil_up = (df["us10y_chg_20d"] > 0.10) & (df["wti_chg_20d"] > 5.0)
    conditions.append(cond_rate_up_oil_up)
    names.append("rate_up_oil_up")

    # rate_up_oil_down
    cond_rate_up_oil_down = (df["us10y_chg_20d"] > 0.10) & (df["wti_chg_20d"] < -5.0)
    conditions.append(cond_rate_up_oil_down)
    names.append("rate_up_oil_down")

    # rate_down
    cond_rate_down = df["us10y_chg_20d"] < -0.10
    conditions.append(cond_rate_down)
    names.append("rate_down")

    # デフォルト neutral
    df["regime_name"] = "neutral"

    for cond, name in zip(conditions, names):
        df.loc[cond, "regime_name"] = name

    # 20日分のデータがまだ揃っていない部分は落とす
    df = df.dropna(subset=["us10y_chg_20d", "wti_chg_20d", "vix_level"])

    df = df.reset_index().rename(columns={"index": "date"})
    df["date"] = df["date"].dt.date

    return df[["date", "regime_name", "us10y_chg_20d", "wti_chg_20d", "vix_level"]]


def upsert_regimes(df: pd.DataFrame) -> None:
    with engine.begin() as conn:
        for row in df.itertuples(index=False, name="RegimeRow"):
            conn.execute(
                text(
                    """
                    INSERT INTO regimes (date, regime_name, us10y_chg_20d, wti_chg_20d, vix_level)
                    VALUES (:date, :regime_name, :us10y_chg_20d, :wti_chg_20d, :vix_level)
                    ON CONFLICT (date) DO UPDATE SET
                      regime_name = EXCLUDED.regime_name,
                      us10y_chg_20d = EXCLUDED.us10y_chg_20d,
                      wti_chg_20d = EXCLUDED.wti_chg_20d,
                      vix_level = EXCLUDED.vix_level
                    """
                ),
                {
                    "date": row.date,
                    "regime_name": row.regime_name,
                    "us10y_chg_20d": float(row.us10y_chg_20d),
                    "wti_chg_20d": float(row.wti_chg_20d),
                    "vix_level": float(row.vix_level),
                },
            )


def main() -> None:
    df = build_regimes()
    upsert_regimes(df)
    print(f"upserted {len(df)} regime rows")


if __name__ == "__main__":
    main()
