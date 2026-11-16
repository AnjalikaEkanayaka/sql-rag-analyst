FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

# Hugging Face Spaces runs containers as user 1000, so use that user everywhere
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:${PATH}"
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --user -r requirements.txt

COPY --chown=user src ./src
COPY --chown=user data ./data

# Download the embedding model and build the search index at build time, not at startup
RUN python -m src.retrieval build

ENV WARMUP=1
EXPOSE 8000
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]