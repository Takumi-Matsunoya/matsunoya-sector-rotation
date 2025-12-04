import os
import sys
import datetime as dt

import pandas as pd
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.db import engine


HORIZON = 20
MIN_TRADES = 50  # サンプル数の最低ライン


# レジームごとの固定ルール（シンボルの優先順位）
REGIME_PREFERENCES = {
    "neutral": ["XLK", "XLY", "XLC", "^GSPC"],
    "rate_down": ["XLK", "XLY", "XLC", "^GSPC"],
    "rate_up_oil_down": ["XLE", "XLK", "XLI", "^GSPC"],
    "rate_up_oil_up": ["XLE", "XLU", "XLP", "^GSPC"],
}


def get_latest_regime() -> tuple[dt.date, str]:
    """regimes テーブルから最新日のレジームを取得"""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT date, regime_name
                FROM regimes
                ORDER BY date DESC
                LIMIT 1
                """
            )
        ).fetchone()

    if row is None:
        raise RuntimeError("regimes が空です")

    return row.date, row.regime_name


def load_stats_for_regime(regime_name: str) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT regime_name, symbol, horizon_days, n_trades, avg_return, win_rate
                FROM regime_stats
                WHERE regime_name = :regime_name
                  AND horizon_days = :horizon
            """
            ),
            conn,
            params={"regime_name": regime_name, "horizon": HORIZON},
        )
    return df


def select_sectors_for_today(top_n: int = 3) -> dict:
    """今日のレジームに基づく推奨セクターを返す"""
    asof_date, regime = get_latest_regime()
    print(f"Latest regime: {regime} (as of {asof_date})")

    df = load_stats_for_regime(regime)
    if df.empty:
        raise RuntimeError(
            f"regime_stats に {regime} / horizon={HORIZON} のデータがありません"
        )

    # サンプル数フィルタ
    df = df[df["n_trades"] >= MIN_TRADES].copy()
    if df.empty:
        raise RuntimeError(f"{regime} の n_trades >= {MIN_TRADES} が存在しません")

    prefs = REGIME_PREFERENCES.get(regime)

    if prefs:
        # 優先リストの順に並べ、存在するものだけ拾う
        order_map = {sym: i for i, sym in enumerate(prefs)}
        df = df[df["symbol"].isin(order_map.keys())].copy()
        df["pref_order"] = df["symbol"].map(order_map)
        df = df.sort_values(["pref_order"]).drop(columns=["pref_order"])
        picks = df.head(top_n)
    else:
        # 未定義レジームなら avg_return 順
        picks = df.sort_values("avg_return", ascending=False).head(top_n)

    picks = picks.reset_index(drop=True)

    result = {
        "asof_date": asof_date,
        "regime_name": regime,
        "horizon_days": HORIZON,
        "sectors": [],
    }

    for rec in picks.to_dict(orient="records"):
        result["sectors"].append(
            {
                "symbol": rec["symbol"],
                "n_trades": int(rec["n_trades"]),
                "avg_return": float(rec["avg_return"]),
                "win_rate": float(rec["win_rate"]),
            }
        )

    return result


def main() -> None:
    res = select_sectors_for_today(top_n=3)
    print("=== Suggested sectors ===")
    print(
        f"Regime: {res['regime_name']} (as of {res['asof_date']}), horizon={res['horizon_days']} days"
    )
    for s in res["sectors"]:
        print(
            f"- {s['symbol']}: avg_return={s['avg_return']:.2f}%, "
            f"win_rate={s['win_rate']:.2%} (n={s['n_trades']})"
        )


if __name__ == "__main__":
    main()
