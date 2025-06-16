#!/bin/bash

# mkdir tester
# cp readonly-kubeconfig tester/
# cp run_inner.sh tester/
# cp -rf public/ *_kubectl.py requirements.txt tester/

# Run an interactive bash shell in an Anaconda container with current directory mounted
docker run -it -v $(pwd)/tester:/mnt -p 8000:8000 continuumio/anaconda3:latest /bin/bash
