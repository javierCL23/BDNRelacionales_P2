FROM python:3.11-slim

WORKDIR /app


COPY mongodb/pyproject.toml .
RUN pip install --no-cache-dir . || pip install flask pymongo pandas

COPY mongodb/app.py .
COPY mongodb/inserciones.py .
COPY mongodb/templates/ ./templates/

COPY estaciones.csv .
COPY campus.csv .
COPY estudios.csv .

EXPOSE 5000

CMD ["sh", "-c", "python inserciones.py && python app.py"]