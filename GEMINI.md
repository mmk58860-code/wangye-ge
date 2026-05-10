# Project Strategy: wangye-ge

## 1. Backend Architecture (FastAPI)
- **API Manager**: Implements a token bucket or similar algorithm to manage multiple API keys. It will handle retries and failover.
- **Block Monitor**: A background thread/process that connects to Dwellir WSS, subscribes to new headers, and fetches events for `Subtensor.SubnetAdded` and `Subtensor.SubnetRemoved`.
- **Data Scraper**: Periodic task to fetch `getAllDynamicInfo`, `currentAlphaPrice`, etc.
- **Racing Logic**: Calculates eviction candidates by checking immunity periods and EMA rankings.
- **Notification Engine**: Dispatches alerts to Telegram.

## 2. Frontend Architecture (React + Vanilla CSS)
- **Dashboard Layout**: Left sidebar for navigation (Dashboard, Racing, Settings, Logs).
- **Subnet Cards**: 128 responsive cards with real-time updates via WebSocket or long-polling.
- **State Management**: React Context or Zustand for global settings and data.
- **Sorting Logic**: Client-side sorting for responsiveness.

## 3. Installation & Upgrade (Scripts)
- `scripts/install.sh`: Interactive Bash script. Uses `read` to get user input for port, user, and password. Configures Nginx (optional) or just exposes the port via PM2.
- `scripts/upgrade.sh`: Forceful git sync. `git clean -fd && git fetch --all && git reset --hard origin/main`.

## 4. API Pool Design
- Configuration stored in SQLite.
- Each key has `requests_per_second` limit.
- Global `requests_per_second` limit.
- Middleware or helper class to wrap all external RPC calls.

## 5. Timeline
- [ ] Research & Setup (In Progress)
- [ ] Backend Implementation (API Pool, Database, Monitor)
- [ ] Frontend Implementation (UI, Cards, Sorting)
- [ ] Racing Mechanism & Logs
- [ ] Installation Wizard & Upgrade Script
- [ ] Testing & Validation
