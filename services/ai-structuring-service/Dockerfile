# ai-structuring-service - Estruturacao do curso por LLM: extracao de requisitos, geracao de ementa e metricas de qualidade.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY app ./app

EXPOSE 8003

# TODO: implementar app/main.py antes de subir este container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
