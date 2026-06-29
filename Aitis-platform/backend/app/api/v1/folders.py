"""Folders API — Hierarchical organization for test suites."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role
from app.db.database import get_db
from app.schemas.testcase import (
    TestSuiteFolderCreate, 
    TestSuiteFolderOut, 
    TestSuiteFolderUpdate
)
from app.services import manual_test_service

router = APIRouter()

@router.get("/tree", response_model=List[TestSuiteFolderOut])
async def get_folder_tree(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the hierarchical folder tree for a project."""
    return await manual_test_service.get_folder_tree(db, project_id)

@router.post("", response_model=TestSuiteFolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: TestSuiteFolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    if not payload.organization_id:
        payload.organization_id = current_user.get("organization_id")
    if not payload.workspace_id:
        payload.workspace_id = current_user.get("workspace_id")
    
    return await manual_test_service.create_folder(db, payload)

@router.get("/{folder_id}", response_model=TestSuiteFolderOut)
async def get_folder(
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    folder = await manual_test_service.get_folder(db, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder

@router.put("/{folder_id}", response_model=TestSuiteFolderOut)
async def update_folder(
    folder_id: uuid.UUID,
    payload: TestSuiteFolderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "qa_lead")),
):
    folder = await manual_test_service.update_folder(db, folder_id, payload)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder

@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("administrator", "org_owner")),
):
    success = await manual_test_service.delete_folder(db, folder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Folder not found")
    return None
