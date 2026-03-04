"""Shared pytest fixtures for Portfolio Intelligence Hub tests."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest


# User Context Fixtures
@pytest.fixture
def sample_user_context() -> Dict[str, Any]:
    """Fixture for a sample property manager user context."""
    return {
        "user_id": "user_123",
        "username": "jsmith",
        "role": "property_manager",
        "assigned_properties": [101, 102, 103],
        "tenant_id": "tenant_456",
        "email": "jsmith@realestateop.com",
    }


@pytest.fixture
def sample_admin_context() -> Dict[str, Any]:
    """Fixture for a sample admin user context."""
    return {
        "user_id": "admin_001",
        "username": "admin_user",
        "role": "admin",
        "assigned_properties": None,  # Admin sees all
        "tenant_id": "tenant_456",
        "email": "admin@realestateop.com",
    }


@pytest.fixture
def sample_finance_context() -> Dict[str, Any]:
    """Fixture for a finance user context."""
    return {
        "user_id": "user_finance_01",
        "username": "fsmith",
        "role": "finance",
        "assigned_properties": [101, 102, 103, 104, 105],
        "tenant_id": "tenant_456",
        "email": "fsmith@realestateop.com",
    }


@pytest.fixture
def sample_broker_context() -> Dict[str, Any]:
    """Fixture for a broker user context."""
    return {
        "user_id": "user_broker_01",
        "username": "bjones",
        "role": "broker",
        "assigned_properties": [101, 102, 103],
        "tenant_id": "tenant_456",
        "email": "bjones@realestateop.com",
    }


# Property Fixtures
@pytest.fixture
def sample_properties() -> List[Dict[str, Any]]:
    """Fixture for 10 sample real estate properties."""
    return [
        {
            "property_id": 101,
            "property_name": "Sunset Apartments",
            "property_type": "apartment",
            "address": "123 Main St, Los Angeles, CA 90001",
            "units": 45,
            "valuation": 8500000,
            "cap_rate": 0.045,
            "noi_annual": 382500,
        },
        {
            "property_id": 102,
            "property_name": "Downtown Office Tower",
            "property_type": "commercial",
            "address": "456 Market St, San Francisco, CA 94102",
            "units": 30,
            "valuation": 12500000,
            "cap_rate": 0.055,
            "noi_annual": 687500,
        },
        {
            "property_id": 103,
            "property_name": "Grand Plaza Retail",
            "property_type": "retail",
            "address": "789 5th Ave, New York, NY 10001",
            "units": 12,
            "valuation": 6200000,
            "cap_rate": 0.052,
            "noi_annual": 322400,
        },
        {
            "property_id": 104,
            "property_name": "Industrial Hub",
            "property_type": "industrial",
            "address": "321 Industrial Blvd, Chicago, IL 60601",
            "units": 8,
            "valuation": 4500000,
            "cap_rate": 0.062,
            "noi_annual": 279000,
        },
        {
            "property_id": 105,
            "property_name": "Harbor Bay Apartments",
            "property_type": "apartment",
            "address": "555 Bay View, San Diego, CA 92101",
            "units": 120,
            "valuation": 18000000,
            "cap_rate": 0.048,
            "noi_annual": 864000,
        },
        {
            "property_id": 106,
            "property_name": "Tech Park Office",
            "property_type": "commercial",
            "address": "100 Silicon Valley Way, Mountain View, CA 94040",
            "units": 25,
            "valuation": 11000000,
            "cap_rate": 0.058,
            "noi_annual": 638000,
        },
        {
            "property_id": 107,
            "property_name": "Fashion District Retail",
            "property_type": "retail",
            "address": "200 Fashion Lane, Miami, FL 33101",
            "units": 18,
            "valuation": 7800000,
            "cap_rate": 0.051,
            "noi_annual": 397800,
        },
        {
            "property_id": 108,
            "property_name": "East Side Warehouse",
            "property_type": "industrial",
            "address": "750 Warehouse Row, Houston, TX 77001",
            "units": 6,
            "valuation": 3200000,
            "cap_rate": 0.065,
            "noi_annual": 208000,
        },
        {
            "property_id": 109,
            "property_name": "Uptown Living Complex",
            "property_type": "apartment",
            "address": "888 Highland Ave, Denver, CO 80202",
            "units": 85,
            "valuation": 12800000,
            "cap_rate": 0.050,
            "noi_annual": 640000,
        },
        {
            "property_id": 110,
            "property_name": "Central Station Mixed Use",
            "property_type": "commercial",
            "address": "1000 Central Ave, Boston, MA 02101",
            "units": 40,
            "valuation": 14200000,
            "cap_rate": 0.056,
            "noi_annual": 795200,
        },
    ]


# Query and Result Fixtures
@pytest.fixture
def sample_query_results() -> List[Dict[str, Any]]:
    """Fixture for sample query results."""
    return [
        {
            "building_id": 101,
            "building_name": "Sunset Apartments",
            "open_work_orders": 12,
            "in_progress": 5,
            "total": 17,
        },
        {
            "building_id": 105,
            "building_name": "Harbor Bay Apartments",
            "open_work_orders": 28,
            "in_progress": 8,
            "total": 36,
        },
        {
            "building_id": 109,
            "building_name": "Uptown Living Complex",
            "open_work_orders": 15,
            "in_progress": 6,
            "total": 21,
        },
    ]


# Mock Database Connection Fixtures
@pytest.fixture
def mock_snowflake_connection() -> MagicMock:
    """Fixture for a mock Snowflake connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Mock execute method
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = [
        {
            "building_id": 101,
            "open_work_orders": 12,
        },
        {
            "building_id": 105,
            "open_work_orders": 28,
        },
    ]

    mock_conn.cursor.return_value = mock_cursor
    mock_conn.is_closed.return_value = False

    return mock_conn


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Fixture for a mock Supabase client."""
    mock_client = MagicMock()

    # Mock search functionality
    mock_search_result = {
        "data": [
            {
                "id": "doc_1",
                "metadata": {"source": "lease_101.pdf", "section": "terms"},
                "content": "Lease renewal option available on 12/31/2025",
                "similarity": 0.92,
            },
            {
                "id": "doc_2",
                "metadata": {"source": "lease_102.pdf", "section": "renewal"},
                "content": "Automatic renewal with 30-day notice requirement",
                "similarity": 0.88,
            },
        ]
    }

    mock_client.table.return_value.select.return_value.execute.return_value = (
        mock_search_result
    )

    return mock_client


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Fixture for a mock OpenAI client."""
    mock_client = MagicMock()

    # Mock embedding endpoint
    mock_embedding = [0.1] * 3072  # 3072-dimensional vector
    mock_client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=mock_embedding)]
    )

    return mock_client


# Sample Document Fixtures
@pytest.fixture
def sample_lease_document() -> str:
    """Fixture for sample lease document text."""
    return """
    COMMERCIAL LEASE AGREEMENT
    
    This Lease is entered into as of January 1, 2023, by and between 
    Property Owner ("Landlord") and Tenant Corp ("Tenant").
    
    PREMISES:
    Unit 101, 123 Main Street, Los Angeles, CA 90001
    
    TERM:
    Initial Term: 24 months commencing February 1, 2023
    Renewal Options: Two (2) consecutive renewal terms of 12 months each
    
    RENT:
    Base Rent: $5,000 per month
    Annual Increase: 3% per year
    
    RENEWAL CLAUSE:
    Tenant may renew this lease by providing written notice at least 60 days 
    prior to the expiration of the initial term or any renewal term.
    
    SECURITY DEPOSIT:
    $10,000 refundable security deposit
    
    MAINTENANCE:
    Landlord responsible for structural maintenance. Tenant responsible for 
    interior maintenance and repairs.
    """


@pytest.fixture
def sample_inspection_report() -> str:
    """Fixture for sample inspection report text."""
    return """
    PROPERTY INSPECTION REPORT
    Date: March 1, 2025
    Property: Harbor Bay Apartments
    Inspector: John Doe
    
    ROOF INSPECTION:
    The roof is in good condition with an estimated 8 years of remaining life.
    Minor repairs recommended for section C. Cost estimate: $2,500.
    
    ELECTRICAL SYSTEMS:
    Main panel upgraded in 2020. All circuits functioning properly.
    Emergency backup system operational.
    
    PLUMBING:
    Main line inspected using camera. No blockages detected.
    Water heater replaced 2022, estimated 5 years remaining life.
    
    HVAC SYSTEMS:
    Central HVAC system well-maintained. Filters changed quarterly.
    Thermostat upgrade recommended for better efficiency. Cost: $5,000.
    
    STRUCTURAL INTEGRITY:
    Foundation in good condition. No signs of settling or cracks.
    Exterior walls show minor weathering. Repainting recommended in 2026.
    
    SUMMARY:
    Property is well-maintained. Recommended maintenance schedule provided.
    Overall condition: Excellent (8.5/10)
    """


# Work Order Fixtures
@pytest.fixture
def sample_work_orders() -> List[Dict[str, Any]]:
    """Fixture for sample work orders."""
    return [
        {
            "work_order_id": "WO_001",
            "property_id": 101,
            "category": "HVAC",
            "description": "Replace air filter in Unit 201",
            "status": "completed",
            "created_date": (datetime.now() - timedelta(days=30)).isoformat(),
            "completed_date": (datetime.now() - timedelta(days=25)).isoformat(),
            "cost": 150,
        },
        {
            "work_order_id": "WO_002",
            "property_id": 105,
            "category": "Plumbing",
            "description": "Fix leak in bathroom Unit 305",
            "status": "in_progress",
            "created_date": (datetime.now() - timedelta(days=5)).isoformat(),
            "completed_date": None,
            "cost": 350,
        },
        {
            "work_order_id": "WO_003",
            "property_id": 101,
            "category": "Electrical",
            "description": "Repair broken outlet in lobby",
            "status": "open",
            "created_date": datetime.now().isoformat(),
            "completed_date": None,
            "cost": 200,
        },
    ]


# Financial Data Fixtures
@pytest.fixture
def sample_financial_data() -> List[Dict[str, Any]]:
    """Fixture for sample monthly financial data."""
    return [
        {
            "property_id": 101,
            "month": "2025-01",
            "revenue": 225000,
            "expenses": 95000,
            "noi": 130000,
            "budget_variance": 5000,
        },
        {
            "property_id": 101,
            "month": "2025-02",
            "revenue": 220000,
            "expenses": 98000,
            "noi": 122000,
            "budget_variance": -3000,
        },
        {
            "property_id": 105,
            "month": "2025-01",
            "revenue": 600000,
            "expenses": 250000,
            "noi": 350000,
            "budget_variance": 25000,
        },
    ]
