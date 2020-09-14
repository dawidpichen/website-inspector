#!/bin/bash
docker run -it --rm -v `pwd`/configs:/opt/website-inspector/configs website-inspector python init_db.py
