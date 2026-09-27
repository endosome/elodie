# syntax=docker/dockerfile:1

# Elodie in a container. The default target runs elodie:
#   docker build -t elodie .
#   docker run --rm --user "$(id -u):$(id -g)" -e TZ=Europe/Warsaw \
#       -v ~/.elodie:/elodie -v ~/Pictures:/photos \
#       elodie import --destination /photos/library /photos/new
# The dev target runs the tests:
#   docker build --target dev -t elodie-dev .
#   docker run --rm elodie-dev pytest elodie/tests -n auto --dist loadgroup
# See "Running in Docker" in the Readme.

# Python 3.12 on Debian 13 (trixie). The digest makes the build reproducible,
#  Dependabot updates it (see .github/dependabot.yml).
FROM python:3.12-slim-trixie@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f AS python-base

# ExifTool without its documentation and tests
FROM python-base AS exiftool
ARG EXIFTOOL_VERSION=13.59
ARG EXIFTOOL_SHA256=87d3317882fdae9cb4dcfe57a96a378d0132ffc02c731315bf128b19ddcf7aac
ADD --checksum=sha256:${EXIFTOOL_SHA256} \
    https://github.com/exiftool/exiftool/archive/refs/tags/${EXIFTOOL_VERSION}.tar.gz \
    /tmp/exiftool.tar.gz
RUN mkdir /opt/exiftool && \
    tar -xzf /tmp/exiftool.tar.gz -C /opt/exiftool --strip-components=1 \
        exiftool-${EXIFTOOL_VERSION}/exiftool exiftool-${EXIFTOOL_VERSION}/lib


FROM python-base AS base

ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# ExifTool is written in Perl. Elodie requires 13.49 or higher which Debian
#  does not ship, the archive of the official repository's tag is used.
RUN apt-get update && \
    apt-get install -y --no-install-recommends perl && \
    rm -rf /var/lib/apt/lists/*
COPY --from=exiftool /opt/exiftool /opt/exiftool
RUN ln -s /opt/exiftool/exiftool /usr/local/bin/exiftool && \
    exiftool -ver

WORKDIR /opt/elodie

# The requirements of elodie and its plugins
COPY requirements.txt .
COPY elodie/plugins/googlephotos/requirements.txt elodie/plugins/googlephotos/requirements.txt
COPY elodie/plugins/immich/requirements.txt elodie/plugins/immich/requirements.txt
RUN pip install --no-cache-dir \
        -r requirements.txt \
        -r elodie/plugins/googlephotos/requirements.txt \
        -r elodie/plugins/immich/requirements.txt


# The whole project with the tests, for development
FROM base AS dev

COPY elodie/tests/requirements.txt elodie/tests/requirements.txt
RUN pip install --no-cache-dir -r elodie/tests/requirements.txt

COPY . .

# Not root, the tests check that permissions are respected
RUN useradd --create-home --uid 1000 elodie && \
    chown -R elodie:elodie /opt/elodie
USER elodie

CMD ["/bin/bash"]


# Elodie without its tests
FROM base AS source
COPY elodie.py /src/
COPY elodie /src/elodie
RUN rm -rf /src/elodie/tests


FROM base AS runtime

COPY --from=source /src /opt/elodie
COPY docker/entrypoint.sh /usr/local/bin/elodie-entrypoint

# Elodie keeps its hash and location databases and config.ini in this
#  folder, mount it to keep them. There is no VOLUME: a new anonymous volume
#  for every run would lose them without notice, the entrypoint warns
#  instead. The user can be changed with --user so the files it creates
#  belong to the user who runs it.
ENV ELODIE_APPLICATION_DIRECTORY=/elodie
RUN useradd --create-home --uid 1000 elodie && \
    mkdir /elodie && \
    chown elodie:elodie /elodie && \
    chmod 777 /elodie
USER elodie

ENTRYPOINT ["elodie-entrypoint"]
CMD ["--help"]
