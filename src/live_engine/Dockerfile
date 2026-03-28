FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/live_engine/ ./src/live_engine/
COPY src/__init__.py ./src/

EXPOSE 8000

CMD ["uvicorn", "src.live_engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
