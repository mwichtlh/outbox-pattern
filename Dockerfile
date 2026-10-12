FROM python:3.12-slim
WORKDIR /app
COPY outbox_demo.py .
CMD ["python", "outbox_demo.py"]
