FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt waitress
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["sh", "-c", "waitress-serve --host=0.0.0.0 --port=${PORT:-10000} app:app"]
