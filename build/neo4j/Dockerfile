FROM python:3.11-slim

WORKDIR /app


COPY neo4j/pyproject.toml .
RUN pip install --no-cache-dir . || pip install .

COPY neo4j/app.py .
COPY neo4j/inserciones.py .
COPY neo4j/templates/ ./templates/

COPY estaciones.csv .
COPY campus.csv .
COPY estudios.csv .

EXPOSE 5001

CMD ["sh", "-c", "python inserciones.py && python app.py"]
