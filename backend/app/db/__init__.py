"""
Database package for MATPOWER Web Backend.
Provides SQLAlchemy models, CRUD operations, and database session management.
"""

from .database import get_db, init_db, get_engine, Base
from .models import (
    SimulationRecord,
    DisturbanceEvent,
    TimeSeriesData,
    ScenarioLabel,
    ExportTask,
)
from .crud import (
    # Simulation records
    create_simulation_record,
    get_simulation_record,
    list_simulation_records,
    delete_simulation_record,
    # Disturbance events
    create_disturbance_event,
    list_disturbance_events,
    # Time series data
    create_time_series_point,
    batch_create_time_series,
    get_time_series,
    # Scenario labels
    create_scenario_label,
    list_scenario_labels,
    # Export tasks
    create_export_task,
    update_export_task,
)

__all__ = [
    # Database
    "get_db",
    "init_db",
    "get_engine",
    "Base",
    # Models
    "SimulationRecord",
    "DisturbanceEvent",
    "TimeSeriesData",
    "ScenarioLabel",
    "ExportTask",
    # CRUD
    "create_simulation_record",
    "get_simulation_record",
    "list_simulation_records",
    "delete_simulation_record",
    "create_disturbance_event",
    "list_disturbance_events",
    "create_time_series_point",
    "batch_create_time_series",
    "get_time_series",
    "create_scenario_label",
    "list_scenario_labels",
    "create_export_task",
    "update_export_task",
]
