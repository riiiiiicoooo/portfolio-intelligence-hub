"""Role-specific Snowflake views for enforced access control.

This module generates DDL statements that create role-specific views in Snowflake.
Instead of checking permissions at query time, we can create views that enforce
restrictions at the database level.

PM Context: Snowflake supports role-based view definitions. We can create views
like "properties_for_property_managers" that automatically filter by assigned
properties, preventing even SQL injection from leaking data to unauthorized users.

These views are generated once during setup and can be updated when roles change.
"""

import logging
from enum import Enum
from typing import Dict

from .rbac import Role

logger = logging.getLogger(__name__)


def generate_view_ddl(role: Role) -> Dict[str, str]:
    """Generate SQL DDL for all role-specific views.
    
    Returns a dict mapping view names to CREATE VIEW statements.
    
    Args:
        role: User role to generate views for
    
    Returns:
        Dict of {view_name: sql_ddl_statement}
    
    Example:
        >>> views = generate_view_ddl(Role.PROPERTY_MANAGER)
        >>> for view_name, ddl in views.items():
        ...     print(f"Creating {view_name}...")
        ...     conn.execute(ddl)
    """
    
    if role == Role.ADMIN:
        # Admin sees everything, no views needed
        return {}
    
    elif role == Role.PROPERTY_MANAGER:
        return {
            "properties_for_pm": """
                CREATE OR REPLACE VIEW properties_for_pm AS
                SELECT *
                FROM properties
                WHERE property_id IN (
                    SELECT assigned_properties FROM users 
                    WHERE role = 'property_manager' 
                    AND user_id = CURRENT_USER()
                );
            """,
            
            "units_for_pm": """
                CREATE OR REPLACE VIEW units_for_pm AS
                SELECT u.*
                FROM units u
                JOIN properties p ON u.property_id = p.property_id
                WHERE p.property_id IN (
                    SELECT assigned_properties FROM users 
                    WHERE role = 'property_manager' 
                    AND user_id = CURRENT_USER()
                );
            """,
            
            "leases_for_pm": """
                CREATE OR REPLACE VIEW leases_for_pm AS
                SELECT l.*
                FROM leases l
                JOIN units u ON l.unit_id = u.unit_id
                JOIN properties p ON u.property_id = p.property_id
                WHERE p.property_id IN (
                    SELECT assigned_properties FROM users 
                    WHERE role = 'property_manager' 
                    AND user_id = CURRENT_USER()
                );
            """,
            
            "work_orders_for_pm": """
                CREATE OR REPLACE VIEW work_orders_for_pm AS
                SELECT wo.*
                FROM work_orders wo
                JOIN properties p ON wo.property_id = p.property_id
                WHERE p.property_id IN (
                    SELECT assigned_properties FROM users 
                    WHERE role = 'property_manager' 
                    AND user_id = CURRENT_USER()
                )
                AND status IN ('open', 'in_progress', 'completed');
            """,
            
            "financials_for_pm": """
                CREATE OR REPLACE VIEW financials_for_pm AS
                SELECT 
                    f.financial_id,
                    f.property_id,
                    f.period_start_date,
                    f.period_end_date,
                    f.gross_rent_income,
                    f.other_income,
                    f.operating_expenses,
                    NULL as cost_basis,  -- Masked
                    NULL as acquisition_price  -- Masked
                FROM financials f
                JOIN properties p ON f.property_id = p.property_id
                WHERE p.property_id IN (
                    SELECT assigned_properties FROM users 
                    WHERE role = 'property_manager' 
                    AND user_id = CURRENT_USER()
                );
            """,
        }
    
    elif role == Role.BROKER:
        return {
            "properties_for_brokers": """
                CREATE OR REPLACE VIEW properties_for_brokers AS
                SELECT *
                FROM properties;
            """,
            
            "units_for_brokers": """
                CREATE OR REPLACE VIEW units_for_brokers AS
                SELECT 
                    unit_id,
                    property_id,
                    unit_number,
                    sqft,
                    bedrooms,
                    bathrooms,
                    status,
                    NULL as current_rent,  -- Masked
                    tenant_id
                FROM units
                WHERE status IN ('vacant', 'available_soon');
            """,
            
            "leases_for_brokers": """
                CREATE OR REPLACE VIEW leases_for_brokers AS
                SELECT 
                    lease_id,
                    unit_id,
                    NULL as tenant_name,  -- Masked
                    lease_start_date,
                    lease_end_date,
                    NULL as monthly_rent,  -- Masked
                    renewal_option,
                    tenant_id
                FROM leases
                WHERE lease_end_date >= CURRENT_DATE() - INTERVAL '30 day'
                ORDER BY lease_end_date;
            """,
            
            "renewal_pipeline": """
                CREATE OR REPLACE VIEW renewal_pipeline AS
                SELECT 
                    l.lease_id,
                    l.unit_id,
                    p.property_name,
                    u.unit_number,
                    l.lease_end_date,
                    DATEDIFF(day, CURRENT_DATE(), l.lease_end_date) as days_to_renewal,
                    l.renewal_option,
                    CASE 
                        WHEN DATEDIFF(day, CURRENT_DATE(), l.lease_end_date) <= 90 THEN 'URGENT'
                        WHEN DATEDIFF(day, CURRENT_DATE(), l.lease_end_date) <= 180 THEN 'NEAR_TERM'
                        ELSE 'FUTURE'
                    END as renewal_stage
                FROM leases l
                JOIN units u ON l.unit_id = u.unit_id
                JOIN properties p ON u.property_id = p.property_id
                WHERE l.lease_end_date >= CURRENT_DATE()
                ORDER BY l.lease_end_date ASC;
            """,
        }
    
    elif role == Role.FINANCE:
        return {
            "properties_for_finance": """
                CREATE OR REPLACE VIEW properties_for_finance AS
                SELECT *
                FROM properties;
            """,
            
            "leases_for_finance": """
                CREATE OR REPLACE VIEW leases_for_finance AS
                SELECT 
                    lease_id,
                    unit_id,
                    NULL as tenant_name,  -- Masked
                    lease_start_date,
                    lease_end_date,
                    monthly_rent,
                    renewal_option,
                    tenant_id
                FROM leases;
            """,
            
            "financials_for_finance": """
                CREATE OR REPLACE VIEW financials_for_finance AS
                SELECT *
                FROM financials;
            """,
            
            "rent_collections_for_finance": """
                CREATE OR REPLACE VIEW rent_collections_for_finance AS
                SELECT 
                    collection_id,
                    lease_id,
                    property_id,
                    billing_period,
                    rent_due,
                    rent_collected,
                    due_date,
                    payment_date,
                    days_overdue,
                    CASE 
                        WHEN days_overdue > 30 THEN 'SEVERELY_DELINQUENT'
                        WHEN days_overdue > 0 THEN 'DELINQUENT'
                        ELSE 'CURRENT'
                    END as status
                FROM rent_collections;
            """,
            
            "budget_variance_analysis": """
                CREATE OR REPLACE VIEW budget_variance_analysis AS
                SELECT 
                    f.property_id,
                    p.property_name,
                    f.period_start_date,
                    f.operating_expenses as actual,
                    b.budgeted_amount as budgeted,
                    (f.operating_expenses - b.budgeted_amount) as variance,
                    ROUND((f.operating_expenses - b.budgeted_amount) / 
                          NULLIF(b.budgeted_amount, 0) * 100, 2) as variance_pct
                FROM financials f
                JOIN budgets b ON f.property_id = b.property_id 
                                 AND f.period_start_date = b.period_start_date
                JOIN properties p ON f.property_id = p.property_id
                ORDER BY variance_pct DESC;
            """,
        }
    
    elif role == Role.EXECUTIVE:
        return {
            "portfolio_summary": """
                CREATE OR REPLACE VIEW portfolio_summary AS
                SELECT 
                    COUNT(DISTINCT p.property_id) as total_properties,
                    COUNT(DISTINCT u.unit_id) as total_units,
                    ROUND(COUNT(CASE WHEN u.status = 'occupied' THEN 1 END) / 
                          NULLIF(COUNT(DISTINCT u.unit_id), 0) * 100, 2) as occupancy_pct,
                    ROUND(SUM(f.gross_rent_income + f.other_income - f.operating_expenses) / 1000000, 2) as noi_millions,
                    ROUND(AVG((f.gross_rent_income + f.other_income - f.operating_expenses) / 
                              NULLIF(p.property_value, 0)) * 100, 2) as avg_cap_rate
                FROM properties p
                LEFT JOIN units u ON p.property_id = u.property_id
                LEFT JOIN financials f ON p.property_id = f.property_id;
            """,
            
            "regional_performance": """
                CREATE OR REPLACE VIEW regional_performance AS
                SELECT 
                    p.state as region,
                    COUNT(DISTINCT p.property_id) as properties,
                    ROUND(COUNT(CASE WHEN u.status = 'occupied' THEN 1 END) / 
                          NULLIF(COUNT(DISTINCT u.unit_id), 0) * 100, 2) as occupancy_pct,
                    ROUND(SUM(f.gross_rent_income + f.other_income - f.operating_expenses) / 1000000, 2) as noi_millions,
                    ROUND(SUM(rc.rent_collected) / NULLIF(SUM(rc.rent_due), 0) * 100, 2) as collections_rate
                FROM properties p
                LEFT JOIN units u ON p.property_id = u.property_id
                LEFT JOIN financials f ON p.property_id = f.property_id
                LEFT JOIN rent_collections rc ON p.property_id = rc.property_id
                GROUP BY p.state
                ORDER BY noi_millions DESC;
            """,
            
            "top_performers": """
                CREATE OR REPLACE VIEW top_performers AS
                SELECT 
                    p.property_id,
                    p.property_name,
                    p.property_type,
                    p.city,
                    ROUND(COUNT(CASE WHEN u.status = 'occupied' THEN 1 END) / 
                          NULLIF(COUNT(DISTINCT u.unit_id), 0) * 100, 2) as occupancy_pct,
                    ROUND((SUM(f.gross_rent_income + f.other_income - f.operating_expenses) / 
                           NULLIF(SUM(f.debt_service), 0)), 2) as debt_coverage_ratio,
                    ROUND(SUM(f.gross_rent_income + f.other_income - f.operating_expenses) / 1000000, 2) as noi_millions
                FROM properties p
                LEFT JOIN units u ON p.property_id = u.property_id
                LEFT JOIN financials f ON p.property_id = f.property_id
                GROUP BY p.property_id, p.property_name, p.property_type, p.city
                ORDER BY noi_millions DESC
                LIMIT 10;
            """,
        }
    
    return {}


def get_view_name(role: Role, base_table: str) -> str:
    """Get the role-specific view name for a table.
    
    Args:
        role: User role
        base_table: Base table name (e.g., 'properties', 'leases')
    
    Returns:
        View name (e.g., 'properties_for_pm')
    
    Example:
        >>> view = get_view_name(Role.PROPERTY_MANAGER, 'properties')
        >>> print(view)  # 'properties_for_pm'
        >>> # Now SELECT from this view instead of base table
    """
    
    mapping = {
        Role.ADMIN: {
            'properties': 'properties',
            'units': 'units',
            'leases': 'leases',
            'financials': 'financials',
            'rent_collections': 'rent_collections',
            'work_orders': 'work_orders',
        },
        Role.PROPERTY_MANAGER: {
            'properties': 'properties_for_pm',
            'units': 'units_for_pm',
            'leases': 'leases_for_pm',
            'work_orders': 'work_orders_for_pm',
            'financials': 'financials_for_pm',
        },
        Role.BROKER: {
            'properties': 'properties_for_brokers',
            'units': 'units_for_brokers',
            'leases': 'leases_for_brokers',
        },
        Role.FINANCE: {
            'properties': 'properties_for_finance',
            'leases': 'leases_for_finance',
            'financials': 'financials_for_finance',
            'rent_collections': 'rent_collections_for_finance',
        },
        Role.EXECUTIVE: {
            'properties': 'portfolio_summary',
            'summary': 'portfolio_summary',
            'performance': 'regional_performance',
        },
    }
    
    role_mapping = mapping.get(role, {})
    return role_mapping.get(base_table, base_table)
