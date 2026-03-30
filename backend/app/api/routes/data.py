"""
Data API routes for MATPOWER Web Backend.
Provides endpoints for simulation data management, labeling, and export.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_db
from ...db.crud import (
    get_simulation_record,
    delete_simulation_record,
    update_simulation_record,
    list_disturbance_events,
    get_time_series,
    create_scenario_label,
    list_scenario_labels,
    update_scenario_label,
    delete_scenario_label,
)
from ...services.data_service import DataService
from ...services.export_service import ExportService

router = APIRouter(prefix="/api/data", tags=["data"])

# Export directory for downloads
EXPORT_DIR = Path("E:/matpower-web/backend/exports")


# =============================================================================
# Pydantic Schemas for API
# =============================================================================

from pydantic import BaseModel, Field


class SimulationSummaryResponse(BaseModel):
    """Response schema for simulation list items."""
    id: int
    case_name: str
    sim_type: str
    status: str
    iterations: Optional[int]
    computation_time: Optional[float]
    created_at: str
    tags: Optional[str]
    system_summary: dict


class SimulationListResponse(BaseModel):
    """Response schema for simulation list."""
    records: List[SimulationSummaryResponse]
    total: int
    page: int
    page_size: int


class SimulationDetailResponse(BaseModel):
    """Response schema for simulation detail."""
    id: int
    case_name: str
    sim_type: str
    status: str
    iterations: Optional[int]
    computation_time: Optional[float]
    input_snapshot: dict
    result_snapshot: dict
    system_summary: dict
    created_at: str
    tags: Optional[str]
    disturbance_events: List[dict]
    time_series: List[dict]
    labels: List[dict]


class LabelCreate(BaseModel):
    """Schema for creating a label."""
    label_type: str = Field(..., description="Type of label: normal, fault, overload, voltage_violation, corrected")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    description: Optional[str] = Field(None, description="Optional description")


class LabelUpdate(BaseModel):
    """Schema for updating a label."""
    label_type: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None


class ExportRequest(BaseModel):
    """Schema for export requests."""
    export_format: str = Field(..., description="Format: json, csv, training")
    case_name: Optional[str] = None
    sim_type: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[str] = None


class ExportResponse(BaseModel):
    """Response schema for export requests."""
    task_id: int
    status: str
    file_path: Optional[str] = None
    record_count: Optional[int] = None
    format: str


class StatisticsResponse(BaseModel):
    """Response schema for statistics."""
    total_records: int
    by_case: List[dict]
    by_sim_type: List[dict]
    by_status: List[dict]
    recent_week: int


# =============================================================================
# Simulation Records Endpoints
# =============================================================================

@router.get("/simulations", response_model=SimulationListResponse)
async def list_simulations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    case_name: Optional[str] = Query(None, description="Filter by case name"),
    sim_type: Optional[str] = Query(None, description="Filter by simulation type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    tags: Optional[str] = Query(None, description="Filter by tags"),
    db: AsyncSession = Depends(get_db),
):
    """
    List simulation records with pagination and filtering.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum records per page (max 100)
    - **case_name**: Filter by case name (e.g., "case14")
    - **sim_type**: Filter by simulation type (PF, DCPF, OPF)
    - **status**: Filter by status (success, failed)
    - **tags**: Filter by tags (substring match)
    """
    service = DataService(db)

    filters = {
        "case_name": case_name,
        "sim_type": sim_type,
        "status": status,
        "tags": tags,
    }

    records, total = await service.query_simulations(filters, skip=skip, limit=limit)

    record_summaries = []
    for r in records:
        record_summaries.append(SimulationSummaryResponse(
            id=r.id,
            case_name=r.case_name,
            sim_type=r.sim_type,
            status=r.status,
            iterations=r.iterations,
            computation_time=r.computation_time,
            created_at=r.created_at.isoformat(),
            tags=r.tags,
            system_summary=eval(r.system_summary) if isinstance(r.system_summary, str) else r.system_summary,
        ))

    return SimulationListResponse(
        records=record_summaries,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/simulations/{record_id}", response_model=SimulationDetailResponse)
async def get_simulation_detail(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a simulation record.

    Includes full input/output snapshots, disturbance events,
    time series data, and labels.
    """
    service = DataService(db)
    detail = await service.get_simulation_detail(record_id)

    if not detail:
        raise HTTPException(status_code=404, detail="Simulation record not found")

    return SimulationDetailResponse(**detail)


@router.delete("/simulations/{record_id}")
async def delete_simulation(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a simulation record.
    """
    success = await delete_simulation_record(db, record_id)

    if not success:
        raise HTTPException(status_code=404, detail="Simulation record not found")

    return {"message": "Simulation record deleted successfully"}


@router.get("/simulations/{record_id}/timeseries")
async def get_simulation_timeseries(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get time series data for a simulation.
    """
    record = await get_simulation_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Simulation record not found")

    time_series = await get_time_series(db, record_id)

    return {
        "simulation_id": record_id,
        "time_series": [
            {
                "id": t.id,
                "step": t.step,
                "bus_data": eval(t.bus_data),
                "gen_data": eval(t.gen_data),
                "branch_data": eval(t.branch_data),
                "summary": eval(t.summary),
                "created_at": t.created_at.isoformat(),
            }
            for t in time_series
        ],
    }


@router.get("/simulations/{record_id}/disturbances")
async def get_simulation_disturbances(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get disturbance events for a simulation.
    """
    record = await get_simulation_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Simulation record not found")

    disturbances = await list_disturbance_events(db, record_id)

    return {
        "simulation_id": record_id,
        "disturbances": [
            {
                "id": d.id,
                "event_type": d.event_type,
                "target_type": d.target_type,
                "target_id": d.target_id,
                "parameter": d.parameter,
                "old_value": d.old_value,
                "new_value": d.new_value,
                "description": d.description,
                "created_at": d.created_at.isoformat(),
            }
            for d in disturbances
        ],
    }


# =============================================================================
# Labels Endpoints
# =============================================================================

@router.post("/simulations/{record_id}/labels")
async def add_label(
    record_id: int,
    label: LabelCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a label to a simulation record.
    """
    record = await get_simulation_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Simulation record not found")

    from ...db.crud import ScenarioLabelCreate
    db_label = await create_scenario_label(
        db,
        ScenarioLabelCreate(
            simulation_id=record_id,
            label_type=label.label_type,
            severity=label.severity,
            description=label.description,
        ),
    )

    return {
        "id": db_label.id,
        "simulation_id": record_id,
        "label_type": db_label.label_type,
        "severity": db_label.severity,
        "description": db_label.description,
    }


@router.put("/simulations/{record_id}/labels/{label_id}")
async def update_label(
    record_id: int,
    label_id: int,
    label: LabelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a scenario label.
    """
    update_data = label.model_dump(exclude_unset=True)
    db_label = await update_scenario_label(db, label_id, update_data)

    if not db_label:
        raise HTTPException(status_code=404, detail="Label not found")

    return {
        "id": db_label.id,
        "simulation_id": record_id,
        "label_type": db_label.label_type,
        "severity": db_label.severity,
        "description": db_label.description,
    }


@router.delete("/simulations/{record_id}/labels/{label_id}")
async def delete_label(
    record_id: int,
    label_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a scenario label.
    """
    success = await delete_scenario_label(db, label_id)

    if not success:
        raise HTTPException(status_code=404, detail="Label not found")

    return {"message": "Label deleted successfully"}


@router.post("/simulations/{record_id}/auto-label")
async def auto_label_simulation(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Automatically label a simulation scenario based on violations.
    """
    record = await get_simulation_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Simulation record not found")

    service = DataService(db)
    labels = await service.auto_label_scenario(record_id)

    return {
        "simulation_id": record_id,
        "labels": labels,
        "message": f"Created {len(labels)} label(s)",
    }


# =============================================================================
# Export Endpoints
# =============================================================================

@router.post("/export/json", response_model=ExportResponse)
async def export_json(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Export simulation data as JSON.

    Returns a task ID that can be used to check status and download the file.
    """
    filters = {
        "case_name": request.case_name,
        "sim_type": request.sim_type,
        "status": request.status,
        "tags": request.tags,
    }

    service = ExportService(db)
    result = await service.create_export_task("json", filters)

    return ExportResponse(**result)


@router.post("/export/csv", response_model=ExportResponse)
async def export_csv(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Export simulation data as CSV.

    Creates a directory with separate CSV files for:
    - records.csv: Simulation metadata
    - buses.csv: Bus data
    - generators.csv: Generator data
    - branches.csv: Branch/line data
    """
    filters = {
        "case_name": request.case_name,
        "sim_type": request.sim_type,
        "status": request.status,
        "tags": request.tags,
    }

    service = ExportService(db)
    result = await service.create_export_task("csv", filters)

    return ExportResponse(**result)


@router.post("/export/training", response_model=ExportResponse)
async def export_training(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Export simulation data as LLM training format (JSONL).

    Generates conversation-style training data with:
    - System prompt for power system scheduling
    - User input with system state description
    - Assistant response with actions and results

    Suitable for fine-tuning language models on power system tasks.
    """
    filters = {
        "case_name": request.case_name,
        "sim_type": request.sim_type,
        "status": request.status or "success",  # Default to successful simulations
        "tags": request.tags,
    }

    service = ExportService(db)
    result = await service.create_export_task("training", filters)

    return ExportResponse(**result)


@router.get("/export/tasks")
async def list_export_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List export tasks.
    """
    service = ExportService(db)
    tasks = await service.list_export_tasks(skip=skip, limit=limit)

    return {
        "tasks": tasks,
        "total": len(tasks),
    }


@router.get("/export/tasks/{task_id}")
async def get_export_task_status(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status of an export task.
    """
    service = ExportService(db)
    task = await service.get_export_task_status(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Export task not found")

    return task


@router.get("/export/download/{task_id}")
async def download_export_file(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Download an exported file.

    Returns file information including path. The actual file download
    should be handled by a static file server or separate endpoint.
    """
    from ...db.crud import get_export_task as crud_get_task

    task = await crud_get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Export task not found")

    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Export not completed. Current status: {task.status}"
        )

    file_path = Path(task.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    return {
        "task_id": task_id,
        "file_path": task.file_path,
        "file_name": file_path.name,
        "file_size": file_path.stat().st_size,
        "record_count": task.record_count,
        "format": task.export_format,
    }


# =============================================================================
# Statistics Endpoint
# =============================================================================

@router.get("/stats", response_model=StatisticsResponse)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get overall statistics about simulation records.

    Returns:
    - Total number of records
    - Records by case name
    - Records by simulation type
    - Records by status
    - Records from the last 7 days
    """
    service = DataService(db)
    stats = await service.get_statistics()

    return StatisticsResponse(**stats)


# =============================================================================
# Main App Registration Comment
# =============================================================================

"""
To register these routes in main.py, add:

from app.api.routes import data
app.include_router(data.router, tags=["data"])

Or include with prefix if not already defined:
app.include_router(data.router)
"""
