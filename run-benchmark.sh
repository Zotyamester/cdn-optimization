#!/bin/bash
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi
source venv/bin/activate
python app/benchmark.py
ps | grep cbc | awk '{print $1}' | xargs kill -9 # clean up leak caused by cbc
