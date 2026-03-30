"""
Data service for MATPOWER Web Backend.
High-level business logic for simulation data management.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..db.crud import (
    create_simulation_record,
    get_simulation_record,
    list_simulation_records,
    delete_simulation_record,
    update_simulation_record,
    create_disturbance_event,
    list_disturbance_events,
    batch_create_disturbance_events,
    create_time_series_point,
    batch_create_time_series,
    get_time_series,
    create_scenario_label,
    list_scenario_labels,
    delete_scenario_label,
)
from ..db.models import SimulationRecord


class DataService:
    """Service for managing simulation data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_simulation(
        self,
        case_name: str,
        sim_type: str,
        input_data: Dict[str, Any],
        result_data: Dict[str, Any],
        status: str = "success",
        iterations: Optional[int] = None,
        computation_time: Optional[float] = None,
        tags: Optional[str] = None,
    ) -> SimulationRecord:
        """
        Save a complete simulation record.

        Args:
            case_name: Name of the test case (e.g., "case14")
            sim_type: Simulation type (PF, DCPF, OPF)
            input_data: Complete input parameters (bus, gen, branch, etc.)
            result_data: Complete results (bus results, gen results, etc.)
            status: Simulation status (success, failed)
            iterations: Number of iterations
            computation_time: Computation time in seconds
            tags: Optional tags (comma-separated)

        Returns:
            Created SimulationRecord
        """
        from ..db.crud import SimulationRecordCreate

        # Build system summary
        system_summary = self._build_system_summary(result_data)

        record = SimulationRecordCreate(
            case_name=case_name,
            sim_type=sim_type,
            status=status,
            iterations=iterations,
            computation_time=computation_time,
            input_snapshot=json.dumps(input_data),
            result_snapshot=json.dumps(result_data),
            system_summary=json.dumps(system_summary),
            tags=tags,
        )

        return await create_simulation_record(self.db, record)

    def _build_system_summary(self, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a summary of system state from results.

        Args:
            result_data: Complete simulation results

        Returns:
            System summary dictionary
        """
        summary = {
            "total buses": len(result_data.get("bus", [])),
            "total generators": len(result_data.get("gen", [])),
            "total branches": len(result_data.get("branch", [])),
            "total generation_mw": 0.0,
            "total_load_mw": 0.0,
            "total_generation_mvar": 0.0,
            "total_load_mvar": 0.0,
            "max_loading_percent": 0.0,
            "violations": [],
        }

        # Calculate totals from bus data
        for bus in result_data.get("bus", []):
            # bus columns: bus_i, type, area, v_mag, v_ang, base_kv, zone, v_max, v_min
            # Load data is in separate matrices
            pass

        # Calculate generation totals
        for gen in result_data.get("gen", []):
            # gen columns: bus, pg, qg, qmax, qmin, vg, mbase, status, pmax, pmin
            summary["total_generation_mw"] += gen[1] if len(gen) > 1 else 0
            summary["total_generation_mvar"] += gen[2] if len(gen) > 2 else 0

        # Calculate branch loading
        max_loading = 0.0
        overloaded_branches = []

        for idx, branch in enumerate(result_data.get("branch", [])):
            # branch columns: fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
            # Flow data: pf, qf, pt, qt
            if len(branch) >= 15:
                rate_a = branch[5] if branch[5] > 0 else float('inf')
                pf_mw = abs(branch[13]) if len(branch) > 13 else 0
                pt_mw = abs(branch[15]) if len(branch) > 15 else 0

                if rate_a > 0 and rate_a != float('inf'):
                    loading = max(pf_mw, pt_mw) / rate_a * 100
                    if loading > max_loading:
                        max_loading = loading

                    if loading > 100:
                        overloaded_branches.append({
                            "from_bus": int(branch[0]),
                            "to_bus": int(branch[1]),
                            "loading_percent": loading,
                        })

        summary["max_loading_percent"] = max_loading

        # Check voltage violations
        voltage_violations = []
        for bus in result_data.get("bus", []):
            if len(bus) >= 10:
                v_mag = bus[7]
                v_min = bus[11] if len(bus) > 11 else 0.95
                v_max = bus[12] if len(bus) > 12 else 1.05

                if v_mag < v_min or v_mag > v_max:
                    voltage_violations.append({
                        "bus": int(bus[0]),
                        "voltage": v_mag,
                        "min": v_min,
                        "max": v_max,
                    })

        if overloaded_branches:
            summary["violations"].append({
                "type": "overload",
                "count": len(overloaded_branches),
                "details": overloaded_branches,
            })

        if voltage_violations:
            summary["violations"].append({
                "type": "voltage",
                "count": len(voltage_violations),
                "details": voltage_violations,
            })

        return summary

    async def save_disturbance_sequence(
        self, simulation_id: int, disturbances: List[Dict[str, Any]]
    ) -> List:
        """
        Batch save disturbance events for a simulation.

        Args:
            simulation_id: Simulation record ID
            disturbances: List of disturbance dictionaries

        Returns:
            List of created disturbance events
        """
        from ..db.crud import DisturbanceEventCreate

        events = [
            DisturbanceEventCreate(
                simulation_id=simulation_id,
                event_type=d["event_type"],
                target_type=d["target_type"],
                target_id=d["target_id"],
                parameter=d.get("parameter", ""),
                old_value=d.get("old_value"),
                new_value=d.get("new_value"),
                description=d.get("description", ""),
            )
            for d in disturbances
        ]

        return await batch_create_disturbance_events(self.db, events)

    async def save_time_series(
        self, simulation_id: int, time_steps_data: List[Dict[str, Any]]
    ) -> List:
        """
        Batch save time series data for a simulation.

        Args:
            simulation_id: Simulation record ID
            time_steps_data: List of time step data dictionaries

        Returns:
            List of created time series data points
        """
        from ..db.crud import TimeSeriesDataCreate

        data_points = [
            TimeSeriesDataCreate(
                simulation_id=simulation_id,
                step=step["step"],
                bus_data=json.dumps(step["bus_data"]),
                gen_data=json.dumps(step["gen_data"]),
                branch_data=json.dumps(step["branch_data"]),
                summary=json.dumps(step.get("summary", {})),
            )
            for step in time_steps_data
        ]

        return await batch_create_time_series(self.db, data_points)

    async def query_simulations(
        self,
        filters: Dict[str, Any],
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[SimulationRecord], int]:
        """
        Query simulation records with advanced filtering.

        Args:
            filters: Filter parameters
                - case_name: str
                - sim_type: str
                - status: str
                - tags: str
                - start_date: datetime
                - end_date: datetime
            skip: Pagination offset
            limit: Maximum records to return

        Returns:
            Tuple of (records, total_count)
        """
        return await list_simulation_records(
            self.db,
            skip=skip,
            limit=limit,
            case_name=filters.get("case_name"),
            sim_type=filters.get("sim_type"),
            status=filters.get("status"),
            tags=filters.get("tags"),
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
        )

    async def get_simulation_detail(
        self, simulation_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete simulation details including disturbances and time series.

        Args:
            simulation_id: Simulation record ID

        Returns:
            Complete simulation data or None if not found
        """
        record = await get_simulation_record(self.db, simulation_id)
        if not record:
            return None

        disturbances = await list_disturbance_events(self.db, simulation_id)
        time_series = await get_time_series(self.db, simulation_id)
        labels = await list_scenario_labels(self.db, simulation_id)

        return {
            "id": record.id,
            "case_name": record.case_name,
            "sim_type": record.sim_type,
            "status": record.status,
            "iterations": record.iterations,
            "computation_time": record.computation_time,
            "input_snapshot": json.loads(record.input_snapshot),
            "result_snapshot": json.loads(record.result_snapshot),
            "system_summary": json.loads(record.system_summary),
            "created_at": record.created_at.isoformat(),
            "tags": record.tags,
            "disturbance_events": [
                {
                    "id": d.id,
                    "event_type": d.event_type,
                    "target_type": d.target_type,
                    "target_id": d.target_id,
                    "parameter": d.parameter,
                    "old_value": d.old_value,
                    "new_value": d.new_value,
                    "description": d.description,
                }
                for d in disturbances
            ],
            "time_series": [
                {
                    "id": t.id,
                    "step": t.step,
                    "bus_data": json.loads(t.bus_data),
                    "gen_data": json.loads(t.gen_data),
                    "branch_data": json.loads(t.branch_data),
                    "summary": json.loads(t.summary),
                }
                for t in time_series
            ],
            "labels": [
                {
                    "id": l.id,
                    "label_type": l.label_type,
                    "severity": l.severity,
                    "description": l.description,
                }
                for l in labels
            ],
        }

    async def auto_label_scenario(self, simulation_id: int) -> List[Dict[str, Any]]:
        """
        Automatically label a scenario based on system violations.

        Args:
            simulation_id: Simulation record ID

        Returns:
            List of created/updated labels
        """
        record = await get_simulation_record(self.db, simulation_id)
        if not record:
            return []

        summary = json.loads(record.system_summary)
        labels_created = []

        # Clear existing auto-generated labels
        existing_labels = await list_scenario_labels(self.db, simulation_id)
        for label in existing_labels:
            await delete_scenario_label(self.db, label.id)

        violations = summary.get("violations", [])

        if not violations:
            # Normal scenario
            label = await create_scenario_label(
                self.db,
                {
                    "simulation_id": simulation_id,
                    "label_type": "normal",
                    "severity": "low",
                    "description": "No violations detected",
                },
            )
            labels_created.append({"label_type": "normal", "severity": "low"})

        else:
            # Check for overloads
            for v in violations:
                if v["type"] == "overload":
                    severity = self._calculate_overload_severity(v["details"])
                    await create_scenario_label(
                        self.db,
                        {
                            "simulation_id": simulation_id,
                            "label_type": "overload",
                            "severity": severity,
                            "description": f"{v['count']} overloaded branch(es)",
                        },
                    )
                    labels_created.append({"label_type": "overload", "severity": severity})

                elif v["type"] == "voltage":
                    severity = self._calculate_voltage_severity(v["details"])
                    await create_scenario_label(
                        self.db,
                        {
                            "simulation_id": simulation_id,
                            "label_type": "voltage_violation",
                            "severity": severity,
                            "description": f"{v['count']} voltage violation(s)",
                        },
                    )
                    labels_created.append({"label_type": "voltage_violation", "severity": severity})

        # Check if it's a corrected scenario (has disturbances but no violations)
        disturbances = await list_disturbance_events(self.db, simulation_id)
        if disturbances and not violations:
            await create_scenario_label(
                self.db,
                {
                    "simulation_id": simulation_id,
                    "label_type": "corrected",
                    "severity": "medium",
                    "description": "Disturbances applied and successfully mitigated",
                },
            )
            labels_created.append({"label_type": "corrected", "severity": "medium"})

        return labels_created

    def _calculate_overload_severity(self, overloaded_branches: List[Dict]) -> str:
        """Calculate severity based on overload percentages."""
        max_loading = max(b["loading_percent"] for b in overloaded_branches)

        if max_loading > 150:
            return "critical"
        elif max_loading > 120:
            return "high"
        elif max_loading > 105:
            return "medium"
        else:
            return "low"

    def _calculate_voltage_severity(self, voltage_violations: List[Dict]) -> str:
        """Calculate severity based on voltage deviation."""
        max_deviation = 0.0

        for v in voltage_violations:
            deviation = min(
                abs(v["voltage"] - v["min"]),
                abs(v["voltage"] - v["max"])
            )
            max_deviation = max(max_deviation, deviation)

        if max_deviation > 0.1:
            return "critical"
        elif max_deviation > 0.05:
            return "high"
        elif max_deviation > 0.02:
            return "medium"
        else:
            return "low"

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics about simulation records.

        Returns:
            Statistics dictionary
        """
        from sqlalchemy import func

        # Total records
        total_result = await self.db.execute(
            select(func.count()).select_from(SimulationRecord)
        )
        total = total_result.scalar()

        # Records by case name
        case_result = await self.db.execute(
            select(SimulationRecord.case_name, func.count())
            .group_by(SimulationRecord.case_name)
            .order_by(func.count().desc())
        )
        by_case = [{"case": row[0], "count": row[1]} for row in case_result.all()]

        # Records by simulation type
        type_result = await self.db.execute(
            select(SimulationRecord.sim_type, func.count())
            .group_by(SimulationRecord.sim_type)
        )
        by_type = [{"type": row[0], "count": row[1]} for row in type_result.all()]

        # Records by status
        status_result = await self.db.execute(
            select(SimulationRecord.status, func.count())
            .group_by(SimulationRecord.status)
        )
        by_status = [{"status": row[0], "count": row[1]} for row in status_result.all()]

        # Recent records (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_result = await self.db.execute(
            select(func.count()).select_from(SimulationRecord)
            .where(SimulationRecord.created_at >= week_ago)
        )
        recent = recent_result.scalar()

        return {
            "total_records": total,
            "by_case": by_case,
            "by_sim_type": by_type,
            "by_status": by_status,
            "recent_week": recent,
        }
