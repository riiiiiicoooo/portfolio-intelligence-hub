"""RBAC and tenant isolation for Portfolio Intelligence Hub.

Provides:
- Role definitions (Admin, Property Manager, Broker, Finance, Executive)
- Permission checks for data access
- Column masking for sensitive fields
- Tenant filtering for multi-tenant deployments
- Audit logging for compliance

PM Context: Real estate platforms must enforce strict access controls. A property
manager should only see their assigned properties. Finance teams should see detailed
financials. Brokers should see available units and renewal pipeline. This module
enforces those guardrails consistently across SQL queries and document searches.
"""

from .rbac import Role, Permission, get_user_properties, get_user_role, can_access, get_column_mask, build_tenant_filter
from .snowflake_views import generate_view_ddl, get_view_name

__all__ = [
    'Role',
    'Permission',
    'get_user_properties',
    'get_user_role',
    'can_access',
    'get_column_mask',
    'build_tenant_filter',
    'generate_view_ddl',
    'get_view_name',
]
