FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y curl wget iputils-ping && rm -rf /var/lib/apt/lists/*
COPY app.py .
EXPOSE 8080
CMD ["python", "app.py"]