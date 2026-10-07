# syntax=docker/dockerfile:1
# Sandbox image: every command an agent runs, and every verifier, executes in a
# throwaway container from this image with --network none.
FROM python:3.12-slim
# Optional build secret "ca": a CA bundle for builds behind a TLS-intercepting
# proxy. Absent on a normal machine; only used while installing packages.
RUN --mount=type=secret,id=ca \
    if [ -f /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi; \
    pip install --no-cache-dir pytest==8.3.4
RUN useradd --create-home --uid 1000 agent && mkdir /work && chown agent /work
WORKDIR /work
