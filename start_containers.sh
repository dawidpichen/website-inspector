#!/bin/bash
docker run -it -d -v `pwd`/configs:/opt/website-inspector/configs --log-opt mode=non-blocking --name wi-monitor website-inspector python monitor.py
docker run -it -d -v `pwd`/configs:/opt/website-inspector/configs --log-opt mode=non-blocking --name wi-dbwriter website-inspector python db_writer.py
