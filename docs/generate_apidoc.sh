#!/bin/bash
PROJECT=tardis

source ${VIRTUAL_ENV}/bin/activate
sphinx-apidoc --force --module-first --separate -o source/api ../${PROJECT} && \
make html && \
open _build/html/index.html
