# matsunoya-sector-rotation

セクターローテーション検証用のローカル環境。  
Airflow から HTTP 経由で batch コンテナのジョブを起動し、PostgreSQL に価格データとマクロ指標を蓄積・集計します。

## 構成

- matsunoya-db  
  - PostgreSQL 16  
  - 初期スキーマ: `db/init.sql`（prices, factors, regimes, regime_stats など）
- matsunoya-batch  
  - Python バッチ用コンテナ  
  - FastAPI サーバ（`/jobs/*` エンドポイント）  
  - yfinance でデータ取得 → SQLAlchemy 経由で DB に書き込み  
  - Jupyter / matplotlib / seaborn を利用可能
- matsunoya-airflow  
  - Apache Airflow 2.9  
  - DAG から HTTP 経由で batch のジョブをスケジューリング

## 事前準備

- `.env` をプロジェクト直下に作成（例）

```
DB_USER=matsunoya_user
DB_PASSWORD=xxxxxxxx
AIRFLOW_FERNET_KEY=xxxxxxxx
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=xxxxxxxx
AIRFLOW_ADMIN_EMAIL=you@example.com
```

- Docker / Docker Compose が使える環境（macOS + Docker Desktop 想定）

## 起動

```
docker compose down
docker compose build
docker compose up -d
docker compose ps
```

- Airflow Web UI: `http://localhost:8080`  
- batch FastAPI: `http://localhost:8000/docs`

## Airflow 設定

1. Airflow にログイン（`.env` で設定した管理者ユーザー）  
2. メニュー → `Admin > Connections` で HTTP 接続を追加

- Conn Id: `matsunoya_batch`  
- Conn Type: `HTTP`  
- Host: `http://matsunoya-batch:8000`  

3. DAG 一覧で `matsunoya_sector_rotation_daily` を ON にする。

### 現状の DAG フロー

- `fetch_prices`  
  - `POST /jobs/fetch_prices`  
  - 米国セクターETF + S&P500 の日次 OHLCV を取得し `prices` テーブルに UPSERT
- `update_factors`  
  - `POST /jobs/update_factors`  
  - VIX / WTI / GOLD / US10Y / USDJPY を取得し `factors` テーブルに UPSERT
- `compute_regimes`  
  - `POST /jobs/compute_regimes`  
  - `factors` から直近 20 営業日の変化率などを計算し、日別レジームを `regimes` に書き込み  

（`compute_stats` / `select_sectors` はバッチとして手動実行が前提）

## バッチスクリプト概要

- `src/fetch_prices.py`  
  - `US_SYMBOLS`（XLK, XLB, …, ^GSPC）の日次価格を10年分取得し、`prices` に UPSERT
- `src/update_factors.py`  
  - `FACTOR_SYMBOLS`（^VIX, CL=F, GC=F, ^TNX, JPY=X）から終値を取得し、`factors` に UPSERT
- `src/compute_regimes.py`  
  - `factors` の US10Y / WTI / VIX から 20営業日変化率等を計算し、  
  - `rate_up_oil_up` / `rate_up_oil_down` / `rate_down` / `neutral` の4レジームを判定して `regimes` に UPSERT  
- `src/compute_stats.py`  
  - `prices` と `regimes` を結合し、レジームごと・シンボルごと・ホールド期間ごとの将来リターンを集計  
  - 結果（`regime_name`, `symbol`, `horizon_days`, `n_trades`, `avg_return`, `win_rate`）を `regime_stats` に保存
- `src/select_sectors.py`  
  - 最新レジームを `regimes` から取得  
  - `regime_stats`（デフォルト 20 日・十分なサンプル数）から、そのレジームにおける推奨セクター上位3本を返す関数を提供

## FastAPI エンドポイント

`src/api.py` で定義:

- `POST /jobs/fetch_prices` → `fetch_prices.main()`  
- `POST /jobs/update_factors` → `update_factors.main()`  
- `POST /jobs/compute_regimes` → `compute_regimes.main()`  

Airflow の `SimpleHttpOperator` からこれらのエンドポイントを呼び出している。

FastAPI ログを見る:

```
docker compose logs -f matsunoya-batch
```

## コードスタイル

Python コードは `black` で一括整形可能。

```
pip install black
black batch/src
```

## 今後の拡張メモ

- レジーム定義のチューニング（閾値変更、VIX 水準による risk-on/off 分類など）  
- `compute_stats.py` のホールド期間バリエーション（5日, 10日, 40日 など）  
- 「最新レジーム＋推奨セクター」を日次レポート（CSV / HTML）として自動出力するタスクの追加  
- 簡易バックテスト Notebook（「常にレジーム別トップ3セクター均等」を過去に適用した場合のカーブ生成）
