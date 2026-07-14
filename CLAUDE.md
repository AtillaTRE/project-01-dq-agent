## Project
Data quality agent for BigQuery.
Analyzes tables and generates anomaly reports.
Stack: Python 3.11, LangGraph, Google Cloud BigQuery.

## How to run
source .venv/bin/activate
python -m src.agent        # direct BigQuery mode
python -m src.cube_agent   # hybrid Cube mode

Both entry points are modules and must be run with `python -m` from the repo root.
`python src/agent.py` breaks the `from src.… import` statements.

## Checks (same as CI)
ruff check src tests scripts
mypy src
pytest

## Structure
- src/agent.py       → entry point (BQ mode), builds the agent
- src/cube_agent.py  → entry point (Cube mode), hybrid agent
- src/tools.py       → tools the agent can use
- src/harness.py     → validations and safety gates
- src/cube_harness.py→ Cube-specific gates
- tests/             → harness gate tests; must run without cloud credentials
- scripts/           → manual scripts needing live credentials (never collected by pytest)

## Conventions
- Code, comments and docstrings are written in English
- Tests must not require BigQuery, Cube or Anthropic credentials
