# matsunoya-sector-rotation

セクターローテーション検証用のローカル環境。Airflow から HTTP 経由で batch コンテナのジョブを起動し、PostgreSQL に価格データとマクロ指標を蓄積します。

## 構成

- matsunoya-db: PostgreSQL 16（初期スキーマは db/init.sql）
- matsunoya-batch: FastAPI サーバ（/jobs/* エンドポイントでバッチ起動、yfinance で取得→DB書き込み）
- matsunoya-airflow: Airflow 2.9（Web UI から DAG を実行）

## 事前準備

- .env をプロジェクト直下に作成
  - DB_USER, DB_PASSWORD, AIRFLOW_FERNET_KEY, AIRFLOW_ADMIN_USER, AIRFLOW_ADMIN_PASSWORD, AIRFLOW_ADMIN_EMAIL など
- Docker と Docker Compose が動作する環境

## 起動

```bash
docker compose down
docker compose build
docker compose up -d
docker compose ps
```

- Airflow UI: http://localhost:8080
- batch FastAPI: http://localhost:8000/docs

## Airflow 設定

1) Airflow にログイン（.env の管理者ユーザー）  
2) Connections で HTTP 接続を追加
- Conn Id: matsunoya_batch
- Conn Type: HTTP
- Host: http://matsunoya-batch:8000

3) DAG matsunoya_sector_rotation_daily を有効化

現状の DAG 例
- fetch_prices: /jobs/fetch_prices を POST
- update_factors: （必要に応じて後述のエンドポイントを追加）

## バッチエンドポイント（FastAPI）

- /jobs/fetch_prices: セクターETFや指数のOHLCVを取得して prices テーブルにUPSERT
- /jobs/update_factors: マクロ指標（VIX / WTI / GOLD / US10Y / USDJPY）を取得して factors テーブルにUPSERT

FastAPI サーバのログ確認:

```bash
docker compose logs -f matsunoya-batch
```

## 手動実行（動作確認）

価格データ:
```bash
docker compose exec matsunoya-batch python src/fetch_prices.py
```

マクロ指標:
```bash
docker compose exec matsunoya-batch python src/update_factors.py
```

DB 確認:
```bash
docker compose exec matsunoya-batch python - << 'EOF'
from sqlalchemy import text
from src.db import engine

with engine.connect() as conn:
    r = conn.execute(
        text("SELECT symbol, date, close FROM prices ORDER BY date DESC LIMIT 5")
    )
    for row in r:
        print(row)

    r = conn.execute(text("SELECT COUNT(*) FROM prices"))
    print("rows in prices:", r.scalar())

    r = conn.execute(
        text("SELECT name, date, value FROM factors ORDER BY date DESC LIMIT 5")
    )
    for row in r:
        print(row)
EOF
```

## コードスタイル

プロジェクト全体を一発で整形:
```bash
pip install black
black .
```

## よくあるトラブルと対処

- Airflow からの HTTP 500
  - batch 側ログで例外を確認: docker compose logs -f matsunoya-batch
  - pandas の Series/列名由来のエラーは、reset_index→列名固定→itertuples(name=...) で回避
- Airflow から接続できない
  - Connections の Host が http://matsunoya-batch:8000 になっているか確認
  - コンテナが同一 docker-compose ネットワークにいるか確認

## 今後の拡張予定

- compute_regimes.py: factors を用いた局面判定
- compute_stats.py: レジーム×セクターの勝率・超過リターン集計
- /jobs/update_factors・/jobs/compute_regimes・/jobs/compute_stats を FastAPI に追加し、DAG から順次実行
