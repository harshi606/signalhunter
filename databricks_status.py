import os

from databricks.sdk import WorkspaceClient
from dotenv import load_dotenv

load_dotenv()


def get_required_env(name: str) -> str:
    """Read required environment variable."""
    value = os.getenv(name)

    if not value:
        raise ValueError(f"{name} is missing. Add it to your .env file.")

    return value


def get_databricks_client() -> WorkspaceClient:
    """Create Databricks workspace client."""
    host = get_required_env("DATABRICKS_HOST")
    token = get_required_env("DATABRICKS_TOKEN")

    return WorkspaceClient(
        host=host,
        token=token,
    )


def get_job_run_state(databricks_run_id: int) -> str:
    """Get current Databricks job run state."""

    client = get_databricks_client()

    run = client.jobs.get_run(
        run_id=databricks_run_id
    )

    lifecycle = (
        run.state.life_cycle_state.value
        if run.state and run.state.life_cycle_state
        else "UNKNOWN"
    )

    result = (
        run.state.result_state.value
        if run.state and run.state.result_state
        else ""
    )

    state_message = (
        run.state.state_message
        if run.state and run.state.state_message
        else ""
    )

    if result:
        return f"{lifecycle} / {result} — {state_message}"

    return f"{lifecycle} — {state_message}"