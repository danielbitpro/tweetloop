#!/bin/bash

# Start TweetLoop App
cd /home/danny/workspace/tweetloop

# Install dependencies if needed
pip install flask > /dev/null 2>&1

# Start the app
python3 app.py
