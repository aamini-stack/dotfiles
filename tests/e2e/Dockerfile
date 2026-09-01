FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends sudo curl ca-certificates git \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m -s /bin/bash test \
 && echo 'test ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/test

USER test
WORKDIR /home/test
