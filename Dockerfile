# The HTTP and agent surfaces, in a container, for the readers who will never
# install the package: a sustainability team, a procurement reviewer, an auditor,
# a colleague with a browser or an agent.
#
# Two decisions in here are about what the service is not allowed to do, and both
# are the same decision the package makes everywhere else.
#
# It never runs a repository's code. Measuring executes a slice of somebody's
# repository with the permissions of the process doing it, which is a question
# for a person at a terminal. There is no route for it, so there is nothing here
# to confine.
#
# It clones nothing unless the operator says so. SAGGIO_API_ALLOW_CLONE is unset
# below on purpose: the /audit route answers with what it would take instead,
# which is a better default for a service somebody may expose without reading
# this file.

FROM python:3.12-slim AS build

WORKDIR /src
COPY pyproject.toml README.md ./
COPY saggio ./saggio

# Wheels, not an editable install: the image carries the package the way a user
# would get it from an index, so a file that never made it into the wheel fails
# here rather than in production.
RUN pip install --no-cache-dir --upgrade pip build \
    && python -m build --wheel --outdir /dist


FROM python:3.12-slim

# git is here for one route, /audit, and that route is off unless the operator
# turns it on. The alternative was an image where turning it on does not work.
RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /dist/*.whl /tmp/
# The extra has to be spelled against the file, and a glob cannot carry one:
# `/tmp/*.whl[api]` is a glob matching a name ending in a, p or i, which
# matches nothing and installs nothing.
RUN set -eux; \
    wheel="$(find /tmp -maxdepth 1 -name '*.whl')"; \
    pip install --no-cache-dir "${wheel}[api]"; \
    rm -f "${wheel}"

# Nothing here needs to be root, and the catalogues it reads ship inside the
# wheel, so the filesystem can be read-only in the compose file above it.
RUN useradd --create-home --uid 10001 saggio
USER saggio
WORKDIR /home/saggio

EXPOSE 8000

# Both surfaces at once: the routes at /, the agent protocol at /mcp. Serve only
# the HTTP one by pointing uvicorn at saggio.api.app:app instead.
CMD ["uvicorn", "saggio.api.mcp:app", "--host", "0.0.0.0", "--port", "8000"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"
