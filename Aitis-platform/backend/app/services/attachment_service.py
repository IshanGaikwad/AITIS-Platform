"""Attachment service for file uploads to requirements."""

import os
import uuid
import re
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExecutionArtifact


class AttachmentService:
    """File upload and storage management for attachments."""

    # Configuration
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'zip', 
        'csv', 'xlsx', 'json', 'xml', 'log'
    }
    UPLOAD_DIRECTORY = "uploads/attachments"

    @staticmethod
    def _make_safe_filename(original_name: str) -> str:
        """Sanitize filename to prevent directory traversal and invalid characters."""
        # Remove path separators and null bytes
        safe_name = original_name.replace('/', '_').replace('\\', '_').replace('\0', '')
        # Remove special characters except dots, hyphens, underscores
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', safe_name)
        # Limit to 255 chars (filesystem limit)
        if len(safe_name) > 255:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:252 - len(ext)] + ext
        return safe_name

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Extract and validate file extension."""
        _, ext = os.path.splitext(filename)
        ext = ext.lstrip('.').lower()
        return ext

    @staticmethod
    def validate_file(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate file size and type."""
        # Check size
        if len(file_content) > AttachmentService.MAX_FILE_SIZE:
            return False, f"File exceeds maximum size of {AttachmentService.MAX_FILE_SIZE / 1024 / 1024:.0f} MB"

        # Check extension
        ext = AttachmentService._get_file_extension(filename)
        if ext not in AttachmentService.ALLOWED_EXTENSIONS:
            return False, f"File type '.{ext}' not allowed. Allowed types: {', '.join(sorted(AttachmentService.ALLOWED_EXTENSIONS))}"

        return True, None

    @staticmethod
    async def upload_attachment(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        requirement_id: UUID,
        file_content: bytes,
        original_filename: str,
        uploaded_by_user_id: UUID,
    ) -> Optional[ExecutionArtifact]:
        """
        Upload and store a file attachment.
        
        Returns ExecutionArtifact record (repurposed for requirement attachments).
        """
        # Validate
        is_valid, error_msg = AttachmentService.validate_file(file_content, original_filename)
        if not is_valid:
            return None

        # Create upload directory if needed
        upload_dir = Path(AttachmentService.UPLOAD_DIRECTORY)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate safe filename
        safe_name = AttachmentService._make_safe_filename(original_filename)
        # Add UUID prefix to guarantee uniqueness
        unique_filename = f"{uuid.uuid4()}_{safe_name}"
        file_path = upload_dir / unique_filename

        # Write file
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            return None

        # Create artifact record (using ExecutionArtifact model to store attachment metadata)
        # Type 'requirement_attachment' marks it as a requirement attachment
        artifact = ExecutionArtifact(
            organization_id=organization_id,
            project_id=project_id,
            artifact_type="requirement_attachment",
            storage_key=str(file_path),
            size_bytes=len(file_content),
            name=original_filename,
            metadata_={
                "requirement_id": str(requirement_id),
                "uploaded_by": str(uploaded_by_user_id),
                "uploaded_at": datetime.utcnow().isoformat(),
            }
        )
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)
        return artifact

    @staticmethod
    async def get_attachment(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        attachment_id: UUID,
    ) -> Optional[ExecutionArtifact]:
        """Retrieve attachment metadata."""
        result = await db.execute(
            select(ExecutionArtifact).where(
                and_(
                    ExecutionArtifact.id == attachment_id,
                    ExecutionArtifact.organization_id == organization_id,
                    ExecutionArtifact.project_id == project_id,
                    ExecutionArtifact.artifact_type == "requirement_attachment",
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_requirement_attachments(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        requirement_id: UUID,
    ) -> list[ExecutionArtifact]:
        """List all attachments for a requirement."""
        result = await db.execute(
            select(ExecutionArtifact).where(
                and_(
                    ExecutionArtifact.organization_id == organization_id,
                    ExecutionArtifact.project_id == project_id,
                    ExecutionArtifact.artifact_type == "requirement_attachment",
                    ExecutionArtifact.metadata_["requirement_id"].as_string() == str(requirement_id),
                )
            )
        )
        return result.scalars().all()

    @staticmethod
    async def download_attachment(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        attachment_id: UUID,
    ) -> Optional[Tuple[bytes, str]]:
        """
        Retrieve file content and original filename for download.
        Returns (file_content, original_filename) or None if not found.
        """
        artifact = await AttachmentService.get_attachment(
            db, organization_id, project_id, attachment_id
        )
        if not artifact:
            return None

        # Read file from disk
        try:
            with open(artifact.storage_key, 'rb') as f:
                content = f.read()
            return content, artifact.name
        except Exception:
            return None

    @staticmethod
    async def delete_attachment(
        db: AsyncSession,
        organization_id: UUID,
        project_id: UUID,
        attachment_id: UUID,
    ) -> bool:
        """Delete an attachment (file and record)."""
        artifact = await AttachmentService.get_attachment(
            db, organization_id, project_id, attachment_id
        )
        if not artifact:
            return False

        # Delete file from disk
        try:
            Path(artifact.storage_key).unlink(missing_ok=True)
        except Exception:
            pass

        # Delete record
        await db.delete(artifact)
        await db.commit()
        return True
