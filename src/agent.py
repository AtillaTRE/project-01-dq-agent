# src/agent.py

from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from src.config import settings
from src.tools import get_table_schema, run_bq_query
from src.harness import validate_output
from src.logging_config import setup_logging
import uuid

logger = setup_logging(service_name="dq-agent")

llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=4096)
tools = [get_table_schema, run_bq_query]

with open("AGENTS.md") as f:
    system_prompt = f.read()

agent = create_react_agent(llm, tools, prompt=system_prompt)


def analyze_table(dataset: str, table: str, user_id: str = "local") -> dict:
    """Entry point. Retorna um DQReport validado."""
    session_id = str(uuid.uuid4())

    logger.info(
        "Starting analysis",
        extra={
            "session_id": session_id,
            "user_id":    user_id,
            "table":      f"{dataset}.{table}",
        },
    )

    config = RunnableConfig(
        configurable={"thread_id": session_id},
        metadata={
            "user_id":     user_id,
            "environment": "production" if settings.use_secret_manager else "dev",
            "table":       f"{dataset}.{table}",
        },
        tags=["data-quality", "bigquery"],
    )

    result = agent.invoke(
        {"messages": [{
            "role": "user",
            "content": (
                f"Analyze {dataset}.{table}: check for nulls, "
                f"duplicates, outliers. Return JSON matching the schema."
            ),
        }]},
        config=config,
    )

    final_message = result["messages"][-1].content
    report = validate_output(final_message)  # harness gate

    logger.info(
        "Analysis completed",
        extra={
            "session_id":     session_id,
            "issues_found":   len(report.issues),
            "total_rows":     report.total_rows,
        },
    )
    return report.model_dump()


if __name__ == "__main__":
    report = analyze_table(settings.bq_dataset, settings.bq_table)
    print(report)
