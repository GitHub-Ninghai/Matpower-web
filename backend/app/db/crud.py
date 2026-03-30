"""
CRUD operations for MATPOWER Web Backend.
Provides async database operations for all models.
"""

from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import select, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    SimulationRecord,
    DisturbanceEvent,
    TimeSeriesData,
    ScenarioLabel,
    ExportTask,
)


# =============================================================================
# Pydantic Schemas for Input Validation
# =============================================================================

from pydantic import BaseModel, Field


class SimulationRecordCreate(BaseModel):
    """Schema for creating a simulation record."""
    case_name: str
    sim_type: str
    status: str
    iterations: Optional[int] = None
    computation_time: Optional[float] = None
    input_snapshot: str  # JSON string
    result_snapshot: str  # JSON string
    system_summary: str  # JSON string
    tags: Optional[str] = None


class SimulationRecordUpdate(BaseModel):
    """Schema for updating a simulation record."""
    tags: Optional[str] = None
    status: Optional[str] = None


class DisturbanceEventCreate(BaseModel):
    """Schema for creating a disturbance event."""
    simulation_id: int
    event_type: str
    target_type: str
    target_id: int
    parameter: str
    old_value: Optional[float] = None
    new_value: Optional[float] = None
    description: Optional[str] = None


class TimeSeriesDataCreate(BaseModel):
    """Schema for creating a time series data point."""
    simulation_id: int
    step: int
    bus_data: str  # JSON string
    gen_data: str  # JSON string
    branch_data: str  # JSON string
    summary: str  # JSON string


class ScenarioLabelCreate(BaseModel):
    """Schema for creating a scenario label."""
    simulation_id: int
    label_type: str
    severity: str
    description: Optional[str] = None


class ExportTaskCreate(BaseModel):
    """Schema for creating an export task."""
    export_format: str
    filter_params: str  # JSON string
    file_path: str


# =============================================================================
# Simulation Records CRUD
# =============================================================================

async def create_simulation_record(
    db: AsyncSession, record: SimulationRecordCreate
) -> SimulationRecord:
    """
    Create a new simulation record.

    Args:
        db: Database session
        record: Simulation record data

    Returns:
        Created SimulationRecord instance
    """
    db_record = SimulationRecord(**record.model_dump())
    db.add(db_record)
    await db.commit()
    await db.refresh(db_record)
    return db_record


async def get_simulation_record(db: AsyncSession, record_id: int) -> Optional[SimulationRecord]:
    """
    Get a simulation record by ID.

    Args:
        db: Database session
        record_id: Record ID

    Returns:
        SimulationRecord or None if not found
    """
    result = await db.execute(
        select(SimulationRecord).where(SimulationRecord.id == record_id)
    )
    return result.scalar_one_or_none()


async def list_simulation_records(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    case_name: Optional[str] = None,
    sim_type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> tuple[List[SimulationRecord], int]:
    """
    List simulation records with filtering and pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        case_name: Filter by case name
        sim_type: Filter by simulation type
        status: Filter by status
        tags: Filter by tags (comma-separated match)
        start_date: Filter by start date
        end_date: Filter by end date

    Returns:
        Tuple of (list of records, total count)
    """
    query = select(SimulationRecord)

    # Apply filters
    conditions = []
    if case_name:
        conditions.append(SimulationRecord.case_name == case_name)
    if sim_type:
        conditions.append(SimulationRecord.sim_type == sim_type)
    if status:
        conditions.append(SimulationRecord.status == status)
    if tags:
        conditions.append(SimulationRecord.tags.contains(tags))
    if start_date:
        conditions.append(SimulationRecord.created_at >= start_date)
    if end_date:
        conditions.append(SimulationRecord.created_at <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination and ordering
    query = query.order_by(SimulationRecord.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    return list(records), total


async def delete_simulation_record(db: AsyncSession, record_id: int) -> bool:
    """
    Delete a simulation record by ID.

    Args:
        db: Database session
        record_id: Record ID

    Returns:
        True if deleted, False if not found
    """
    result = await db.execute(
        delete(SimulationRecord).where(SimulationRecord.id == record_id)
    )
    await db.commit()
    return result.rowcount > 0


async def update_simulation_record(
    db: AsyncSession, record_id: int, update_data: dict
) -> Optional[SimulationRecord]:
    """
    Update a simulation record.

    Args:
        db: Database session
        record_id: Record ID
        update_data: Fields to update

    Returns:
        Updated SimulationRecord or None if not found
    """
    record = await get_simulation_record(db, record_id)
    if not record:
        return None

    for key, value in update_data.items():
        if hasattr(record, key) and value is not None:
            setattr(record, key, value)

    await db.commit()
    await db.refresh(record)
    return record


# =============================================================================
# Disturbance Events CRUD
# =============================================================================

async def create_disturbance_event(
    db: AsyncSession, event: DisturbanceEventCreate
) -> DisturbanceEvent:
    """
    Create a new disturbance event.

    Args:
        db: Database session
        event: Disturbance event data

    Returns:
        Created DisturbanceEvent instance
    """
    db_event = DisturbanceEvent(**event.model_dump())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def list_disturbance_events(
    db: AsyncSession, simulation_id: int
) -> List[DisturbanceEvent]:
    """
    List all disturbance events for a simulation.

    Args:
        db: Database session
        simulation_id: Simulation record ID

    Returns:
        List of DisturbanceEvent instances
    """
    result = await db.execute(
        select(DisturbanceEvent)
        .where(DisturbanceEvent.simulation_id == simulation_id)
        .order_by(DisturbanceEvent.created_at)
    )
    return list(result.scalars().all())


async def batch_create_disturbance_events(
    db: AsyncSession, events: List[DisturbanceEventCreate]
) -> List[DisturbanceEvent]:
    """
    Batch create disturbance events.

    Args:
        db: Database session
        events: List of disturbance event data

    Returns:
        List of created DisturbanceEvent instances
    """
    db_events = [DisturbanceEvent(**event.model_dump()) for event in events]
    db.add_all(db_events)
    await db.commit()
    for event in db_events:
        await db.refresh(event)
    return db_events


# =============================================================================
# Time Series Data CRUD
# =============================================================================

async def create_time_series_point(
    db: AsyncSession, data: TimeSeriesDataCreate
) -> TimeSeriesData:
    """
    Create a single time series data point.

    Args:
        db: Database session
        data: Time series data

    Returns:
        Created TimeSeriesData instance
    """
    db_data = TimeSeriesData(**data.model_dump())
    db.add(db_data)
    await db.commit()
    await db.refresh(db_data)
    return db_data


async def batch_create_time_series(
    db: AsyncSession, data_list: List[TimeSeriesDataCreate]
) -> List[TimeSeriesData]:
    """
    Batch create time series data points.

    Args:
        db: Database session
        data_list: List of time series data

    Returns:
        List of created TimeSeriesData instances
    """
    db_data_list = [TimeSeriesData(**data.model_dump()) for data in data_list]
    db.add_all(db_data_list)
    await db.commit()
    for data in db_data_list:
        await db.refresh(data)
    return db_data_list


async def get_time_series(
    db: AsyncSession, simulation_id: int
) -> List[TimeSeriesData]:
    """
    Get all time series data for a simulation.

    Args:
        db: Database session
        simulation_id: Simulation record ID

    Returns:
        List of TimeSeriesData instances ordered by step
    """
    result = await db.execute(
        select(TimeSeriesData)
        .where(TimeSeriesData.simulation_id == simulation_id)
        .order_by(TimeSeriesData.step)
    )
    return list(result.scalars().all())


async def delete_time_series(db: AsyncSession, simulation_id: int) -> int:
    """
    Delete all time series data for a simulation.

    Args:
        db: Database session
        simulation_id: Simulation record ID

    Returns:
        Number of deleted records
    """
    result = await db.execute(
        delete(TimeSeriesData).where(TimeSeriesData.simulation_id == simulation_id)
    )
    await db.commit()
    return result.rowcount


# =============================================================================
# Scenario Labels CRUD
# =============================================================================

async def create_scenario_label(
    db: AsyncSession, label: ScenarioLabelCreate
) -> ScenarioLabel:
    """
    Create a new scenario label.

    Args:
        db: Database session
        label: Scenario label data

    Returns:
        Created ScenarioLabel instance
    """
    db_label = ScenarioLabel(**label.model_dump())
    db.add(db_label)
    await db.commit()
    await db.refresh(db_label)
    return db_label


async def list_scenario_labels(
    db: AsyncSession, simulation_id: int
) -> List[ScenarioLabel]:
    """
    List all labels for a simulation.

    Args:
        db: Database session
        simulation_id: Simulation record ID

    Returns:
        List of ScenarioLabel instances
    """
    result = await db.execute(
        select(ScenarioLabel)
        .where(ScenarioLabel.simulation_id == simulation_id)
        .order_by(ScenarioLabel.created_at)
    )
    return list(result.scalars().all())


async def update_scenario_label(
    db: AsyncSession, label_id: int, update_data: dict
) -> Optional[ScenarioLabel]:
    """
    Update a scenario label.

    Args:
        db: Database session
        label_id: Label ID
        update_data: Fields to update

    Returns:
        Updated ScenarioLabel or None if not found
    """
    result = await db.execute(
        select(ScenarioLabel).where(ScenarioLabel.id == label_id)
    )
    label = result.scalar_one_or_none()

    if not label:
        return None

    for key, value in update_data.items():
        if hasattr(label, key) and value is not None:
            setattr(label, key, value)

    await db.commit()
    await db.refresh(label)
    return label


async def delete_scenario_label(db: AsyncSession, label_id: int) -> bool:
    """
    Delete a scenario label.

    Args:
        db: Database session
        label_id: Label ID

    Returns:
        True if deleted, False if not found
    """
    result = await db.execute(
        delete(ScenarioLabel).where(ScenarioLabel.id == label_id)
    )
    await db.commit()
    return result.rowcount > 0


# =============================================================================
# Export Tasks CRUD
# =============================================================================

async def create_export_task(
    db: AsyncSession, task: ExportTaskCreate
) -> ExportTask:
    """
    Create a new export task.

    Args:
        db: Database session
        task: Export task data

    Returns:
        Created ExportTask instance
    """
    db_task = ExportTask(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


async def update_export_task(
    db: AsyncSession, task_id: int, status: str, file_path: Optional[str] = None, record_count: Optional[int] = None
) -> Optional[ExportTask]:
    """
    Update an export task status.

    Args:
        db: Database session
        task_id: Task ID
        status: New status
        file_path: Optional file path update
        record_count: Optional record count update

    Returns:
        Updated ExportTask or None if not found
    """
    result = await db.execute(
        select(ExportTask).where(ExportTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        return None

    task.status = status
    if file_path is not None:
        task.file_path = file_path
    if record_count is not None:
        task.record_count = record_count

    await db.commit()
    await db.refresh(task)
    return task


async def get_export_task(db: AsyncSession, task_id: int) -> Optional[ExportTask]:
    """
    Get an export task by ID.

    Args:
        db: Database session
        task_id: Task ID

    Returns:
        ExportTask or None if not found
    """
    result = await db.execute(
        select(ExportTask).where(ExportTask.id == task_id)
    )
    return result.scalar_one_or_none()


async def list_export_tasks(
    db: AsyncSession, skip: int = 0, limit: int = 50, status: Optional[str] = None
) -> List[ExportTask]:
    """
    List export tasks.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter

    Returns:
        List of ExportTask instances
    """
    query = select(ExportTask)

    if status:
        query = query.where(ExportTask.status == status)

    query = query.order_by(ExportTask.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())
