"""
Disturbance injection engine for MATPOWER Web platform.

This module provides the core functionality for applying disturbances
to power system case data and detecting constraint violations.
"""

import copy
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from .disturbance import (
    DisturbanceConfig,
    DisturbanceResult,
    DisturbanceType,
    Violation,
    ViolationSeverity
)


class DisturbanceEngine:
    """
    Engine for applying disturbances to power system case data.

    This class handles validation and application of various disturbance types
    including line outages, generator outages, load changes, and parameter modifications.
    All operations work on copies of the original data to preserve integrity.
    """

    # MATPOWER column indices for different matrices
    BUS_COLUMNS = {
        'bus_i': 0, 'type': 1, 'area': 2, 'vm': 7, 'va': 8,
        'base_kv': 9, 'zone': 10, 'vmax': 11, 'vmin': 12,
        'pd': 13, 'qd': 14
    }

    GEN_COLUMNS = {
        'gen_bus': 0, 'pg': 1, 'qg': 2, 'qmax': 3, 'qmin': 4,
        'vg': 5, 'mbase': 6, 'gen_status': 7, 'pmax': 8, 'pmin': 9
    }

    BRANCH_COLUMNS = {
        'fbus': 0, 'tbus': 1, 'br_r': 2, 'br_x': 3, 'br_b': 4,
        'rate_a': 5, 'rate_b': 6, 'rate_c': 7, 'ratio': 8, 'angle': 9,
        'br_status': 10, 'angmin': 11, 'angmax': 12
    }

    def __init__(self):
        """Initialize the disturbance engine."""
        self._presets_cache = {}

    def validate_disturbance(self, case_data: Dict, disturbance: DisturbanceConfig) -> bool:
        """
        Validate if a disturbance configuration is valid for the given case.

        Args:
            case_data: MATPOWER case dictionary with 'bus', 'gen', 'branch' arrays
            disturbance: Disturbance configuration to validate

        Returns:
            True if disturbance is valid, raises ValueError otherwise

        Raises:
            ValueError: If disturbance is invalid
        """
        target_type = disturbance.target_type
        target_idx = disturbance.target_index

        # Check if target matrix exists
        if target_type == 'bus':
            matrix = case_data.get('bus')
            if matrix is None:
                raise ValueError("Case data missing 'bus' matrix")
            max_idx = len(matrix) - 1
        elif target_type == 'gen':
            matrix = case_data.get('gen')
            if matrix is None:
                raise ValueError("Case data missing 'gen' matrix")
            max_idx = len(matrix) - 1
        elif target_type == 'branch':
            matrix = case_data.get('branch')
            if matrix is None:
                raise ValueError("Case data missing 'branch' matrix")
            max_idx = len(matrix) - 1
        else:
            raise ValueError(f"Invalid target_type: {target_type}")

        # Check index bounds
        if target_idx < 0 or target_idx > max_idx:
            raise ValueError(
                f"Target index {target_idx} out of bounds for {target_type} "
                f"(size: {max_idx + 1})"
            )

        # Type-specific validation
        if disturbance.disturbance_type == DisturbanceType.LINE_OUTAGE:
            self._validate_line_outage(case_data, disturbance)
        elif disturbance.disturbance_type == DisturbanceType.GEN_OUTAGE:
            self._validate_gen_outage(case_data, disturbance)
        elif disturbance.disturbance_type in [
            DisturbanceType.LOAD_INCREASE,
            DisturbanceType.LOAD_DECREASE,
            DisturbanceType.LOAD_CHANGE
        ]:
            self._validate_load_change(case_data, disturbance)

        return True

    def _validate_line_outage(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Validate line outage disturbance."""
        branch = case_data['branch'][disturbance.target_index]
        status_idx = self.BRANCH_COLUMNS['br_status']

        if branch[status_idx] == 0:
            raise ValueError(f"Branch {disturbance.target_index} is already out of service")

    def _validate_gen_outage(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Validate generator outage disturbance."""
        gen = case_data['gen'][disturbance.target_index]
        status_idx = self.GEN_COLUMNS['gen_status']

        if gen[status_idx] == 0:
            raise ValueError(f"Generator {disturbance.target_index} is already out of service")

    def _validate_load_change(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Validate load change disturbance."""
        bus = case_data['bus'][disturbance.target_index]
        pd_idx = self.BUS_COLUMNS['pd']

        current_load = bus[pd_idx]

        if disturbance.new_value is not None and disturbance.new_value < 0:
            raise ValueError("New load value cannot be negative")

        if disturbance.change_percent is not None:
            new_load = current_load * (1 + disturbance.change_percent / 100)
            if new_load < 0:
                raise ValueError(
                    f"Change percent {disturbance.change_percent}% would result in negative load"
                )

    def apply_disturbance(self, case_data: Dict, disturbance: DisturbanceConfig) -> Dict:
        """
        Apply a single disturbance to a copy of the case data.

        Args:
            case_data: Original MATPOWER case dictionary
            disturbance: Disturbance configuration to apply

        Returns:
            Modified copy of case_data with disturbance applied

        Raises:
            ValueError: If disturbance is invalid
        """
        # Validate first
        self.validate_disturbance(case_data, disturbance)

        # Deep copy to avoid modifying original
        modified_case = copy.deepcopy(case_data)

        # Apply based on disturbance type
        if disturbance.disturbance_type == DisturbanceType.LINE_OUTAGE:
            self._apply_line_outage(modified_case, disturbance)
        elif disturbance.disturbance_type == DisturbanceType.GEN_OUTAGE:
            self._apply_gen_outage(modified_case, disturbance)
        elif disturbance.disturbance_type == DisturbanceType.LOAD_INCREASE:
            self._apply_load_increase(modified_case, disturbance)
        elif disturbance.disturbance_type == DisturbanceType.LOAD_DECREASE:
            self._apply_load_decrease(modified_case, disturbance)
        elif disturbance.disturbance_type == DisturbanceType.LOAD_CHANGE:
            self._apply_load_change(modified_case, disturbance)
        elif disturbance.disturbance_type == DisturbanceType.VOLTAGE_SETPOINT_CHANGE:
            self._apply_voltage_setpoint_change(modified_case, disturbance)
        elif disturbance.disturbance_type == DisturbanceType.GEN_OUTPUT_CHANGE:
            self._apply_gen_output_change(modified_case, disturbance)
        elif disturbance.disturbance_type == DisturbanceType.LINE_PARAMETER_CHANGE:
            self._apply_line_parameter_change(modified_case, disturbance)

        return modified_case

    def _apply_line_outage(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Apply line outage by setting br_status to 0."""
        branch = case_data['branch'][disturbance.target_index]
        status_idx = self.BRANCH_COLUMNS['br_status']

        # Store old value
        if disturbance.old_value is None:
            disturbance.old_value = float(branch[status_idx])

        branch[status_idx] = 0.0

    def _apply_gen_outage(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Apply generator outage by setting gen_status to 0."""
        gen = case_data['gen'][disturbance.target_index]
        status_idx = self.GEN_COLUMNS['gen_status']

        # Store old value
        if disturbance.old_value is None:
            disturbance.old_value = float(gen[status_idx])

        gen[status_idx] = 0.0
        gen[self.GEN_COLUMNS['pg']] = 0.0
        gen[self.GEN_COLUMNS['qg']] = 0.0

    def _apply_load_increase(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Apply load increase by percentage or absolute value."""
        bus = case_data['bus'][disturbance.target_index]
        pd_idx = self.BUS_COLUMNS['pd']
        qd_idx = self.BUS_COLUMNS['qd']

        old_pd = float(bus[pd_idx])
        old_qd = float(bus[qd_idx])

        if disturbance.old_value is None:
            disturbance.old_value = old_pd

        if disturbance.change_percent is not None:
            factor = 1 + disturbance.change_percent / 100
            new_pd = old_pd * factor
            new_qd = old_qd * factor
            disturbance.new_value = new_pd
        elif disturbance.new_value is not None:
            # Scale both P and Q proportionally
            ratio = disturbance.new_value / old_pd if old_pd > 0 else 1
            new_pd = disturbance.new_value
            new_qd = old_qd * ratio
        else:
            raise ValueError("Must specify either change_percent or new_value")

        bus[pd_idx] = new_pd
        bus[qd_idx] = new_qd

    def _apply_load_decrease(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Apply load decrease by percentage or absolute value."""
        bus = case_data['bus'][disturbance.target_index]
        pd_idx = self.BUS_COLUMNS['pd']
        qd_idx = self.BUS_COLUMNS['qd']

        old_pd = float(bus[pd_idx])
        old_qd = float(bus[qd_idx])

        if disturbance.old_value is None:
            disturbance.old_value = old_pd

        if disturbance.change_percent is not None:
            factor = 1 + disturbance.change_percent / 100  # negative for decrease
            new_pd = max(0, old_pd * factor)
            new_qd = max(0, old_qd * factor)
            disturbance.new_value = new_pd
        elif disturbance.new_value is not None:
            new_pd = disturbance.new_value
            ratio = new_pd / old_pd if old_pd > 0 else 1
            new_qd = old_qd * ratio
        else:
            raise ValueError("Must specify either change_percent or new_value")

        bus[pd_idx] = new_pd
        bus[qd_idx] = new_qd

    def _apply_load_change(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Apply direct load change to absolute value."""
        bus = case_data['bus'][disturbance.target_index]
        pd_idx = self.BUS_COLUMNS['pd']
        qd_idx = self.BUS_COLUMNS['qd']

        old_pd = float(bus[pd_idx])
        old_qd = float(bus[qd_idx])

        if disturbance.old_value is None:
            disturbance.old_value = old_pd

        if disturbance.new_value is None:
            raise ValueError("new_value must be specified for load_change")

        # Scale Q proportionally
        ratio = disturbance.new_value / old_pd if old_pd > 0 else 1
        new_qd = old_qd * ratio

        bus[pd_idx] = disturbance.new_value
        bus[qd_idx] = new_qd

    def _apply_voltage_setpoint_change(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Apply voltage setpoint change for generator."""
        gen = case_data['gen'][disturbance.target_index]
        vg_idx = self.GEN_COLUMNS['vg']

        old_vg = float(gen[vg_idx])

        if disturbance.old_value is None:
            disturbance.old_value = old_vg

        if disturbance.change_percent is not None:
            new_vg = old_vg * (1 + disturbance.change_percent / 100)
            disturbance.new_value = new_vg
        elif disturbance.new_value is not None:
            new_vg = disturbance.new_value
        else:
            raise ValueError("Must specify either change_percent or new_value")

        # Reasonable voltage limits (0.9 - 1.1 p.u.)
        if not (0.85 <= new_vg <= 1.15):
            raise ValueError(f"Voltage setpoint {new_vg} p.u. is outside reasonable range (0.85-1.15)")

        gen[vg_idx] = new_vg

    def _apply_gen_output_change(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Apply generator output change."""
        gen = case_data['gen'][disturbance.target_index]
        pg_idx = self.GEN_COLUMNS['pg']
        pmin_idx = self.GEN_COLUMNS['pmin']
        pmax_idx = self.GEN_COLUMNS['pmax']

        old_pg = float(gen[pg_idx])
        pmin = float(gen[pmin_idx])
        pmax = float(gen[pmax_idx])

        if disturbance.old_value is None:
            disturbance.old_value = old_pg

        if disturbance.change_percent is not None:
            new_pg = old_pg * (1 + disturbance.change_percent / 100)
            disturbance.new_value = new_pg
        elif disturbance.new_value is not None:
            new_pg = disturbance.new_value
        else:
            raise ValueError("Must specify either change_percent or new_value")

        # Check limits
        if new_pg < pmin or new_pg > pmax:
            raise ValueError(
                f"Generator output {new_pg} MW is outside limits ({pmin}-{pmax} MW)"
            )

        gen[pg_idx] = new_pg

    def _apply_line_parameter_change(self, case_data: Dict, disturbance: DisturbanceConfig) -> None:
        """Apply line parameter change (resistance, reactance, or susceptance)."""
        branch = case_data['branch'][disturbance.target_index]

        if disturbance.parameter is None:
            raise ValueError("parameter must be specified for line_param_change")

        param_map = {
            'br_r': self.BRANCH_COLUMNS['br_r'],
            'r': self.BRANCH_COLUMNS['br_r'],
            'br_x': self.BRANCH_COLUMNS['br_x'],
            'x': self.BRANCH_COLUMNS['br_x'],
            'br_b': self.BRANCH_COLUMNS['br_b'],
            'b': self.BRANCH_COLUMNS['br_b'],
        }

        param_key = disturbance.parameter.lower()
        if param_key not in param_map:
            raise ValueError(
                f"Invalid parameter '{disturbance.parameter}'. "
                f"Valid options: br_r, br_x, br_b"
            )

        col_idx = param_map[param_key]
        old_value = float(branch[col_idx])

        if disturbance.old_value is None:
            disturbance.old_value = old_value

        if disturbance.change_percent is not None:
            new_value = old_value * (1 + disturbance.change_percent / 100)
            disturbance.new_value = new_value
        elif disturbance.new_value is not None:
            new_value = disturbance.new_value
        else:
            raise ValueError("Must specify either change_percent or new_value")

        # Validate new value
        if param_key in ['r', 'br_r'] and new_value < 0:
            raise ValueError("Line resistance cannot be negative")
        if param_key in ['x', 'br_x'] and new_value < 0:
            raise ValueError("Line reactance cannot be negative")

        branch[col_idx] = new_value

    def apply_multiple(self, case_data: Dict, disturbances: List[DisturbanceConfig]) -> Dict:
        """
        Apply multiple disturbances sequentially.

        Args:
            case_data: Original MATPOWER case dictionary
            disturbances: List of disturbances to apply in order

        Returns:
            Modified copy of case_data with all disturbances applied
        """
        modified_case = copy.deepcopy(case_data)

        for i, disturbance in enumerate(disturbances):
            try:
                modified_case = self.apply_disturbance(modified_case, disturbance)
            except ValueError as e:
                raise ValueError(f"Failed to apply disturbance {i+1}/{len(disturbances)}: {e}")

        return modified_case

    def detect_violations(self, case_data: Dict, result: Dict) -> List[Violation]:
        """
        Detect constraint violations in power flow results.

        Args:
            case_data: Original case data with limits
            result: Power flow result with voltages, flows, etc.

        Returns:
            List of violations detected
        """
        violations = []

        # Check voltage violations
        violations.extend(self._check_voltage_violations(case_data, result))

        # Check line overloads
        violations.extend(self._check_line_overloads(case_data, result))

        # Check generator limit violations
        violations.extend(self._check_generator_limits(case_data, result))

        # Sort by severity
        violations.sort(key=lambda v: v.violation_percent, reverse=True)

        return violations

    def _check_voltage_violations(self, case_data: Dict, result: Dict) -> List[Violation]:
        """Check for voltage magnitude violations."""
        violations = []
        bus = case_data['bus']

        for i, bus_row in enumerate(bus):
            vm_idx = self.BUS_COLUMNS['vm']
            vmin_idx = self.BUS_COLUMNS['vmin']
            vmax_idx = self.BUS_COLUMNS['vmax']

            vm = float(bus_row[vm_idx])
            vmin = float(bus_row[vmin_idx])
            vmax = float(bus_row[vmax_idx])

            # Check under voltage
            if vm < vmin:
                violation_percent = abs((vm - vmin) / vmin * 100)
                severity = self._calculate_voltage_severity(violation_percent)
                violations.append(Violation(
                    type="voltage",
                    target_type="bus",
                    target_index=i,
                    parameter="vm",
                    current_value=vm,
                    limit_value=vmin,
                    severity=severity,
                    violation_percent=violation_percent
                ))

            # Check over voltage
            elif vm > vmax:
                violation_percent = abs((vm - vmax) / vmax * 100)
                severity = self._calculate_voltage_severity(violation_percent)
                violations.append(Violation(
                    type="voltage",
                    target_type="bus",
                    target_index=i,
                    parameter="vm",
                    current_value=vm,
                    limit_value=vmax,
                    severity=severity,
                    violation_percent=violation_percent
                ))

        return violations

    def _check_line_overloads(self, case_data: Dict, result: Dict) -> List[Violation]:
        """Check for line flow violations (thermal limits)."""
        violations = []

        # Get branch data
        branch = case_data.get('branch', [])
        if len(branch) == 0:
            return violations

        # Get flow results if available
        branch_flow = result.get('branch', None)
        if branch_flow is None:
            return violations

        rate_a_idx = self.BRANCH_COLUMNS['rate_a']

        for i, branch_row in enumerate(branch):
            rate_a = float(branch_row[rate_a_idx])

            if rate_a <= 0:
                continue  # No limit set

            # Get apparent power flow (MVA)
            # In MATPOWER results, column indices may differ
            if hasattr(branch_flow, '__len__') and len(branch_flow) > i:
                pf = float(branch_flow[i][13]) if len(branch_flow[i]) > 13 else 0  # From bus flow
                pt = float(branch_flow[i][15]) if len(branch_flow[i]) > 15 else 0  # To bus flow
                max_flow = max(abs(pf), abs(pt))

                if max_flow > rate_a:
                    violation_percent = (max_flow - rate_a) / rate_a * 100
                    severity = self._calculate_overload_severity(violation_percent)
                    violations.append(Violation(
                        type="line_overload",
                        target_type="branch",
                        target_index=i,
                        parameter="flow_mva",
                        current_value=max_flow,
                        limit_value=rate_a,
                        severity=severity,
                        violation_percent=violation_percent
                    ))

        return violations

    def _check_generator_limits(self, case_data: Dict, result: Dict) -> List[Violation]:
        """Check for generator output limit violations."""
        violations = []

        gen = case_data.get('gen', [])
        if len(gen) == 0:
            return violations

        pg_idx = self.GEN_COLUMNS['pg']
        qg_idx = self.GEN_COLUMNS['qg']
        pmin_idx = self.GEN_COLUMNS['pmin']
        pmax_idx = self.GEN_COLUMNS['pmax']
        qmin_idx = self.GEN_COLUMNS['qmin']
        qmax_idx = self.GEN_COLUMNS['qmax']

        for i, gen_row in enumerate(gen):
            status = float(gen_row[self.GEN_COLUMNS['gen_status']])
            if status == 0:
                continue  # Generator is out of service

            pg = float(gen_row[pg_idx])
            qg = float(gen_row[qg_idx])
            pmin = float(gen_row[pmin_idx])
            pmax = float(gen_row[pmax_idx])
            qmin = float(gen_row[qmin_idx])
            qmax = float(gen_row[qmax_idx])

            # Check active power limits
            if pg < pmin:
                violation_percent = abs((pg - pmin) / pmin * 100) if pmin > 0 else 0
                violations.append(Violation(
                    type="gen_limit",
                    target_type="gen",
                    target_index=i,
                    parameter="pg",
                    current_value=pg,
                    limit_value=pmin,
                    severity=ViolationSeverity.MEDIUM,
                    violation_percent=violation_percent
                ))

            elif pg > pmax:
                violation_percent = (pg - pmax) / pmax * 100
                violations.append(Violation(
                    type="gen_limit",
                    target_type="gen",
                    target_index=i,
                    parameter="pg",
                    current_value=pg,
                    limit_value=pmax,
                    severity=self._calculate_overload_severity(violation_percent),
                    violation_percent=violation_percent
                ))

            # Check reactive power limits
            if qg < qmin:
                violation_percent = abs((qg - qmin) / qmin * 100) if qmin > 0 else 0
                violations.append(Violation(
                    type="gen_limit",
                    target_type="gen",
                    target_index=i,
                    parameter="qg",
                    current_value=qg,
                    limit_value=qmin,
                    severity=ViolationSeverity.LOW,
                    violation_percent=violation_percent
                ))

            elif qg > qmax:
                violation_percent = (qg - qmax) / qmax * 100 if qmax > 0 else 0
                violations.append(Violation(
                    type="gen_limit",
                    target_type="gen",
                    target_index=i,
                    parameter="qg",
                    current_value=qg,
                    limit_value=qmax,
                    severity=ViolationSeverity.LOW,
                    violation_percent=violation_percent
                ))

        return violations

    def _calculate_voltage_severity(self, violation_percent: float) -> ViolationSeverity:
        """Calculate severity level for voltage violations."""
        if violation_percent > 10:
            return ViolationSeverity.CRITICAL
        elif violation_percent > 5:
            return ViolationSeverity.HIGH
        elif violation_percent > 2:
            return ViolationSeverity.MEDIUM
        else:
            return ViolationSeverity.LOW

    def _calculate_overload_severity(self, violation_percent: float) -> ViolationSeverity:
        """Calculate severity level for overload violations."""
        if violation_percent > 50:
            return ViolationSeverity.CRITICAL
        elif violation_percent > 20:
            return ViolationSeverity.HIGH
        elif violation_percent > 10:
            return ViolationSeverity.MEDIUM
        else:
            return ViolationSeverity.LOW

    def get_system_summary(self, case_data: Dict, result: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate a summary of the power system state.

        Args:
            case_data: MATPOWER case data
            result: Optional power flow result

        Returns:
            Dictionary with system summary
        """
        bus = case_data.get('bus', np.array([]))
        gen = case_data.get('gen', np.array([]))
        branch = case_data.get('branch', np.array([]))

        summary = {
            'total_buses': len(bus),
            'total_generators': len(gen),
            'total_branches': len(branch),
            'total_load_mw': 0.0,
            'total_gen_mw': 0.0,
            'online_generators': 0,
            'online_branches': 0,
        }

        # Sum loads
        if len(bus) > 0:
            pd_idx = self.BUS_COLUMNS['pd']
            summary['total_load_mw'] = float(np.sum(bus[:, pd_idx]))

        # Sum generation
        if len(gen) > 0:
            pg_idx = self.GEN_COLUMNS['pg']
            status_idx = self.GEN_COLUMNS['gen_status']
            summary['total_gen_mw'] = float(np.sum(gen[:, pg_idx]))
            summary['online_generators'] = int(np.sum(gen[:, status_idx]))

        # Count online branches
        if len(branch) > 0:
            status_idx = self.BRANCH_COLUMNS['br_status']
            summary['online_branches'] = int(np.sum(branch[:, status_idx]))

        # Add result data if available
        if result is not None:
            summary['convergence'] = result.get('success', False)
            summary['iterations'] = result.get('iterations', 0)

        return summary

    def get_disturbance_presets(self, case_name: str) -> List[Dict[str, Any]]:
        """
        Get predefined disturbance scenarios for a given test case.

        Args:
            case_name: Name of the test case (e.g., 'case14', 'case30')

        Returns:
            List of preset disturbance configurations
        """
        # Common presets for different IEEE test cases
        presets_map = {
            'case9': [
                {
                    'name': 'Critical Line Outage (4-5)',
                    'description': 'Outage of line connecting bus 4 to 5',
                    'disturbance': {
                        'disturbance_type': 'line_outage',
                        'target_type': 'branch',
                        'target_index': 0,  # Would be determined by analysis
                        'parameter': 'br_status'
                    }
                },
                {
                    'name': 'Generator 1 Outage',
                    'description': 'Loss of slack bus generator',
                    'disturbance': {
                        'disturbance_type': 'gen_outage',
                        'target_type': 'gen',
                        'target_index': 0,
                        'parameter': 'gen_status'
                    }
                },
            ],
            'case14': [
                {
                    'name': 'Line 1-2 Outage',
                    'description': 'Outage of transmission line between bus 1 and 2',
                    'disturbance': {
                        'disturbance_type': 'line_outage',
                        'target_type': 'branch',
                        'target_index': 0,
                        'parameter': 'br_status'
                    }
                },
                {
                    'name': 'Bus 2 Load Increase 50%',
                    'description': 'Increase load at bus 2 by 50 percent',
                    'disturbance': {
                        'disturbance_type': 'load_increase',
                        'target_type': 'bus',
                        'target_index': 1,
                        'parameter': 'pd',
                        'change_percent': 50
                    }
                },
                {
                    'name': 'Generator 2 Outage',
                    'description': 'Loss of generator at bus 2',
                    'disturbance': {
                        'disturbance_type': 'gen_outage',
                        'target_type': 'gen',
                        'target_index': 1,
                        'parameter': 'gen_status'
                    }
                },
            ],
            'case30': [
                {
                    'name': 'Line 2-5 Outage',
                    'description': 'Outage of line connecting bus 2 to 5',
                    'disturbance': {
                        'disturbance_type': 'line_outage',
                        'target_type': 'branch',
                        'target_index': 1,
                        'parameter': 'br_status'
                    }
                },
                {
                    'name': 'Bus 5 Load Increase 30%',
                    'description': 'Increase load at bus 5 by 30 percent',
                    'disturbance': {
                        'disturbance_type': 'load_increase',
                        'target_type': 'bus',
                        'target_index': 4,
                        'parameter': 'pd',
                        'change_percent': 30
                    }
                },
            ],
        }

        # Extract base name if full path is given
        base_name = case_name.split('/')[-1].split('\\')[-1].replace('.m', '').lower()

        return presets_map.get(base_name, self._get_generic_presets())

    def _get_generic_presets(self) -> List[Dict[str, Any]]:
        """Get generic presets applicable to any case."""
        return [
            {
                'name': 'First Line Outage',
                'description': 'Outage of first transmission line',
                'disturbance': {
                    'disturbance_type': 'line_outage',
                    'target_type': 'branch',
                    'target_index': 0,
                    'parameter': 'br_status'
                }
            },
            {
                'name': 'Load Increase 20%',
                'description': 'Increase all loads by 20 percent',
                'disturbance': {
                    'disturbance_type': 'load_increase',
                    'target_type': 'bus',
                    'target_index': 0,
                    'parameter': 'pd',
                    'change_percent': 20
                }
            },
            {
                'name': 'First Generator Outage',
                'description': 'Outage of first generator',
                'disturbance': {
                    'disturbance_type': 'gen_outage',
                    'target_type': 'gen',
                    'target_index': 0,
                    'parameter': 'gen_status'
                }
            },
        ]
