from fastapi import FastAPI
from src import fetch_prices

app = FastAPI()


@app.post("/jobs/fetch_prices")
def run_fetch_prices():
    fetch_prices.main()
    return {"status": "ok"}
