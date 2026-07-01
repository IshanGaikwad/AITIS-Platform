"""Application management service for deployment targets."""

from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, Workspace, ApplicationType


class ApplicationService:
    """CRUD and business logic for Applications."""

    @staticmethod
    async def create_application(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        workspace_id: UUID,
        name: str,
        application_type: ApplicationType,
        description: Optional[str] = None,
        repository_url: Optional[str] = None,
        metadata_: Optional[dict] = None,
    ) -> Application:
        """Create a new application."""
        app = Application(
            organization_id=organization_id,
            project_id=project_id,
            workspace_id=workspace_id,
            name=name,
            application_type=application_type,
            description=description,
            repository_url=repository_url,
            metadata_=metadata_ or {},
        )
        db.add(app)
        await db.commit()
        await db.refresh(app)
        return app

    @staticmethod
    async def get_application(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        application_id: UUID,
    ) -> Optional[Application]:
        """Get application by ID with tenant scoping."""
        result = await db.execute(
            select(Application).where(
                and_(
                    Application.id == application_id,
                    Application.organization_id == organization_id,
                    Application.project_id == project_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_workspace_applications(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Application], int]:
        """List all applications in a workspace with pagination."""
        stmt = select(Application).where(
            and_(
                Application.organization_id == organization_id,
                Application.project_id == project_id,
                Application.workspace_id == workspace_id,
            )
        )
        
        total_result = await db.execute(stmt)
        total = len(total_result.all())
        
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all(), total

    @staticmethod
    async def update_application(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        application_id: UUID,
        name: Optional[str] = None,
        application_type: Optional[ApplicationType] = None,
        description: Optional[str] = None,
        repository_url: Optional[str] = None,
        metadata_: Optional[dict] = None,
    ) -> Optional[Application]:
        """Update application fields."""
        app = await ApplicationService.get_application(
            db, organization_id, project_id, application_id
        )
        if not app:
            return None

        if name is not None:
            app.name = name
        if application_type is not None:
            app.application_type = application_type
        if description is not None:
            app.description = description
        if repository_url is not None:
            app.repository_url = repository_url
        if metadata_ is not None:
            app.metadata_ = metadata_

        await db.commit()
        await db.refresh(app)
        return app

    @staticmethod
    async def delete_application(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        application_id: UUID,
    ) -> bool:
        """Delete an application (soft delete via archive or hard delete)."""
        app = await ApplicationService.get_application(
            db, organization_id, project_id, application_id
        )
        if not app:
            return False

        await db.delete(app)
        await db.commit()
        return True
