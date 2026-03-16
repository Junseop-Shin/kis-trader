FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/backtest_engine/ ./src/backtest_engine/
COPY src/__init__.py ./src/

EXPOSE 8001

CMD ["uvicorn", "src.backtest_engine.main:app", "--host", "0.0.0.0", "--port", "8001"]
