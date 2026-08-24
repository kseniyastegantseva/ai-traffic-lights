FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY pyproject.toml ./
RUN mkdir -p src/traffic_light && touch src/traffic_light/__init__.py README.md \
    && pip install --no-cache-dir -e .

COPY AGENTS.md ./
COPY README.md ./
COPY configs ./configs
COPY models ./models
COPY src ./src
COPY tests ./tests
COPY wiki ./wiki

RUN pip install --no-cache-dir --no-deps -e .

CMD ["traffic-sim", "compare", "--config", "configs/demo_uniform.yaml"]

FROM base AS app

COPY .streamlit ./.streamlit
COPY app ./app

RUN pip install --no-cache-dir -e ".[dashboard]"
