FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 goodware
COPY --chown=goodware:goodware . .
RUN chmod +x start.sh && mkdir -p instance && chown goodware:goodware instance
USER goodware
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/healthz',timeout=3)"
CMD ["./start.sh"]
