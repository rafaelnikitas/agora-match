FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && addgroup --system app && adduser --system --ingroup app --home /app app
COPY --chown=app:app agora_match ./agora_match
COPY --chown=app:app static ./static
USER app
RUN python -m agora_match.build_static
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=3)"
CMD ["python", "-m", "agora_match.server"]
