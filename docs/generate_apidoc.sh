#!/bin/bash
PROJECT=tardis

sphinx-apidoc --force --module-first --separate -o source/api ../${PROJECT} && \
make html && \
open _build/html/index.html