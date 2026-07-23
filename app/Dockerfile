FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicit, per-item COPY instead of "COPY . ." so the image only ever
# contains the files the application actually needs at runtime.
COPY app.py validation.py ./
COPY templates ./templates
COPY static ./static

RUN useradd --no-create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
