FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc ffmpeg || \
    (sleep 5 && apt-get update && apt-get install -y gcc ffmpeg) && \
    apt-get clean

EXPOSE 8000
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/instagrapi-rest
COPY . /app/instagrapi-rest/
WORKDIR /app/instagrapi-rest
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
