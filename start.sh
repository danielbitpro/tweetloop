#!/bin/bash

# Start Twitter Reviewer App
cd /home/danny/workspace/twitter-reviewer

# Install dependencies if needed
pip install flask > /dev/null 2>&1

# Start the app
python3 app.py
