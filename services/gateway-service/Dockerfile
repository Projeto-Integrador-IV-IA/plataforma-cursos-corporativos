# gateway-service - Porta de entrada unica da plataforma: autenticacao, roteamento e agregacao para o frontend.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY app ./app

EXPOSE 8000

# TODO: implementar app/main.py antes de subir este container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
