# Frontend

Property quality inspection system frontend, built with Vue 3 + Vite. Supports PC (management) and mobile (inspector) interfaces.

## Tech Stack

| Tech | Purpose |
|---|---|
| Vue 3 | Core framework |
| Vite | Build tool |
| Element Plus | PC UI component library |
| Vant 4 | Mobile UI component library |
| Pinia | State management |
| Vue Router | Routing |
| Axios | HTTP client |
| ECharts | Data visualization |

## Directory Structure

```
frontend/
├── src/
│   ├── api/                    # API client modules
│   │   ├── auth.js             # Authentication
│   │   ├── tasks.js            # Task management
│   │   ├── inspection.js       # Inspection records
│   │   ├── scoring.js          # AI scoring
│   │   ├── report.js           # Report generation
│   │   ├── rectification.js    # Rectification tracking
│   │   ├── analysis.js         # Cross-project analysis
│   │   ├── llm.js              # LLM monitoring
│   │   ├── notification.js     # Notifications
│   │   ├── orchestrator.js     # Agent orchestration
│   │   ├── stats.js            # Dashboard statistics
│   │   ├── sync.js             # Offline sync
│   │   ├── guide.js            # Inspection guide
│   │   └── ...
│   ├── components/             # Shared components
│   │   ├── WatermarkCamera.vue # Camera with watermark overlay
│   │   └── OfflineBanner.vue   # Offline status indicator
│   ├── stores/                 # Pinia state stores
│   │   ├── auth.js             # Auth state + JWT management
│   │   └── task.js             # Task state
│   ├── router/                 # Vue Router config
│   ├── utils/                  # Utility modules
│   │   ├── request.js          # Axios interceptor (auth, error handling)
│   │   ├── echarts.js          # ECharts wrapper
│   │   ├── watermark.js        # Photo watermark generation
│   │   ├── offlineDB.js        # IndexedDB for offline storage
│   │   ├── syncManager.js      # Offline-to-server sync
│   │   ├── photoCompress.js    # Client-side photo compression
│   │   ├── photoSigner.js      # Photo integrity signing
│   │   ├── geolocation.js      # GPS location capture
│   │   ├── markdown.js         # Markdown rendering
│   │   └── ...
│   ├── views/
│   │   ├── pc/                 # PC management pages
│   │   │   ├── Dashboard.vue   # Data overview dashboard
│   │   │   ├── Analysis.vue    # Cross-project analysis
│   │   │   ├── LlmMonitor.vue  # LLM cost & usage monitoring
│   │   │   ├── Rectifications.vue # Rectification management
│   │   │   ├── Settings.vue    # System settings
│   │   │   ├── PcLayout.vue    # PC layout shell (sidebar + header)
│   │   │   └── dashboard/      # Dashboard sub-components
│   │   └── mobile/             # Mobile inspector pages
│   │       ├── MobileDashboard.vue  # Mobile dashboard
│   │       ├── TaskList.vue         # Task list + creation
│   │       ├── TaskDetail.vue       # Task detail view
│   │       ├── Inspection.vue       # Inspection form
│   │       ├── InspectionCard.vue   # Card-style inspection
│   │       ├── Scoring.vue          # Scoring view
│   │       ├── ReportList.vue       # Report list
│   │       ├── Report.vue           # Report detail
│   │       ├── Rectification.vue    # Rectification tracking
│   │       ├── RectificationSubmit.vue # Submit rectification
│   │       ├── MobileAnalysis.vue   # Mobile analysis
│   │       ├── Login.vue            # Login
│   │       └── ChangePassword.vue   # Change password
│   ├── App.vue
│   └── main.js
├── index.html
├── vite.config.js
├── package.json
└── README.md
```

## Development

```bash
npm install
npm run dev        # → http://localhost:5173
```

## Production Build

```bash
npm run build      # → dist/
npm run preview    # Preview production build
```

## Environment Variables

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Route Guard

Unauthenticated users are redirected to the login page. Implemented in `src/router/index.js` via `beforeEach` guard.
