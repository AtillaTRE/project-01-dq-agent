# Dockerfile — multi-stage build

FROM python:3.11-slim AS builder

WORKDIR /app

# Instala dependências em layer separada (cache)
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ========= Stage 2: runtime final =========
FROM python:3.11-slim

WORKDIR /app

# Usuário não-root (boa prática de segurança)
RUN useradd --create-home --shell /bin/bash agent

# Copia só os pacotes instalados
COPY --from=builder /root/.local /home/agent/.local

# Copia código
COPY --chown=agent:agent src/       ./src/
COPY --chown=agent:agent AGENTS.md  .

USER agent

ENV PATH=/home/agent/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "src.agent"]