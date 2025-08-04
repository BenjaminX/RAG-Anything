#!/usr/bin/env python3
"""Keep container alive script for Docker"""

import time
import signal
import sys

def signal_handler(sig, frame):
    print('\nShutting down gracefully...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print('RAG-Anything container is ready!')
print('Use "docker exec -it raganything /bin/bash" to access the container')
print('Press Ctrl+C to stop')

while True:
    time.sleep(3600)  # Sleep for 1 hour