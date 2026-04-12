FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY pyspider/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY pyspider ./pyspider

WORKDIR /app/pyspider
RUN pip install -e .

EXPOSE 5000
CMD ["python", "web/app.py"]
