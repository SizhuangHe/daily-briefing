# Daily Briefing

A personal daily briefing app that keeps me updated on what's happening in the world and in my life. It aggregates news from multiple RSS sources, enriches them with AI (Gemini), and presents a structured morning briefing alongside calendar events, stock market data, and daily inspiration.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, TanStack React Query
- **AI:** Google Gemini API (article summarization, story clustering, importance extraction, text embeddings)
- **Calendar:** Google Calendar API (multi-account OAuth2) + Apple Reminders (AppleScript)

## Features

### Daily Briefing

The main view presents a structured briefing assembled from clustered news stories, organized into three tiers:

- **Urgent** — Critical events: public safety, severe weather, health emergencies, infrastructure failures
- **Affects You** — News that impacts daily life: policy changes, financial shocks, local governance
- **Your Interests** — Personalized picks split into "For You" (top 70% by interest score) and "Explore" (remaining 30%, shuffled for discovery)

Story clustering is powered by Gemini — individual articles covering the same event are grouped into a single story with a headline, narrative, and "why it matters" explanation. Each story links back to its original source articles.

### Personalized Recommendation System

The recommendation engine learns from user behavior to deliver increasingly relevant content. It operates as a hybrid scoring system with four signal channels:

#### Score Formula

```
score = 0.30 * topic + 0.35 * content + 0.15 * source + 0.20 * recency
```

All four channels are **percentile-rank normalized** before weighting. Raw scores from each channel are converted to their rank position within the current article set (ties averaged), then mapped to [0, 1]. This ensures channels with different natural distributions (e.g., sparse cosine similarity vs. stepped recency) contribute proportionally rather than one dominating.

#### Signal Channels

**1. Topic Preferences (30%)**

Topic weights are derived from three sources, blended together:

- **Implicit signals from ratings:** Each thumbs-up/down on an article or story updates `TopicWeight` entries. Ratings are aggregated per topic and mapped from `[-1, 1]` to weight range `[0.2, 2.0]`.
- **Explicit topic selection:** Users can select interested topics in Settings (e.g., Technology, Health, Markets). Selected topics receive a +0.5 boost (capped at 2.0). This is applied at read-time, not written back to `TopicWeight`, keeping implicit and explicit signals clean.
- **Blending:** Stored weights (60%) are blended with recent rating signals (40%) to balance long-term preferences with short-term interest shifts.

**2. Content Similarity (35%) — Gemini Embeddings with TF-IDF Fallback**

Article text (`title + description`) is embedded using **Gemini `text-embedding-004`**. Embeddings are cached in the `Article.embedding` column (JSON-encoded float vectors) and only generated once per article.

The user profile is built as a **time-decayed weighted mean** of liked article embeddings:
- Weight = `0.5 ^ (age_days / 7)` — 7-day half-life
- Recent likes have much stronger influence, naturally handling interest drift
- Each article is scored by **cosine similarity** to the user profile vector

This approach captures semantic similarity that goes beyond keyword matching — synonyms, paraphrasing, and cross-language content are handled naturally by the embedding space.

**Fallback:** When embeddings are unavailable (cold start, Gemini API down, <30% of articles embedded), the system falls back to a bag-of-words **TF-IDF cosine similarity** model built from article titles and descriptions.

**3. Source Preference (15%)**

Source credibility is inferred from ratings. If a user consistently likes articles from a particular source, that source's weight increases. Mapped from `[-1, 1]` to `[0.2, 1.0]`.

**Credit assignment:** Story-level ratings are **discounted by ×0.2** for source preference calculation. This prevents a story-level thumbs-up (which means "I'm interested in this event") from incorrectly boosting all sources in the cluster. Article-level ratings carry full weight for source preference. Topic and content channels use full weight from both rating types.

**4. Recency (20%)**

A time-decay function favoring fresh content:

| Age | Score |
|-----|-------|
| < 1 hour | 1.0 |
| 1-6 hours | 0.9 |
| 6-12 hours | 0.8 |
| 12-24 hours | 0.6 |
| 1-2 days | 0.4 |
| 2-3 days | 0.2 |
| > 3 days | 0.1 |

#### Diversity and Exploration

To prevent filter bubbles, the engine enforces:

- **Source cap:** No single source can exceed 30% of top results
- **Topic cap:** No single topic can exceed 40% of top results
- **Quality-constrained exploration (10% probability):** Instead of random insertion, explore articles are selected from outside the top results with a **quality floor** (`importance_score >= 0.3`) and **coverage-gap preference** (topics not already represented in the selected set). Among candidates, the highest-importance article is chosen. This ensures exploration surfaces genuinely interesting content rather than noise.

#### For You vs. Explore Split

In the "Your Interests" briefing section, stories are split:

- **For You (70%):** Top stories ranked by interest score — these are what the system is most confident you'll want to read
- **Explore (30%):** Stories selected with **coverage-based diversity** — preferring event types not already represented in the For You section, then shuffled for freshness

#### User Interaction

- **Story-level rating:** Thumbs up/down on a story rates all underlying articles at once, updating topic weights and content profile. Source weights are only weakly affected (×0.2 discount) to avoid credit misattribution.
- **Article-level rating:** Individual articles within a story's source list can be rated independently for finer-grained feedback. These carry full weight across all channels including source preference.
- **Rating toggle:** Clicking the same thumb again removes the rating (score=0 deletes the `ArticleRating` row)
- **Liked page:** A dedicated page (`/liked`) shows all thumbs-up'd articles for easy reference

### Importance Scoring (Must-Know Channel)

A separate scoring pipeline determines which stories are truly important, independent of user preferences:

- **Rule-based baseline:** Event type weights (disasters=0.90, policy=0.55, sports=0.15, etc.) combined with severity, time sensitivity, geographic scope, and source confirmation count
- **Gemini extraction:** Structured fields (event_type, severity, geo_scope, time_sensitivity, personal_impact_flags) are extracted via Gemini and used to refine the baseline score
- **Tier classification:** Articles above 0.75 importance are "Urgent", above 0.45 are "Affects You", rest flow to "Your Interests"

### Other Features

- **Google Calendar:** Multi-account support with timezone-aware event queries. OAuth2 tokens stored per account.
- **Apple Reminders:** Today's reminders fetched via AppleScript
- **Stock Market:** Market indices + personal watchlist with real-time quotes
- **Daily Inspiration:** Rotating quotes, fun facts, and activity suggestions
- **Settings:** Stock watchlist management, topic interest selection, RSS source management

## Project Structure

```
backend/
  app/
    routers/          # FastAPI endpoints (news, briefing, calendar, stocks, preferences, inspiration)
    models/           # SQLAlchemy models (Article, ArticleRating, TopicWeight, UserPreference, ...)
    schemas/          # Pydantic request/response models
    services/         # Business logic
      recommendation.py      # Hybrid recommendation engine
      importance.py          # Must-know importance scoring
      briefing_service.py    # Story clustering + tier assembly
      gemini_service.py      # Gemini API calls
      news_service.py        # RSS feed fetching
      calendar_service.py    # Calendar aggregation
      calendar_providers/    # Google Calendar, AppleScript providers
      stock_service.py       # Stock market data
      inspiration_service.py # Quotes and fun facts
    database.py       # SQLite setup
  data/               # SQLite DB, Google OAuth tokens

frontend/
  src/
    components/
      Dashboard/      # Main dashboard page
      Briefing/       # Story cards, section cards, briefing view
      Liked/          # Liked articles page
      Calendar/       # Calendar events and reminders
      Stocks/         # Market indices and watchlist
      News/           # Article cards, ratings, topic filter
      Inspiration/    # Daily quote/fact/activity
      Settings/       # Watchlist, topic selector, source manager
      Layout/         # Header, main layout
    hooks/            # React Query hooks
    api/              # Axios API client functions
    types/            # TypeScript interfaces
```

## Development

```bash
# Backend (conda environment)
conda run -n daily-briefing uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

Requires environment variables for Gemini API key, NewsAPI key, and Google OAuth credentials in `backend/data/`.
