# Divimero — PRD

## Original Problem
Build "Divimero" for the Building Türkiye challenge: a BIST portfolio tracker combined with a financial social network. Core loop: TRACK PORTFOLIO → UNDERSTAND PERFORMANCE → SHARE A THESIS → ATTACH PORTFOLIO POSITION → FOLLOW HOW THAT POSITION CHANGES. Turkish-first, mobile-first, premium financial product.

## Architecture
- Backend: FastAPI + MongoDB (Motor). JWT (Bearer + cookie) auth, bcrypt hashing. All routes under `/api`.
- Frontend: React 19 + CRA (craco) + Tailwind + shadcn UI + recharts + sonner + lucide-react.
- Market data: `market_data.py` provider abstraction with a `DemoMarketDataProvider` returning deterministic, clearly-labelled TRY prices for 12 BIST tickers.
- Portfolio math: `portfolio_calc.py` (pure functions, FIFO cost basis, allocation %, unrealized/realized P&L).
- Seed: `seed_demo.py` runs on startup, creates admin + Deniz/Ece/Mert/Zeynep, transactions, posts, comments, likes, follows including the THYAO position-reduced flow.
- Tests: `test_portfolio.py` (FIFO, cash, allocation, closed position, dividend).

## Users
- Admin: `admin@divimero.com` / `admin123`
- Deniz (creator): `deniz@divimero.com` / `demo1234` — username `deniz.yatirim`
- Ece (follower): `ece@divimero.com` / `demo1234` — username `ece.market`
- Mert / Zeynep: `mert@divimero.com` / `zeynep@divimero.com` / `demo1234`

## Implemented (Feb 2026)
- Auth (register/login/logout/me), JWT bearer + httpOnly cookie fallback
- Portfolio: transactions CRUD, valuation (KPIs, holdings, allocations), performance series
- Market: tickers list + quote endpoints (demo provider)
- Social: create posts, feed, post detail, comments, likes, follow/unfollow, user posts, user disclosures
- Portfolio-linked position disclosure with immutable snapshot at publication + live current allocation
- Landing / Login / Register / Feed / Portfolio / Compose / Transaction / Profile / Post detail
- Mobile bottom nav + desktop top nav
- Deterministic portfolio unit tests pass

## Golden Demo Path
1. Landing → "Demo: İçerik üreticisi (Deniz)" button
2. Feed shows Deniz's THYAO thesis with Yayınlandığında %5.20 vs Güncel %2.70 (↓ Azalttı)
3. Portfolio page shows KPIs, chart, holdings — THYAO now at %2.70
4. Profile `/u/deniz.yatirim` shows disclosed positions with position history
5. Log in as Ece; open the same post — the publication snapshot remains %5.20, current updates dynamically

## P1 Backlog
- Onboarding flow for new users (bio, avatar upload)
- Modified Dietz / XIRR when enough cash-flow history exists
- Video upload via Emergent object storage
- Notifications for new posts from followed users
- Range disclosure UX polish (%1-3, %3-5 pickers)
