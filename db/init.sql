-- 必要に応じて権限などを追加
CREATE TABLE IF NOT EXISTS prices (
  id SERIAL PRIMARY KEY,
  symbol VARCHAR(32) NOT NULL,
  date DATE NOT NULL,
  open DOUBLE PRECISION,
  high DOUBLE PRECISION,
  low DOUBLE PRECISION,
  close DOUBLE PRECISION,
  volume BIGINT,
  UNIQUE(symbol, date)
);

CREATE TABLE IF NOT EXISTS factors (
  id SERIAL PRIMARY KEY,
  name VARCHAR(64) NOT NULL,
  date DATE NOT NULL,
  value DOUBLE PRECISION,
  UNIQUE(name, date)
);

CREATE TABLE IF NOT EXISTS regimes (
    date DATE PRIMARY KEY,
    regime_name TEXT NOT NULL,
    us10y_chg_20d REAL,
    wti_chg_20d REAL,
    vix_level REAL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS regimes (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL UNIQUE,
  regime_name VARCHAR(128) NOT NULL
);

CREATE TABLE IF NOT EXISTS regime_stats (
  id SERIAL PRIMARY KEY,
  regime_name VARCHAR(128) NOT NULL,
  country VARCHAR(8) NOT NULL,
  sector VARCHAR(64) NOT NULL,
  horizon_days INT NOT NULL,
  avg_excess_return DOUBLE PRECISION,
  win_rate DOUBLE PRECISION,
  max_dd DOUBLE PRECISION,
  sample_size INT
);

CREATE TABLE IF NOT EXISTS regime_stats (
    id SERIAL PRIMARY KEY,
    regime_name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    horizon_days INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    n_trades INTEGER NOT NULL,
    avg_return REAL NOT NULL,
    win_rate REAL NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
