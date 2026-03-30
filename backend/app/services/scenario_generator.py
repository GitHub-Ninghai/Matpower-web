"""
Random scenario generator for MATPOWER Web platform.

This module provides functionality for generating random disturbance scenarios
for batch testing, training data generation, and stress testing.
"""

import copy
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import random
from datetime import datetime

from .disturbance import (
    DisturbanceConfig,
    DisturbanceType,
    ViolationSeverity
)
from .disturbance_engine import DisturbanceEngine


class ScenarioGenerator:
    """
    Random disturbance scenario generator.

    This class generates random but valid disturbance scenarios for various
    purposes including stress testing, training data generation, and
    uncertainty analysis.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the scenario generator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        self.disturbance_engine = DisturbanceEngine()

        # Severity level configurations
        self.severity_configs = {
            'light': {
                'load_change_range': (-0.1, 0.1),  # -10% to +10%
                'outage_probability': 0.02,
                'max_simultaneous_disturbances': 1,
                'parameter_change_range': (-0.05, 0.05)
            },
            'medium': {
                'load_change_range': (-0.2, 0.3),  # -20% to +30%
                'outage_probability': 0.05,
                'max_simultaneous_disturbances': 2,
                'parameter_change_range': (-0.1, 0.1)
            },
            'severe': {
                'load_change_range': (-0.3, 0.5),  # -30% to +50%
                'outage_probability': 0.15,
                'max_simultaneous_disturbances': 4,
                'parameter_change_range': (-0.2, 0.2)
            }
        }

        # Available disturbance types for random generation
        self.available_disturbance_types = [
            DisturbanceType.LOAD_INCREASE,
            DisturbanceType.LOAD_DECREASE,
            DisturbanceType.LINE_OUTAGE,
            DisturbanceType.GEN_OUTAGE,
            DisturbanceType.VOLTAGE_SETPOINT_CHANGE,
            DisturbanceType.GEN_OUTPUT_CHANGE,
            DisturbanceType.LINE_PARAMETER_CHANGE
        ]

    def generate_random_disturbances(
        self,
        case_data: Dict,
        n_scenarios: int,
        severity: str = "medium",
        allowed_types: Optional[List[DisturbanceType]] = None
    ) -> List[List[DisturbanceConfig]]:
        """
        Generate random disturbance scenarios.

        Args:
            case_data: MATPOWER case data
            n_scenarios: Number of scenarios to generate
            severity: Severity level ('light', 'medium', 'severe')
            allowed_types: List of allowed disturbance types (default: all)

        Returns:
            List of scenarios, each scenario is a list of disturbances
        """
        if severity not in self.severity_configs:
            raise ValueError(f"Invalid severity: {severity}. Must be one of {list(self.severity_configs.keys())}")

        config = self.severity_configs[severity]

        # Determine which disturbance types to use
        if allowed_types is None:
            allowed_types = self.available_disturbance_types

        scenarios = []
        bus_count = len(case_data.get('bus', []))
        gen_count = len(case_data.get('gen', []))
        branch_count = len(case_data.get('branch', []))

        for _ in range(n_scenarios):
            scenario = []

            # Determine number of disturbances for this scenario
            n_disturbances = random.randint(1, config['max_simultaneous_disturbances'])

            for _ in range(n_disturbances):
                disturbance = self._generate_single_disturbance(
                    case_data,
                    config,
                    allowed_types,
                    bus_count,
                    gen_count,
                    branch_count
                )
                if disturbance is not None:
                    scenario.append(disturbance)

            if scenario:  # Only add non-empty scenarios
                scenarios.append(scenario)

        return scenarios

    def _generate_single_disturbance(
        self,
        case_data: Dict,
        config: Dict,
        allowed_types: List[DisturbanceType],
        bus_count: int,
        gen_count: int,
        branch_count: int
    ) -> Optional[DisturbanceConfig]:
        """Generate a single random disturbance."""
        # Randomly select disturbance type
        dist_type = random.choice(allowed_types)

        try:
            if dist_type == DisturbanceType.LINE_OUTAGE:
                if branch_count == 0:
                    return None
                idx = random.randint(0, branch_count - 1)
                return DisturbanceConfig(
                    disturbance_type=dist_type,
                    target_type='branch',
                    target_index=idx,
                    parameter='br_status',
                    description=f"Random line outage at branch {idx}"
                )

            elif dist_type == DisturbanceType.GEN_OUTAGE:
                if gen_count == 0:
                    return None
                idx = random.randint(0, gen_count - 1)
                return DisturbanceConfig(
                    disturbance_type=dist_type,
                    target_type='gen',
                    target_index=idx,
                    parameter='gen_status',
                    description=f"Random generator outage at gen {idx}"
                )

            elif dist_type in [DisturbanceType.LOAD_INCREASE, DisturbanceType.LOAD_DECREASE]:
                if bus_count == 0:
                    return None
                idx = random.randint(0, bus_count - 1)
                change_percent = random.uniform(*config['load_change_range']) * 100
                return DisturbanceConfig(
                    disturbance_type=dist_type,
                    target_type='bus',
                    target_index=idx,
                    parameter='pd',
                    change_percent=change_percent,
                    description=f"Random load change at bus {idx}: {change_percent:.1f}%"
                )

            elif dist_type == DisturbanceType.VOLTAGE_SETPOINT_CHANGE:
                if gen_count == 0:
                    return None
                idx = random.randint(0, gen_count - 1)
                change_percent = random.uniform(-5, 5)
                return DisturbanceConfig(
                    disturbance_type=dist_type,
                    target_type='gen',
                    target_index=idx,
                    parameter='vg',
                    change_percent=change_percent,
                    description=f"Random voltage setpoint change at gen {idx}"
                )

            elif dist_type == DisturbanceType.GEN_OUTPUT_CHANGE:
                if gen_count == 0:
                    return None
                idx = random.randint(0, gen_count - 1)
                change_percent = random.uniform(-30, 30)
                return DisturbanceConfig(
                    disturbance_type=dist_type,
                    target_type='gen',
                    target_index=idx,
                    parameter='pg',
                    change_percent=change_percent,
                    description=f"Random generator output change at gen {idx}: {change_percent:.1f}%"
                )

            elif dist_type == DisturbanceType.LINE_PARAMETER_CHANGE:
                if branch_count == 0:
                    return None
                idx = random.randint(0, branch_count - 1)
                params = ['br_r', 'br_x', 'br_b']
                param = random.choice(params)
                change_percent = random.uniform(*config['parameter_change_range']) * 100
                return DisturbanceConfig(
                    disturbance_type=dist_type,
                    target_type='branch',
                    target_index=idx,
                    parameter=param,
                    change_percent=change_percent,
                    description=f"Random {param} change at branch {idx}: {change_percent:.1f}%"
                )

        except Exception:
            # Skip invalid disturbances
            pass

        return None

    def generate_composite_scenarios(
        self,
        case_data: Dict,
        n_scenarios: int,
        min_disturbances: int = 2,
        max_disturbances: int = 5
    ) -> List[List[DisturbanceConfig]]:
        """
        Generate composite scenarios with multiple simultaneous disturbances.

        These scenarios represent cascading events or simultaneous failures.

        Args:
            case_data: MATPOWER case data
            n_scenarios: Number of scenarios to generate
            min_disturbances: Minimum disturbances per scenario
            max_disturbances: Maximum disturbances per scenario

        Returns:
            List of composite scenarios
        """
        scenarios = []
        bus_count = len(case_data.get('bus', []))
        gen_count = len(case_data.get('gen', []))
        branch_count = len(case_data.get('branch', []))

        config = self.severity_configs['severe']  # Use severe config for composite

        for _ in range(n_scenarios):
            n_disturbances = random.randint(min_disturbances, max_disturbances)
            scenario = []

            # Ensure diversity in disturbance types
            types_pool = self.available_disturbance_types.copy()
            random.shuffle(types_pool)

            for i in range(n_disturbances):
                dist_type = types_pool[i % len(types_pool)]

                disturbance = self._generate_single_disturbance(
                    case_data,
                    config,
                    [dist_type],
                    bus_count,
                    gen_count,
                    branch_count
                )

                if disturbance is not None:
                    scenario.append(disturbance)

            if scenario:
                scenarios.append(scenario)

        return scenarios

    def generate_load_variation_scenarios(
        self,
        case_data: Dict,
        n_scenarios: int,
        variation_range: Tuple[float, float] = (-0.3, 0.5),
        correlated: bool = False
    ) -> List[DisturbanceConfig]:
        """
        Generate load variation scenarios.

        Args:
            case_data: MATPOWER case data
            n_scenarios: Number of scenarios
            variation_range: Range of load variation as (min, max) fraction
            correlated: If True, all loads vary together (system-wide change)
                        If False, each load varies independently

        Returns:
            List of load change disturbances
        """
        scenarios = []
        bus = case_data.get('bus', [])

        if len(bus) == 0:
            return scenarios

        for scenario_idx in range(n_scenarios):
            if correlated:
                # System-wide variation
                change_percent = random.uniform(variation_range[0], variation_range[1]) * 100

                # Apply to all buses with load
                for bus_idx in range(len(bus)):
                    pd_idx = self.disturbance_engine.BUS_COLUMNS['pd']
                    if bus[bus_idx][pd_idx] > 0:
                        scenarios.append(DisturbanceConfig(
                            disturbance_type=DisturbanceType.LOAD_INCREASE if change_percent > 0 else DisturbanceType.LOAD_DECREASE,
                            target_type='bus',
                            target_index=bus_idx,
                            parameter='pd',
                            change_percent=change_percent,
                            description=f"Scenario {scenario_idx}: System-wide load change {change_percent:.1f}%"
                        ))
            else:
                # Independent variations per bus
                for bus_idx in range(len(bus)):
                    pd_idx = self.disturbance_engine.BUS_COLUMNS['pd']
                    if bus[bus_idx][pd_idx] > 0:
                        change_percent = random.uniform(variation_range[0], variation_range[1]) * 100

                        scenarios.append(DisturbanceConfig(
                            disturbance_type=DisturbanceType.LOAD_INCREASE if change_percent > 0 else DisturbanceType.LOAD_DECREASE,
                            target_type='bus',
                            target_index=bus_idx,
                            parameter='pd',
                            change_percent=change_percent,
                            description=f"Scenario {scenario_idx}: Bus {bus_idx} load change {change_percent:.1f}%"
                        ))

        return scenarios

    def validate_scenario(
        self,
        case_data: Dict,
        scenario: List[DisturbanceConfig]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if a scenario is reasonable and won't cause numerical issues.

        Args:
            case_data: MATPOWER case data
            scenario: List of disturbances to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Create a copy to test
            test_case = copy.deepcopy(case_data)

            # Count disturbances by type
            outage_count = sum(
                1 for d in scenario
                if d.disturbance_type in [DisturbanceType.LINE_OUTAGE, DisturbanceType.GEN_OUTAGE]
            )

            # Check for too many outages
            gen_count = len(test_case.get('gen', []))
            branch_count = len(test_case.get('branch', []))

            gen_outages = sum(
                1 for d in scenario
                if d.disturbance_type == DisturbanceType.GEN_OUTAGE
            )

            line_outages = sum(
                1 for d in scenario
                if d.disturbance_type == DisturbanceType.LINE_OUTAGE
            )

            # Don't allow all generators to be out
            if gen_outages >= gen_count * 0.8:  # More than 80% generators out
                return False, "Too many generator outages - system would collapse"

            # Don't allow all lines to be out
            if line_outages >= branch_count * 0.7:  # More than 70% lines out
                return False, "Too many line outages - network would be disconnected"

            # Try applying each disturbance
            for disturbance in scenario:
                try:
                    self.disturbance_engine.validate_disturbance(test_case, disturbance)
                    test_case = self.disturbance_engine.apply_disturbance(test_case, disturbance)
                except ValueError as e:
                    return False, f"Invalid disturbance: {e}"

            # Check if any loads became negative
            bus = test_case.get('bus', [])
            pd_idx = self.disturbance_engine.BUS_COLUMNS['pd']

            for bus_row in bus:
                if bus_row[pd_idx] < 0:
                    return False, "Negative load detected after applying disturbances"

            return True, None

        except Exception as e:
            return False, f"Validation error: {e}"

    def export_scenarios(
        self,
        scenarios: List[List[DisturbanceConfig]],
        format: str = "json",
        filepath: Optional[str] = None
    ) -> str:
        """
        Export generated scenarios to a file or return as string.

        Args:
            scenarios: List of scenarios to export
            format: Export format ('json' or 'csv')
            filepath: Optional file path to save to

        Returns:
            String representation of scenarios
        """
        if format == "json":
            # Convert scenarios to dict format
            scenarios_dict = []
            for i, scenario in enumerate(scenarios):
                scenario_data = {
                    'scenario_id': i,
                    'num_disturbances': len(scenario),
                    'disturbances': [
                        d.dict() if hasattr(d, 'dict') else d
                        for d in scenario
                    ]
                }
                scenarios_dict.append(scenario_data)

            output = json.dumps(scenarios_dict, indent=2, default=str)

        elif format == "csv":
            # CSV format: one disturbance per row
            lines = ['scenario_id,disturbance_index,disturbance_type,target_type,target_index,parameter,change_percent,new_value,description']

            for i, scenario in enumerate(scenarios):
                for j, disturbance in enumerate(scenario):
                    d = disturbance.dict() if hasattr(disturbance, 'dict') else disturbance
                    lines.append(
                        f"{i},{j},{d.get('disturbance_type','')},{d.get('target_type','')},"
                        f"{d.get('target_index','')},{d.get('parameter','')},"
                        f"{d.get('change_percent','')},{d.get('new_value','')},"
                        f"\"{d.get('description','')}\""
                    )

            output = '\n'.join(lines)

        else:
            raise ValueError(f"Unsupported format: {format}")

        # Save to file if path provided
        if filepath:
            with open(filepath, 'w') as f:
                f.write(output)

        return output

    def generate_cascading_scenarios(
        self,
        case_data: Dict,
        n_scenarios: int,
        initial_trigger: Optional[DisturbanceType] = None,
        max_cascade_steps: int = 5
    ) -> List[List[DisturbanceConfig]]:
        """
        Generate cascading failure scenarios.

        These scenarios start with an initial disturbance and add follow-on
        disturbances that might occur as a result.

        Args:
            case_data: MATPOWER case data
            n_scenarios: Number of scenarios to generate
            initial_trigger: Type of initial disturbance (random if None)
            max_cascade_steps: Maximum number of cascading steps

        Returns:
            List of cascading scenarios
        """
        scenarios = []
        bus_count = len(case_data.get('bus', []))
        gen_count = len(case_data.get('gen', []))
        branch_count = len(case_data.get('branch', []))

        for _ in range(n_scenarios):
            scenario = []

            # Initial trigger
            if initial_trigger is None:
                initial_trigger = random.choice([
                    DisturbanceType.LINE_OUTAGE,
                    DisturbanceType.GEN_OUTAGE
                ])

            initial = self._generate_single_disturbance(
                case_data,
                self.severity_configs['severe'],
                [initial_trigger],
                bus_count,
                gen_count,
                branch_count
            )

            if initial is None:
                continue

            scenario.append(initial)

            # Cascading effects
            n_cascades = random.randint(1, max_cascade_steps)

            # Cascade types that typically follow
            cascade_types = [
                DisturbanceType.LINE_OUTAGE,  # Overloaded lines trip
                DisturbanceType.GEN_OUTAGE,   # Generators trip
                DisturbanceType.LOAD_INCREASE  # Load increases due to redistribution
            ]

            for _ in range(n_cascades):
                cascade = self._generate_single_disturbance(
                    case_data,
                    self.severity_configs['medium'],
                    cascade_types,
                    bus_count,
                    gen_count,
                    branch_count
                )

                if cascade is not None:
                    scenario.append(cascade)

            if scenario:
                scenarios.append(scenario)

        return scenarios

    def generate_weather_scenarios(
        self,
        case_data: Dict,
        weather_type: str = "storm",
        n_scenarios: int = 10
    ) -> List[List[DisturbanceConfig]]:
        """
        Generate weather-related disturbance scenarios.

        Args:
            case_data: MATPOWER case data
            weather_type: Type of weather ('storm', 'heat_wave', 'cold_snap')
            n_scenarios: Number of scenarios

        Returns:
            List of weather scenarios
        """
        scenarios = []
        branch_count = len(case_data.get('branch', []))
        bus_count = len(case_data.get('bus', []))

        if weather_type == "storm":
            # Storm: line outages due to wind/faults
            for i in range(n_scenarios):
                scenario = []
                # Multiple line outages
                n_outages = random.randint(1, min(5, branch_count))
                selected_branches = random.sample(range(branch_count), min(n_outages, branch_count))

                for branch_idx in selected_branches:
                    scenario.append(DisturbanceConfig(
                        disturbance_type=DisturbanceType.LINE_OUTAGE,
                        target_type='branch',
                        target_index=branch_idx,
                        parameter='br_status',
                        description=f"Storm damage - line {branch_idx} outage"
                    ))

                if scenario:
                    scenarios.append(scenario)

        elif weather_type == "heat_wave":
            # Heat wave: high loads due to AC, possible line derating
            for i in range(n_scenarios):
                scenario = []

                # System-wide load increase
                load_increase = random.uniform(0.2, 0.4)  # 20-40% increase
                for bus_idx in range(min(10, bus_count)):  # Affect first 10 buses
                    scenario.append(DisturbanceConfig(
                        disturbance_type=DisturbanceType.LOAD_INCREASE,
                        target_type='bus',
                        target_index=bus_idx,
                        parameter='pd',
                        change_percent=load_increase * 100,
                        description=f"Heat wave load increase at bus {bus_idx}"
                    ))

                # Line derating (reduce capacity)
                if branch_count > 0:
                    branch_idx = random.randint(0, branch_count - 1)
                    scenario.append(DisturbanceConfig(
                        disturbance_type=DisturbanceType.LINE_PARAMETER_CHANGE,
                        target_type='branch',
                        target_index=branch_idx,
                        parameter='rate_a',
                        change_percent=-30,  # Derate by 30%
                        description=f"Heat wave line derating at branch {branch_idx}"
                    ))

                if scenario:
                    scenarios.append(scenario)

        elif weather_type == "cold_snap":
            # Cold snap: high heating loads
            for i in range(n_scenarios):
                scenario = []
                load_increase = random.uniform(0.15, 0.35)

                for bus_idx in range(min(8, bus_count)):
                    scenario.append(DisturbanceConfig(
                        disturbance_type=DisturbanceType.LOAD_INCREASE,
                        target_type='bus',
                        target_index=bus_idx,
                        parameter='pd',
                        change_percent=load_increase * 100,
                        description=f"Cold snap heating load at bus {bus_idx}"
                    ))

                if scenario:
                    scenarios.append(scenario)

        return scenarios
