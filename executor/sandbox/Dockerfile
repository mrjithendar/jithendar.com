# Sandbox image: one pod per job runs `python -I runner.py` (see ../README.md). Standard library only.
# Build one image per supported runtime: --build-arg PYTHON_VERSION=3.13 (or 3.12) → practice-sandbox:py3.13-<sha>.
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

# Nothing to install packages with, and no compilers: submitted code gets the standard library only.
RUN set -eux; \
    rm -rf /usr/local/lib/python*/ensurepip /usr/local/lib/python*/site-packages/pip* /usr/local/bin/pip* /root/.cache; \
    find / -xdev -perm /6000 -type f -exec chmod a-s {} + || true

COPY runner.py /sandbox/runner.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 HOME=/tmp
WORKDIR /tmp
USER 65532:65532
ENTRYPOINT ["python", "-I", "/sandbox/runner.py"]
