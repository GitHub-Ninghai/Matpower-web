"""
Time series simulation for MATPOWER Web platform.

This module provides functionality for simulating power system behavior
over time with varying load profiles and disturbance events.
"""

import copy
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import logging

from .disturbance import (
    DisturbanceConfig,
    TimeSeriesResult,
    Violation
)
from .disturbance_engine import DisturbanceEngine
from .auto_correction import SimulationEngineInterface

logger = logging.getLogger(__name__)


class TimeSeriesSimulator:
    """
    Time series simulator for sequential power flow simulations.

    This class handles simulating power system behavior over time with
    varying load profiles and injection of disturbance events at specific times.
    """

    def __init__(self, simulation_engine: Optional[SimulationEngineInterface] = None):
        """
        Initialize the time series simulator.

        Args:
            simulation_engine: Optional simulation engine for running power flow
        """
        self.engine = simulation_engine or SimulationEngineInterface()
        self.disturbance_engine = DisturbanceEngine()

        # Typical daily load profile coefficients (hourly multipliers)
        self._typical_daily_profile = np.array([
            0.65, 0.60, 0.58, 0.58, 0.60, 0.65,  # 00:00 - 05:00
            0.75, 0.85, 0.95, 1.00, 1.00, 0.98,  # 06:00 - 11:00
            0.95, 0.90, 0.88, 0.90, 0.95, 1.00,  # 12:00 - 17:00
            1.05, 1.10, 1.05, 0.95, 0.85, 0.75   # 18:00 - 23:00
        ])

        self._peak_day_profile = self._typical_daily_profile * 1.15
        self._valley_day_profile = self._typical_daily_profile * 0.80

    def generate_daily_load_profile(
        self,
        base_loads: Dict[int, float],
        pattern: str = "typical",
        resolution_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Generate a 24-hour daily load profile.

        Args:
            base_loads: Dictionary mapping bus indices to base load values (MW)
            pattern: Load pattern type ('typical', 'peak', 'valley', 'custom')
            resolution_minutes: Time resolution in minutes

        Returns:
            List of time steps with load factors for each bus
        """
        steps_per_hour = 60 // resolution_minutes
        n_steps = 24 * steps_per_hour

        # Select base profile
        if pattern == "peak":
            base_profile = self._peak_day_profile
        elif pattern == "valley":
            base_profile = self._valley_day_profile
        else:
            base_profile = self._typical_daily_profile

        # Interpolate to requested resolution
        profile = np.interp(
            np.linspace(0, 23, n_steps),
            np.arange(24),
            base_profile
        )

        # Generate time steps
        time_steps = []
        base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for i, factor in enumerate(profile):
            step_time = base_time + timedelta(minutes=i * resolution_minutes)

            # Add some randomness to make different buses have different patterns
            load_factors = {}
            for bus_id, base_load in base_loads.items():
                # Each bus has slight variation around the base profile
                bus_variation = np.random.normal(0, 0.05)  # 5% std dev
                bus_factor = max(0.5, min(1.5, factor * (1 + bus_variation)))
                load_factors[bus_id] = round(bus_factor, 4)

            time_steps.append({
                'step': i,
                'time': step_time.strftime('%H:%M'),
                'hour': i * resolution_minutes / 60,
                'base_factor': round(factor, 4),
                'load_factors': load_factors
            })

        return time_steps

    def run_time_series(
        self,
        case_data: Dict,
        load_profile: List[Dict[str, Any]],
        run_opf: bool = False,
        track_metrics: Optional[List[str]] = None
    ) -> TimeSeriesResult:
        """
        Run time series simulation following a load profile.

        Args:
            case_data: Base MATPOWER case data
            load_profile: List of time steps with load factors
            run_opf: Whether to run OPF at each step (default: power flow only)
            track_metrics: Optional list of metrics to track

        Returns:
            TimeSeriesResult with all time step results
        """
        if track_metrics is None:
            track_metrics = ['total_generation', 'total_load', 'min_voltage', 'max_voltage']

        results = []
        all_violations = []
        total_cost = 0.0

        bus = case_data.get('bus', np.array([]))
        pd_idx = self.disturbance_engine.BRANCH_COLUMNS.get('pd', 13)

        # Store original loads
        original_loads = {}
        for i, bus_row in enumerate(bus):
            if i < len(bus):
                original_loads[i] = float(bus_row[i, pd_idx]) if len(bus_row) > pd_idx else 0.0

        for step_info in load_profile:
            step = step_info['step']
            load_factors = step_info['load_factors']

            # Create modified case with updated loads
            modified_case = copy.deepcopy(case_data)

            # Apply load factors
            for bus_idx, factor in load_factors.items():
                if bus_idx < len(modified_case['bus']):
                    original_load = original_loads.get(bus_idx, 0)
                    modified_case['bus'][bus_idx, pd_idx] = original_load * factor

            # Run simulation
            try:
                if run_opf:
                    sim_result = self.engine.run_opf(modified_case)
                else:
                    sim_result = self.engine.run_power_flow(modified_case)

                convergence = sim_result.get('success', False)
            except Exception as e:
                logger.error(f"Time step {step} failed: {e}")
                convergence = False
                sim_result = {}

            # Get summary and detect violations
            summary = self.disturbance_engine.get_system_summary(modified_case, sim_result)
            violations = self.disturbance_engine.detect_violations(modified_case, sim_result)

            # Calculate metrics
            metrics = self._calculate_step_metrics(modified_case, sim_result, track_metrics)

            results.append({
                'step': step,
                'time': step_info['time'],
                'hour': step_info['hour'],
                'load_factors': load_factors,
                'convergence': convergence,
                'summary': summary,
                'violations': [v.dict() if hasattr(v, 'dict') else v for v in violations],
                'metrics': metrics,
                'num_violations': len(violations)
            })

            all_violations.extend(violations)

            if run_opf and 'cost' in sim_result:
                total_cost += sim_result['cost']

        # Find maximum violations
        max_violations = self._find_max_violations(all_violations)

        # Aggregate statistics
        agg_stats = self._calculate_aggregate_stats(results, track_metrics)

        return TimeSeriesResult(
            time_steps=len(load_profile),
            results=results,
            aggregate_statistics=agg_stats,
            max_violations=max_violations,
            total_cost=total_cost if run_opf else None
        )

    def _calculate_step_metrics(
        self,
        case_data: Dict,
        sim_result: Dict,
        metrics: List[str]
    ) -> Dict[str, float]:
        """Calculate metrics for a single time step."""
        calculated = {}
        bus = case_data.get('bus', np.array([]))
        gen = case_data.get('gen', np.array([]))

        if 'total_generation' in metrics and len(gen) > 0:
            pg_idx = self.disturbance_engine.GEN_COLUMNS['pg']
            calculated['total_generation'] = float(np.sum(gen[:, pg_idx]))

        if 'total_load' in metrics and len(bus) > 0:
            pd_idx = self.disturbance_engine.BUS_COLUMNS['pd']
            calculated['total_load'] = float(np.sum(bus[:, pd_idx]))

        if 'min_voltage' in metrics and len(bus) > 0:
            vm_idx = self.disturbance_engine.BUS_COLUMNS['vm']
            calculated['min_voltage'] = float(np.min(bus[:, vm_idx]))

        if 'max_voltage' in metrics and len(bus) > 0:
            vm_idx = self.disturbance_engine.BUS_COLUMNS['vm']
            calculated['max_voltage'] = float(np.max(bus[:, vm_idx]))

        if 'max_loading' in metrics:
            # Placeholder for max line loading
            calculated['max_loading'] = 0.0

        return calculated

    def _find_max_violations(self, violations: List[Violation]) -> List[Violation]:
        """Find the most severe violations across all time steps."""
        if not violations:
            return []

        # Sort by violation percent and return top 10
        sorted_violations = sorted(
            violations,
            key=lambda v: v.violation_percent,
            reverse=True
        )
        return sorted_violations[:10]

    def _calculate_aggregate_stats(
        self,
        results: List[Dict],
        metrics: List[str]
    ) -> Dict[str, Any]:
        """Calculate aggregate statistics across all time steps."""
        stats = {
            'convergence_rate': sum(1 for r in results if r['convergence']) / len(results) if results else 0,
            'steps_with_violations': sum(1 for r in results if r['num_violations'] > 0),
            'total_violations': sum(r['num_violations'] for r in results)
        }

        # Min/max for each metric
        for metric in metrics:
            values = [r['metrics'].get(metric, 0) for r in results if metric in r['metrics']]
            if values:
                stats[f'{metric}_min'] = min(values)
                stats[f'{metric}_max'] = max(values)
                stats[f'{metric}_avg'] = sum(values) / len(values)

        return stats

    def inject_event_at_step(
        self,
        case_data: Dict,
        load_profile: List[Dict[str, Any]],
        event_step: int,
        event: DisturbanceConfig,
        apply_to_subsequent: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Inject a disturbance event at a specific time step.

        Args:
            case_data: Base MATPOWER case data
            load_profile: Load profile for the simulation
            event_step: Time step at which to inject the event
            event: Disturbance configuration to apply
            apply_to_subsequent: Whether to keep disturbance for subsequent steps

        Returns:
            List of results for all time steps
        """
        results = []
        event_active = False
        modified_base_case = None

        for step_info in load_profile:
            step = step_info['step']
            load_factors = step_info['load_factors']

            # Check if we should activate the event
            if step == event_step:
                event_active = True
                # Apply event to create modified base case
                try:
                    modified_base_case = self.disturbance_engine.apply_disturbance(case_data, event)
                except ValueError as e:
                    logger.error(f"Failed to apply event at step {step}: {e}")
                    event_active = False
                    modified_base_case = case_data

            # Check if we should deactivate the event
            if not apply_to_subsequent and step > event_step:
                event_active = False
                modified_base_case = None

            # Use appropriate base case
            base_case = modified_base_case if event_active else case_data

            # Apply load factors
            modified_case = copy.deepcopy(base_case)
            bus = modified_case.get('bus', np.array([]))
            pd_idx = self.disturbance_engine.BUS_COLUMNS['pd']

            for bus_idx, factor in load_factors.items():
                if bus_idx < len(bus):
                    # Need to get original load from case_data
                    original_load = case_data['bus'][bus_idx, pd_idx]
                    modified_case['bus'][bus_idx, pd_idx] = original_load * factor

            # Run simulation
            try:
                sim_result = self.engine.run_power_flow(modified_case)
                convergence = sim_result.get('success', False)
            except Exception as e:
                logger.error(f"Step {step} failed: {e}")
                convergence = False
                sim_result = {}

            # Get results
            summary = self.disturbance_engine.get_system_summary(modified_case, sim_result)
            violations = self.disturbance_engine.detect_violations(modified_case, sim_result)

            results.append({
                'step': step,
                'time': step_info['time'],
                'hour': step_info['hour'],
                'event_active': event_active,
                'convergence': convergence,
                'summary': summary,
                'violations': [v.dict() if hasattr(v, 'dict') else v for v in violations],
                'num_violations': len(violations)
            })

        return results

    def generate_ramp_scenario(
        self,
        case_data: Dict,
        target_bus: int,
        start_load: float,
        end_load: float,
        steps: int,
        ramp_type: str = 'linear'
    ) -> List[Dict[str, Any]]:
        """
        Generate a load ramping scenario.

        Creates a sequence of load values that ramp from start_load to end_load
        over a specified number of steps.

        Args:
            case_data: Base MATPOWER case data
            target_bus: Bus index to apply the ramp
            start_load: Starting load value (MW)
            end_load: Ending load value (MW)
            steps: Number of ramp steps
            ramp_type: Type of ramp ('linear', 'exponential', 'step')

        Returns:
            List of time steps with load values
        """
        time_steps = []

        if ramp_type == 'linear':
            load_values = np.linspace(start_load, end_load, steps)
        elif ramp_type == 'exponential':
            # Exponential ramp (avoiding negative values)
            if start_load > 0 and end_load > 0:
                log_start = np.log(start_load)
                log_end = np.log(end_load)
                log_values = np.linspace(log_start, log_end, steps)
                load_values = np.exp(log_values)
            else:
                load_values = np.linspace(start_load, end_load, steps)
        elif ramp_type == 'step':
            # Step function: first half at start, second half at end
            mid_point = steps // 2
            load_values = np.concatenate([
                np.full(mid_point, start_load),
                np.full(steps - mid_point, end_load)
            ])
        else:
            raise ValueError(f"Unknown ramp_type: {ramp_type}")

        for i, load_value in enumerate(load_values):
            time_steps.append({
                'step': i,
                'bus': target_bus,
                'load_mw': round(load_value, 4),
                'load_factor': round(load_value / start_load if start_load > 0 else 1, 4),
                'ramp_type': ramp_type
            })

        return time_steps

    def generate_weekly_profile(
        self,
        base_loads: Dict[int, float],
        weekend_reduction: float = 0.85,
        daily_pattern: str = "typical"
    ) -> List[Dict[str, Any]]:
        """
        Generate a weekly load profile (7 days).

        Args:
            base_loads: Dictionary mapping bus indices to base load values
            weekend_reduction: Factor to reduce weekend loads (0-1)
            daily_pattern: Daily load pattern type

        Returns:
            List of 168 hourly time steps (24 * 7)
        """
        weekly_profile = []

        # Day types: weekday, Saturday, Sunday
        day_types = ['weekday'] * 5 + ['saturday', 'sunday']

        for day, day_type in enumerate(day_types):
            # Generate daily profile for this day
            if day_type == 'weekday':
                daily_profile = self.generate_daily_load_profile(
                    base_loads, pattern=daily_pattern, resolution_minutes=60
                )
            else:
                # Weekend has reduced loads
                weekend_loads = {k: v * weekend_reduction for k, v in base_loads.items()}
                daily_profile = self.generate_daily_load_profile(
                    weekend_loads, pattern=daily_pattern, resolution_minutes=60
                )

            # Add day offset
            day_offset = day * 24
            for step in daily_profile:
                step_copy = step.copy()
                step_copy['step'] += day_offset
                step_copy['day'] = day
                step_copy['day_type'] = day_type
                weekly_profile.append(step_copy)

        return weekly_profile

    def simulate_contingency_sequence(
        self,
        case_data: Dict,
        events: List[Dict[str, Any]],
        duration_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Simulate a sequence of contingency events over time.

        Args:
            case_data: Base MATPOWER case data
            events: List of events with 'time_hour' and 'disturbance' keys
            duration_hours: Total simulation duration

        Returns:
            List of hourly results
        """
        results = []
        current_case = copy.deepcopy(case_data)

        # Sort events by time
        sorted_events = sorted(events, key=lambda e: e['time_hour'])
        event_idx = 0

        for hour in range(duration_hours):
            # Apply any events scheduled for this hour
            while event_idx < len(sorted_events) and sorted_events[event_idx]['time_hour'] <= hour:
                try:
                    current_case = self.disturbance_engine.apply_disturbance(
                        current_case,
                        sorted_events[event_idx]['disturbance']
                    )
                except ValueError as e:
                    logger.error(f"Failed to apply event at hour {hour}: {e}")
                event_idx += 1

            # Run simulation for this hour
            try:
                sim_result = self.engine.run_power_flow(current_case)
                convergence = sim_result.get('success', False)
            except Exception as e:
                logger.error(f"Hour {hour} simulation failed: {e}")
                convergence = False
                sim_result = {}

            # Get results
            summary = self.disturbance_engine.get_system_summary(current_case, sim_result)
            violations = self.disturbance_engine.detect_violations(current_case, sim_result)

            results.append({
                'hour': hour,
                'convergence': convergence,
                'summary': summary,
                'violations': [v.dict() if hasattr(v, 'dict') else v for v in violations],
                'num_violations': len(violations),
                'events_this_hour': [
                    e for e in sorted_events if e['time_hour'] == hour
                ]
            })

        return results
