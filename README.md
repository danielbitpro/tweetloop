# Twitter Reviewer

A dashboard for reviewing, editing, and scheduling tweets from your AI pipeline.

## Features

- 📝 **Edit Tweets** - Fix typos or adjust wording
- ⏰ **Schedule** - Pick exact time to post
- ✅ **Approve** - Mark tweets for posting
- 📤 **Manual Add** - Add tweets outside the pipeline
- 🌙 **Dark Mode** - Easy on the eyes

## Quick Start

### 1. Install Dependencies

```bash
pip install flask
```

Or using the requirements file:

```bash
pip install -r requirements.txt
```

### 2. Run the App

```bash
python3 app.py
```

### 3. Open Dashboard

Navigate to `http://localhost:7777`

## Integration with AI Pipeline

The app reads tweets from `data/tweets.json`. Your AI pipeline should save verified tweets to this file:

```json
[
  {
    "id": "unique-id",
    "text": "Your tweet text",
    "hashtags": "#AI #LocalLLM",
    "status": "draft",
    "schedule_time": "2024-01-01T08:00:00"
  }
]
```

## Hermes Agent Integration

For Hermes users, install the `twitter-reviewer` skill to automatically connect your pipeline to this dashboard.

## Configuration

Change the port by setting the PORT environment variable:

```bash
PORT=8080 python3 app.py
```

## License

MIT License