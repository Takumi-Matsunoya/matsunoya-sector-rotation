from fastapi import FastAPI
from src import fetch_prices, update_factors, compute_regimes  # ここを調整

app = FastAPI()


@app.post("/jobs/fetch_prices")
def run_fetch_prices():
    fetch_prices.main()
    return {"status": "ok"}


@app.post("/jobs/update_factors")
def run_update_factors():
    update_factors.main()
    return {"status": "ok"}


@app.post("/jobs/compute_regimes")
def run_compute_regimes():
    compute_regimes.main()
    return {"status": "ok"}
