FROM python:3.13-slim
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt
COPY agent.py tools.py web_store.py web_api.py ./
COPY public ./public
ENV PORT=8080 PYTHONUNBUFFERED=1
CMD ["sh","-c","exec uvicorn web_api:app --host 0.0.0.0 --port ${PORT}"]
