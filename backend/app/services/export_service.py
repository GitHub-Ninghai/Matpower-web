"""
Export service for MATPOWER Web Backend.
Handles exporting simulation data in various formats including LLM training format.
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.crud import (
    list_simulation_records,
    get_simulation_record,
    list_disturbance_events,
    list_scenario_labels,
    create_export_task,
    update_export_task,
    get_export_task,
)


# Export directory
EXPORT_DIR = Path("E:/matpower-web/backend/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class ExportService:
    """Service for exporting simulation data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_json(
        self,
        filters: Dict[str, Any],
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export simulation records as JSON.

        Args:
            filters: Filter parameters for selecting records
            file_name: Optional custom file name

        Returns:
            Export result with file path and record count
        """
        # Query records
        records, total = await list_simulation_records(
            self.db,
            skip=0,
            limit=10000,  # Large limit for export
            case_name=filters.get("case_name"),
            sim_type=filters.get("sim_type"),
            status=filters.get("status"),
            tags=filters.get("tags"),
        )

        # Build export data
        export_data = {
            "metadata": {
                "export_time": datetime.utcnow().isoformat(),
                "total_records": len(records),
                "filters": filters,
            },
            "records": [],
        }

        for record in records:
            disturbances = await list_disturbance_events(self.db, record.id)
            labels = await list_scenario_labels(self.db, record.id)

            record_data = {
                "metadata": {
                    "id": record.id,
                    "case": record.case_name,
                    "sim_type": record.sim_type,
                    "timestamp": record.created_at.isoformat(),
                    "status": record.status,
                    "iterations": record.iterations,
                    "computation_time": record.computation_time,
                    "tags": record.tags,
                },
                "input": json.loads(record.input_snapshot),
                "result": json.loads(record.result_snapshot),
                "system_summary": json.loads(record.system_summary),
                "disturbances": [
                    {
                        "type": d.event_type,
                        "target_type": d.target_type,
                        "target_id": d.target_id,
                        "parameter": d.parameter,
                        "old_value": d.old_value,
                        "new_value": d.new_value,
                        "description": d.description,
                    }
                    for d in disturbances
                ],
                "labels": [l.label_type for l in labels],
            }
            export_data["records"].append(record_data)

        # Write to file
        if not file_name:
            file_name = f"matpower_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

        file_path = EXPORT_DIR / file_name

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return {
            "file_path": str(file_path),
            "record_count": len(records),
            "format": "json",
        }

    async def export_csv(
        self,
        filters: Dict[str, Any],
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export simulation records as CSV files.

        Args:
            filters: Filter parameters for selecting records
            file_name: Optional base file name (without extension)

        Returns:
            Export result with file paths and record count
        """
        # Query records
        records, total = await list_simulation_records(
            self.db,
            skip=0,
            limit=10000,
            case_name=filters.get("case_name"),
            sim_type=filters.get("sim_type"),
            status=filters.get("status"),
        )

        if not file_name:
            base_name = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        else:
            base_name = Path(file_name).stem

        # Create a directory for this export
        export_subdir = EXPORT_DIR / f"csv_export_{base_name}"
        export_subdir.mkdir(parents=True, exist_ok=True)

        records_summary = []
        bus_rows = []
        gen_rows = []
        branch_rows = []

        for record in records:
            result = json.loads(record.result_snapshot)
            input_data = json.loads(record.input_snapshot)

            # Summary row
            records_summary.append({
                "id": record.id,
                "case_name": record.case_name,
                "sim_type": record.sim_type,
                "status": record.status,
                "iterations": record.iterations,
                "computation_time": record.computation_time,
                "created_at": record.created_at.isoformat(),
                "tags": record.tags,
            })

            # Bus data
            for bus in input_data.get("bus", []):
                bus_result = next(
                    (b for b in result.get("bus", []) if int(b[0]) == int(bus[0])),
                    None
                )
                if bus_result:
                    bus_rows.append({
                        "record_id": record.id,
                        "case_name": record.case_name,
                        "bus_i": int(bus[0]),
                        "vm_before": float(bus_result[7]) if len(bus_result) > 7 else None,
                        "va_before": float(bus_result[8]) if len(bus_result) > 8 else None,
                        "pd": float(bus[2]) if len(bus) > 2 else None,
                        "qd": float(bus[3]) if len(bus) > 3 else None,
                    })

            # Generator data
            for gen in result.get("gen", []):
                gen_rows.append({
                    "record_id": record.id,
                    "case_name": record.case_name,
                    "gen_bus": int(gen[0]),
                    "pg": float(gen[1]) if len(gen) > 1 else None,
                    "qg": float(gen[2]) if len(gen) > 2 else None,
                    "pmax": float(gen[8]) if len(gen) > 8 else None,
                    "pmin": float(gen[9]) if len(gen) > 9 else None,
                })

            # Branch data
            for branch in result.get("branch", []):
                rate_a = branch[5] if len(branch) > 5 else 0
                pf = abs(branch[13]) if len(branch) > 13 else 0
                loading = (pf / rate_a * 100) if rate_a > 0 else 0

                branch_rows.append({
                    "record_id": record.id,
                    "case_name": record.case_name,
                    "f_bus": int(branch[0]),
                    "t_bus": int(branch[1]),
                    "pf": float(branch[13]) if len(branch) > 13 else None,
                    "qf": float(branch[14]) if len(branch) > 14 else None,
                    "pt": float(branch[15]) if len(branch) > 15 else None,
                    "qt": float(branch[16]) if len(branch) > 16 else None,
                    "loading_percent": loading,
                })

        # Write CSV files
        def write_csv(path: Path, rows: List[Dict], fieldnames: List[str]):
            with open(path, "w", newline="", encoding="utf-8") as f:
                if rows:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

        write_csv(
            export_subdir / "records.csv",
            records_summary,
            ["id", "case_name", "sim_type", "status", "iterations", "computation_time", "created_at", "tags"]
        )

        write_csv(
            export_subdir / "buses.csv",
            bus_rows,
            ["record_id", "case_name", "bus_i", "vm_before", "va_before", "pd", "qd"]
        )

        write_csv(
            export_subdir / "generators.csv",
            gen_rows,
            ["record_id", "case_name", "gen_bus", "pg", "qg", "pmax", "pmin"]
        )

        write_csv(
            export_subdir / "branches.csv",
            branch_rows,
            ["record_id", "case_name", "f_bus", "t_bus", "pf", "qf", "pt", "qt", "loading_percent"]
        )

        return {
            "file_path": str(export_subdir),
            "record_count": len(records),
            "format": "csv",
            "files": ["records.csv", "buses.csv", "generators.csv", "branches.csv"],
        }

    async def export_training_format(
        self,
        filters: Dict[str, Any],
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Export simulation records as LLM training data (conversation format).

        Generates state-description -> action -> result triplets suitable for
        training large language models on power system scheduling tasks.

        Args:
            filters: Filter parameters for selecting records
            file_name: Optional custom file name

        Returns:
            Export result with file path and record count
        """
        # Query records
        records, total = await list_simulation_records(
            self.db,
            skip=0,
            limit=10000,
            case_name=filters.get("case_name"),
            sim_type=filters.get("sim_type"),
            status="success",  # Only successful simulations for training
        )

        training_data = []

        for record in records:
            disturbances = await list_disturbance_events(self.db, record.id)
            labels = await list_scenario_labels(self.db, record.id)

            input_data = json.loads(record.input_snapshot)
            result = json.loads(record.result_snapshot)
            summary = json.loads(record.system_summary)

            # Generate natural language descriptions
            state_description = self._generate_state_description(input_data, result, record)
            action_description = self._generate_action_description(disturbances, input_data)
            result_description = self._generate_result_description(summary, result)

            # Build conversation
            conversation = {
                "conversations": [
                    {
                        "role": "system",
                        "content": (
                            "You are a power system scheduling assistant. "
                            "You help operators understand system states, identify issues, "
                            "and suggest control actions to maintain system security."
                        )
                    },
                    {
                        "role": "user",
                        "content": state_description
                    }
                ],
                "metadata": {
                    "case": record.case_name,
                    "sim_type": record.sim_type,
                    "record_id": record.id,
                    "timestamp": record.created_at.isoformat(),
                    "disturbance_count": len(disturbances),
                    "labels": [l.label_type for l in labels],
                }
            }

            # Add assistant response based on scenario
            if disturbances:
                conversation["conversations"].append({
                    "role": "assistant",
                    "content": action_description
                })
                conversation["conversations"].append({
                    "role": "user",
                    "content": "What is the result of these actions?"
                })

            conversation["conversations"].append({
                "role": "assistant",
                "content": result_description
            })

            training_data.append(conversation)

        # Write to file
        if not file_name:
            file_name = f"matpower_training_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"

        file_path = EXPORT_DIR / file_name

        with open(file_path, "w", encoding="utf-8") as f:
            for item in training_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        return {
            "file_path": str(file_path),
            "record_count": len(training_data),
            "format": "training",
        }

    def _generate_state_description(
        self,
        input_data: Dict[str, Any],
        result: Dict[str, Any],
        record,
    ) -> str:
        """Generate natural language description of system state."""
        buses = input_data.get("bus", [])
        gens = input_data.get("gen", [])
        branches = input_data.get("branch", [])

        total_load = sum(b[2] for b in buses if len(b) > 2)  # PD
        total_gen = sum(g[1] for g in result.get("gen", []) if len(g) > 1)  # PG

        desc = f"System: {record.case_name} (IEEE {len(buses)}-bus system)\n\n"
        desc += f"Current state:\n"
        desc += f"- Total load: {total_load:.1f} MW\n"
        desc += f"- Total generation: {total_gen:.1f} MW\n"
        desc += f"- Number of generators: {len(gens)}\n"
        desc += f"- Number of transmission lines: {len(branches)}\n\n"

        # Add key voltage information
        desc += "Voltage levels (key buses):\n"
        for bus in result.get("bus", [])[:5]:  # First 5 buses
            if len(bus) > 8:
                desc += f"- Bus {int(bus[0])}: {bus[7]:.3f} pu\n"

        return desc

    def _generate_action_description(
        self,
        disturbances: List,
        input_data: Dict[str, Any],
    ) -> str:
        """Generate description of control actions taken."""
        if not disturbances:
            return "No control actions were applied. The system is in its base case state."

        desc = "Control actions applied:\n\n"

        for d in disturbances:
            if d.event_type == "load_change":
                desc += f"- Load change at {d.target_type} {d.target_id}: "
                desc += f"{d.parameter} adjusted from {d.old_value} to {d.new_value}\n"
            elif d.event_type == "gen_outage":
                desc += f"- Generator {d.target_id} taken out of service\n"
            elif d.event_type == "line_outage":
                desc += f"- Transmission line from bus {d.target_id} disconnected\n"
            elif d.event_type == "voltage_change":
                desc += f"- Voltage setpoint at {d.target_type} {d.target_id}: "
                desc += f"{d.parameter} adjusted from {d.old_value} to {d.new_value} pu\n"

        return desc

    def _generate_result_description(
        self,
        summary: Dict[str, Any],
        result: Dict[str, Any],
    ) -> str:
        """Generate description of simulation results."""
        desc = "Simulation results:\n\n"

        # Generation summary
        total_gen = summary.get("total_generation_mw", 0)
        desc += f"- Total generation: {total_gen:.1f} MW\n"

        # Loading
        max_loading = summary.get("max_loading_percent", 0)
        desc += f"- Maximum line loading: {max_loading:.1f}%\n"

        # Violations
        violations = summary.get("violations", [])
        if violations:
            desc += "\n⚠️ Violations detected:\n"
            for v in violations:
                if v["type"] == "overload":
                    desc += f"- {v['count']} overloaded branch(es)\n"
                elif v["type"] == "voltage":
                    desc += f"- {v['count']} voltage violation(s)\n"
        else:
            desc += "\n✅ No violations - system is secure\n"

        # Iterations
        desc += f"\nSolution converged in {summary.get('iterations', 'N/A')} iterations"

        return desc

    async def create_export_task(
        self,
        export_format: str,
        filter_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create an export task and execute it.

        Args:
            export_format: Format to export (json, csv, training)
            filter_params: Filter parameters for selecting records

        Returns:
            Export task result
        """
        # Create export task record
        from ..db.crud import ExportTaskCreate

        file_name = f"temp_{export_format}_{datetime.utcnow().timestamp()}.json"
        task = await create_export_task(
            self.db,
            ExportTaskCreate(
                export_format=export_format,
                filter_params=json.dumps(filter_params),
                file_path=file_name,
            )
        )

        try:
            # Execute export
            if export_format == "json":
                result = await self.export_json(filter_params)
            elif export_format == "csv":
                result = await self.export_csv(filter_params)
            elif export_format == "training":
                result = await self.export_training_format(filter_params)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

            # Update task with success
            await update_export_task(
                self.db,
                task.id,
                status="completed",
                file_path=result["file_path"],
                record_count=result["record_count"],
            )

            return {
                "task_id": task.id,
                "status": "completed",
                **result,
            }

        except Exception as e:
            # Update task with failure
            await update_export_task(self.db, task.id, status="failed")
            raise e

    async def get_export_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the status of an export task.

        Args:
            task_id: Task ID

        Returns:
            Task status or None if not found
        """
        task = await get_export_task(self.db, task_id)
        if not task:
            return None

        return {
            "id": task.id,
            "format": task.export_format,
            "file_path": task.file_path,
            "status": task.status,
            "record_count": task.record_count,
            "created_at": task.created_at.isoformat(),
        }

    async def list_export_tasks(
        self, skip: int = 0, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List export tasks.

        Args:
            skip: Pagination offset
            limit: Maximum records to return

        Returns:
            List of export tasks
        """
        from ..db.crud import list_export_tasks as crud_list_tasks

        tasks = await crud_list_tasks(self.db, skip=skip, limit=limit)

        return [
            {
                "id": t.id,
                "format": t.export_format,
                "file_path": t.file_path,
                "status": t.status,
                "record_count": t.record_count,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ]
