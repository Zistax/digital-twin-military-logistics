FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
WORKDIR /app
COPY requirements-local.txt ./
RUN pip install --no-cache-dir -r requirements-local.txt && pip check \
    && groupadd --gid 10001 demo && useradd --uid 10001 --gid demo --no-create-home demo
COPY src ./src
COPY conf ./conf
COPY docs ./docs
COPY models ./models
COPY reports/m03-v1 ./reports/m03-v1
COPY reports/m02-v1 ./reports/m02-v1
COPY reports/m01-v1 ./reports/m01-v1
COPY reports/r01-v1/pilot-summary.json ./reports/r01-v1/pilot-summary.json
COPY scripts/run_demo.py ./scripts/run_demo.py
RUN mkdir runtime && chown demo:demo runtime
USER demo
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3)"
CMD ["python", "scripts/run_demo.py", "--listen", "0.0.0.0"]
