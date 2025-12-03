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
