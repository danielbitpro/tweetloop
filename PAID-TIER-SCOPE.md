# TweetLoop App — Paid Tier Scope

**Created:** 2026-07-09  
**Status:** Scoping  
**Goal:** Define the technical scope for a paid SaaS tier that delivers a hosted, multi-tenant X content pipeline with auto-posting, source research, and analytics.

---

## 1. Product Vision

**Paid tier = "TweetLoop Cloud"**  
A hosted X content pipeline where users get:
- **Source research** — automatic content discovery from GitHub, Twitter, Reddit, Hacker News, ArXiv
- **AI tweet generation** — research-driven tweet drafts (not generic prompts)
- **Review dashboard** — approve/edit tweets before posting
- **Auto-posting** — schedule and publish tweets automatically
- **Analytics** — engagement tracking, performance metrics
- **Multi-account** — manage multiple X accounts from one dashboard

**Free tier = self-hosted**  
Open-source Docker image. Users run it on their own hardware. Manual pipeline, no auto-posting, no analytics.

---

## 2. Current App Analysis

### What We Have (✅)
| Feature | Status | Notes |
|---------|--------|-------|
| Flask backend | ✅ | Full CRUD API for tweets |
| Password auth | ✅ | Session-based, .env file |
| Frontend UI | ✅ | Cyberpunk Dark Terminal theme |
| Tweet storage | ✅ | JSON file (`tweets.json`) |
| Settings system | ✅ | JSON file (`settings.json`) |
| Post to X button | ✅ | Via `xurl` CLI |
| Pipeline bridge | ✅ | Reads markdown → JSON |
| systemd service | ✅ | Port 7777 |

### What We Need to Change (❌)
| Issue | Impact | Fix Required |
|-------|--------|--------------|
| **File-based storage** (JSON) | Can't scale to multi-tenant, no concurrency safety | Migrate to PostgreSQL |
| **Single-tenant design** | No user isolation, no auth tokens | Add Supabase auth + tenant isolation |
| **No API keys** | Can't connect to X API or other sources | Add per-user credential storage |
| **No scheduling** | Can't auto-post on a schedule | Add cron job engine + schedule table |
| **No analytics** | Can't track engagement | Add analytics tracking + dashboard |
| **No source research** | Manual research only | Add source connectors (GitHub, Reddit, Twitter, etc.) |
| **No Docker** | Hard to deploy for paid users | Create Dockerfile + docker-compose |
| **No onboarding** | Users just get a login screen | Add signup flow + first-time setup wizard |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Browser                          │
│              (app.twitterreviewer.io)                    │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Railway / Fly.io                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Flask App (Docker) — Multi-Tenant                │  │
│  │                                                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │  │
│  │  │ Auth     │  │ API      │  │ Cron Engine  │   │  │
│  │  │ (Supabase│  │ Routes   │  │ (APScheduler)│   │  │
│  │  │  JWT)    │  │          │  │              │   │  │
│  │  └──────────┘  └──────────┘  └──────────────┘   │  │
│  └───────────────────────────────────────────────────┐  │
└───────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Supabase     │ │ PostgreSQL   │ │ Stripe       │
│ (Auth + JWT) │ │ (Tweets,     │ │ (Billing)    │
│              │ │  Settings,   │ │              │
│              │ │  Analytics)  │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Flask (existing) | API server, multi-tenant |
| **Frontend** | Flask templates + JS (existing) | Dashboard UI |
| **Auth** | Supabase | User signup, login, JWT |
| **Database** | PostgreSQL (Supabase) | Tweets, settings, analytics |
| **Billing** | Stripe | Subscriptions, webhooks |
| **Cron Engine** | APScheduler (Python) | Auto-posting, pipeline runs |
| **Hosting** | Railway / Fly.io | Docker deployment |
| **X API** | User-provided keys | Post tweets, read engagement |
| **Source Connectors** | Custom Python | GitHub, Reddit, Twitter API |

---

## 4. Database Schema (New)

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    subscription_status VARCHAR(50) DEFAULT 'free', -- 'free', 'active', 'past_due', 'canceled'
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    is_suspended BOOLEAN DEFAULT FALSE
);
```

### Accounts Table (X accounts per user)
```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    x_api_key_encrypted TEXT NOT NULL, -- encrypted with Fernet
    x_api_secret_encrypted TEXT NOT NULL, -- encrypted with Fernet
    x_access_token_encrypted TEXT NOT NULL, -- encrypted with Fernet
    x_access_token_secret_encrypted TEXT NOT NULL, -- encrypted with Fernet
    x_account_id VARCHAR(255), -- X user ID
    account_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### API Keys Table (any user-provided API key)
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- 'x', 'openrouter', 'openai', 'github', 'reddit', etc.
    key_encrypted TEXT NOT NULL, -- encrypted with Fernet
    secret_encrypted TEXT, -- encrypted with Fernet (if applicable)
    access_token_encrypted TEXT, -- encrypted with Fernet (if applicable)
    access_token_secret_encrypted TEXT, -- encrypted with Fernet (if applicable)
    label VARCHAR(255), -- user-friendly name for this key
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tweets Table (replaces JSON file)
```sql
CREATE TABLE tweets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    label VARCHAR(50),
    hashtags VARCHAR(255),
    why_it_works TEXT,
    section_number INTEGER,
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'approved', 'scheduled', 'posted', 'failed'
    schedule_time TIMESTAMP,
    posted_at TIMESTAMP,
    post_message TEXT,
    source VARCHAR(50) DEFAULT 'manual', -- 'manual', 'pipeline', 'import'
    source_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Settings Table (replaces JSON file)
```sql
CREATE TABLE settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, key)
);
```

### Analytics Table
```sql
CREATE TABLE analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    tweet_id UUID REFERENCES tweets(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- 'impression', 'like', 'retweet', 'reply', 'quote', 'bookmark'
    event_count INTEGER DEFAULT 1,
    event_value JSONB, -- raw API response
    recorded_at TIMESTAMP DEFAULT NOW()
);
```

### Pipeline Runs Table
```sql
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'running', -- 'running', 'complete', 'failed'
    stories_found INTEGER,
    tweets_generated INTEGER,
    tweets_verified INTEGER,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT
);
```

---

## 5. Multi-Tenant Architecture

### How It Works

Every API request includes a `user_id` (from JWT token). All database queries are filtered by `user_id`:

```python
# Example: Get tweets for current user
@app.route('/api/tweets')
@require_auth  # Extracts user_id from JWT
def get_tweets():
    user_id = get_current_user_id()  # From JWT
    tweets = db.execute(
        "SELECT * FROM tweets WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    return jsonify(tweets)
```

### Data Isolation

| Table | Tenant Key | Isolation Method |
|-------|-----------|------------------|
| `users` | `id` | Primary key (each user has one row) |
| `accounts` | `user_id` | Foreign key + WHERE clause |
| `tweets` | `user_id` | Foreign key + WHERE clause |
| `settings` | `user_id` | Foreign key + WHERE clause |
| `analytics` | `user_id` | Foreign key + WHERE clause |
| `pipeline_runs` | `user_id` | Foreign key + WHERE clause |

### API Key Security

User's X API keys are stored encrypted in the database:

```python
from cryptography.fernet import Fernet

class EncryptedColumn:
    """Encrypts/decrypts API keys before storing in DB."""
    def __init__(self, key):
        self.cipher = Fernet(key)
    
    def encrypt(self, value):
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt(self, value):
        return self.cipher.decrypt(value.encode()).decode()
```

---

## 6. Authentication Flow

### User Signup
```
1. User visits app.twitterreviewer.io/signup
2. Enters email + password
3. Supabase creates user + sends email verification
4. User clicks verification link
5. User is redirected to /onboarding
```

### Onboarding Flow (First-Time Setup)
```
1. User logs in for the first time
2. Redirected to /onboarding
3. Step 1: Connect X account
   - Enter X API key, API secret, access token, access token secret
   - App validates credentials by fetching account info
   - If valid: save to database, proceed
   - If invalid: show error, retry
4. Step 2: Configure pipeline settings
   - Choose sources (GitHub, Reddit, Twitter, etc.)
   - Set keywords, date range, max stories
   - Choose tone/instructions for AI
5. Step 3: Choose posting mode
   - Manual: review and approve tweets before posting
   - Automatic: schedule and post tweets automatically
   - Hybrid: review some, auto-post others
6. User is redirected to dashboard
```

### Authentication Middleware
```python
from supabase import create_client, Client

supabase: Client = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_KEY']
)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Verify JWT with Supabase
        user = supabase.auth.get_user(token)
        if not user:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Attach user_id to request context
        request.user_id = user.user.id
        return f(*args, **kwargs)
    return decorated
```

---

## 7. Billing Integration (Stripe)

### Subscription Tiers

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | Self-hosted Docker image, manual pipeline, no auto-posting, no analytics |
| **Pro** | $19/mo | Hosted app, 1 X account, 100 tweets/month, source research, manual review |
| **Pro Plus** | $39/mo | Hosted app, 3 X accounts, 500 tweets/month, source research, analytics, auto-posting |
| **Business** | $79/mo | Hosted app, unlimited accounts, unlimited tweets, source research, analytics, auto-posting, team access |

### Stripe Webhook Handler
```python
@app.route('/api/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle events
    if event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        update_user_subscription(subscription['customer'], 'active', subscription['id'])
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        update_user_subscription(subscription['customer'], subscription['status'], subscription['id'])
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        update_user_subscription(subscription['customer'], 'canceled', None)
    
    return jsonify({'status': 'ok'})
```

### Checkout Flow
```python
@app.route('/api/billing/checkout', methods=['POST'])
@require_auth
def checkout():
    user_id = request.user_id
    plan = request.json.get('plan')  # 'pro', 'pro_plus', 'business'
    
    # Get or create Stripe customer
    user = get_user_by_id(user_id)
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email)
        user.stripe_customer_id = customer.id
        save_user(user)
    
    # Create checkout session
    checkout_session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        line_items=[{
            'price': get_stripe_price_for_plan(plan),
            'quantity': 1,
        }],
        mode='subscription',
        success_url=f'{os.environ["APP_URL"]}/billing/success?session_id={{CHECKOUT_SESSION_ID}}',
        cancel_url=f'{os.environ["APP_URL"]}/billing/cancel',
    )
    
    return jsonify({'url': checkout_session.url})
```

---

## 8. Feature Differences: Free vs Paid

| Feature | Free (Self-Hosted) | Paid (Cloud) |
|---------|-------------------|--------------|
| **Hosting** | User's own hardware | Railway/Fly.io |
| **Auth** | Password (.env) | Supabase JWT |
| **Tweet Storage** | JSON file | PostgreSQL |
| **Source Research** | Manual (user provides sources) | Automatic (GitHub, Reddit, Twitter, etc.) |
| **AI Tweet Generation** | Manual (user runs pipeline) | Automatic (scheduled runs) |
| **Auto-Posting** | ❌ | ✅ |
| **Scheduling** | ❌ | ✅ |
| **Analytics** | ❌ | ✅ |
| **Multi-Account** | ❌ (1 account via xurl) | ✅ (1-3+ accounts) |
| **Cross-Platform** | ❌ | ❌ (X only, for now) |
| **Updates** | Manual (git pull) | Automatic |
| **Support** | Community | Priority |
| **Cost** | $0 | $19-79/mo |

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Goal:** Migrate from JSON to PostgreSQL, add Supabase auth

| Task | Effort | Notes |
|------|--------|-------|
| Set up Supabase project | 1 day | Create DB, auth, storage |
| Create database schema | 1 day | Run migrations |
| Add Supabase auth to Flask | 2 days | JWT middleware, login/logout |
| Migrate tweets.json to PostgreSQL | 1 day | Import existing data |
| Migrate settings.json to PostgreSQL | 1 day | Import existing data |
| Update all API routes | 2 days | Add user_id filtering |
| Update frontend | 2 days | Login screen, JWT tokens |

**Deliverable:** Multi-tenant app with Supabase auth, PostgreSQL storage

### Phase 2: Billing & Onboarding (Week 3-4)
**Goal:** Stripe integration, user signup, onboarding flow

| Task | Effort | Notes |
|------|--------|-------|
| Set up Stripe account | 1 day | Create products, prices |
| Add Stripe webhook handler | 1 day | Handle subscription events |
| Add checkout flow | 1 day | /api/billing/checkout endpoint |
| Add billing dashboard | 2 days | Show subscription status, upgrade |
| Create onboarding flow | 2 days | First-time setup wizard |
| Add X API key storage | 1 day | Encrypted column in DB |
| Add account management | 1 day | CRUD for X accounts |

**Deliverable:** Paid tier with Stripe billing, onboarding, multi-account support

### Phase 3: Source Research (Week 5-6)
**Goal:** Automatic content discovery from multiple sources

| Task | Effort | Notes |
|------|--------|-------|
| GitHub trending API | 1 day | Fetch trending repos |
| Reddit API integration | 1 day | Fetch posts from subreddits |
| Twitter API integration | 1 day | Fetch tweets by keyword |
| Hacker News API | 0.5 day | Fetch top stories |
| ArXiv API | 0.5 day | Fetch recent papers |
| Source aggregation engine | 2 days | Combine results, deduplicate |
| Source quota system | 1 day | Limit sources per tier |
| Update pipeline prompt | 1 day | Include source results |

**Deliverable:** Automatic source research integrated into pipeline

### Phase 4: Auto-Posting & Scheduling (Week 7-8)
**Goal:** Schedule and auto-post tweets

| Task | Effort | Notes |
|------|--------|-------|
| Add APScheduler | 1 day | Cron job engine |
| Add schedule_time to tweets | 0.5 day | DB migration |
| Add post_tweet_via_api | 2 days | X API v2 for posting |
| Add schedule queue view | 2 days | Frontend for scheduled tweets |
| Add post history | 1 day | Track posted tweets |
| Add error handling | 1 day | Retry failed posts |
| Add posting mode toggle | 1 day | Manual vs automatic |

**Deliverable:** Auto-posting with scheduling and error handling

### Phase 5: Analytics (Week 9-10)
**Goal:** Track tweet engagement and performance

| Task | Effort | Notes |
|------|--------|-------|
| Add analytics table | 0.5 day | DB migration |
| Fetch tweet metrics via X API | 2 days | Likes, retweets, replies, etc. |
| Add analytics polling | 1 day | Cron job to fetch metrics |
| Add analytics dashboard | 2 days | Charts, metrics, trends |
| Add performance insights | 1 day | AI-generated suggestions |

**Deliverable:** Analytics dashboard with engagement tracking

### Phase 6: Docker & Deployment (Week 11-12)
**Goal:** Dockerize app, deploy to Railway/Fly.io

| Task | Effort | Notes |
|------|--------|-------|
| Create Dockerfile | 1 day | Multi-stage build |
| Create docker-compose | 0.5 day | For local development |
| Configure Railway/Fly.io | 1 day | Deploy, set env vars |
| Add health checks | 0.5 day | /api/status endpoint |
| Add logging | 1 day | Structured logging |
| Add monitoring | 1 day | Uptime monitoring |
| Create user documentation | 2 days | Setup guide, FAQ |

**Deliverable:** Production-ready Docker deployment

---

## 10. Tech Stack Summary

| Component | Technology | Cost |
|-----------|-----------|------|
| **Backend** | Flask (Python 3.12) | Free |
| **Frontend** | Flask templates + Vanilla JS | Free |
| **Auth** | Supabase (Free tier: 50k MAU) | Free |
| **Database** | Supabase PostgreSQL (Free tier: 500MB) | Free |
| **Billing** | Stripe (2.9% + $0.30 per transaction) | Pay per use |
| **Hosting** | Railway ($5/mo hobby tier) | $5-20/mo |
| **X API** | User-provided keys | User pays |
| **Source APIs** | GitHub (free), Reddit (free), Twitter (user pays) | Free |
| **Monitoring** | UptimeRobot (free tier) | Free |

**Total cost at 100 users:**
- Hosting: $5-20/mo (shared instance)
- Supabase: $0 (free tier covers 50k MAU)
- Stripe: ~$57/mo (2.9% of $1,900 revenue)
- **Total: ~$62-77/mo**
- **Revenue: $1,900/mo**
- **Net profit: ~$1,823-1,838/mo**

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **X API raises prices** | Users may drop app | Monitor pricing, add warning, consider alternative posting methods |
| **Supabase free tier limits** | Can't scale beyond 50k MAU | Budget for $25/mo when needed |
| **Railway downtime** | Users can't access app | Add status page, communicate proactively |
| **Stripe chargebacks** | Revenue loss | Clear terms of service, refund policy |
| **Data breach** | User data exposed | Encrypt API keys, use HTTPS, regular security audits |
| **Feature creep** | Delayed launch | Stick to Phase 1-2 for MVP, defer Phase 3-6 |
| **Competition** | Established players (Buffer, HypeFury) | Differentiate with research-driven content, open-source wedge |

---

## 12. Success Metrics

| Metric | Target (Month 3) | Target (Month 6) | Target (Month 12) |
|--------|-----------------|-----------------|------------------|
| **Paid users** | 50 | 150 | 500 |
| **Monthly revenue** | $950 | $2,850 | $9,500 |
| **Churn rate** | <5% | <3% | <2% |
| **NPS score** | >40 | >50 | >60 |
| **Uptime** | >99% | >99.5% | >99.9% |

---

## 13. Open Questions

1. **Should we use Supabase or build our own auth?**  
   Supabase is faster to implement, but we lose control. Building our own auth takes 2-3 weeks but gives full control.

2. **Should we support multiple X API versions?**  
   X API v2 is the current standard, but some users may still use v1. We should support v2 only for now.

3. **Should we add Bluesky/LinkedIn support?**  
   No — focus on X first. Add other platforms after we have 100+ paying users.

4. **Should we offer a free hosted tier (with limits)?**  
   No — free tier should be self-hosted only. This drives open-source adoption and reduces support burden.

5. **Should we add team access?**  
   Yes — for Business tier ($79/mo). Allow 2-5 team members per account.

6. **Should we add a public API?**  
   Maybe — for power users who want to integrate with their own tools. Add after Phase 4.

---

## 14. Next Steps

1. **Approve this scope** — Confirm the architecture, phases, and tech stack
2. **Set up Supabase account** — Create project, configure auth
3. **Set up Stripe account** — Create products, prices, webhooks
4. **Start Phase 1** — Migrate to PostgreSQL + Supabase auth
5. **Build incrementally** — One phase at a time, with user confirmation before each

---

*This scope is a living document. Update it as we learn more during implementation.*
