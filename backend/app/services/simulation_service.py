"""
Simulation Service
Business logic layer for power system simulations
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.engine import get_engine
from app.models.schemas import (
    CaseData, SimulationResult, SystemSummary,
    BusData, GeneratorData, BranchData
)

logger = logging.getLogger(__name__)


class SimulationService:
    """Service for handling simulation operations"""

    def __init__(self):
        """Initialize the simulation service"""
        self.engine = get_engine()

    def list_available_cases(self) -> List[Dict[str, Any]]:
        """
        Get list of all available MATPOWER test cases

        Returns:
            List of case summaries
        """
        try:
            return self.engine.list_cases()
        except Exception as e:
            logger.error(f"Error listing cases: {e}")
            return []

    def load_case_by_name(self, case_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific case by name

        Args:
            case_name: Name of the case (e.g., 'case9')

        Returns:
            Case data dictionary
        """
        try:
            return self.engine.load_case(case_name)
        except Exception as e:
            logger.error(f"Error loading case {case_name}: {e}")
            return None

    def run_simulation(
        self,
        case_name: str,
        sim_type: str = "PF",
        algorithm: str = "NR",
        modifications: Optional[Dict[str, Any]] = None
    ) -> SimulationResult:
        """
        Run a power system simulation

        Args:
            case_name: Name of the case to simulate
            sim_type: Type of simulation ('PF', 'DCPF', 'OPF')
            algorithm: Power flow algorithm (for PF)
            modifications: Optional modifications to apply

        Returns:
            SimulationResult object
        """
        start_time = datetime.now()

        try:
            # Load the case
            case_data = self.load_case_by_name(case_name)
            if not case_data:
                return SimulationResult(
                    success=False,
                    message=f"Failed to load case: {case_name}",
                    iterations=0,
                    et=0.0
                )

            # Apply modifications if provided
            if modifications:
                case_data = self.engine.apply_modifications(case_data, modifications)

            # Run the appropriate simulation
            if sim_type == "DCPF":
                raw_result = self.engine.run_dc_power_flow(case_data)
            elif sim_type == "OPF":
                raw_result = self.engine.run_opf(case_data)
            else:  # Default to AC power flow
                raw_result = self.engine.run_power_flow(case_data, algorithm)

            # Build result object
            elapsed = datetime.now() - start_time
            elapsed_seconds = elapsed.total_seconds()

            if not raw_result.get('success'):
                return SimulationResult(
                    success=False,
                    message=raw_result.get('error', 'Simulation failed'),
                    iterations=raw_result.get('iterations', 0),
                    et=elapsed_seconds
                )

            # Convert result data to Pydantic models
            bus_results = [BusData(**b) for b in raw_result.get('bus_results', [])]
            gen_results = [GeneratorData(**g) for g in raw_result.get('gen_results', [])]
            branch_results = [BranchData(**br) for br in raw_result.get('branch_results', [])]

            # Calculate system summary
            system_summary = self._calculate_system_summary(
                case_data['base_mva'],
                bus_results,
                gen_results,
                branch_results
            )

            result = SimulationResult(
                success=True,
                converged=raw_result.get('converged', True),
                iterations=raw_result.get('iterations', 0),
                et=elapsed_seconds,
                message="Simulation completed successfully",
                bus_results=bus_results,
                gen_results=gen_results,
                branch_results=branch_results,
                system_summary=system_summary,
                total_cost=raw_result.get('total_cost')
            )

            return result

        except Exception as e:
            logger.error(f"Simulation error: {e}")
            elapsed = datetime.now() - start_time
            return SimulationResult(
                success=False,
                message=f"Simulation error: {str(e)}",
                iterations=0,
                et=elapsed.total_seconds()
            )

    def _calculate_system_summary(
        self,
        base_mva: float,
        bus_results: List[BusData],
        gen_results: List[GeneratorData],
        branch_results: List[BranchData]
    ) -> SystemSummary:
        """
        Calculate system summary statistics

        Args:
            base_mva: System base MVA
            bus_results: Bus results from simulation
            gen_results: Generator results from simulation
            branch_results: Branch results from simulation

        Returns:
            SystemSummary object
        """
        # Calculate total generation (MW and MVAr)
        total_pg = sum(g.pg for g in gen_results if g.gen_status == 1)
        total_qg = sum(g.qg for g in gen_results if g.gen_status == 1)

        # Calculate total load (MW and MVAr)
        total_pd = sum(b.pd for b in bus_results)
        total_qd = sum(b.qd for b in bus_results)

        # Calculate total losses (generation - load)
        total_losses = total_pg - total_pd

        # Find min/max voltage buses
        vm_values = [(b.bus_i, b.vm) for b in bus_results]
        min_voltage_bus, min_voltage = min(vm_values, key=lambda x: x[1])
        max_voltage_bus, max_voltage = max(vm_values, key=lambda x: x[1])

        return SystemSummary(
            total_generation=total_pg,
            total_load=total_pd,
            total_losses=total_losses,
            total_reactive_gen=total_qg,
            total_reactive_load=total_qd,
            min_voltage=min_voltage,
            max_voltage=max_voltage,
            min_voltage_bus=min_voltage_bus,
            max_voltage_bus=max_voltage_bus
        )

    def apply_disturbance(
        self,
        case_name: str,
        disturbance_type: str,
        target_id: Dict[str, Any],
        new_value: Optional[float] = None
    ) -> SimulationResult:
        """
        Apply a disturbance and re-run simulation

        Args:
            case_name: Base case name
            disturbance_type: Type of disturbance ('line_outage', 'gen_outage', etc.)
            target_id: Target identifier (e.g., {f_bus, t_bus} for line)
            new_value: New value for parameter changes

        Returns:
            SimulationResult after disturbance
        """
        try:
            # Validate inputs
            if not disturbance_type:
                return SimulationResult(
                    success=False,
                    message="disturbance_type is required",
                    iterations=0,
                    et=0.0
                )

            if target_id is None:
                return SimulationResult(
                    success=False,
                    message="target_id is required and must not be None",
                    iterations=0,
                    et=0.0
                )

            if not isinstance(target_id, dict):
                return SimulationResult(
                    success=False,
                    message=f"target_id must be a dict, got {type(target_id).__name__}",
                    iterations=0,
                    et=0.0
                )

            # Load the base case
            case_data = self.load_case_by_name(case_name)
            if not case_data:
                return SimulationResult(
                    success=False,
                    message=f"Failed to load case: {case_name}",
                    iterations=0,
                    et=0.0
                )

            logger.info(
                f"Applying disturbance: type={disturbance_type}, "
                f"target_id={target_id}, new_value={new_value}"
            )

            # Build modifications based on disturbance type
            modifications = self._build_disturbance_modifications(
                case_data, disturbance_type, target_id, new_value
            )

            if not modifications:
                return SimulationResult(
                    success=False,
                    message=f"Could not build modifications for disturbance type '{disturbance_type}' "
                            f"with target_id={target_id}",
                    iterations=0,
                    et=0.0
                )

            logger.info(f"Built modifications: {modifications}")

            # Run simulation with modifications
            return self.run_simulation(
                case_name=case_name,
                sim_type="PF",
                modifications=modifications
            )

        except Exception as e:
            logger.error(f"Disturbance application error: {e}", exc_info=True)
            return SimulationResult(
                success=False,
                message=f"Disturbance error: {str(e)}",
                iterations=0,
                et=0.0
            )

    def _build_disturbance_modifications(
        self,
        case_data: Dict[str, Any],
        disturbance_type: str,
        target_id: Dict[str, Any],
        new_value: Optional[float]
    ) -> Dict[str, Any]:
        """
        Build modification dict for disturbance application.

        Returns a dict with keys from {'bus', 'gen', 'branch', 'outages'}.
        Each value is a list of modification dicts (for bus/gen/branch)
        or an outage descriptor dict (for outages).
        """
        # Guard against None target_id
        if target_id is None:
            target_id = {}

        modifications: Dict[str, Any] = {}

        if disturbance_type == "line_outage":
            # Set branch status to 0 (disconnected)
            br_idx = None
            if 'index' in target_id and target_id['index'] is not None:
                br_idx = int(target_id['index'])
            else:
                f_bus = target_id.get('f_bus')
                t_bus = target_id.get('t_bus')
                if f_bus is not None and t_bus is not None:
                    for idx, branch in enumerate(case_data['branch']):
                        if branch['f_bus'] == int(f_bus) and branch['t_bus'] == int(t_bus):
                            br_idx = idx
                            break

            if br_idx is not None:
                modifications['branch'] = [{
                    'index': br_idx,
                    'field': 'br_status',
                    'value': 0
                }]

        elif disturbance_type == "gen_outage":
            # Set generator offline: gen_status=0, pg=0, qg=0
            gen_idx = None
            if 'index' in target_id and target_id['index'] is not None:
                gen_idx = int(target_id['index'])
            else:
                gen_bus = target_id.get('gen_bus')
                if gen_bus is not None:
                    for idx, gen in enumerate(case_data['gen']):
                        if gen['gen_bus'] == int(gen_bus):
                            gen_idx = idx
                            break

            if gen_idx is not None:
                modifications['gen'] = [
                    {'index': gen_idx, 'field': 'gen_status', 'value': 0},
                    {'index': gen_idx, 'field': 'pg', 'value': 0.0},
                    {'index': gen_idx, 'field': 'qg', 'value': 0.0},
                ]

        elif disturbance_type == "load_change":
            # Modify active load at specified bus
            bus_idx = target_id.get('bus_index') or target_id.get('index')
            if bus_idx is not None:
                bus_idx = int(bus_idx)
                change_percent = new_value if new_value is not None else 0
                current_pd = case_data['bus'][bus_idx]['pd']
                modifications['bus'] = [{
                    'index': bus_idx,
                    'field': 'pd',
                    'value': current_pd * (1 + change_percent / 100)
                }]

        elif disturbance_type in ("voltage_change", "voltage_adjust"):
            # Modify voltage setpoint at generator
            gen_idx = target_id.get('gen_index') or target_id.get('index')
            if gen_idx is not None:
                gen_idx = int(gen_idx)
                new_vm = new_value if new_value is not None else 1.0
                modifications['gen'] = [{
                    'index': gen_idx,
                    'field': 'vg',
                    'value': new_vm
                }]

        return modifications

    def get_case_metadata(self, case_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a case without loading full data

        Args:
            case_name: Name of the case

        Returns:
            Metadata dictionary
        """
        try:
            cases = self.list_available_cases()
            for case in cases:
                if case['name'] == case_name:
                    return case
            return None
        except Exception as e:
            logger.error(f"Error getting case metadata: {e}")
            return None


# Global service instance
_service_instance: Optional[SimulationService] = None


def get_simulation_service() -> SimulationService:
    """Get or create the global simulation service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = SimulationService()
    return _service_instance
