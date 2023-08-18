FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip3 install --no-cache-dir -r requirements.txt
VOLUME ["/out"]

CMD ["python", "app/main.py"]