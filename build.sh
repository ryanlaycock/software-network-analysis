#!/bin/bash
docker build . -f Dockerfile -t ryanlaycock/software-network-analysis:1.0.0
docker push ryanlaycock/software-network-analysis:1.0.0