# practice-executor: the API (`python -m app.main`) and the dispatcher (`python -m app.dispatcher`).
# Neither runs submitted code in-process; the dispatcher starts sandbox pods (sandbox/Dockerfile).
FROM python:3.13-slim

WORKDIR /srv
COPY pyproject.toml ./
RUN pip install --no-cache-dir "fastapi==0.162.0" "uvicorn==0.54.0" "redis==8.1.0" "httpx==0.28.1" "pydantic==2.14.2"
COPY app ./app
COPY sandbox/runner.py ./sandbox/runner.py

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "app.main"]
