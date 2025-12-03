import os
from sqlalchemy import create_engine

user = os.environ["DB_USER"]
password = os.environ["DB_PASSWORD"]
host = os.environ.get("DB_HOST", "matsunoya-db")
port = os.environ.get("DB_PORT", "5432")
name = os.environ.get("DB_NAME", "matsunoya_sector_rotation")

DATABASE_URL = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
engine = create_engine(DATABASE_URL, echo=False, future=True)
