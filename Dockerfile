# Dockerfile — multi-stage build

FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies in a separate layer so they stay cached across code changes
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ========= Stage 2: final runtime =========
FROM python:3.11-slim

WORKDIR /app

# Non-root user (security best practice)
RUN useradd --create-home --shell /bin/bash agent

# Copy only the installed packages
COPY --from=builder /root/.local /home/agent/.local

# Copy code and the system prompts for both modes
COPY --chown=agent:agent src/            ./src/
COPY --chown=agent:agent AGENTS.md       .
COPY --chown=agent:agent AGENTS_cube.md  .

USER agent

ENV PATH=/home/agent/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Override with `docker run ... dq-agent python -m src.cube_agent` for Cube mode
CMD ["python", "-m", "src.agent"]
