FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git config --global --add safe.directory '*'
RUN pip install --no-cache-dir .
COPY backend ./backend

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
