FROM python:3.13-slim

WORKDIR /app

ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv
RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "gunicorn", "src.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "2", \
     "--timeout", "120"]
