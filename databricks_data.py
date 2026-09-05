import os
import time

import streamlit as st
from dotenv import load_dotenv
from databricks import sql
import pandas as pd

load_dotenv()


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if value:
        return value

    try:
        value = st.secrets[name]
    except Exception:
        value = None

    if not value:
        raise ValueError(f"{name} is missing. Add it to Streamlit secrets.")

    return str(value)


def get_sql_connection():
    """
    Create Databricks SQL connection.

    _socket_timeout is set so that a cold/scaled-to-zero SQL warehouse fails
    with a clear TimeoutError after 120s instead of hanging indefinitely with
    no feedback to the user. Free-tier warehouses can take 30-90s to wake up
    from idle, so this is set comfortably above that, not right at the edge.
    """
    server_hostname = get_required_env("DATABRICKS_SERVER_HOSTNAME")
    http_path = get_required_env("DATABRICKS_HTTP_PATH")
    access_token = get_required_env("DATABRICKS_TOKEN")

    return sql.connect(
        server_hostname=server_hostname,
        http_path=http_path,
        access_token=access_token,
        _socket_timeout=120,
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


def load_gold_opportunities_with_retry(
    run_id: str,
    max_attempts: int = 3,
    wait_seconds: int = 20,
    status_callback=None,
) -> pd.DataFrame:
    """
    Wraps load_gold_opportunities_from_databricks with retries.

    A cold SQL warehouse can time out on the first attempt (see
    get_sql_connection's _socket_timeout). Rather than surfacing that as a
    hard failure, retry a couple of times with a short wait, since the
    warehouse is very likely awake by the second or third attempt.

    status_callback, if provided, is called with a short status string before
    each retry so the caller (Streamlit) can show progress instead of a
    silent wait.
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return load_gold_opportunities_from_databricks(run_id)

        except Exception as exc:
            last_exception = exc

            if attempt == max_attempts:
                raise

            if status_callback:
                status_callback(
                    f"Warehouse may still be starting up. "
                    f"Retrying ({attempt}/{max_attempts})..."
                )

            time.sleep(wait_seconds)

    # Unreachable, but keeps type checkers happy.
    raise last_exception


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
