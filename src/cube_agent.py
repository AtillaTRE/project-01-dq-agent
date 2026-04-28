# src/cube_agent.py
# Hybrid agent: uses BQ for schema, Cube for metrics.

from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from src.config         import settings
from src.tools          import get_table_schema  # reused from the original
from src.cube_tools     import list_cube_metrics, query_cube
from src.harness        import DQReport, validate_output
from src.logging_config import setup_logging
import uuid

logger = setup_logging(service_name="cube-agent")

llm    = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=4096)
tools  = [get_table_schema, list_cube_metrics, query_cube]

with open("AGENTS_cube.md") as f:
    system_prompt = f.read()

agent          = create_react_agent(llm, tools, prompt=system_prompt)
structured_llm = llm.with_structured_output(DQReport)


def analyze_table_with_cube(
    dataset: str, table: str, user_id: str = "local"
) -> dict:
    session_id = str(uuid.uuid4())

    logger.info(
        "Starting hybrid analysis",
        extra={
            "session_id": session_id,
            "table":      f"{dataset}.{table}",
        },
    )

    config = RunnableConfig(
        configurable={"thread_id": session_id},
        metadata={
            "user_id":  user_id,
            "table":    f"{dataset}.{table}",
            "approach": "cube-hybrid",
        },
        tags=["data-quality", "cube"],
    )

    investigation = agent.invoke(
        {"messages": [{
            "role": "user",
            "content": (
                f"Analyze the table {dataset}.{table}. "
                f"First inspect the schema. "
                f"Then use Cube metrics to detect quality issues "
                f"(check counts, revenue, cancellation rates). "
                f"Return findings in the required JSON format."
            ),
        }]},
        config=config,
    )

    findings = investigation["messages"][-1].content

    report = structured_llm.invoke(
        f"""Based on this investigation, produce a DQReport.

Findings:
{findings}

Table: {dataset}.{table}

Return structured DQReport with all issues as objects."""
    )

    logger.info(
        "Hybrid analysis completed",
        extra={
            "session_id":   session_id,
            "issues_found": len(report.issues),
        },
    )
    return report.model_dump()


if __name__ == "__main__":
    import json
    report = analyze_table_with_cube(settings.bq_dataset, settings.bq_table)
    print(json.dumps(report, indent=2, ensure_ascii=False))