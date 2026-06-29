"""Compatibility exports for legacy organization model imports."""

from app.models.tenant import Organization, OrganizationMembership

__all__ = ["Organization", "OrganizationMembership"]

