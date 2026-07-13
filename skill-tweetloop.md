# TweetLoop Skill

This skill integrates your AI pipeline with the TweetLoop dashboard.

## Setup

1. Clone or copy the `tweetloop` app to your workspace
2. Install dependencies: `pip install flask`
3. Start the app: `python3 app.py`

## Integration Steps

1. When your pipeline finishes verification, save the tweets to:
   `X-proposed-tweets/{date}-final.md`

2. Format each tweet as:
```markdown
## X. [Label] | **Tweet:**
> Tweet text line 1
>
> #Hashtag
|
**Source:** [Name](url)
**Why it works:** ...
```

3. Run the bridge script to import tweets:
```bash
python3 pipeline_to_app_bridge.py
```

The bridge will read the pipeline output and import new tweets into the app's SQLite database.

## Configuration

Change the port by setting `PORT` environment variable:
```bash
PORT=8080 python3 app.py
```

Configure pipeline paths:
```bash
export TLP_WORKSPACE=/path/to/workspace
export TLP_DB_PATH=/path/to/data/tweetloop.db
python3 pipeline_to_app_bridge.py
```