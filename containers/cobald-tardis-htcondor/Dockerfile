FROM rockylinux:8
LABEL maintainer="Manuel Giffels <giffels@gmail.com>"

ARG SOURCE_BRANCH=master
ARG SOURCE_REPO_URL=https://github.com/MatterMiners/tardis

RUN rpm --import http://research.cs.wisc.edu/htcondor/yum/RPM-GPG-KEY-HTCondor
RUN dnf install -y https://research.cs.wisc.edu/htcondor/repo/10/10.0/htcondor-release-current.el8.noarch.rpm

RUN dnf -y install epel-release && dnf clean all
RUN dnf config-manager --set-enabled powertools

RUN dnf -y update \
    && dnf -y install condor \
                      git \
                      python39 \
                      gcc \
                      python39-devel \
    && dnf clean all

RUN python3.9 -m pip install --no-cache-dir --upgrade pip \
    && python3.9 -m pip install --no-cache-dir git+$SOURCE_REPO_URL@$SOURCE_BRANCH

WORKDIR /srv

COPY cobald.yml /srv/cobald.yml

ENTRYPOINT ["python3.9", "-m", "cobald.daemon"]
CMD ["/srv/cobald.yml"]
