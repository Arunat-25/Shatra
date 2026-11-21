# ADR 0001 — PWA instead of native mobile app

- **Status:** Accepted
- **Date:** 2026-11-21

## Context

Players want to play on phones. Native iOS/Android apps require separate
builds and store accounts; for a developer in Russia, App Store / Google Play
registration and payments are practically unavailable, and RuStore reaches only
Android. The game (board game with local hotseat and AI) needs nothing a
browser cannot provide.

## Decision

Ship the web app as a Progressive Web App (PWA): manifest + service worker
with offline precache of the hotseat mode. One codebase serves desktop and
mobile; updates are instant (redeploy the site).

## Consequences

- No separate iOS/Android builds or store listings.
- Hotseat works offline after the first load.
- Online play and AI still require network; PWA does not change that.
- Native app remains an option later if the web platform proves insufficient.
