# TweetLoop Skill

This skill integrates your AI pipeline with the TweetLoop dashboard.

## Setup

1. Clone or copy the `tweetloop` app to your workspace
2. Install dependencies: `pip install flask`
3. Start the app: `python3 app.py`

## Integration Steps

1. When your pipeline finishes verification, save the tweets to:
   `/path/to/tweetloop/data/tweets.json`

2. Format each tweet as:
```json
{
  "id": "unique-uuid",
  "text": "Tweet content here",
  "hashtags": "#hashtags",
  "status": "draft",
  "schedule_time": null
}
```

3. The dashboard will automatically display your tweets.

## Manual Tweet Addition

Use the "+ Add Tweet" button in the dashboard to manually create tweets outside your pipeline.

## Configuration

Change the port by setting `PORT` environment variable:
```bash
PORT=8080 python3 app.py
```