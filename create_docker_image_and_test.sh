#!/bin/bash
docker build -t website-inspector .
docker run -it --rm -v `pwd`/configs:/opt/website-inspector/configs website-inspector # Runs tests
