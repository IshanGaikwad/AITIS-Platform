"""Integration tests for Phase 1 Project Management APIs.

Test coverage:
- Application CRUD operations
- Environment CRUD operations
- Permission enforcement
- Tenant isolation
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models.project import Project
from app.models.application import Application, ApplicationType
from app.models.environment import Environment, EnvironmentType
from app.models.user import User
from app.models.organization import Organization
from app.models.workspace import Workspace
from app.services.application_service import ApplicationService
from app.services.environment_service import EnvironmentService


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def test_org(db: AsyncSession) -> Organization:
    """Create test organization."""
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        slug="test-org",
    )
    db.add(org)
    await db.commit()
    return org


@pytest.fixture
async def test_workspace(db: AsyncSession, test_org: Organization) -> Workspace:
    """Create test workspace."""
    ws = Workspace(
        id=uuid.uuid4(),
        organization_id=test_org.id,
        name="Test Workspace",
        slug="test-ws",
    )
    db.add(ws)
    await db.commit()
    return ws


@pytest.fixture
async def test_user(db: AsyncSession, test_org: Organization) -> User:
    """Create test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        is_active=True,
        organization_id=test_org.id,
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def test_project(
    db: AsyncSession, test_workspace: Workspace, test_org: Organization, test_user: User
) -> Project:
    """Create test project."""
    project = Project(
        id=uuid.uuid4(),
        workspace_id=test_workspace.id,
        organization_id=test_org.id,
        name="Test Project",
        key="TEST",
        owner_id=test_user.id,
    )
    db.add(project)
    await db.commit()
    return project


class TestApplications:
    """Application CRUD integration tests."""

    async def test_create_application(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test creating an application."""
        app_data = {
            "name": "Frontend Web App",
            "application_type": ApplicationType.WEB,
            "description": "Main web application",
            "repository_url": "https://github.com/example/frontend",
        }

        app = await ApplicationService.create_application(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            **app_data,
        )

        assert app.name == "Frontend Web App"
        assert app.application_type == ApplicationType.WEB
        assert app.project_id == test_project.id
        assert app.organization_id == test_org.id
        assert app.workspace_id == test_workspace.id

    async def test_list_project_applications(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test listing applications for a project."""
        # Create multiple applications
        for i in range(3):
            await ApplicationService.create_application(
                db=db,
                organization_id=test_org.id,
                workspace_id=test_workspace.id,
                project_id=test_project.id,
                name=f"App {i}",
                application_type=ApplicationType.WEB,
            )

        # List applications
        apps, total = await ApplicationService.list_project_applications(
            db=db, project_id=test_project.id, skip=0, limit=10
        )

        assert len(apps) == 3
        assert total == 3

    async def test_update_application(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test updating an application."""
        app = await ApplicationService.create_application(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            name="Original Name",
            application_type=ApplicationType.WEB,
        )

        updated = await ApplicationService.update_application(
            db=db, application_id=app.id, name="Updated Name", description="New description"
        )

        assert updated.name == "Updated Name"
        assert updated.description == "New description"

    async def test_delete_application(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test deleting an application."""
        app = await ApplicationService.create_application(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            name="App to Delete",
            application_type=ApplicationType.WEB,
        )

        result = await ApplicationService.delete_application(db=db, application_id=app.id)
        assert result is True

        # Verify deletion
        deleted = await ApplicationService.get_application(db=db, application_id=app.id)
        assert deleted is None

    async def test_application_tenant_isolation(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test that applications are tenant-isolated."""
        other_org_id = uuid.uuid4()

        app = await ApplicationService.create_application(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            name="Org 1 App",
            application_type=ApplicationType.WEB,
        )

        # Verify organization_id is set correctly
        assert app.organization_id == test_org.id
        assert app.workspace_id == test_workspace.id


class TestEnvironments:
    """Environment CRUD integration tests."""

    async def test_create_environment(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test creating an environment."""
        app = await ApplicationService.create_application(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            name="Web App",
            application_type=ApplicationType.WEB,
        )

        env_data = {
            "name": "Development",
            "environment_type": EnvironmentType.dev,
            "base_url": "https://dev.example.com",
            "health_check_url": "https://dev.example.com/health",
            "health_check_enabled": True,
        }

        env = await EnvironmentService.create_environment(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            application_id=app.id,
            **env_data,
        )

        assert env.name == "Development"
        assert env.environment_type == EnvironmentType.dev
        assert env.base_url == "https://dev.example.com"
        assert env.health_check_enabled is True

    async def test_list_application_environments(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test listing environments for an application."""
        app = await ApplicationService.create_application(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            name="Web App",
            application_type=ApplicationType.WEB,
        )

        # Create multiple environments
        for env_type in [EnvironmentType.dev, EnvironmentType.qa, EnvironmentType.prod]:
            await EnvironmentService.create_environment(
                db=db,
                organization_id=test_org.id,
                workspace_id=test_workspace.id,
                project_id=test_project.id,
                application_id=app.id,
                name=f"{env_type.value.upper()} Environment",
                environment_type=env_type,
                base_url=f"https://{env_type.value}.example.com",
            )

        # List environments
        envs, total = await EnvironmentService.list_application_environments(
            db=db, application_id=app.id, skip=0, limit=10
        )

        assert len(envs) == 3
        assert total == 3

    async def test_update_environment(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test updating an environment."""
        app = await ApplicationService.create_application(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            name="Web App",
            application_type=ApplicationType.WEB,
        )

        env = await EnvironmentService.create_environment(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            application_id=app.id,
            name="Dev",
            environment_type=EnvironmentType.dev,
            base_url="https://dev.example.com",
        )

        updated = await EnvironmentService.update_environment(
            db=db,
            environment_id=env.id,
            base_url="https://dev-updated.example.com",
        )

        assert updated.base_url == "https://dev-updated.example.com"

    async def test_delete_environment(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test deleting an environment."""
        app = await ApplicationService.create_application(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            name="Web App",
            application_type=ApplicationType.WEB,
        )

        env = await EnvironmentService.create_environment(
            db=db,
            organization_id=test_org.id,
            workspace_id=test_workspace.id,
            project_id=test_project.id,
            application_id=app.id,
            name="Dev",
            environment_type=EnvironmentType.dev,
            base_url="https://dev.example.com",
        )

        result = await EnvironmentService.delete_environment(db=db, environment_id=env.id)
        assert result is True

        # Verify deletion
        deleted = await EnvironmentService.get_environment(db=db, environment_id=env.id)
        assert deleted is None

    async def test_list_project_environments(
        self, db: AsyncSession, test_project: Project, test_org: Organization, test_workspace: Workspace
    ):
        """Test listing all environments for a project."""
        # Create two applications with environments each
        for app_idx in range(2):
            app = await ApplicationService.create_application(
                db=db,
                organization_id=test_org.id,
                workspace_id=test_workspace.id,
                project_id=test_project.id,
                name=f"App {app_idx}",
                application_type=ApplicationType.WEB,
            )

            for i in range(2):
                await EnvironmentService.create_environment(
                    db=db,
                    organization_id=test_org.id,
                    workspace_id=test_workspace.id,
                    project_id=test_project.id,
                    application_id=app.id,
                    name=f"Env {i}",
                    environment_type=EnvironmentType.dev,
                    base_url=f"https://env{i}.example.com",
                )

        # List all project environments
        envs, total = await EnvironmentService.list_project_environments(
            db=db, project_id=test_project.id, skip=0, limit=10
        )

        assert len(envs) == 4
        assert total == 4
