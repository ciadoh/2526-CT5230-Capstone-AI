FROM python:3.11-slim

RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org mlflow==2.13.0 psycopg2-binary boto3

EXPOSE 5000

CMD ["mlflow", "server", \
     "--backend-store-uri", "${MLFLOW_BACKEND_STORE_URI}", \
     "--artifacts-destination", "${MLFLOW_ARTIFACT_ROOT}", \
     "--host", "0.0.0.0", \
     "--port", "5000"]
