"""Tests for role-based access control in Portfolio Intelligence Hub.

This module tests user roles, property assignments, column masking, and
audit logging for access control.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest


class Role:
    """Enumeration of user roles."""

    PROPERTY_MANAGER = "property_manager"
    BROKER = "broker"
    FINANCE = "finance"
    EXECUTIVE = "executive"
    ADMIN = "admin"


class AccessControlService:
    """Service for enforcing role-based access control."""

    def __init__(self, audit_logger: MagicMock = None):
        """Initialize AccessControlService.

        Args:
            audit_logger: Optional audit logger
        """
        self.audit_logger = audit_logger

    def can_view_property(
        self, user_role: str, assigned_properties: List[int], property_id: int
    ) -> bool:
        """Check if user can view a property.

        Args:
            user_role: User's role
            assigned_properties: List of assigned property IDs
            property_id: Property to check access for

        Returns:
            True if user can view property
        """
        if user_role == Role.ADMIN:
            return True

        if user_role == Role.PROPERTY_MANAGER:
            return property_id in assigned_properties

        if user_role == Role.FINANCE:
            return property_id in assigned_properties

        if user_role == Role.BROKER:
            return property_id in assigned_properties

        if user_role == Role.EXECUTIVE:
            # Executive sees aggregated data (filtering applied elsewhere)
            return True

        return False

    def can_access_financial_data(self, user_role: str) -> bool:
        """Check if user can access financial data.

        Args:
            user_role: User's role

        Returns:
            True if user can access financials
        """
        return user_role in [Role.FINANCE, Role.EXECUTIVE, Role.ADMIN]

    def can_access_leasing_data(self, user_role: str) -> bool:
        """Check if user can access leasing data.

        Args:
            user_role: User's role

        Returns:
            True if user can access leasing
        """
        return user_role in [Role.BROKER, Role.PROPERTY_MANAGER, Role.ADMIN]

    def get_visible_columns(self, user_role: str) -> List[str]:
        """Get list of visible columns for user role.

        Args:
            user_role: User's role

        Returns:
            List of column names visible to user
        """
        all_columns = [
            "property_id",
            "property_name",
            "address",
            "valuation",
            "units",
            "noi",
            "employee_salary",
            "employee_benefits",
            "vendor_payment_details",
        ]

        if user_role == Role.ADMIN:
            return all_columns

        if user_role == Role.FINANCE:
            return [
                col
                for col in all_columns
                if col not in ["employee_salary", "employee_benefits"]
            ]

        if user_role == Role.PROPERTY_MANAGER:
            return [
                col
                for col in all_columns
                if col
                not in [
                    "employee_salary",
                    "employee_benefits",
                    "vendor_payment_details",
                ]
            ]

        if user_role == Role.BROKER:
            return [col for col in all_columns if col not in ["employee_salary"]]

        return ["property_id", "property_name", "address"]

    def build_tenant_filter(self, tenant_id: str) -> str:
        """Build WHERE clause for tenant filtering.

        Args:
            tenant_id: Tenant ID

        Returns:
            SQL WHERE clause fragment
        """
        return f"tenant_id = '{tenant_id}'"

    def build_property_filter(
        self, assigned_properties: List[int]
    ) -> str:
        """Build WHERE clause for property filtering.

        Args:
            assigned_properties: List of assigned property IDs

        Returns:
            SQL WHERE clause fragment
        """
        if not assigned_properties:
            return "1=1"

        props_str = ",".join(str(p) for p in assigned_properties)
        return f"property_id IN ({props_str})"

    def log_access(self, user_id: str, resource: str, allowed: bool) -> None:
        """Log resource access attempt.

        Args:
            user_id: User ID
            resource: Resource accessed
            allowed: Whether access was allowed
        """
        if self.audit_logger:
            self.audit_logger.log(
                {
                    "timestamp": datetime.now().isoformat(),
                    "user_id": user_id,
                    "resource": resource,
                    "allowed": allowed,
                }
            )

    def check_access(
        self,
        user_role: str,
        resource: str,
        assigned_properties: Optional[List[int]] = None,
    ) -> bool:
        """Check access to a resource.

        Args:
            user_role: User's role
            resource: Resource type
            assigned_properties: Optional list of assigned properties

        Returns:
            True if access is allowed
        """
        if user_role == Role.ADMIN:
            return True

        if resource == "financial_data":
            return self.can_access_financial_data(user_role)

        if resource == "leasing_data":
            return self.can_access_leasing_data(user_role)

        return True


# Test Fixtures
@pytest.fixture
def access_control_service() -> AccessControlService:
    """Create access control service."""
    return AccessControlService()


@pytest.fixture
def mock_audit_logger() -> MagicMock:
    """Mock audit logger."""
    logger = MagicMock()
    logger.log = MagicMock()
    return logger


@pytest.fixture
def access_control_with_audit(mock_audit_logger) -> AccessControlService:
    """Create access control service with audit logging."""
    return AccessControlService(audit_logger=mock_audit_logger)


# Property Manager Tests
class TestPropertyManagerAccess:
    """Tests for property manager access control."""

    def test_property_manager_sees_assigned_only(self, access_control_service):
        """Test that property managers only see assigned properties."""
        assigned = [101, 102, 103]

        # Can see assigned properties
        assert (
            access_control_service.can_view_property(
                Role.PROPERTY_MANAGER, assigned, 101
            )
            is True
        )
        assert (
            access_control_service.can_view_property(
                Role.PROPERTY_MANAGER, assigned, 102
            )
            is True
        )

        # Cannot see unassigned properties
        assert (
            access_control_service.can_view_property(
                Role.PROPERTY_MANAGER, assigned, 104
            )
            is False
        )

    def test_property_manager_column_visibility(self, access_control_service):
        """Test that property managers can't see sensitive columns."""
        columns = access_control_service.get_visible_columns(Role.PROPERTY_MANAGER)

        # Should not see these columns
        assert "employee_salary" not in columns
        assert "employee_benefits" not in columns
        assert "vendor_payment_details" not in columns

        # Should see these columns
        assert "property_id" in columns
        assert "property_name" in columns
        assert "noi" in columns


# Broker Tests
class TestBrokerAccess:
    """Tests for broker access control."""

    def test_broker_sees_leasing_data(self, access_control_service):
        """Test that brokers can access leasing data."""
        can_access = access_control_service.can_access_leasing_data(Role.BROKER)
        assert can_access is True

    def test_broker_cannot_see_financial_data(self, access_control_service):
        """Test that brokers cannot access financial data."""
        can_access = access_control_service.can_access_financial_data(Role.BROKER)
        assert can_access is False


# Finance Tests
class TestFinanceAccess:
    """Tests for finance user access control."""

    def test_finance_sees_all_financials(self, access_control_service):
        """Test that finance users see all financial data."""
        can_access = access_control_service.can_access_financial_data(Role.FINANCE)
        assert can_access is True

    def test_finance_cannot_see_employee_details(self, access_control_service):
        """Test that finance users cannot see employee salary data."""
        columns = access_control_service.get_visible_columns(Role.FINANCE)

        assert "employee_salary" not in columns
        assert "employee_benefits" not in columns

    def test_finance_sees_property_financials(self, access_control_service):
        """Test that finance users see property financial metrics."""
        columns = access_control_service.get_visible_columns(Role.FINANCE)

        assert "noi" in columns
        assert "valuation" in columns


# Executive Tests
class TestExecutiveAccess:
    """Tests for executive access control."""

    def test_executive_sees_aggregates(self, access_control_service):
        """Test that executives see portfolio summary data."""
        # Executives can access financial data
        can_access_fin = access_control_service.can_access_financial_data(Role.EXECUTIVE)
        assert can_access_fin is True

        # Executives can view properties
        can_view = access_control_service.can_view_property(Role.EXECUTIVE, [], 101)
        assert can_view is True


# Admin Tests
class TestAdminAccess:
    """Tests for admin access control."""

    def test_admin_full_access(self, access_control_service):
        """Test that admins have full access."""
        # Can view any property
        assert (
            access_control_service.can_view_property(Role.ADMIN, [], 101)
            is True
        )

        # Can access financial data
        assert (
            access_control_service.can_access_financial_data(Role.ADMIN) is True
        )

        # Can access leasing data
        assert (
            access_control_service.can_access_leasing_data(Role.ADMIN) is True
        )

        # Can see all columns
        columns = access_control_service.get_visible_columns(Role.ADMIN)
        assert len(columns) > 5


# Column Masking Tests
class TestColumnMasking:
    """Tests for column visibility control."""

    def test_column_masking(self, access_control_service):
        """Test that sensitive columns are masked."""
        pm_columns = access_control_service.get_visible_columns(Role.PROPERTY_MANAGER)
        finance_columns = access_control_service.get_visible_columns(Role.FINANCE)
        admin_columns = access_control_service.get_visible_columns(Role.ADMIN)

        # Admin sees more columns than finance
        assert len(admin_columns) > len(finance_columns)

        # Finance sees more columns than property manager
        assert len(finance_columns) >= len(pm_columns)

    @pytest.mark.parametrize(
        "role,has_salary",
        [
            (Role.ADMIN, True),
            (Role.FINANCE, False),
            (Role.PROPERTY_MANAGER, False),
        ],
    )
    def test_salary_visibility_by_role(
        self, access_control_service, role, has_salary
    ):
        """Parametrized test for salary column visibility by role."""
        columns = access_control_service.get_visible_columns(role)
        if has_salary:
            assert "employee_salary" in columns
        else:
            assert "employee_salary" not in columns


# Tenant Filter Tests
class TestTenantFiltering:
    """Tests for tenant-level filtering."""

    def test_build_tenant_filter(self, access_control_service):
        """Test building tenant filter clause."""
        filter_clause = access_control_service.build_tenant_filter("tenant_123")

        assert "tenant_id = 'tenant_123'" in filter_clause

    def test_build_property_filter(self, access_control_service):
        """Test building property filter clause."""
        assigned = [101, 102, 103]
        filter_clause = access_control_service.build_property_filter(assigned)

        assert "property_id IN (101,102,103)" in filter_clause

    def test_build_property_filter_empty(self, access_control_service):
        """Test building property filter with no assigned properties."""
        filter_clause = access_control_service.build_property_filter([])

        assert "1=1" in filter_clause


# Audit Logging Tests
class TestAuditLogging:
    """Tests for audit logging of access."""

    def test_audit_logging_allowed(self, access_control_with_audit, mock_audit_logger):
        """Test that allowed access is logged."""
        access_control_with_audit.log_access("user_123", "property_101", True)

        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args[0][0]

        assert call_args["user_id"] == "user_123"
        assert call_args["resource"] == "property_101"
        assert call_args["allowed"] is True

    def test_audit_logging_denied(self, access_control_with_audit, mock_audit_logger):
        """Test that denied access is logged."""
        access_control_with_audit.log_access("user_456", "property_999", False)

        mock_audit_logger.log.assert_called_once()
        call_args = mock_audit_logger.log.call_args[0][0]

        assert call_args["allowed"] is False


# Invalid Role Tests
class TestInvalidRole:
    """Tests for handling invalid roles."""

    def test_invalid_role_denied(self, access_control_service):
        """Test that invalid roles are denied access."""
        result = access_control_service.can_view_property(
            "invalid_role", [101, 102], 101
        )
        assert result is False

    def test_invalid_role_no_financial_access(self, access_control_service):
        """Test that invalid roles cannot access financial data."""
        result = access_control_service.can_access_financial_data("invalid_role")
        assert result is False


# Integration Tests
class TestRBACIntegration:
    """Integration tests for RBAC system."""

    def test_property_manager_workflow(
        self, access_control_service, mock_audit_logger
    ):
        """Test complete property manager workflow."""
        pm_assigned = [101, 102, 103]

        # Can view assigned property
        can_view_101 = access_control_service.can_view_property(
            Role.PROPERTY_MANAGER, pm_assigned, 101
        )
        assert can_view_101 is True

        # Cannot view unassigned property
        can_view_104 = access_control_service.can_view_property(
            Role.PROPERTY_MANAGER, pm_assigned, 104
        )
        assert can_view_104 is False

        # Can see leasing data
        can_see_leasing = access_control_service.can_access_leasing_data(
            Role.PROPERTY_MANAGER
        )
        assert can_see_leasing is True

        # Cannot see financial data
        can_see_fin = access_control_service.can_access_financial_data(
            Role.PROPERTY_MANAGER
        )
        assert can_see_fin is False

    def test_finance_workflow(self, access_control_service):
        """Test complete finance workflow."""
        finance_assigned = [101, 102, 103, 104, 105]

        # Can access financial data
        can_access = access_control_service.can_access_financial_data(Role.FINANCE)
        assert can_access is True

        # Can view assigned properties
        can_view = access_control_service.can_view_property(
            Role.FINANCE, finance_assigned, 104
        )
        assert can_view is True

        # Cannot see employee details
        columns = access_control_service.get_visible_columns(Role.FINANCE)
        assert "employee_salary" not in columns

    def test_multi_tenant_isolation(self, access_control_service):
        """Test isolation between multiple tenants."""
        tenant_a_filter = access_control_service.build_tenant_filter("tenant_a")
        tenant_b_filter = access_control_service.build_tenant_filter("tenant_b")

        assert tenant_a_filter != tenant_b_filter
        assert "tenant_a" in tenant_a_filter
        assert "tenant_b" in tenant_b_filter
