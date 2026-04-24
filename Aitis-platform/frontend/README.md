# Frontend Wiring Pack

This pack updates the **Next.js frontend** to use the **real FastAPI backend** instead of local/mock generation.

## What changes
- Replaces local test generation with backend API calls
- Wires the page to:
  - `POST /api/intents/generate`
  - `POST /api/tests/generate`
  - `POST /api/scenarios/generate`
  - `POST /api/automation/generate`
- Keeps the same Story Workspace UX
- Adds stronger loading and error handling

## Files to copy into your project
Copy these files into your repo root, preserving paths:

- `apps/web/app/page.tsx`
- `apps/web/lib/api.ts`
- `apps/web/lib/types.ts`
- `apps/web/.env.example`
- `apps/web/components/ui/badge.tsx`
- `apps/web/components/ui/section.tsx`

## Environment file
Copy:

```bash
apps/web/.env.example -> apps/web/.env.local
```

Ensure the API URL matches your backend:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

## Expected backend endpoints
The frontend expects these endpoints to exist:

```text
GET  /api/stories/sample
POST /api/intents/generate
POST /api/tests/generate
POST /api/scenarios/generate
POST /api/automation/generate
```

## Run

### Backend
```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```
### python3 -m uvicorn app.main:app --reload --port 8000
### Frontend
```bash
cd apps/web
npm install
npm run dev
```

## Verify
- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health
