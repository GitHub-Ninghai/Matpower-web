"""
Case Management API Routes
Endpoints for retrieving and managing MATPOWER test cases
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import copy

from app.services.simulation_service import get_simulation_service
from app.models.schemas import CaseListItem, CaseData, ApiResponse, BusData, GeneratorData, BranchData

router = APIRouter(prefix="/api/cases", tags=["cases"])

# In-memory storage for modified cases
_modified_cases: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[CaseListItem])
async def list_cases(demo_only: bool = False) -> List[CaseListItem]:
    """
    Get list of all available MATPOWER test cases

    Args:
        demo_only: If true, only return cases suitable for web demo

    Returns:
        List of case summaries with name, buses, generators, branches counts
    """
    service = get_simulation_service()
    cases = service.list_available_cases()
    if demo_only:
        cases = [c for c in cases if c.get('is_demo', False)]
    return [CaseListItem(**case) for case in cases]


@router.get("/refresh/list")
async def refresh_case_list() -> ApiResponse:
    """
    Refresh the case list by rescanning the data directory

    Returns:
        Confirmation message with updated count
    """
    service = get_simulation_service()
    cases = service.list_available_cases()

    return ApiResponse(
        success=True,
        message=f"Found {len(cases)} cases",
        data={'count': len(cases)}
    )


@router.get("/{case_name}")
async def get_case(case_name: str):
    """
    Get complete data for a specific test case

    Args:
        case_name: Name of the case (e.g., 'case9', 'case14')

    Returns:
        Complete case data including buses, generators, branches
    """
    service = get_simulation_service()
    case_data = service.load_case_by_name(case_name)

    if not case_data:
        raise HTTPException(status_code=404, detail=f"Case '{case_name}' not found")

    # Return raw case data directly (gencost is raw matrix format)
    return case_data


@router.get("/{case_name}/metadata")
async def get_case_metadata(case_name: str) -> Dict[str, Any]:
    """
    Get metadata for a specific test case

    Args:
        case_name: Name of the case

    Returns:
        Case metadata (name, buses, generators, branches, base_mva, description, is_demo)
    """
    service = get_simulation_service()
    metadata = service.get_case_metadata(case_name)

    if not metadata:
        raise HTTPException(status_code=404, detail=f"Case '{case_name}' not found")

    return metadata


@router.put("/{case_name}/params", response_model=ApiResponse)
async def modify_case_params(
    case_name: str,
    bus_modifications: Optional[List[Dict[str, Any]]] = None,
    gen_modifications: Optional[List[Dict[str, Any]]] = None,
    branch_modifications: Optional[List[Dict[str, Any]]] = None
) -> ApiResponse:
    """
    Modify parameters of a test case

    This endpoint allows modifying case parameters before simulation.
    Modifications are stored in memory for the session.

    Args:
        case_name: Name of the case to modify
        bus_modifications: List of bus modifications (each with index, field, value)
        gen_modifications: List of generator modifications
        branch_modifications: List of branch modifications

    Returns:
        Confirmation message with modified case data

    Example:
        PUT /api/cases/case9/params
        {
            "bus_modifications": [
                {"index": 0, "field": "pd", "value": 150}
            ],
            "gen_modifications": [
                {"index": 0, "field": "pg", "value": 100}
            ]
        }
    """
    service = get_simulation_service()

    # Load the base case
    case_data = service.load_case_by_name(case_name)
    if not case_data:
        raise HTTPException(status_code=404, detail=f"Case '{case_name}' not found")

    # Create a copy for modifications
    modified_case = copy.deepcopy(case_data)

    # Apply bus modifications
    if bus_modifications:
        for mod in bus_modifications:
            idx = mod.get('index')
            field = mod.get('field')
            value = mod.get('value')
            if 0 <= idx < len(modified_case['bus']):
                modified_case['bus'][idx][field] = value

    # Apply generator modifications
    if gen_modifications:
        for mod in gen_modifications:
            idx = mod.get('index')
            field = mod.get('field')
            value = mod.get('value')
            if 0 <= idx < len(modified_case['gen']):
                modified_case['gen'][idx][field] = value

    # Apply branch modifications
    if branch_modifications:
        for mod in branch_modifications:
            idx = mod.get('index')
            field = mod.get('field')
            value = mod.get('value')
            if 0 <= idx < len(modified_case['branch']):
                modified_case['branch'][idx][field] = value

    # Store modified case
    storage_key = f"{case_name}_modified"
    _modified_cases[storage_key] = modified_case

    return ApiResponse(
        success=True,
        message=f"Case '{case_name}' parameters modified",
        data={
            'storage_key': storage_key,
            'bus_count': len(modified_case['bus']),
            'gen_count': len(modified_case['gen']),
            'branch_count': len(modified_case['branch'])
        }
    )


@router.post("/{case_name}/reset", response_model=ApiResponse)
async def reset_case_params(case_name: str) -> ApiResponse:
    """
    Reset a modified case back to its original state

    Args:
        case_name: Name of the case to reset

    Returns:
        Confirmation message
    """
    storage_key = f"{case_name}_modified"
    if storage_key in _modified_cases:
        del _modified_cases[storage_key]

    return ApiResponse(
        success=True,
        message=f"Case '{case_name}' reset to original state"
    )
