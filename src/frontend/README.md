# NEXT.JS FRONTEND SETUP

## Quick Start

```bash
cd src/frontend
npm install
npm run dev
```

Visit http://localhost:3000

## Environment Variables

Create `.env.local`:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_MAPBOX_TOKEN=your_mapbox_public_token
```

## Project Structure

```
src/frontend/
├── public/                 # Static assets
├── src/
│   ├── components/        # React components (Map, Dashboard, etc.)
│   ├── pages/             # Next.js pages (app router)
│   ├── styles/            # Global styles, Tailwind
│   ├── hooks/             # Custom React hooks
│   ├── store/             # Zustand state management
│   ├── types/             # TypeScript interfaces
│   └── lib/               # Utilities, API client
├── package.json
├── next.config.js
├── tsconfig.json
└── tailwind.config.js
```

## Key Pages

- `/` - Home / interactive map
- `/dashboard` - ESG-style statistics dashboard
- `/clusters` - Cluster explorer
- `/tract/[geoid]` - Tract detail view

## Components to Build

1. **Map** (components/Map.tsx)
   - Mapbox GL choropleth
   - CBI color scale
   - Interaction handlers

2. **Dashboard** (components/Dashboard.tsx)
   - Key metrics cards
   - Charts (Recharts)
   - Filters

3. **ClusterExplorer** (components/ClusterExplorer.tsx)
   - Cluster selector
   - Comparison view

4. **DetailPanel** (components/DetailPanel.tsx)
   - Tract details
   - SHAP explanations
   - Score breakdown

## API Integration

`src/lib/api.ts` provides functions:
- `getScore(lat, lon, explain)` → ScoreResponse
- `getClusters(method)` → ClustersResponse
- `getNLPInsights(geoid)` → InsightResponse

## Styling

- Tailwind CSS for utility-first styling
- Custom components in `src/styles/`
- Dark mode support via theme store

## State Management

Zustand store in `src/store/`:
- Map state (selected tract, viewport)
- Filter state (cluster, region)
- UI state (panel visibility)
- Data caching

## Testing

```bash
npm run lint        # ESLint
npm run type-check  # TypeScript
npm test            # Jest (if configured)
```

## Deployment

```bash
npm run build
npm start
```

Or deploy to Vercel:
```bash
vercel --prod
```
