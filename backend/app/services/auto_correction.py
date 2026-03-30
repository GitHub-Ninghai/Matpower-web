"""
Automatic correction system for post-disturbance remedial actions.

This module provides functionality to automatically correct constraint violations
using Optimal Power Flow (OPF) and suggest load shedding when necessary.
"""

import copy
import numpy as np
from typing import Dict, List, Optional, Any
from .disturbance import (
    DisturbanceConfig,
    DisturbanceResult,
    Violation,
    ViolationSeverity
)


# Simulation engine interface - TODO: Replace with actual implementation
class SimulationEngineInterface:
    """
    Interface for the simulation engine.

    This is a placeholder interface that will be replaced by the actual
    implementation in engine.py during integration.
    """

    def run_power_flow(self, case_data: Dict, algorithm: str = 'NR') -> Dict:
        """
        Run power flow analysis.

        Args:
            case_data: MATPOWER case dictionary
            algorithm: Power flow algorithm ('NR' = Newton-Raphson)

        Returns:
            Dictionary with power flow results
        """
        # TODO: Implement actual power flow computation
        raise NotImplementedError(
            "Simulation engine not yet integrated. "
            "This will be replaced by engine.py implementation."
        )

    def run_opf(self, case_data: Dict, opf_type: str = 'AC') -> Dict:
        """
        Run Optimal Power Flow analysis.

        Args:
            case_data: MATPOWER case dictionary
            opf_type: Type of OPF ('AC' or 'DC')

        Returns:
            Dictionary with OPF results including optimal dispatch
        """
        # TODO: Implement actual OPF computation
        raise NotImplementedError(
            "Simulation engine not yet integrated. "
            "This will be replaced by engine.py implementation."
        )


class AutoCorrection:
    """
    Automatic correction system for post-disturbance remedial actions.

    This class provides methods to correct constraint violations using OPF,
    generate correction reports, and suggest load shedding when OPF fails.
    """

    def __init__(self, simulation_engine: Optional[SimulationEngineInterface] = None):
        """
        Initialize the auto-correction system.

        Args:
            simulation_engine: Optional simulation engine instance.
                             If None, uses placeholder interface.
        """
        self.engine = simulation_engine or SimulationEngineInterface()

    def correct_with_opf(
        self,
        case_data: Dict,
        disturbance_result: DisturbanceResult
    ) -> Dict[str, Any]:
        """
        Apply OPF-based correction to a disturbed case.

        This method runs OPF on the post-disturbance case to find optimal
        generator dispatch that resolves violations while minimizing cost.

        Args:
            case_data: Post-disturbance case data
            disturbance_result: Result from disturbance injection

        Returns:
            Dictionary with correction results including:
                - success: Whether correction was successful
                - corrected_case: Case data after OPF correction
                - dispatch_changes: List of generator output changes
                - cost_change: Difference in generation cost
                - violations_resolved: List of resolved violations
                - remaining_violations: List of remaining violations
        """
        from .disturbance_engine import DisturbanceEngine

        engine = DisturbanceEngine()

        # Store original disturbed case
        disturbed_case = copy.deepcopy(case_data)

        # Check if there are violations to correct
        if not disturbance_result.violations:
            return {
                'success': True,
                'message': 'No violations to correct',
                'corrected_case': disturbed_case,
                'dispatch_changes': [],
                'cost_change': 0.0,
                'violations_resolved': [],
                'remaining_violations': []
            }

        try:
            # Run OPF to find optimal corrective dispatch
            opf_result = self.engine.run_opf(disturbed_case, opf_type='AC')

            if not opf_result.get('success', False):
                # OPF failed - try DC OPF as fallback
                opf_result = self.engine.run_opf(disturbed_case, opf_type='DC')

                if not opf_result.get('success', False):
                    return {
                        'success': False,
                        'message': 'OPF failed to converge',
                        'corrected_case': None,
                        'dispatch_changes': [],
                        'cost_change': 0.0,
                        'violations_resolved': [],
                        'remaining_violations': disturbance_result.violations
                    }

            # Extract corrected case
            corrected_case = opf_result.get('case', disturbed_case)

            # Generate correction report
            report = self.generate_correction_report(
                case_data,
                disturbed_case,
                corrected_case,
                opf_result
            )

            # Check for remaining violations
            pf_result = self.engine.run_power_flow(corrected_case)
            remaining_violations = engine.detect_violations(corrected_case, pf_result)

            report['remaining_violations'] = [v.dict() for v in remaining_violations]
            report['violations_resolved'] = [
                v.dict() for v in disturbance_result.violations
                if not self._is_same_violation(v, remaining_violations)
            ]

            report['success'] = len(remaining_violations) == 0

            return report

        except NotImplementedError:
            # Placeholder for development phase
            return {
                'success': False,
                'message': 'Simulation engine not yet integrated',
                'corrected_case': None,
                'dispatch_changes': [],
                'cost_change': 0.0,
                'violations_resolved': [],
                'remaining_violations': [v.dict() for v in disturbance_result.violations]
            }

    def _is_same_violation(self, violation: Violation, remaining: List[Violation]) -> bool:
        """Check if a violation still exists in remaining violations."""
        for v in remaining:
            if (v.type == violation.type and
                v.target_type == violation.target_type and
                v.target_index == violation.target_index and
                v.parameter == violation.parameter):
                return True
        return False

    def generate_correction_report(
        self,
        original_case: Dict,
        disturbed_case: Dict,
        corrected_case: Dict,
        opf_result: Dict
    ) -> Dict[str, Any]:
        """
        Generate a detailed correction report.

        The report compares generator dispatch before and after correction,
        calculates cost changes, and identifies which violations were resolved.

        Args:
            original_case: Pre-disturbance case data
            disturbed_case: Post-disturbance case data (before correction)
            corrected_case: Post-OPF case data
            opf_result: OPF solution with cost information

        Returns:
            Dictionary containing the correction report
        """
        # Extract generator data
        gen_disturbed = disturbed_case.get('gen', np.array([]))
        gen_corrected = corrected_case.get('gen', np.array([]))

        from .disturbance_engine import DisturbanceEngine
        engine = DisturbanceEngine()

        pg_idx = engine.GEN_COLUMNS['pg']
        qg_idx = engine.GEN_COLUMNS['qg']

        dispatch_changes = []
        total_pg_change = 0.0
        total_qg_change = 0.0

        for i in range(len(gen_corrected)):
            old_pg = float(gen_disturbed[i, pg_idx]) if i < len(gen_disturbed) else 0.0
            new_pg = float(gen_corrected[i, pg_idx])
            old_qg = float(gen_disturbed[i, qg_idx]) if i < len(gen_disturbed) else 0.0
            new_qg = float(gen_corrected[i, qg_idx])

            pg_change = new_pg - old_pg
            qg_change = new_qg - old_qg

            if abs(pg_change) > 0.001 or abs(qg_change) > 0.001:
                dispatch_changes.append({
                    'gen_index': i,
                    'gen_bus': int(gen_corrected[i, engine.GEN_COLUMNS['gen_bus']]),
                    'old_pg': old_pg,
                    'new_pg': new_pg,
                    'pg_change': pg_change,
                    'old_qg': old_qg,
                    'new_qg': new_qg,
                    'qg_change': qg_change
                })

            total_pg_change += abs(pg_change)
            total_qg_change += abs(qg_change)

        # Calculate cost change
        original_cost = opf_result.get('original_cost', 0.0)
        corrected_cost = opf_result.get('cost', 0.0)
        cost_change = corrected_cost - original_cost
        cost_change_percent = (cost_change / original_cost * 100) if original_cost > 0 else 0.0

        # Voltage setpoint changes
        voltage_changes = []
        vg_idx = engine.GEN_COLUMNS['vg']

        for i in range(len(gen_corrected)):
            if i < len(gen_disturbed):
                old_vg = float(gen_disturbed[i, vg_idx])
                new_vg = float(gen_corrected[i, vg_idx])

                if abs(new_vg - old_vg) > 0.001:
                    voltage_changes.append({
                        'gen_index': i,
                        'gen_bus': int(gen_corrected[i, engine.GEN_COLUMNS['gen_bus']]),
                        'old_vg': old_vg,
                        'new_vg': new_vg,
                        'vg_change': new_vg - old_vg
                    })

        return {
            'dispatch_changes': dispatch_changes,
            'voltage_changes': voltage_changes,
            'total_pg_change': total_pg_change,
            'total_qg_change': total_qg_change,
            'original_cost': original_cost,
            'corrected_cost': corrected_cost,
            'cost_change': cost_change,
            'cost_change_percent': cost_change_percent,
            'opf_iterations': opf_result.get('iterations', 0),
            'summary': {
                'generators_adjusted': len(dispatch_changes),
                'voltage_setpoints_adjusted': len(voltage_changes),
                'total_adjustment_mw': total_pg_change
            }
        }

    def suggest_load_shedding(
        self,
        case_data: Dict,
        violations: List[Violation]
    ) -> Dict[str, Any]:
        """
        Suggest load shedding when OPF cannot resolve all violations.

        This method identifies which buses should shed load and by how much
        to resolve remaining violations.

        Args:
            case_data: Current case data with violations
            violations: List of remaining violations after OPF

        Returns:
            Dictionary with load shedding suggestions
        """
        from .disturbance_engine import DisturbanceEngine

        engine = DisturbanceEngine()
        bus = case_data.get('bus', np.array([]))

        if len(bus) == 0:
            return {'suggestions': [], 'total_shedding_mw': 0.0}

        pd_idx = engine.BUS_COLUMNS['pd']
        qd_idx = engine.BUS_COLUMNS['qd']

        suggestions = []
        total_shedding = 0.0

        # Analyze violations to determine load shedding priorities
        voltage_violations = [v for v in violations if v.type == 'voltage']
        overload_violations = [v for v in violations if v.type == 'line_overload']

        # For voltage violations, suggest shedding at under-voltage buses
        for violation in voltage_violations:
            if violation.current_value < violation.limit_value:  # Under-voltage
                bus_idx = violation.target_index
                if bus_idx < len(bus):
                    current_load = float(bus[bus_idx, pd_idx])

                    if current_load > 0:
                        # Suggest shedding 10-30% based on severity
                        severity_factor = violation.violation_percent / 100
                        shed_percent = min(30, 10 + severity_factor * 20)
                        shed_amount = current_load * shed_percent / 100

                        suggestions.append({
                            'bus_index': bus_idx,
                            'bus_id': int(bus[bus_idx, engine.BUS_COLUMNS['bus_i']]),
                            'current_load_mw': current_load,
                            'suggested_shed_mw': shed_amount,
                            'shed_percent': shed_percent,
                            'reason': f"Under-voltage ({violation.current_value:.3f} < {violation.limit_value:.3f} p.u.)",
                            'priority': 'high' if violation.severity in [ViolationSeverity.CRITICAL, ViolationSeverity.HIGH] else 'medium'
                        })

                        total_shedding += shed_amount

        # For overload violations, suggest shedding at downstream buses
        for violation in overload_violations:
            branch_idx = violation.target_index
            branch = case_data.get('branch', np.array([]))

            if branch_idx < len(branch):
                # Find load buses connected to this line
                to_bus = int(branch[branch_idx, engine.BRANCH_COLUMNS['tbus']])

                # Find matching bus in bus matrix
                for bus_idx, bus_row in enumerate(bus):
                    if int(bus_row[engine.BUS_COLUMNS['bus_i']]) == to_bus:
                        current_load = float(bus_row[pd_idx])

                        if current_load > 0:
                            # Shed based on overload severity
                            severity_factor = violation.violation_percent / 100
                            shed_percent = min(25, 5 + severity_factor * 20)
                            shed_amount = current_load * shed_percent / 100

                            # Check if already suggested
                            existing = next(
                                (s for s in suggestions if s['bus_index'] == bus_idx),
                                None
                            )

                            if existing:
                                existing['suggested_shed_mw'] += shed_amount
                                existing['shed_percent'] += shed_percent
                                existing['reason'] += f"; Line overload relief"
                            else:
                                suggestions.append({
                                    'bus_index': bus_idx,
                                    'bus_id': to_bus,
                                    'current_load_mw': current_load,
                                    'suggested_shed_mw': shed_amount,
                                    'shed_percent': shed_percent,
                                    'reason': f"Line overload relief ({violation.current_value:.1f} > {violation.limit_value:.1f} MVA)",
                                    'priority': 'critical' if violation.severity == ViolationSeverity.CRITICAL else 'high'
                                })

                            total_shedding += shed_amount
                            break

        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        suggestions.sort(key=lambda s: priority_order.get(s['priority'], 4))

        return {
            'suggestions': suggestions,
            'total_shedding_mw': total_shedding,
            'num_buses_affected': len(suggestions),
            'estimated_cost': self._estimate_load_shedding_cost(total_shedding)
        }

    def _estimate_load_shedding_cost(self, total_shedding_mw: float) -> float:
        """
        Estimate the cost of load shedding.

        Uses a typical value of lost load (VOLL) of $5000/MWh.
        This is a simplified calculation.

        Args:
            total_shedding_mw: Total load to be shed in MW

        Returns:
            Estimated cost in dollars
        """
        voll = 5000  # Value of lost load in $/MWh
        return total_shedding_mw * voll

    def generate_corrective_actions(
        self,
        case_data: Dict,
        violations: List[Violation]
    ) -> List[Dict[str, Any]]:
        """
        Generate a prioritized list of corrective actions.

        This method analyzes violations and suggests specific corrective
        actions ranked by effectiveness and priority.

        Args:
            case_data: Current case data
            violations: List of detected violations

        Returns:
            List of corrective action suggestions with priority rankings
        """
        actions = []

        for violation in violations:
            if violation.type == 'voltage':
                if violation.current_value < violation.limit_value:
                    actions.append({
                        'type': 'increase_voltage_support',
                        'target_type': violation.target_type,
                        'target_index': violation.target_index,
                        'description': f"Increase reactive power support near bus {violation.target_index}",
                        'estimated_effectiveness': 'high',
                        'priority': violation.severity.value,
                        'related_violation': violation.dict()
                    })
                else:
                    actions.append({
                        'type': 'reduce_voltage',
                        'target_type': violation.target_type,
                        'target_index': violation.target_index,
                        'description': f"Reduce voltage setpoint near bus {violation.target_index}",
                        'estimated_effectiveness': 'medium',
                        'priority': violation.severity.value,
                        'related_violation': violation.dict()
                    })

            elif violation.type == 'line_overload':
                actions.append({
                    'type': 'redispatch_generation',
                    'target_type': 'system',
                    'description': f"Redistribute generation to relieve overload on branch {violation.target_index}",
                    'estimated_effectiveness': 'high',
                    'priority': violation.severity.value,
                    'related_violation': violation.dict()
                })

            elif violation.type == 'gen_limit':
                actions.append({
                    'type': 'adjust_generator_output',
                    'target_type': violation.target_type,
                    'target_index': violation.target_index,
                    'parameter': violation.parameter,
                    'description': f"Adjust {violation.parameter} output for generator {violation.target_index}",
                    'estimated_effectiveness': 'medium',
                    'priority': violation.severity.value,
                    'related_violation': violation.dict()
                })

        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        actions.sort(key=lambda a: priority_order.get(a['priority'], 4))

        return actions
