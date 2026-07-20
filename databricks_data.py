import os

import pandas as pd
from databricks import sql
from dotenv import load_dotenv

load_dotenv()


def get_required_env(name: str) -> str:
    """Read required environment variable."""
    value = os.getenv(name)

    if not value:
        raise ValueError(f"{name} is missing. Add it to your .env file.")

    return value


def get_sql_connection():
    """Create Databricks SQL connection."""

    server_hostname = get_required_env("DATABRICKS_SERVER_HOSTNAME")
    http_path = get_required_env("DATABRICKS_HTTP_PATH")
    access_token = get_required_env("DATABRICKS_TOKEN")

    return sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token,
    )


def load_gold_opportunities_from_databricks(
    run_id: str,
) -> pd.DataFrame:
    """Load Gold opportunities for one SignalHunter run."""

    query = """
        SELECT
            intent_score,
            source,
            buying_stage,
            pain_point,
            competitors_mentioned,
            product_fit,
            recommended_action,
            suggested_angle,
            reasoning,
            source_url,
            product_name,
            run_id
        FROM signalhunter.growth.gold_opportunities
        WHERE run_id = ?
        ORDER BY intent_score DESC
    """

    with get_sql_connection() as connection:
        return pd.read_sql(
            query,
            connection,
            params=[run_id],
        )


def load_latest_gold_opportunities_from_databricks(
    limit: int = 20,
) -> pd.DataFrame:
    """Useful local test function: load latest Gold rows from Databricks."""

    query = f"""
        SELECT
            intent_score,
            source,
            buying_stage,
            pain_point,
            competitors_mentioned,
            product_fit,
            recommended_action,
            suggested_angle,
            reasoning,
            source_url,
            product_name,
            run_id,
            analyzed_at
        FROM signalhunter.growth.gold_opportunities
        ORDER BY analyzed_at DESC
        LIMIT {int(limit)}
    """

    with get_sql_connection() as connection:
        return pd.read_sql(
            query,
            connection,
        )