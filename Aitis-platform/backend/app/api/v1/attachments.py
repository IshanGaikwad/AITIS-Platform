"""Attachment management API routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.services import AttachmentService, PermissionService
from app.core.security import claim_uuid, get_current_user, require_project_access
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


def _attachment_to_out(artifact) -> dict:
    """Map an ExecutionArtifact ORM row → AttachmentOut-shaped dict.

    The ExecutionArtifact model stores the attachment as ``name`` / ``size_bytes``
    with datetime timestamps; the response schema exposes string timestamps.
    """
    return {
        "id": artifact.id,
        "original_filename": artifact.name,
        "file_size": artifact.size_bytes or 0,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else "",
        "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else "",
    }


# ── Routes ───────────────────────────────────────────────────────

@router.post("/requirements/{requirement_id}/upload", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    requirement_id: UUID,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file attachment to a requirement."""
    # User must be a project member with a write role
    await require_project_access(
        db, current_user, claim_uuid(current_user, "project_id"), ("administrator", "qa_lead")
    )

    # Read file content
    file_content = await file.read()

    # Validate file
    is_valid, error_msg = AttachmentService.validate_file(file_content, file.filename or "file")
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Upload
    artifact = await AttachmentService.upload_attachment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        requirement_id=requirement_id,
        file_content=file_content,
        original_filename=file.filename or "file",
        uploaded_by_user_id=claim_uuid(current_user, "user_id", "sub"),
    )

    if not artifact:
        raise HTTPException(status_code=500, detail="Failed to upload file")

    return _attachment_to_out(artifact)


@router.get("/requirements/{requirement_id}/attachments", response_model=list[AttachmentOut])
async def list_requirement_attachments(
    requirement_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all attachments for a requirement."""
    # User must be a member of the project
    await require_project_access(db, current_user, claim_uuid(current_user, "project_id"))

    attachments = await AttachmentService.list_requirement_attachments(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        requirement_id=requirement_id,
    )

    return [_attachment_to_out(a) for a in attachments]


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
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        attachment_id=attachment_id,
    )

    if not artifact:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Check permissions to the requirement
    requirement_id = (artifact.metadata_ or {}).get("requirement_id")
    if not requirement_id:
        raise HTTPException(status_code=422, detail="Attachment is missing requirement metadata")
    await require_project_access(db, current_user, claim_uuid(current_user, "project_id"))

    # Download
    result = await AttachmentService.download_attachment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        attachment_id=attachment_id,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to download file")

    content, filename = result
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        attachment_id=attachment_id,
    )

    if not artifact:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Check permissions to the requirement
    requirement_id = (artifact.metadata_ or {}).get("requirement_id")
    if not requirement_id:
        raise HTTPException(status_code=422, detail="Attachment is missing requirement metadata")
    await require_project_access(
        db, current_user, claim_uuid(current_user, "project_id"), ("administrator", "qa_lead")
    )

    await AttachmentService.delete_attachment(
        db,
        organization_id=claim_uuid(current_user, "organization_id", "org_id"),
        project_id=claim_uuid(current_user, "project_id"),
        attachment_id=attachment_id,
    )
