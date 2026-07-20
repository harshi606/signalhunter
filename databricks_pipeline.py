import os
import uuid
from typing import Any

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


def trigger_lakehouse_pipeline(
    product_profile: dict[str, Any],
) -> tuple[int, str]:
    """
    Trigger the Databricks job from Streamlit.

    Returns:
        databricks_run_id: Databricks job run ID
        application_run_id: SignalHunter run_id used in Delta tables
    """

    job_id = get_required_env("DATABRICKS_JOB_ID")
    youtube_api_key = get_required_env("YOUTUBE_API_KEY")
    groq_api_key = get_required_env("GROQ_API_KEY")

    client = get_databricks_client()

    application_run_id = str(uuid.uuid4())

    response = client.jobs.run_now(
        job_id=int(job_id),
        job_parameters={
            "run_id": application_run_id,
            "product_name": product_profile["product_name"],
            "category": product_profile["category"],
            "description": product_profile["description"],
            "target_buyer": product_profile["target_buyer"],
            "competitors": ", ".join(product_profile["competitors"]),
            "verified_capabilities": ", ".join(
                product_profile["verified_capabilities"]
            ),
            "youtube_api_key": youtube_api_key,
            "groq_api_key": groq_api_key,
            "max_signals": "10",
        },
    )

    return response.run_id, application_run_id