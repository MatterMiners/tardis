FROM python:3.8-alpine
MAINTAINER Manuel Giffels <giffels@gmail.com>
ARG SOURCE_BRANCH=master
ARG SOURCE_REPO=https://github.com/MatterMiners/tardis

RUN apk add --no-cache --virtual .build_deps \
             build-base \
             openssl-dev \
             libffi-dev \
             git \
    && pip install --no-cache-dir git+$SOURCE_REPO@$SOURCE_BRANCH \
    && apk del --no-network .build_deps

WORKDIR /srv

COPY cobald.yml /srv/cobald.yml

ENTRYPOINT ["python", "-m", "cobald.daemon"]
CMD ["/srv/cobald.yml"]
