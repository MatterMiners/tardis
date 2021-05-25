FROM centos:7
LABEL maintainer="Manuel Giffels <giffels@gmail.com>"

ARG SOURCE_BRANCH=master
ARG SOURCE_REPO_URL=https://github.com/MatterMiners/tardis

RUN rpm --import http://research.cs.wisc.edu/htcondor/yum/RPM-GPG-KEY-HTCondor
RUN yum install -y https://research.cs.wisc.edu/htcondor/repo/9.0/htcondor-release-current.el7.noarch.rpm

RUN yum -y install epel-release && yum clean all

RUN yum -y update \
    && yum -y install condor \
                      git \
                      python3 \
                      gcc \
                      python3-devel \
    && yum clean all

RUN python3 -m pip install --no-cache-dir "cryptography<3.2"
RUN python3 -m pip install --no-cache-dir "aiohttp<4.0"
RUN python3 -m pip install --no-cache-dir git+$SOURCE_REPO_URL@$SOURCE_BRANCH

WORKDIR /srv

COPY cobald.yml /srv/cobald.yml

ENTRYPOINT ["python3", "-m", "cobald.daemon"]
CMD ["/srv/cobald.yml"]
