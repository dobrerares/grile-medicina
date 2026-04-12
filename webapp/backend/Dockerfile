FROM python:3.12-slim

WORKDIR /app

COPY webapp/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webapp/backend/ .
COPY output/grile.json /data/grile.json
COPY pdfs /data/pdfs

EXPOSE 8000

RUN adduser --disabled-password --no-create-home appuser \
    && mkdir -p /app/data \
    && chown appuser:appuser /app/data
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
