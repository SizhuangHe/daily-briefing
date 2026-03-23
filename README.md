# Daily Briefing

A personal news aggregation and recommendation system designed to work with [Claude Code](https://github.com/anthropics/claude-code). It collects news from RSS feeds, enriches them with AI (Gemini), learns your preferences through ratings, and delivers personalized briefings — all through natural language conversation.

## How It Works

```
                    ┌─────────────┐
                    │  RSS Feeds  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  collect.py │  ← cron (every 30 min)
                    │  fetch +    │
                    │  classify + │
                    │  embed +    │
                    │  score      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   SQLite    │
                    └──┬──────┬──┘
                       │      │
          ┌────────────▼┐  ┌──▼────────────┐
          │  MCP Server │  │  Rating App   │
          │ (Claude Code│  │ (browser UI)  │
          │  15 tools)  │  │ thumbs up/down│
          └─────────────┘  └───────────────┘
```

Three components, one database:

1. **Data Collector** (`collect.py`) — Cron job that fetches RSS feeds, classifies articles by topic/region via Gemini, generates embeddings, scores importance, and recalculates recommendations.

2. **MCP Server** (`mcp_server.py`) — 15 tools exposed to Claude Code via [Model Context Protocol](https://modelcontextprotocol.io/). Claude Code spawns it on demand. You ask for news in natural language; it queries the database and returns results.

3. **Rating App** (`rating_app.py`) — A minimal single-page web UI for training the recommendation system. Browse articles, thumbs up/down, and the model updates in real time.

## Personalized Recommendation

The system learns what you care about from your ratings. Articles are scored by a hybrid formula:

```
score = 0.30 * topic + 0.35 * content + 0.15 * source + 0.20 * recency
```

All channels are percentile-rank normalized before weighting.

| Channel | Weight | Signal |
|---------|--------|--------|
| **Topic** | 30% | Learned from ratings, blended with explicit topic selection |
| **Content** | 35% | Cosine similarity of Gemini embeddings (time-decayed user profile) |
| **Source** | 15% | Source credibility inferred from rating patterns |
| **Recency** | 20% | Step function favoring fresh content (1h → 1.0, 3d+ → 0.1) |

Diversity enforcement prevents filter bubbles: source cap (30%), topic cap (40%), and quality-constrained exploration (10% chance to surface underrepresented topics).

## Importance Scoring

Independent of user preferences, a separate pipeline identifies must-know news:

- Gemini extracts structured fields: event type, severity, geographic scope, time sensitivity
- Rule-based scoring combines these into an importance score (0–1)
- Used by the MCP briefing tools to separate "Urgent" / "Affects You" / "Your Interests"

## Setup

### Prerequisites

- Python 3.12+ (conda recommended)
- [Google Gemini API key](https://aistudio.google.com/apikey)
- [Claude Code](https://github.com/anthropics/claude-code) (for MCP integration)

### Install

```bash
# Create conda environment
conda env create -f environment.yml
conda activate daily-briefing

# Or install manually
cd backend && pip install -r requirements.txt
```

### Configure

Create `backend/.env`:
```env
GEMINI_API_KEY=your-gemini-api-key
```

### Add RSS Sources

Use the MCP tools through Claude Code, or add sources directly to the SQLite database. The collector supports any standard RSS/Atom feed.

### Schedule Data Collection

The collector should run periodically (every 30 minutes recommended):

```bash
# Manual run
cd backend && conda run -n daily-briefing python collect.py

# macOS launchd (see com.dailybriefing.generate.plist for example)
# Linux cron
*/30 * * * * cd /path/to/daily-briefing/backend && conda run -n daily-briefing python collect.py
```

### Connect to Claude Code

Add to your Claude Code MCP config (`~/.claude.json` or project config):

```json
{
  "mcpServers": {
    "daily-briefing": {
      "command": "conda",
      "args": ["run", "-n", "daily-briefing", "--no-banner", "python", "mcp_server.py"],
      "cwd": "/path/to/daily-briefing/backend"
    }
  }
}
```

Once configured, Claude Code can access all 15 tools:

| Category | Tools |
|----------|-------|
| **News** | `get_news_articles`, `refresh_news`, `search_articles` |
| **Ratings** | `rate_article`, `get_ratings`, `get_user_profile` |
| **Sources** | `list_sources`, `add_source`, `toggle_source`, `remove_source` |
| **Stocks** | `get_stock_indices`, `get_watchlist` |
| **Dev** | `get_system_stats`, `get_score_breakdown`, `get_metrics` |

### Train the Recommendation System

Start the rating UI and open `http://localhost:8000`:

```bash
cd backend && conda run -n daily-briefing uvicorn rating_app:app --port 8000
```

Browse articles sorted by score or time. Thumbs up what you like, thumbs down what you don't. The recommendation model updates immediately after each rating.

## Project Structure

```
backend/
  mcp_server.py           # MCP server — 15 tools for Claude Code
  rating_app.py           # Minimal web UI for rating articles
  collect.py              # Cron data collection pipeline
  app/
    models/               # SQLAlchemy models (Article, ArticleRating, TopicWeight, ...)
    services/
      recommendation.py   # Hybrid recommendation engine
      importance.py       # Must-know importance scoring
      gemini_service.py   # Gemini API (classification, embeddings, extraction)
      news_service.py     # RSS fetching, dedup, auto-pruning
    tools/                # MCP tool implementations
    database.py           # SQLite setup
  data/                   # SQLite DB, OAuth tokens

frontend/                 # React frontend (legacy, kept for reference)

environment.yml           # Conda environment spec
com.dailybriefing.generate.plist  # macOS launchd example
```

## Tech Stack

- **Runtime:** Python 3.12, conda
- **AI:** Google Gemini API (topic/region classification, importance extraction, text embeddings)
- **Database:** SQLite + SQLAlchemy
- **MCP:** `mcp` Python SDK (stdio transport)
- **Rating UI:** FastAPI, inline HTML/JS (no build step)

## License

MIT
