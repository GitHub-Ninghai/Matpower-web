"""
SQLAlchemy ORM models for MATPOWER Web Backend.
Defines all database tables for simulation records, disturbances, time series, and exports.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from .database import Base


class SimulationRecord(Base):
    """
    Main simulation record table.
    Stores complete snapshots of simulation inputs and results.
    """
    __tablename__ = "simulation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_name: Mapped[str] = mapped_column(String(100), index=True)
    sim_type: Mapped[str] = mapped_column(String(20), index=True)  # PF, DCPF, OPF
    status: Mapped[str] = mapped_column(String(20), index=True)  # success, failed
    iterations: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    computation_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    input_snapshot: Mapped[str] = mapped_column(Text)  # JSON string
    result_snapshot: Mapped[str] = mapped_column(Text)  # JSON string
    system_summary: Mapped[str] = mapped_column(Text)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    disturbance_events: Mapped[list["DisturbanceEvent"]] = relationship(
        "DisturbanceEvent", back_populates="simulation", cascade="all, delete-orphan"
    )
    time_series_data: Mapped[list["TimeSeriesData"]] = relationship(
        "TimeSeriesData", back_populates="simulation", cascade="all, delete-orphan"
    )
    scenario_labels: Mapped[list["ScenarioLabel"]] = relationship(
        "ScenarioLabel", back_populates="simulation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SimulationRecord(id={self.id}, case={self.case_name}, type={self.sim_type}, status={self.status})>"


class DisturbanceEvent(Base):
    """
    Disturbance events table.
    Records perturbations applied during simulation.
    """
    __tablename__ = "disturbance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("simulation_records.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(50))  # line_outage, gen_outage, load_change, voltage_change
    target_type: Mapped[str] = mapped_column(String(20))  # bus, gen, branch
    target_id: Mapped[int] = mapped_column(Integer)
    parameter: Mapped[str] = mapped_column(String(50))  # Parameter name that was changed
    old_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    new_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    simulation: Mapped["SimulationRecord"] = relationship(
        "SimulationRecord", back_populates="disturbance_events"
    )

    def __repr__(self) -> str:
        return f"<DisturbanceEvent(id={self.id}, type={self.event_type}, target={self.target_type}:{self.target_id})>"


class TimeSeriesData(Base):
    """
    Time series data table.
    Stores system state snapshots at each time step for dynamic simulations.
    """
    __tablename__ = "time_series_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("simulation_records.id", ondelete="CASCADE"), index=True
    )
    step: Mapped[int] = mapped_column(Integer)
    bus_data: Mapped[str] = mapped_column(Text)  # JSON string
    gen_data: Mapped[str] = mapped_column(Text)  # JSON string
    branch_data: Mapped[str] = mapped_column(Text)  # JSON string
    summary: Mapped[str] = mapped_column(Text)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    simulation: Mapped["SimulationRecord"] = relationship(
        "SimulationRecord", back_populates="time_series_data"
    )

    def __repr__(self) -> str:
        return f"<TimeSeriesData(id={self.id}, sim_id={self.simulation_id}, step={self.step})>"


class ScenarioLabel(Base):
    """
    Scenario labels table.
    Stores manual or automatic labels for simulation scenarios.
    """
    __tablename__ = "scenario_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("simulation_records.id", ondelete="CASCADE"), index=True
    )
    label_type: Mapped[str] = mapped_column(String(50))  # normal, fault, overload, voltage_violation, corrected
    severity: Mapped[str] = mapped_column(String(20))  # low, medium, high, critical
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    simulation: Mapped["SimulationRecord"] = relationship(
        "SimulationRecord", back_populates="scenario_labels"
    )

    def __repr__(self) -> str:
        return f"<ScenarioLabel(id={self.id}, type={self.label_type}, severity={self.severity})>"


class ExportTask(Base):
    """
    Export task table.
    Tracks export jobs for different formats.
    """
    __tablename__ = "export_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    export_format: Mapped[str] = mapped_column(String(20))  # json, csv, training
    filter_params: Mapped[str] = mapped_column(Text)  # JSON string
    file_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, completed, failed
    record_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ExportTask(id={self.id}, format={self.export_format}, status={self.status})>"
