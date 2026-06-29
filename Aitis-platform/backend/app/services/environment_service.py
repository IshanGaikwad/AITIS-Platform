"""Environment management service for deployment environments."""

from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Environment, EnvironmentType


class EnvironmentService:
    """CRUD and business logic for Environments."""

    @staticmethod
    async def create_environment(
        db: AsyncSession,
        organization_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        application_id: UUID,
        name: str,
        environment_type: EnvironmentType,
        description: Optional[str] = None,
        base_url: Optional[str] = None,
        environment_variables: Optional[list] = None,
        health_check_url: Optional[str] = None,
        health_check_enabled: bool = False,
    ) -> Environment:
        """Create a new environment."""
        env = Environment(
            organization_id=organization_id,
            workspace_id=workspace_id,
            project_id=project_id,
            application_id=application_id,
            name=name,
            environment_type=environment_type,
            description=description,
            base_url=base_url,
            environment_variables=environment_variables or [],
            health_check_url=health_check_url,
            health_check_enabled=health_check_enabled,
        )
        db.add(env)
        await db.commit()
        await db.refresh(env)
        return env

    @staticmethod
    async def get_environment(
        db: AsyncSession,
        organization_id: UUID,
        workspace_id: UUID,
        environment_id: UUID,
    ) -> Optional[Environment]:
        """Get environment by ID with tenant scoping."""
        result = await db.execute(
            select(Environment).where(
                and_(
                    Environment.id == environment_id,
                    Environment.organization_id == organization_id,
                    Environment.workspace_id == workspace_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_application_environments(
        db: AsyncSession,
        organization_id: UUID,
        workspace_id: UUID,
        application_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Environment], int]:
        """List all environments for an application with pagination."""
        stmt = select(Environment).where(
            and_(
                Environment.organization_id == organization_id,
                Environment.workspace_id == workspace_id,
                Environment.application_id == application_id,
            )
        )
        
        total_result = await db.execute(stmt)
        total = len(total_result.all())
        
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all(), total

    @staticmethod
    async def list_project_environments(
        db: AsyncSession,
        organization_id: UUID,
        workspace_id: UUID,
        project_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Environment], int]:
        """List all environments in a project with pagination."""
        stmt = select(Environment).where(
            and_(
                Environment.organization_id == organization_id,
                Environment.workspace_id == workspace_id,
                Environment.project_id == project_id,
            )
        )
        
        total_result = await db.execute(stmt)
        total = len(total_result.all())
        
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all(), total

    @staticmethod
    async def update_environment(
        db: AsyncSession,
        organization_id: UUID,
        workspace_id: UUID,
        environment_id: UUID,
        name: Optional[str] = None,
        environment_type: Optional[EnvironmentType] = None,
        description: Optional[str] = None,
        base_url: Optional[str] = None,
        environment_variables: Optional[list] = None,
        health_check_url: Optional[str] = None,
        health_check_enabled: Optional[bool] = None,
    ) -> Optional[Environment]:
        """Update environment fields."""
        env = await EnvironmentService.get_environment(
            db, organization_id, workspace_id, environment_id
        )
        if not env:
            return None

        if name is not None:
            env.name = name
        if environment_type is not None:
            env.environment_type = environment_type
        if description is not None:
            env.description = description
        if base_url is not None:
            env.base_url = base_url
        if environment_variables is not None:
            env.environment_variables = environment_variables
        if health_check_url is not None:
            env.health_check_url = health_check_url
        if health_check_enabled is not None:
            env.health_check_enabled = health_check_enabled

        await db.commit()
        await db.refresh(env)
        return env

    @staticmethod
    async def delete_environment(
        db: AsyncSession,
        organization_id: UUID,
        workspace_id: UUID,
        environment_id: UUID,
    ) -> bool:
        """Delete an environment."""
        env = await EnvironmentService.get_environment(
            db, organization_id, workspace_id, environment_id
        )
        if not env:
            return False

        await db.delete(env)
        await db.commit()
        return True
