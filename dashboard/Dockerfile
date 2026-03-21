FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streamlit_app.py .

ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py"]
```

**File 6** — Type:
```
docs/schema_v2.sql
```

**File 7** — Type:
```
docs/README.md
```

**File 8** — Type:
```
docs/ADMIN_GUIDE.md
