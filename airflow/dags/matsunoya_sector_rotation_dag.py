from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator

default_args = {
    "owner": "matsunoya",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="matsunoya_sector_rotation_daily",
    default_args=default_args,
    schedule_interval="0 3 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    fetch_prices = SimpleHttpOperator(
        task_id="fetch_prices",
        http_conn_id="matsunoya_batch",
        endpoint="/jobs/fetch_prices",
        method="POST",
    )

    update_factors = SimpleHttpOperator(
        task_id="update_factors",
        http_conn_id="matsunoya_batch",
        endpoint="/jobs/update_factors",
        method="POST",
    )

    compute_regimes_task = SimpleHttpOperator(
        task_id="compute_regimes",
        http_conn_id="matsunoya_batch",
        endpoint="/jobs/compute_regimes",
        method="POST",
    )

    fetch_prices >> update_factors >> compute_regimes_task
