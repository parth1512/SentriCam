#!/bin/bash
# Helper script to run stop_server.py from project root
cd "$(dirname "$0")/web" && python3 stop_server.py "$@"




