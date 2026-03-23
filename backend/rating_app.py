#!/usr/bin/env python3
"""
Minimal rating web app.

Serves a simple HTML page for browsing articles and rating them
with thumbs up/down. No React needed.

Usage:
    conda run -n daily-briefing uvicorn rating_app:app --port 8000
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from app.database import SessionLocal, init_db
from app.models.article import Article, ArticleRating
from app.services import recommendation

init_db()

app = FastAPI(title="Daily Briefing Ratings")


@app.get("/api/articles")
def api_articles(
    limit: int = Query(default=50, le=500),
    sort: str = Query(default="score", pattern="^(score|time)$"),
):
    """JSON article list."""
    db = SessionLocal()
    try:
        query = db.query(Article)
        if sort == "time":
            query = query.order_by(Article.published_at.desc())
        else:
            query = query.order_by(
                Article.recommendation_score.desc(),
                Article.published_at.desc(),
            )
        articles = query.limit(limit).all()

        # Get existing ratings
        ratings = db.query(ArticleRating).all()
        rating_map = {r.article_id: r.score for r in ratings}

        results = []
        for a in articles:
            topics = []
            if a.topics:
                try:
                    topics = json.loads(a.topics)
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append({
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "source_name": a.source_name,
                "description": a.gemini_summary or a.description or "",
                "topics": topics,
                "recommendation_score": round(a.recommendation_score or 0, 3),
                "importance_score": round(a.importance_score or 0, 3),
                "published_at": str(a.published_at) if a.published_at else None,
                "rating": rating_map.get(a.id),
            })
        return results
    finally:
        db.close()


@app.post("/rate/{article_id}")
def rate(article_id: int, score: int = Query(...)):
    """Rate an article: score=1 (up), -1 (down), 0 (remove)."""
    db = SessionLocal()
    try:
        article = db.query(Article).filter_by(id=article_id).first()
        if not article:
            return {"error": "not found"}

        existing = db.query(ArticleRating).filter_by(article_id=article_id).first()
        if score == 0:
            if existing:
                db.delete(existing)
            db.commit()
        elif existing:
            existing.score = score
            existing.rated_at = datetime.utcnow()
            db.commit()
        else:
            db.add(ArticleRating(
                article_id=article_id,
                score=score,
                rating_source="web",
            ))
            db.commit()

        # Recalculate in background thread so the UI stays responsive
        import threading
        def _recalc():
            recalc_db = SessionLocal()
            try:
                recommendation.update_topic_weights(recalc_db)
                recommendation.recalculate_scores(recalc_db)
            finally:
                recalc_db.close()
        threading.Thread(target=_recalc, daemon=True).start()

        return {"ok": True, "article_id": article_id, "score": score}
    finally:
        db.close()


@app.get("/api/stats")
def api_stats():
    """System stats for the dashboard."""
    db = SessionLocal()
    try:
        total_articles = db.query(Article).count()
        articles_with_embeddings = (
            db.query(Article).filter(Article.embedding.isnot(None)).count()
        )
        total_ratings = db.query(ArticleRating).count()
        total_liked = db.query(ArticleRating).filter(ArticleRating.score > 0).count()
        total_disliked = db.query(ArticleRating).filter(ArticleRating.score < 0).count()

        cutoff = datetime.utcnow() - timedelta(hours=72)
        candidate_window = (
            db.query(Article).filter(Article.published_at >= cutoff).count()
        )

        # Source distribution
        from sqlalchemy import func
        source_counts = (
            db.query(Article.source_name, func.count(Article.id))
            .group_by(Article.source_name)
            .order_by(func.count(Article.id).desc())
            .limit(10)
            .all()
        )

        # Topic distribution
        topic_counts: dict[str, int] = {}
        for (raw_topics,) in db.query(Article.topics).filter(Article.topics.isnot(None)).all():
            try:
                for t in json.loads(raw_topics):
                    topic_counts[t] = topic_counts.get(t, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        top_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:10]

        # Score distribution (histogram buckets)
        score_dist = []
        for low in [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            high = round(low + 0.1, 1)
            count = (
                db.query(Article)
                .filter(Article.recommendation_score >= low, Article.recommendation_score < high)
                .count()
            )
            score_dist.append({"range": f"{low:.1f}-{high:.1f}", "count": count})

        # Recent ratings
        recent_ratings = (
            db.query(ArticleRating, Article.title)
            .join(Article, ArticleRating.article_id == Article.id)
            .order_by(ArticleRating.rated_at.desc())
            .limit(20)
            .all()
        )
        recent = [
            {
                "article_id": r.article_id,
                "title": title,
                "score": r.score,
                "rated_at": str(r.rated_at) if r.rated_at else None,
            }
            for r, title in recent_ratings
        ]

        return {
            "total_articles": total_articles,
            "articles_with_embeddings": articles_with_embeddings,
            "candidate_window": candidate_window,
            "total_ratings": total_ratings,
            "total_liked": total_liked,
            "total_disliked": total_disliked,
            "sources": [{"name": n, "count": c} for n, c in source_counts],
            "topics": [{"name": n, "count": c} for n, c in top_topics],
            "score_distribution": score_dist,
            "recent_ratings": recent,
        }
    finally:
        db.close()


@app.get("/api/profile")
def api_profile():
    """User profile centroids."""
    db = SessionLocal()
    try:
        return recommendation.get_centroid_details(db)
    finally:
        db.close()


PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Briefing</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
    background: #f8fafc; color: #0f172a; line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}
.container { max-width: 780px; margin: 0 auto; padding: 2rem 1rem; }

/* ── Navigation ── */
nav {
    display: flex; align-items: center; gap: 1.5rem;
    margin-bottom: 1.5rem; padding-bottom: 0.75rem;
    border-bottom: 1px solid #e2e8f0;
}
nav h1 { font-size: 1rem; font-weight: 700; color: #0f172a; letter-spacing: -0.02em; }
nav .tabs { display: flex; gap: 0.25rem; margin-left: auto; }
nav .tab {
    padding: 0.375rem 0.875rem; font-size: 0.8rem; font-weight: 500;
    color: #64748b; background: none; border: 1px solid transparent;
    border-radius: 6px; cursor: pointer; transition: all 0.15s;
}
nav .tab:hover { color: #334155; background: #f1f5f9; }
nav .tab.active { color: #2563eb; background: #eff6ff; border-color: #bfdbfe; }

/* ── Topic filter ── */
.filters { display: flex; flex-wrap: wrap; gap: 0.375rem; margin-bottom: 1rem; }
.chip {
    padding: 0.25rem 0.75rem; font-size: 0.7rem; font-weight: 500;
    border-radius: 100px; cursor: pointer; transition: all 0.15s;
    border: none; text-transform: capitalize;
}
.chip-sort {
    color: #475569; background: #f1f5f9;
}
.chip-sort:hover { background: #e2e8f0; }
.chip-sort.active { color: #fff; background: #334155; }
.chip-topic {
    color: #64748b; background: #f1f5f9;
}
.chip-topic:hover { background: #e2e8f0; color: #334155; }
.chip-topic.active { color: #fff; background: #2563eb; }
.chip .count { opacity: 0.6; margin-left: 0.125rem; }
.filter-divider {
    width: 1px; height: 1.25rem; background: #e2e8f0; align-self: center;
    margin: 0 0.25rem;
}

/* ── Article card ── */
.articles { display: flex; flex-direction: column; gap: 0.625rem; }
.card {
    display: flex; gap: 0.875rem; padding: 0.875rem 1rem;
    background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
    transition: box-shadow 0.15s;
}
.card:hover { box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.card .body { flex: 1; min-width: 0; }
.card .headline {
    font-size: 0.8125rem; font-weight: 600; line-height: 1.4;
    color: #0f172a;
}
.card .headline a { color: inherit; text-decoration: none; }
.card .headline a:hover { color: #2563eb; }
.card .desc {
    margin-top: 0.25rem; font-size: 0.75rem; color: #64748b;
    line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden;
}
.card .footer {
    margin-top: 0.5rem; display: flex; align-items: center; gap: 0.5rem;
    font-size: 0.6875rem;
}
.card .source { color: #94a3b8; font-weight: 500; }
.card .time { color: #cbd5e1; }
.card .topic-tag {
    display: inline-block; padding: 0.05rem 0.4rem;
    background: #f1f5f9; color: #64748b; border-radius: 100px;
    font-size: 0.6rem; font-weight: 500; text-transform: capitalize;
}
.card .score-col {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; gap: 0.125rem; flex-shrink: 0; width: 2.5rem;
}
.card .score-num {
    font-size: 0.65rem; font-weight: 600; color: #94a3b8;
    font-variant-numeric: tabular-nums;
}
.card .rate-col {
    display: flex; flex-direction: column; gap: 0.25rem;
    align-items: center; justify-content: center; flex-shrink: 0;
}

/* ── Thumbs buttons (SVG) ── */
.thumb {
    width: 28px; height: 28px; border: none; border-radius: 6px;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    background: transparent; transition: all 0.12s; color: #cbd5e1;
}
.thumb:hover { background: #f8fafc; }
.thumb.up:hover { color: #22c55e; background: #f0fdf4; }
.thumb.down:hover { color: #ef4444; background: #fef2f2; }
.thumb.up.active { color: #16a34a; background: #dcfce7; }
.thumb.down.active { color: #dc2626; background: #fee2e2; }
.thumb svg { width: 14px; height: 14px; }

/* ── Pages ── */
.page { display: none; }
.page.active { display: block; }

/* ── Stats ── */
.section { margin-bottom: 1.25rem; }
.section-card {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 1.25rem; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.section-header {
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 0.875rem;
}
.section-header h3 {
    font-size: 0.8125rem; font-weight: 600; color: #0f172a;
}
.section-header .badge {
    font-size: 0.65rem; font-weight: 500; color: #64748b;
    background: #f1f5f9; padding: 0.125rem 0.5rem; border-radius: 100px;
}
.section-label {
    font-size: 0.65rem; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.05em;
}

/* Stat numbers grid */
.num-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem;
}
.num-box { text-align: center; }
.num-box .val {
    font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums; color: #0f172a;
}
.num-box .val.blue { color: #2563eb; }
.num-box .val.green { color: #16a34a; }
.num-box .val.red { color: #dc2626; }
.num-box .lbl { font-size: 0.65rem; color: #94a3b8; margin-top: 0.125rem; }

/* Bar charts */
.charts-2col {
    display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
}
.bar-row {
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 0.3rem; font-size: 0.75rem;
}
.bar-name {
    width: 80px; text-align: right; color: #64748b; font-size: 0.7rem;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0;
}
.bar-track { flex: 1; height: 8px; background: #f1f5f9; border-radius: 100px; overflow: hidden; }
.bar-val { height: 100%; border-radius: 100px; }
.bar-val.blue { background: #60a5fa; }
.bar-val.emerald { background: #34d399; }
.bar-num { width: 1.5rem; font-size: 0.65rem; color: #94a3b8; text-align: right; font-variant-numeric: tabular-nums; }

/* Histogram */
.histogram { display: flex; align-items: flex-end; gap: 3px; height: 80px; }
.hist-bar {
    flex: 1; background: #93c5fd; border-radius: 3px 3px 0 0;
    min-height: 2px; position: relative; transition: background 0.15s;
}
.hist-bar:hover { background: #60a5fa; }
.hist-bar .tip {
    display: none; position: absolute; bottom: calc(100% + 4px); left: 50%;
    transform: translateX(-50%); font-size: 0.6rem; color: #fff;
    background: #334155; padding: 2px 6px; border-radius: 4px; white-space: nowrap;
}
.hist-bar:hover .tip { display: block; }
.hist-labels { display: flex; gap: 3px; margin-top: 3px; }
.hist-labels span { flex: 1; text-align: center; font-size: 0.55rem; color: #94a3b8; }

/* Centroid cards */
.centroids { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.centroid {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 1rem; border-left: 3px solid #60a5fa;
}
.centroid.c1 { border-left-color: #60a5fa; }
.centroid.c2 { border-left-color: #a78bfa; }
.centroid.c3 { border-left-color: #fbbf24; }
.centroid.c4 { border-left-color: #34d399; }
.centroid .c-head {
    display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.625rem;
}
.centroid .c-id {
    font-size: 0.75rem; font-weight: 700; color: #334155;
}
.centroid .c-count { font-size: 0.65rem; color: #94a3b8; }
.centroid .c-tags { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-bottom: 0.5rem; }
.centroid .c-tag {
    font-size: 0.6rem; font-weight: 500; padding: 0.1rem 0.5rem;
    background: #eff6ff; color: #3b82f6; border-radius: 100px;
}
.centroid .c-label {
    font-size: 0.6rem; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.04em;
    margin: 0.375rem 0 0.25rem;
}
.centroid .c-row {
    display: flex; align-items: center; gap: 0.375rem;
    font-size: 0.7rem; color: #64748b; padding: 0.15rem 0;
}
.centroid .c-row .sim {
    margin-left: auto; font-size: 0.6rem; color: #94a3b8;
    font-variant-numeric: tabular-nums; flex-shrink: 0;
}
.centroid .c-row .ticon { color: #34d399; flex-shrink: 0; }
.centroid .c-row span.trunc {
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    min-width: 0;
}

/* Recent ratings */
.rating-row {
    display: flex; align-items: center; gap: 0.5rem;
    padding: 0.375rem 0.5rem; border-radius: 6px; font-size: 0.75rem;
}
.rating-row:hover { background: #f8fafc; }
.rating-row .r-icon { flex-shrink: 0; }
.rating-row .r-icon.up { color: #22c55e; }
.rating-row .r-icon.down { color: #ef4444; }
.rating-row .r-icon svg { width: 13px; height: 13px; }
.rating-row .r-text {
    flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; color: #475569;
}
.rating-row .r-time { flex-shrink: 0; font-size: 0.65rem; color: #94a3b8; }

.subtitle { font-size: 0.7rem; color: #94a3b8; }
</style>
</head>
<body>
<div class="container">
    <nav>
        <h1>Daily Briefing</h1>
        <span class="subtitle" id="header-sub"></span>
        <div class="tabs">
            <button class="tab active" onclick="switchTab('rate', this)">Rate</button>
            <button class="tab" onclick="switchTab('stats', this)">Stats</button>
        </div>
    </nav>

    <div id="page-rate" class="page active">
        <div class="filters" id="filters"></div>
        <div class="articles" id="list"></div>
    </div>

    <div id="page-stats" class="page">
        <div id="stats-content"></div>
    </div>
</div>

<script>
var SVG_UP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10l5-5 5 5"/><path d="M12 5v14"/></svg>';
var SVG_DOWN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 14l5 5 5-5"/><path d="M12 19V5"/></svg>';
var SVG_THUMB_UP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>';
var SVG_THUMB_DOWN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>';

var articles = [];
var currentSort = 'score';
var currentTopic = null;
var statsLoaded = false;

function switchTab(name, btn) {
    document.querySelectorAll('nav .tab').forEach(function(t) { t.classList.remove('active'); });
    btn.classList.add('active');
    document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
    document.getElementById('page-' + name).classList.add('active');
    if (name === 'stats' && !statsLoaded) loadStats();
}

function setSort(sort, btn) {
    currentSort = sort;
    document.querySelectorAll('.chip-sort').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    load();
}

function setTopic(topic, btn) {
    if (currentTopic === topic) { currentTopic = null; btn.classList.remove('active'); }
    else {
        currentTopic = topic;
        document.querySelectorAll('.chip-topic').forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
    }
    render();
}

async function load() {
    var r = await fetch('/api/articles?sort=' + currentSort + '&limit=500');
    articles = await r.json();
    buildFilters();
    render();
}

function buildFilters() {
    var counts = {};
    articles.forEach(function(a) {
        a.topics.forEach(function(t) { counts[t] = (counts[t] || 0) + 1; });
    });
    var sorted = Object.entries(counts).sort(function(a, b) { return b[1] - a[1]; });
    var el = document.getElementById('filters');
    var html = '<button class="chip chip-sort' + (currentSort === 'score' ? ' active' : '') +
        '" data-sort="score" onclick="setSort(this.dataset.sort, this)">By Score</button>' +
        '<button class="chip chip-sort' + (currentSort === 'time' ? ' active' : '') +
        '" data-sort="time" onclick="setSort(this.dataset.sort, this)">Latest</button>' +
        '<div class="filter-divider"></div>';
    sorted.forEach(function(pair) {
        var active = currentTopic === pair[0] ? ' active' : '';
        html += '<button class="chip chip-topic' + active +
            '" data-topic="' + esc(pair[0]) + '" onclick="setTopic(this.dataset.topic, this)">' +
            esc(pair[0]) + '<span class="count">' + pair[1] + '</span></button>';
    });
    el.innerHTML = html;
}

function render() {
    var filtered = currentTopic
        ? articles.filter(function(a) { return a.topics.indexOf(currentTopic) !== -1; })
        : articles;
    var el = document.getElementById('list');
    el.innerHTML = filtered.map(function(a) {
        var age = a.published_at ? timeAgo(new Date(a.published_at)) : '';
        var desc = a.description || '';
        if (desc.length > 160) desc = desc.substring(0, 160) + '...';
        return '<div class="card">' +
            '<div class="score-col"><span class="score-num">' + a.recommendation_score.toFixed(2) + '</span></div>' +
            '<div class="body">' +
                '<div class="headline"><a href="' + esc(a.url) + '" target="_blank">' + esc(a.title) + '</a></div>' +
                (desc ? '<div class="desc">' + esc(desc) + '</div>' : '') +
                '<div class="footer">' +
                    '<span class="source">' + esc(a.source_name || '') + '</span>' +
                    (age ? '<span class="time">' + age + '</span>' : '') +
                    a.topics.map(function(t) { return '<span class="topic-tag">' + esc(t) + '</span>'; }).join('') +
                '</div>' +
            '</div>' +
            '<div class="rate-col">' +
                '<button class="thumb up' + (a.rating === 1 ? ' active' : '') +
                    '" onclick="rate(' + a.id + ',' + (a.rating === 1 ? 0 : 1) + ')">' + SVG_THUMB_UP + '</button>' +
                '<button class="thumb down' + (a.rating === -1 ? ' active' : '') +
                    '" onclick="rate(' + a.id + ',' + (a.rating === -1 ? 0 : -1) + ')">' + SVG_THUMB_DOWN + '</button>' +
            '</div>' +
        '</div>';
    }).join('');
    document.getElementById('header-sub').textContent =
        filtered.length + (currentTopic ? ' / ' + articles.length : '') + ' articles';
}

async function rate(id, score) {
    await fetch('/rate/' + id + '?score=' + score, {method: 'POST'});
    var a = articles.find(function(x) { return x.id === id; });
    if (a) a.rating = score === 0 ? null : score;
    render();
}

async function loadStats() {
    var el = document.getElementById('stats-content');
    el.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:3rem">Loading...</div>';
    var results = await Promise.all([fetch('/api/stats'), fetch('/api/profile')]);
    var s = await results[0].json();
    var profile = await results[1].json();
    statsLoaded = true;

    var maxSrc = Math.max.apply(null, s.sources.map(function(x) { return x.count; }).concat([1]));
    var maxTop = Math.max.apply(null, s.topics.map(function(x) { return x.count; }).concat([1]));
    var maxHist = Math.max.apply(null, s.score_distribution.map(function(x) { return x.count; }).concat([1]));
    var h = '';

    // System stats
    h += '<div class="section"><div class="section-card">';
    h += '<div class="section-header"><h3>System Stats</h3></div>';
    h += '<div class="num-grid">';
    h += numBox(s.total_articles, 'Total Articles', 'blue');
    h += numBox(s.candidate_window, '72h Window', '');
    h += numBox(s.articles_with_embeddings, 'Embeddings', '');
    h += numBox(s.total_ratings, 'Ratings', 'blue');
    h += numBox(s.total_liked, 'Liked', 'green');
    h += numBox(s.total_disliked, 'Disliked', 'red');
    h += '</div></div></div>';

    // Sources + Topics
    h += '<div class="section"><div class="charts-2col">';
    h += '<div class="section-card"><div class="section-header"><h3>Sources</h3></div>';
    s.sources.forEach(function(x) {
        var pct = (x.count / maxSrc * 100).toFixed(0);
        h += '<div class="bar-row"><span class="bar-name">' + esc(x.name || '?') + '</span>' +
            '<div class="bar-track"><div class="bar-val blue" style="width:' + pct + '%"></div></div>' +
            '<span class="bar-num">' + x.count + '</span></div>';
    });
    h += '</div>';
    h += '<div class="section-card"><div class="section-header"><h3>Topics</h3></div>';
    s.topics.forEach(function(x) {
        var pct = (x.count / maxTop * 100).toFixed(0);
        h += '<div class="bar-row"><span class="bar-name">' + esc(x.name) + '</span>' +
            '<div class="bar-track"><div class="bar-val emerald" style="width:' + pct + '%"></div></div>' +
            '<span class="bar-num">' + x.count + '</span></div>';
    });
    h += '</div></div></div>';

    // Score distribution
    h += '<div class="section"><div class="section-card">';
    h += '<div class="section-header"><h3>Score Distribution</h3></div>';
    h += '<div class="histogram">';
    s.score_distribution.forEach(function(b) {
        var ht = Math.max((b.count / maxHist * 100), 2);
        h += '<div class="hist-bar" style="height:' + ht + '%"><span class="tip">' + b.range + ': ' + b.count + '</span></div>';
    });
    h += '</div><div class="hist-labels">';
    s.score_distribution.forEach(function(b) { h += '<span>' + b.range.split('-')[0] + '</span>'; });
    h += '</div></div></div>';

    // User profile centroids
    if (profile.length > 0) {
        h += '<div class="section"><div class="section-card">';
        h += '<div class="section-header"><h3>Interest Centroids</h3>';
        h += '<span class="badge">' + profile.length + ' clusters</span></div>';
        h += '<div class="centroids">';
        var colors = ['c1','c2','c3','c4'];
        profile.forEach(function(c) {
            h += '<div class="centroid ' + colors[c.id % 4] + '">';
            h += '<div class="c-head"><span class="c-id">Centroid #' + (c.id + 1) + '</span>';
            h += '<span class="c-count">' + c.liked_articles.length + ' liked</span></div>';
            if (c.topics.length > 0) {
                h += '<div class="c-tags">';
                c.topics.forEach(function(t) { h += '<span class="c-tag">' + esc(t) + '</span>'; });
                h += '</div>';
            }
            if (c.liked_articles.length > 0) {
                h += '<div class="c-label">Liked Articles</div>';
                c.liked_articles.slice(0, 5).forEach(function(a) {
                    h += '<div class="c-row"><span class="ticon">' + SVG_THUMB_UP + '</span><span class="trunc">' + esc(a.title || 'Unknown') + '</span></div>';
                });
                if (c.liked_articles.length > 5)
                    h += '<div class="c-row" style="color:#94a3b8">+' + (c.liked_articles.length - 5) + ' more</div>';
            }
            if (c.top_matches.length > 0) {
                h += '<div class="c-label">Top Matches</div>';
                c.top_matches.forEach(function(a) {
                    h += '<div class="c-row"><span class="trunc">' + esc(a.title || 'Unknown') + '</span><span class="sim">' + a.similarity.toFixed(3) + '</span></div>';
                });
            }
            h += '</div>';
        });
        h += '</div></div></div>';
    }

    // Recent ratings
    h += '<div class="section"><div class="section-card">';
    h += '<div class="section-header"><h3>Recent Ratings</h3><span class="badge">Last 20</span></div>';
    s.recent_ratings.forEach(function(r) {
        var cls = r.score > 0 ? 'up' : 'down';
        var icon = r.score > 0 ? SVG_THUMB_UP : SVG_THUMB_DOWN;
        var time = r.rated_at ? timeAgo(new Date(r.rated_at)) : '';
        h += '<div class="rating-row"><span class="r-icon ' + cls + '">' + icon + '</span>' +
            '<span class="r-text">' + esc(r.title || 'Unknown') + '</span>' +
            '<span class="r-time">' + time + '</span></div>';
    });
    h += '</div></div>';

    el.innerHTML = h;
}

function numBox(val, label, color) {
    var cls = color ? ' ' + color : '';
    return '<div class="num-box"><div class="val' + cls + '">' + val + '</div><div class="lbl">' + label + '</div></div>';
}

function timeAgo(date) {
    var s = (new Date() - date) / 1000;
    if (s < 60) return 'just now';
    if (s < 3600) return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

function esc(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

load();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE_HTML
