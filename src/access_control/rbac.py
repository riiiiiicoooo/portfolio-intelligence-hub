"""Role-Based Access Control (RBAC) implementation.

Defines user roles, permissions, and access control rules for Portfolio Intelligence Hub.

PM Context: Real estate platforms must enforce strict access controls:
- Property Managers: See assigned properties only
- Brokers: See available units and leases
- Finance teams: See detailed financials
- Executives: See portfolio-level KPIs
- Admins: Full access

This module enforces those rules consistently across SQL queries and document searches.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Set, Optional, Tuple

logger = logging.getLogger(__name__)


class Role(Enum):
    """User roles in the system.
    
    ADMIN: Full access to all data and functions
    PROPERTY_MANAGER: See assigned properties, can't modify financials
    BROKER: See leases and available units, limited financial visibility
    FINANCE: See all properties' financial data, can't see PII
    EXECUTIVE: See portfolio-level aggregated KPIs only
    """
    ADMIN = "admin"
    PROPERTY_MANAGER = "property_manager"
    BROKER = "broker"
    FINANCE = "finance"
    EXECUTIVE = "executive"


@dataclass
class Permission:
    """A single permission granted to a role.
    
    Attributes:
        role: Role enum
        resource_type: Resource being accessed (table name or document type)
        actions: List of actions allowed (read, write, update, delete)
        property_scope: Which properties can be accessed (all, assigned, none)
        column_mask: Columns to hide from this role (if any)
    """
    role: Role
    resource_type: str
    actions: List[str]
    property_scope: str  # 'all', 'assigned', 'none'
    column_mask: List[str] = field(default_factory=list)


# Master permission matrix
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    
    Role.ADMIN: [
        Permission(Role.ADMIN, "properties", ["read", "write", "update", "delete"], "all"),
        Permission(Role.ADMIN, "units", ["read", "write", "update", "delete"], "all"),
        Permission(Role.ADMIN, "leases", ["read", "write", "update", "delete"], "all"),
        Permission(Role.ADMIN, "financials", ["read", "write", "update", "delete"], "all"),
        Permission(Role.ADMIN, "rent_collections", ["read", "write", "update", "delete"], "all"),
        Permission(Role.ADMIN, "work_orders", ["read", "write", "update", "delete"], "all"),
        Permission(Role.ADMIN, "users", ["read", "write", "update", "delete"], "all"),
    ],
    
    Role.PROPERTY_MANAGER: [
        Permission(Role.PROPERTY_MANAGER, "properties", ["read"], "assigned"),
        Permission(Role.PROPERTY_MANAGER, "units", ["read"], "assigned"),
        Permission(Role.PROPERTY_MANAGER, "leases", ["read"], "assigned"),
        Permission(Role.PROPERTY_MANAGER, "rent_collections", ["read"], "assigned"),
        Permission(Role.PROPERTY_MANAGER, "work_orders", ["read", "write"], "assigned"),
        Permission(Role.PROPERTY_MANAGER, "financials", ["read"], "assigned", 
                   column_mask=["cost_basis", "acquisition_price"]),  # Hide purchase info
    ],
    
    Role.BROKER: [
        Permission(Role.BROKER, "properties", ["read"], "all"),
        Permission(Role.BROKER, "units", ["read"], "all", 
                   column_mask=["current_rent"]),  # Hide rent info
        Permission(Role.BROKER, "leases", ["read"], "all", 
                   column_mask=["tenant_name", "monthly_rent"]),  # Hide PII
        Permission(Role.BROKER, "work_orders", ["read"], "all"),
        # No financials access for brokers
    ],
    
    Role.FINANCE: [
        Permission(Role.FINANCE, "properties", ["read"], "all"),
        Permission(Role.FINANCE, "units", ["read"], "all"),
        Permission(Role.FINANCE, "leases", ["read"], "all",
                   column_mask=["tenant_name"]),  # Hide tenant PII
        Permission(Role.FINANCE, "financials", ["read", "write"], "all"),
        Permission(Role.FINANCE, "rent_collections", ["read"], "all"),
        Permission(Role.FINANCE, "work_orders", ["read"], "all"),
        Permission(Role.FINANCE, "budgets", ["read", "write"], "all"),
    ],
    
    Role.EXECUTIVE: [
        # Executives only see aggregated portfolio metrics
        Permission(Role.EXECUTIVE, "portfolio_summary", ["read"], "all"),
        Permission(Role.EXECUTIVE, "kpi_dashboard", ["read"], "all"),
        # Cannot drill into individual properties or documents
    ],
}


def get_user_role(user_id: str) -> Optional[Role]:
    """Look up user's role from database.
    
    Args:
        user_id: User ID
    
    Returns:
        Role enum or None if user not found
    
    Note:
        In reference implementation, returns mock data.
        Production would query user database.
    
    Example:
        >>> role = get_user_role("pm_john_123")
        >>> if role == Role.PROPERTY_MANAGER:
        ...     print("User is a property manager")
    """
    # In production: SELECT role FROM users WHERE user_id = ?
    mock_roles = {
        "pm_john_123": Role.PROPERTY_MANAGER,
        "broker_jane_456": Role.BROKER,
        "finance_bob_789": Role.FINANCE,
        "exec_alice_000": Role.EXECUTIVE,
        "admin_root": Role.ADMIN,
    }
    return mock_roles.get(user_id)


def get_user_properties(user_id: str) -> List[str]:
    """Get list of properties assigned to user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of property IDs (empty if user has access to all properties)
    
    Note:
        If empty list is returned, interpret as "all properties".
        Non-empty list means only those properties.
    
    Example:
        >>> props = get_user_properties("pm_john_123")
        >>> print(f"Manages: {props}")  # ['PROP_001', 'PROP_002']
    """
    # In production: SELECT assigned_properties FROM users WHERE user_id = ?
    mock_assignments = {
        "pm_john_123": ["PROP_001", "PROP_002"],
        "pm_jane_456": ["PROP_003", "PROP_004", "PROP_005"],
        "broker_jane_456": [],  # Brokers see all
        "finance_bob_789": [],  # Finance sees all
        "exec_alice_000": [],  # Execs see all
    }
    return mock_assignments.get(user_id, [])


def can_access(user_id: str, resource: str, action: str) -> bool:
    """Check if user can perform action on resource.
    
    Args:
        user_id: User ID
        resource: Resource name (table name or document type)
        action: Action (read, write, update, delete)
    
    Returns:
        True if action is allowed, False otherwise
    
    Example:
        >>> if can_access("pm_john_123", "financials", "write"):
        ...     update_financials()
        >>> else:
        ...     raise PermissionError()
    """
    role = get_user_role(user_id)
    if not role:
        logger.warning(f"User {user_id} not found")
        return False
    
    # Admins can always access
    if role == Role.ADMIN:
        return True
    
    # Check permissions for this role
    permissions = ROLE_PERMISSIONS.get(role, [])
    
    for perm in permissions:
        if perm.resource_type == resource and action in perm.actions:
            return True
    
    logger.warning(f"User {user_id} ({role.value}) cannot {action} {resource}")
    return False


def get_column_mask(role: Role, table: str) -> List[str]:
    """Get list of columns this role cannot see.
    
    Args:
        role: User's role
        table: Table/resource name
    
    Returns:
        List of column names to hide from this role
    
    Example:
        >>> masked_cols = get_column_mask(Role.BROKER, "leases")
        >>> print(masked_cols)  # ['tenant_name', 'monthly_rent']
        >>> # Query should exclude these columns for brokers
    """
    permissions = ROLE_PERMISSIONS.get(role, [])
    
    for perm in permissions:
        if perm.resource_type == table:
            return perm.column_mask
    
    return []


def build_tenant_filter(user_context: 'UserContext') -> str:
    """Build SQL WHERE clause for tenant isolation.
    
    Args:
        user_context: UserContext with tenant and property info
    
    Returns:
        SQL WHERE clause fragment (without leading WHERE)
    
    Example:
        >>> ctx = UserContext("user1", "tenant1", "pm", ["p1", "p2"])
        >>> filter_sql = build_tenant_filter(ctx)
        >>> print(filter_sql)
        # tenant_id = 'tenant1' AND property_id IN ('p1', 'p2')
    """
    filters = [f"tenant_id = '{user_context.tenant_id}'"]
    
    if user_context.assigned_properties:
        props = "', '".join(user_context.assigned_properties)
        filters.append(f"property_id IN ('{props}')")
    
    return " AND ".join(filters)


def filter_columns(
    columns: List[str],
    role: Role,
    table: str
) -> List[str]:
    """Filter list of columns to hide masked columns.
    
    Args:
        columns: Original column list
        role: User's role
        table: Table being queried
    
    Returns:
        Filtered column list (masked columns removed)
    
    Example:
        >>> cols = ["tenant_name", "monthly_rent", "lease_id"]
        >>> masked_cols = filter_columns(cols, Role.BROKER, "leases")
        >>> print(masked_cols)  # ['lease_id']
    """
    masked = get_column_mask(role, table)
    return [c for c in columns if c not in masked]


def audit_log(user_id: str, action: str, resource: str, details: str = "") -> None:
    """Log access for compliance audit trail.
    
    Args:
        user_id: User performing action
        action: Action taken (read, write, export, etc.)
        resource: Resource accessed (table, document, report, etc.)
        details: Additional details
    
    Note:
        In production, would INSERT into audit_log table.
        Stored permanently for compliance investigations.
    """
    role = get_user_role(user_id)
    logger.info(f"AUDIT: {user_id} ({role.value if role else 'UNKNOWN'}) {action} {resource} | {details}")
    
    # In production:
    # INSERT INTO audit_log (user_id, role, action, resource, details, timestamp)
    # VALUES (?, ?, ?, ?, ?, NOW())
