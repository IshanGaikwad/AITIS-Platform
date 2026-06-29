# Phase 1 Developer Quick Reference

## 🚀 Quick Start for Developers

### Backend Setup
```bash
cd backend

# Install dependencies
pip install -r requirements.txt
pip install alembic  # For migrations

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload

# Run tests
pytest tests/test_phase1_integration.py -v
```

### Frontend Setup
```bash
cd frontend/apps/web

# Install dependencies
npm install

# Start dev server
npm run dev

# Run E2E tests
npx playwright test tests/e2e/phase1.spec.ts --headed
```

---

## 📚 Key Files Reference

### Backend

**Models** (Single Responsibility)
- `app/models/application.py` - Application deployment targets
- `app/models/environment.py` - Deployment environments
- `app/models/project.py` - Projects (extended)

**Services** (Business Logic)
- `app/services/application_service.py` - Application CRUD
- `app/services/environment_service.py` - Environment CRUD
- `app/services/attachment_service.py` - File upload/download
- `app/services/requirement_version_service.py` - Version tracking
- `app/services/requirement_import_service.py` - Import abstraction

**API Routes**
- `app/api/v1/applications.py` - Application endpoints
- `app/api/v1/environments.py` - Environment endpoints
- `app/api/v1/attachments.py` - File attachment endpoints

**Testing**
- `tests/test_phase1_integration.py` - Integration tests

### Frontend

**Components** (Reusable UI)
- `components/projects-list.tsx` - Project management
- `components/applications-list.tsx` - Application management
- `components/environments-list.tsx` - Environment management
- `components/ui/textarea.tsx` - Textarea component

**Pages**
- `app/projects/page.tsx` - Projects list view
- `app/projects/[projectId]/page.tsx` - Project detail view

**Testing**
- `tests/e2e/phase1.spec.ts` - End-to-end tests

---

## 🔑 Key Concepts

### Tenant Isolation
All models use `organization_id` and `workspace_id` for multi-tenancy:
```python
class TenantMixin:
    organization_id: UUID
    workspace_id: UUID
```

### Service Pattern
Services use async methods with AsyncSession:
```python
async def create_application(
    db: AsyncSession,
    organization_id: UUID,
    workspace_id: UUID,
    **kwargs
) -> Application:
    # Create and return entity
```

### Permission Checking
Routes use PermissionService for RBAC:
```python
await PermissionService.check_permission(
    db, user_id, "applications", "create", org_id, ws_id
)
```

### Provider Pattern
RequirementImport uses provider abstraction:
```python
class RequirementProvider(ABC):
    @abstractmethod
    async def import_requirement(payload) -> RequirementPayload: ...
```

---

## 🔄 Common Workflows

### Create Project → Application → Environment

**Backend API:**
```bash
# 1. Create project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "E-Commerce", "key": "ECOM", ...}'

# 2. Create application
curl -X POST http://localhost:8000/api/v1/projects/{project_id}/applications \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Frontend", "application_type": "WEB", ...}'

# 3. Create environment
curl -X POST http://localhost:8000/api/v1/applications/{app_id}/environments \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Dev", "environment_type": "dev", ...}'
```

### Add a New Service

1. Create service file: `app/services/my_service.py`
```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.my_model import MyModel

class MyService:
    @staticmethod
    async def create_item(db: AsyncSession, **kwargs) -> MyModel:
        item = MyModel(**kwargs)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item
```

2. Add routes: `app/api/v1/my_items.py`
```python
from fastapi import APIRouter, Depends
from app.services.my_service import MyService

router = APIRouter()

@router.post("")
async def create_item(payload: MyItemCreate, db: AsyncSession = Depends(get_db)):
    return await MyService.create_item(db, **payload.dict())
```

3. Register routes: `app/api/routes.py`
```python
from app.api.v1 import my_items
router.include_router(my_items.router, prefix="/my-items", tags=["my-items"])
```

### Add a New Frontend Component

1. Create component: `components/my-component.tsx`
```tsx
"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

export function MyComponent() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-data"],
    queryFn: fetchMyData,
  });

  return <div>{/* JSX */}</div>;
}
```

2. Use in page:
```tsx
import { MyComponent } from "@/components/my-component";

export default function MyPage() {
  return <MyComponent />;
}
```

---

## 🧪 Testing

### Backend Integration Test
```python
async def test_create_application(db: AsyncSession, test_project: Project):
    app = await ApplicationService.create_application(
        db=db,
        organization_id=test_org.id,
        workspace_id=test_workspace.id,
        project_id=test_project.id,
        name="Test App",
        application_type=ApplicationType.WEB,
    )
    assert app.name == "Test App"
```

### Frontend E2E Test
```typescript
test("should create project", async ({ page }) => {
  await page.goto(`${BASE_URL}/projects`);
  await page.click("button:has-text('New Project')");
  await page.fill('input[placeholder="e.g., E-Commerce Platform"]', "Test");
  await page.click("button:has-text('Create Project')");
  await page.waitForURL(/\/projects\/[a-f0-9-]+/);
});
```

---

## 📊 Database Schema

### Key Tables

**projects** (existing, extended)
- `id` (UUID, PK)
- `organization_id`, `workspace_id` (FK, tenant)
- `name`, `key`, `description`
- `status`, `tags`, `owner_id`

**applications** (NEW)
- `id` (UUID, PK)
- `project_id` (FK → projects)
- `organization_id`, `workspace_id` (FK, tenant)
- `name`, `description`
- `application_type` (enum: WEB, MOBILE_WEB, ANDROID, IOS, HYBRID)
- `repository_url`, `metadata_` (JSON)

**environments** (NEW)
- `id` (UUID, PK)
- `project_id`, `application_id` (FK)
- `organization_id`, `workspace_id` (FK, tenant)
- `name`, `base_url`
- `environment_type` (enum: dev, qa, uat, staging, prod, custom)
- `environment_variables` (JSONB array)
- `health_check_enabled`, `health_check_url`

---

## 🔐 Permission Levels

| Action | org_owner | admin | qa_lead | others |
|--------|-----------|-------|---------|--------|
| create | ✅ | ✅ | ✅ | ❌ |
| read | ✅ | ✅ | ✅ | ✅ |
| update | ✅ | ✅ | ✅ | ❌ |
| delete | ✅ | ✅ | ❌ | ❌ |

---

## 🐛 Debugging Tips

### Backend
```bash
# Enable SQL logging
export SQLALCHEMY_ECHO=1
uvicorn app.main:app --reload

# Check migrations
alembic current
alembic history

# Reset database
rm app.db  # SQLite
# or run downgrade for PostgreSQL
alembic downgrade base
```

### Frontend
```bash
# Check API calls
# Open DevTools → Network tab

# Enable React Query DevTools
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

# Check component state
console.log(data, isLoading, error);
```

---

## 📝 Naming Conventions

### Backend
- **Models:** PascalCase (e.g., `Application`, `Environment`)
- **Services:** PascalCase + Service (e.g., `ApplicationService`)
- **Routes:** snake_case prefix (e.g., `/applications`)
- **Functions:** async_verb_noun (e.g., `create_application`)

### Frontend
- **Components:** PascalCase (e.g., `ProjectsList`)
- **Pages:** kebab-case file names (e.g., `[projectId]`)
- **Hooks:** useVerb (e.g., `useProject`)
- **Interfaces:** PascalCase (e.g., `ProjectProps`)

---

## 🔗 API Response Format

### List Response
```json
{
  "items": [...],
  "total": 50,
  "skip": 0,
  "limit": 10
}
```

### Single Resource Response
```json
{
  "id": "uuid",
  "name": "...",
  "created_at": "2025-06-24T..."
}
```

### Error Response
```json
{
  "detail": "Error message"
}
```

---

## 📚 Documentation

- **API Docs:** [PHASE1_API_DOCS.md](./PHASE1_API_DOCS.md)
- **Completion Summary:** [PHASE1_COMPLETION_SUMMARY.md](./PHASE1_COMPLETION_SUMMARY.md)
- **Backend README:** [backend/README.md](./backend/README.md)
- **Frontend README:** [frontend/apps/web/README.md](./frontend/apps/web/README.md)

---

## ⚡ Next Steps

After Phase 1 is tested and validated:

1. **Phase 2:** Requirement Editor & Import UI
2. **Phase 3:** Test Case Generation & Automation
3. **Phase 4:** Test Execution & Reporting
4. **Phase 5:** AI-Powered Insights & Self-Healing

---

## 🆘 Common Issues & Solutions

### Issue: Migration fails
```bash
# Solution: Check migration history
alembic history

# Downgrade and try again
alembic downgrade 001_initial
alembic upgrade 002_application_environment
```

### Issue: API returns 403 Forbidden
```bash
# Check permissions in permission_service.py
# Ensure user role has required action for resource
```

### Issue: React Query not fetching data
```bash
# Check:
# 1. API URL is correct (NEXT_PUBLIC_API_URL)
# 2. Auth token is in localStorage
# 3. Backend CORS is configured correctly
```

### Issue: Typescript errors in components
```bash
# Solutions:
# 1. Ensure "use client" directive for client components
# 2. Import types from correct locations
# 3. Run: npm run lint
```

---

**Happy coding! 🚀**
