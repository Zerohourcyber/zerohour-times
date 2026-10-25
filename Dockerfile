# The ZeroHour Times — job intelligence layer for JobSync.
#
# There is no `pip install` here, and that is deliberate: the application uses
# only the Python standard library, so there is no dependency file to resolve,
# no lockfile to rot, and nothing to break months from now. If you are reading
# this to judge the project, that is the first thing worth noticing.
FROM python:3.12-slim

# Unbuffered so container logs appear as the pipeline runs rather than at exit.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ZHT_STATE_DIR=/data \
    ZHT_DASHBOARD_BIND=0.0.0.0

WORKDIR /app
COPY zhtimes/ /app/zhtimes/
COPY prompts/ /app/prompts/
COPY samples/ /app/samples/
COPY config.example.json profile.example.md /app/

# Runs as a non-root user. /data is the only writable path it needs.
RUN useradd --create-home --uid 10001 zerohour \
 && mkdir -p /data && chown -R zerohour:zerohour /data /app
USER zerohour
VOLUME ["/data"]
EXPOSE 8099

HEALTHCHECK --interval=60s --timeout=5s --start-period=20s --retries=3 \
  CMD python3 -c "import urllib.request,os,sys; \
urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('ZHT_DASHBOARD_PORT','8099')}/\", timeout=4)" \
  || exit 1

ENTRYPOINT ["python3", "/app/zhtimes/run.py"]
