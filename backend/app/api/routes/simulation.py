"""
Simulation Control API Routes
Endpoints for running power system simulations
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import uuid
import asyncio
from datetime import datetime

from app.services.simulation_service import get_simulation_service
from app.models.schemas import (
    SimulationRequest, SimulationResult, ApiResponse, TaskStatus,
    DisturbanceRequest
)
from app.api.ws import manager

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

# In-memory task storage (replace with Redis/Database in production)
_simulation_tasks: Dict[str, TaskStatus] = {}
_simulation_history: List[Dict[str, Any]] = []

# Default client ID for WebSocket notifications
DEFAULT_CLIENT_ID = "frontend"


async def _run_simulation_task(task_id: str, request: SimulationRequest):
    """Background task to run simulation"""
    service = get_simulation_service()

    try:
        # Update task status to running
        _simulation_tasks[task_id].status = "running"
        _simulation_tasks[task_id].message = "Running simulation..."

        # Send WebSocket notification - simulation started
        await manager.send_progress_update(
            task_id=task_id,
            client_id=DEFAULT_CLIENT_ID,
            status="running",
            progress=0,
            message=f"Starting {request.sim_type} simulation for {request.case_name}..."
        )

        # Run the simulation
        result = service.run_simulation(
            case_name=request.case_name,
            sim_type=request.sim_type,
            algorithm=request.algorithm or "NR",
            modifications=request.modifications
        )

        # Send WebSocket notification - progress update
        await manager.send_progress_update(
            task_id=task_id,
            client_id=DEFAULT_CLIENT_ID,
            status="running",
            progress=50,
            message="Processing results..."
        )

        # Update task with result
        _simulation_tasks[task_id].status = "completed" if result.success else "failed"
        _simulation_tasks[task_id].completed_at = datetime.now().isoformat()
        _simulation_tasks[task_id].result = result

        # Send WebSocket notification - completed
        await manager.send_progress_update(
            task_id=task_id,
            client_id=DEFAULT_CLIENT_ID,
            status="completed" if result.success else "failed",
            progress=100,
            message=result.message or ("Simulation completed successfully" if result.success else "Simulation failed")
        )

        if not result.success:
            _simulation_tasks[task_id].error = result.message

    except Exception as e:
        _simulation_tasks[task_id].status = "failed"
        _simulation_tasks[task_id].completed_at = datetime.now().isoformat()
        _simulation_tasks[task_id].error = str(e)

        # Send WebSocket notification - error
        await manager.send_progress_update(
            task_id=task_id,
            client_id=DEFAULT_CLIENT_ID,
            status="failed",
            progress=0,
            message=f"Simulation error: {str(e)}"
        )


@router.post("/run", response_model=TaskStatus)
async def run_simulation(
    request: SimulationRequest
) -> TaskStatus:
    """
    Run a power system simulation

    Args:
        request: Simulation request with case_name, sim_type, and optional modifications

    Returns:
        TaskStatus with task_id for tracking progress
    """
    # Validate case exists
    service = get_simulation_service()
    metadata = service.get_case_metadata(request.case_name)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Case '{request.case_name}' not found")

    # Create task
    task_id = str(uuid.uuid4())
    task = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now().isoformat()
    )
    _simulation_tasks[task_id] = task

    # Run simulation in background task
    asyncio.create_task(_run_simulation_task(task_id, request))

    return task


@router.post("/run/sync", response_model=SimulationResult)
async def run_simulation_sync(request: SimulationRequest) -> SimulationResult:
    """
    Run a power system simulation synchronously (blocking)

    Args:
        request: Simulation request

    Returns:
        SimulationResult directly
    """
    service = get_simulation_service()

    # Validate case exists
    metadata = service.get_case_metadata(request.case_name)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Case '{request.case_name}' not found")

    # Run simulation
    result = service.run_simulation(
        case_name=request.case_name,
        sim_type=request.sim_type,
        algorithm=request.algorithm or "NR",
        modifications=request.modifications
    )

    return result


@router.get("/result/{task_id}", response_model=TaskStatus)
async def get_simulation_result(task_id: str) -> TaskStatus:
    """
    Get the result of a simulation task

    Args:
        task_id: Unique task identifier

    Returns:
        TaskStatus with result if completed
    """
    if task_id not in _simulation_tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    return _simulation_tasks[task_id]


@router.get("/tasks", response_model=List[TaskStatus])
async def list_tasks() -> List[TaskStatus]:
    """
    List all simulation tasks

    Returns:
        List of all tasks and their statuses
    """
    return list(_simulation_tasks.values())


@router.delete("/tasks/{task_id}", response_model=ApiResponse)
async def delete_task(task_id: str) -> ApiResponse:
    """
    Delete a simulation task from memory

    Args:
        task_id: Task identifier to delete

    Returns:
        Confirmation message
    """
    if task_id not in _simulation_tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    del _simulation_tasks[task_id]

    return ApiResponse(success=True, message=f"Task '{task_id}' deleted")


@router.post("/pf", response_model=SimulationResult)
async def run_power_flow(
    request: SimulationRequest
) -> SimulationResult:
    """
    Run AC power flow calculation

    Args:
        request: Simulation request with case_name, algorithm, and modifications

    Returns:
        SimulationResult directly
    """
    service = get_simulation_service()

    # Validate case exists
    metadata = service.get_case_metadata(request.case_name)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Case '{request.case_name}' not found")

    # Run power flow
    result = service.run_simulation(
        case_name=request.case_name,
        sim_type="PF",
        algorithm=request.algorithm or "NR",
        modifications=request.modifications
    )

    # Add to history
    _add_to_history("PF", request.case_name, result)

    return result


@router.post("/opf", response_model=SimulationResult)
async def run_optimal_power_flow(
    request: SimulationRequest
) -> SimulationResult:
    """
    Run optimal power flow (OPF) calculation

    Args:
        request: Simulation request with case_name and modifications

    Returns:
        SimulationResult with optimal dispatch and total cost
    """
    service = get_simulation_service()

    # Validate case exists
    metadata = service.get_case_metadata(request.case_name)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Case '{request.case_name}' not found")

    # Run OPF
    result = service.run_simulation(
        case_name=request.case_name,
        sim_type="OPF",
        modifications=request.modifications
    )

    # Add to history
    _add_to_history("OPF", request.case_name, result)

    return result


@router.post("/opf-with-correction", response_model=SimulationResult)
async def run_opf_with_correction(
    request: Dict[str, Any]
) -> SimulationResult:
    """
    Apply a disturbance and run OPF to find optimal corrective actions

    This endpoint:
    1. Applies the specified disturbance to the base case
    2. Runs OPF to find the optimal generation re-dispatch
    3. Returns the corrected system state

    Args:
        request: Request with case_name and disturbance

    Returns:
        SimulationResult with optimal corrective actions
    """
    service = get_simulation_service()
    case_name = request.get('case_name')
    disturbance_data = request.get('disturbance', {})

    # Validate required fields
    if not case_name:
        raise HTTPException(status_code=400, detail="case_name is required")
    if not disturbance_data:
        raise HTTPException(status_code=400, detail="disturbance data is required")

    # Validate case exists
    metadata = service.get_case_metadata(case_name)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Case '{case_name}' not found")

    # Normalize target_id to a valid dict
    raw_target_id = disturbance_data.get('target_id')
    if raw_target_id is None:
        target_id = {}
    elif isinstance(raw_target_id, int):
        target_id = {'index': raw_target_id}
    elif isinstance(raw_target_id, float):
        target_id = {'index': int(raw_target_id)}
    elif isinstance(raw_target_id, dict):
        target_id = raw_target_id
    elif isinstance(raw_target_id, str):
        try:
            target_id = {'index': int(raw_target_id)}
        except ValueError:
            target_id = {}
    else:
        target_id = {}

    # Create DisturbanceRequest from data
    disturbance = DisturbanceRequest(
        case_name=case_name,
        disturbance_type=disturbance_data.get('disturbance_type'),
        target_id=target_id,
        new_value=disturbance_data.get('new_value')
    )

    # Build modifications for the disturbance
    modifications = service._build_disturbance_modifications(
        service.load_case_by_name(case_name),
        disturbance.disturbance_type,
        disturbance.target_id,
        disturbance.new_value
    )

    # Run OPF with disturbance
    result = service.run_simulation(
        case_name=case_name,
        sim_type="OPF",
        modifications=modifications
    )

    # Add to history
    _add_to_history("OPF_WITH_CORRECTION", case_name, result, disturbance)

    return result


@router.post("/disturbance", response_model=SimulationResult)
async def apply_disturbance_and_run(
    request: Dict[str, Any]
) -> SimulationResult:
    """
    Apply a disturbance and run power flow

    Supported disturbance types:
    - line_outage: Remove a branch (requires f_bus and t_bus in target_id, or index)
    - gen_outage: Remove a generator (requires gen_bus in target_id, or index)
    - load_change: Change load at a bus (requires bus_index and new_value)
    - voltage_change / voltage_adjust: Change voltage setpoint (requires gen_index or index and new_value)

    Args:
        request: Request with case_name and disturbance

    Returns:
        SimulationResult after disturbance
    """
    service = get_simulation_service()
    case_name = request.get('case_name')
    disturbance_data = request.get('disturbance', {})

    # Validate required fields
    if not case_name:
        raise HTTPException(status_code=400, detail="case_name is required")
    if not disturbance_data:
        raise HTTPException(status_code=400, detail="disturbance data is required")

    disturbance_type = disturbance_data.get('disturbance_type')
    if not disturbance_type:
        raise HTTPException(status_code=400, detail="disturbance_type is required")

    # Validate case exists
    metadata = service.get_case_metadata(case_name)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Case '{case_name}' not found")

    # Normalize target_id: accept int, dict, or string formats; always produce a valid dict
    raw_target_id = disturbance_data.get('target_id')
    if raw_target_id is None:
        # Some disturbance types don't strictly require target_id, provide empty dict
        target_id = {}
    elif isinstance(raw_target_id, int):
        target_id = {'index': raw_target_id}
    elif isinstance(raw_target_id, float):
        target_id = {'index': int(raw_target_id)}
    elif isinstance(raw_target_id, dict):
        target_id = raw_target_id
    elif isinstance(raw_target_id, str):
        # Try to parse as int index
        try:
            target_id = {'index': int(raw_target_id)}
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid target_id format: '{raw_target_id}'"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"target_id has unsupported type: {type(raw_target_id).__name__}"
        )

    new_value = disturbance_data.get('new_value')

    # Apply disturbance
    result = service.apply_disturbance(
        case_name=case_name,
        disturbance_type=disturbance_type,
        target_id=target_id,
        new_value=new_value
    )

    # Add to history
    _add_to_history("DISTURBANCE_PF", case_name, result, disturbance_data)

    return result


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_simulation_history(
    limit: int = 50,
    case_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get simulation history

    Args:
        limit: Maximum number of records to return
        case_name: Optional filter by case name

    Returns:
        List of historical simulation records
    """
    history = _simulation_history

    if case_name:
        history = [h for h in history if h.get('case_name') == case_name]

    # Return most recent first
    return history[-limit:][::-1]


@router.delete("/history")
async def clear_simulation_history() -> ApiResponse:
    """
    Clear all simulation history

    Returns:
        Confirmation message
    """
    global _simulation_history
    _simulation_history = []
    return ApiResponse(success=True, message="Simulation history cleared")


@router.post("/validate")
async def validate_simulation_request(request: SimulationRequest) -> ApiResponse:
    """
    Validate a simulation request without running it

    Args:
        request: Simulation request to validate

    Returns:
        Validation result with any errors found
    """
    errors = []

    # Check case exists
    service = get_simulation_service()
    metadata = service.get_case_metadata(request.case_name)
    if not metadata:
        errors.append(f"Case '{request.case_name}' not found")

    # Validate simulation type
    if request.sim_type not in ["PF", "DCPF", "OPF"]:
        errors.append(f"Invalid simulation type: {request.sim_type}")

    # Validate algorithm for PF
    if request.sim_type == "PF" and request.algorithm:
        valid_algos = ["NR", "FDXB", "FDBX", "GS"]
        if request.algorithm.upper() not in valid_algos:
            errors.append(f"Invalid algorithm: {request.algorithm}")

    return ApiResponse(
        success=len(errors) == 0,
        message="Validation passed" if len(errors) == 0 else "Validation failed",
        data={'errors': errors}
    )


def _add_to_history(
    sim_type: str,
    case_name: str,
    result: SimulationResult,
    disturbance: Optional[DisturbanceRequest] = None
):
    global _simulation_history
    """Add a simulation record to history"""
    record = {
        'timestamp': datetime.now().isoformat(),
        'sim_type': sim_type,
        'case_name': case_name,
        'success': result.success,
        'converged': result.converged,
        'iterations': result.iterations,
        'et': result.et
    }

    if disturbance:
        record['disturbance'] = {
            'type': disturbance.get('disturbance_type', '') if isinstance(disturbance, dict) else disturbance.disturbance_type,
            'target_id': disturbance.get('target_id', '') if isinstance(disturbance, dict) else disturbance.target_id,
            'new_value': disturbance.get('new_value', '') if isinstance(disturbance, dict) else disturbance.new_value
        }

    if result.system_summary:
        record['summary'] = {
            'total_generation': result.system_summary.total_generation,
            'total_load': result.system_summary.total_load,
            'total_losses': result.system_summary.total_losses
        }

    _simulation_history.append(record)

    # Keep only last 1000 records
    if len(_simulation_history) > 1000:
        _simulation_history = _simulation_history[-1000:]
