FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 gh2gl \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/sh gh2gl

WORKDIR /src

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN pip install --no-cache-dir . \
    && chmod 755 /usr/local/bin/docker-entrypoint.sh \
    && rm -rf /src

WORKDIR /config
USER gh2gl
ENV HOME=/home/gh2gl \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["--help"]
