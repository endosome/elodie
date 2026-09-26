# Base image with Python 3.11 slim
FROM python:3.11-slim

# Avoid interactive prompts and set UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        perl \
        wget \
        make \
        locales && \
    locale-gen C.UTF-8 && \
    pip install --upgrade pip setuptools wheel && \
    rm -rf /var/lib/apt/lists/*

# Install ExifTool, Elodie requires 13.49 or higher which Debian does not ship
ARG EXIFTOOL_VERSION=13.59
ARG EXIFTOOL_SHA256=87d3317882fdae9cb4dcfe57a96a378d0132ffc02c731315bf128b19ddcf7aac
RUN wget -O /tmp/Image-ExifTool.tar.gz https://github.com/exiftool/exiftool/archive/refs/tags/${EXIFTOOL_VERSION}.tar.gz && \
    echo "${EXIFTOOL_SHA256}  /tmp/Image-ExifTool.tar.gz" | sha256sum --check && \
    tar -xzf /tmp/Image-ExifTool.tar.gz -C /tmp && \
    cd /tmp/exiftool-${EXIFTOOL_VERSION} && \
    perl Makefile.PL && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/Image-ExifTool.tar.gz /tmp/exiftool-${EXIFTOOL_VERSION} && \
    exiftool -ver

# Set working directory
WORKDIR /opt/elodie

# Copy Elodie requirements files
COPY requirements.txt .
COPY docs/requirements.txt docs/requirements.txt
COPY elodie/tests/requirements.txt elodie/tests/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r docs/requirements.txt && \
    pip install --no-cache-dir -r elodie/tests/requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Elodie project
COPY . .

# Default command (interactive bash for debugging)
CMD ["/bin/bash"]

