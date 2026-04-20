## Project
Data quality agent for BigQuery.
Analyzes tables and generates anomaly reports.
Stack: Python 3.11, LangGraph, Google Cloud BigQuery.

## How to run
source .venv/bin/activate
python src/agent.py

## Structure
- src/agent.py   → entry point, builds the agent
- src/tools.py   → tools the agent can use
- src/harness.py → validations and safety gates

## Conventions
- Code is written in English