# src/config.py
# Centrilizes all configuration. In Prod it searches for Secret Manager.
# In dev local, uses .env if exists. Always validates with Pydantic.

import os

from dotenv import load_dotenv
from google.cloud import secretmanager  # type: ignore[attr-defined]
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()  # fallback to .env in dev local


def get_secret(secret_id: str, project_id: str) -> str:
    """Fetches a secret from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


class Settings(BaseSettings):
    # GCP
    google_cloud_project: str = Field(..., alias="GOOGLE_CLOUD_PROJECT")
    bq_dataset:           str = Field("ecommerce_demo", alias="BQ_DATASET")
    bq_table:             str = Field("orders",         alias="BQ_TABLE")
    cube_api_url:    str = Field("", alias="CUBE_API_URL")
    cube_api_token: str = Field("", alias="CUBE_API_TOKEN")

    # Feature flag: uses Secret Manager or .env
    use_secret_manager: bool = Field(False, alias="USE_SECRET_MANAGER")

    # Keys (populated after __init__)
    anthropic_api_key: str = ""
    langsmith_api_key: str = ""

    # Harness config
    max_query_rows:       int = 1000
    max_retries:          int = 3
    langsmith_project:    str = "dq-agent-project"
    langsmith_tracing:    bool = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.use_secret_manager:
            self.anthropic_api_key = get_secret(
                "anthropic-api-key", self.google_cloud_project
            )
            self.langsmith_api_key = get_secret(
                "langsmith-api-key", self.google_cloud_project
            )
        else:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
            self.langsmith_api_key = os.getenv("LANGSMITH_API_KEY", "")

        # Exports to env vars for libs that read directly from env vars
        os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
        os.environ["LANGSMITH_TRACING"] = "true" if self.langsmith_tracing else "false"
        os.environ["LANGSMITH_PROJECT"] = self.langsmith_project


settings = Settings()  # singleton, imports each config once and shares across the app
