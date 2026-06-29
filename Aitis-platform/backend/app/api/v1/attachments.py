"""Attachment management API routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.services import AttachmentService, PermissionService
from app.core.security import get_current_user
from app.db.database import get_db

router = APIRouter(prefix="/attachments", tags=["attachments"])


# ── Schemas ──────────────────────────────────────────────────────
class AttachmentOut(BaseModel):
    """Attachment response."""
    id: UUID
    original_filename: str
    file_size: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ── Routes ───────────────────────────────────────────────────────

@router.post("/requirements/{requirement_id}/upload", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    requirement_id: UUID,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file attachment to a requirement."""
    # Check permissions (user can read/update requirements)
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "requirements",
        "update",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=requirement_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to add attachments to this requirement")

    # Read file content
    file_content = await file.read()

    # Validate file
    is_valid, error_msg = AttachmentService.validate_file(file_content, file.filename or "file")
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Upload
    artifact = await AttachmentService.upload_attachment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        requirement_id=requirement_id,
        file_content=file_content,
        original_filename=file.filename or "file",
        uploaded_by_user_id=current_user.id,
    )

    if not artifact:
        raise HTTPException(status_code=500, detail="Failed to upload file")

    return artifact


@router.get("/requirements/{requirement_id}/attachments", response_model=list[AttachmentOut])
async def list_requirement_attachments(
    requirement_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all attachments for a requirement."""
    # Check permissions
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "requirements",
        "read",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=requirement_id,
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to view this requirement")

    attachments = await AttachmentService.list_requirement_attachments(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        requirement_id=requirement_id,
    )

    return [AttachmentOut.from_orm(a).model_dump() for a in attachments]


@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download an attachment file."""
    # Get attachment to check permission
    artifact = await AttachmentService.get_attachment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        attachment_id=attachment_id,
    )

    if not artifact:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Check permissions to the requirement
    requirement_id = artifact.metadata_.get("requirement_id")
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "requirements",
        "read",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=UUID(requirement_id),
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to download this attachment")

    # Download
    result = await AttachmentService.download_attachment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        attachment_id=attachment_id,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to download file")

    content, filename = result
    from fastapi.responses import FileResponse
    return FileResponse(
        content=content,
        media_type="application/octet-stream",
        filename=filename,
    )


@router.delete("/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an attachment."""
    # Get attachment first
    artifact = await AttachmentService.get_attachment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        attachment_id=attachment_id,
    )

    if not artifact:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Check permissions to the requirement
    requirement_id = artifact.metadata_.get("requirement_id")
    has_perm = await PermissionService.check_permission(
        db,
        current_user.id,
        "requirements",
        "update",
        current_user.organization_id,
        current_user.workspace_id,
        resource_id=UUID(requirement_id),
    )
    if not has_perm:
        raise HTTPException(status_code=403, detail="No permission to delete this attachment")

    await AttachmentService.delete_attachment(
        db,
        organization_id=current_user.organization_id,
        workspace_id=current_user.workspace_id,
        attachment_id=attachment_id,
    )
