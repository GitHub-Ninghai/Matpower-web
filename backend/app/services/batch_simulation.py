"""
Batch simulation executor for MATPOWER Web platform.

This module provides functionality for running multiple power flow simulations
with various disturbances, including N-1 analysis, sensitivity analysis,
and Monte Carlo simulations.
"""

import copy
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from .disturbance import (
    DisturbanceConfig,
    DisturbanceResult,
    DisturbanceType,
    N1AnalysisResult,
    BatchSimulationResult,
    Violation
)
from .disturbance_engine import DisturbanceEngine
from .auto_correction import SimulationEngineInterface

logger = logging.getLogger(__name__)


class BatchSimulator:
    """
    Batch simulation executor for multiple disturbance scenarios.

    This class handles running multiple power flow simulations with different
    disturbance configurations, N-1 contingency analysis, and parameter sweeps.
    """

    def __init__(self, simulation_engine: Optional[SimulationEngineInterface] = None):
        """
        Initialize the batch simulator.

        Args:
            simulation_engine: Optional simulation engine for running power flow
        """
        self.engine = simulation_engine or SimulationEngineInterface()
        self.disturbance_engine = DisturbanceEngine()

    def run_batch(
        self,
        case_data: Dict,
        disturbances_list: List[List[DisturbanceConfig]],
        parallel: bool = True,
        max_workers: int = 4
    ) -> BatchSimulationResult:
        """
        Run batch simulations with multiple disturbance scenarios.

        Args:
            case_data: Base MATPOWER case data
            disturbances_list: List of disturbance scenarios (each scenario is a list)
            parallel: Whether to run simulations in parallel
            max_workers: Maximum number of parallel workers

        Returns:
            BatchSimulationResult with all scenario results
        """
        results = []
        successful = 0
        failed = 0

        def run_scenario(disturbances: List[DisturbanceConfig]) -> DisturbanceResult:
            """Run a single scenario."""
            # Apply disturbances
            modified_case = self.disturbance_engine.apply_multiple(case_data, disturbances)

            # Get pre-disturbance summary
            pre_summary = self.disturbance_engine.get_system_summary(case_data)

            # Run power flow
            try:
                pf_result = self.engine.run_power_flow(modified_case)
                convergence = pf_result.get('success', False)
            except Exception as e:
                logger.error(f"Power flow failed: {e}")
                pf_result = {}
                convergence = False

            # Get post-disturbance summary
            post_summary = self.disturbance_engine.get_system_summary(modified_case, pf_result)

            # Detect violations
            violations = self.disturbance_engine.detect_violations(modified_case, pf_result)

            return DisturbanceResult(
                disturbance=disturbances[0] if len(disturbances) == 1 else disturbances[0],
                pre_disturbance_summary=pre_summary,
                post_disturbance_summary=post_summary,
                violations=[Violation(**v) if isinstance(v, dict) else v for v in violations],
                convergence=convergence
            )

        # Execute scenarios
        if parallel and len(disturbances_list) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(run_scenario, disturbances): i
                    for i, disturbances in enumerate(disturbances_list)
                }

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        if result.convergence:
                            successful += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(f"Scenario failed: {e}")
                        failed += 1
        else:
            for disturbances in disturbances_list:
                try:
                    result = run_scenario(disturbances)
                    results.append(result)
                    if result.convergence:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Scenario failed: {e}")
                    failed += 1

        # Generate summary
        total_violations = sum(len(r.violations) for r in results)
        critical_violations = sum(
            1 for r in results
            for v in r.violations
            if v.severity.value in ['critical', 'high']
        )

        summary = {
            'total_violations': total_violations,
            'critical_violations': critical_violations,
            'scenarios_with_violations': sum(1 for r in results if r.violations),
            'convergence_rate': successful / len(disturbances_list) if disturbances_list else 0
        }

        return BatchSimulationResult(
            total_scenarios=len(disturbances_list),
            successful_scenarios=successful,
            failed_scenarios=failed,
            results=results,
            summary=summary
        )

    def run_n1_analysis(
        self,
        case_data: Dict,
        analyze_line_outages: bool = True,
        analyze_gen_outages: bool = True,
        parallel: bool = True
    ) -> N1AnalysisResult:
        """
        Perform N-1 contingency analysis.

        Tests each branch and generator outage to identify critical contingencies.

        Args:
            case_data: Base MATPOWER case data
            analyze_line_outages: Whether to analyze line outages
            analyze_gen_outages: Whether to analyze generator outages
            parallel: Whether to run in parallel

        Returns:
            N1AnalysisResult with detailed contingency information
        """
        branch = case_data.get('branch', np.array([]))
        gen = case_data.get('gen', np.array([]))

        line_outages = []
        gen_outages = []

        # Analyze line outages
        if analyze_line_outages:
            for i in range(len(branch)):
                # Skip if already out of service
                status_idx = self.disturbance_engine.BRANCH_COLUMNS['br_status']
                if branch[i][status_idx] == 0:
                    continue

                result = self._analyze_contingency(
                    case_data,
                    DisturbanceConfig(
                        disturbance_type=DisturbanceType.LINE_OUTAGE,
                        target_type='branch',
                        target_index=i,
                        parameter='br_status'
                    )
                )

                fbus = int(branch[i][self.disturbance_engine.BRANCH_COLUMNS['fbus']])
                tbus = int(branch[i][self.disturbance_engine.BRANCH_COLUMNS['tbus']])

                line_outages.append({
                    'branch_index': i,
                    'from_bus': fbus,
                    'to_bus': tbus,
                    'success': result['convergence'],
                    'violations': [v.dict() if hasattr(v, 'dict') else v for v in result['violations']],
                    'has_violations': len(result['violations']) > 0,
                    'severity': self._get_contingency_severity(result['violations'])
                })

        # Analyze generator outages
        if analyze_gen_outages:
            for i in range(len(gen)):
                # Skip if already out of service
                status_idx = self.disturbance_engine.GEN_COLUMNS['gen_status']
                if gen[i][status_idx] == 0:
                    continue

                result = self._analyze_contingency(
                    case_data,
                    DisturbanceConfig(
                        disturbance_type=DisturbanceType.GEN_OUTAGE,
                        target_type='gen',
                        target_index=i,
                        parameter='gen_status'
                    )
                )

                gen_bus = int(gen[i][self.disturbance_engine.GEN_COLUMNS['gen_bus']])

                gen_outages.append({
                    'gen_index': i,
                    'gen_bus': gen_bus,
                    'success': result['convergence'],
                    'violations': [v.dict() if hasattr(v, 'dict') else v for v in result['violations']],
                    'has_violations': len(result['violations']) > 0,
                    'severity': self._get_contingency_severity(result['violations'])
                })

        # Categorize contingencies
        critical_contingencies = []
        safe_contingencies = []

        for outage in line_outages + gen_outages:
            if outage['has_violations'] or not outage['success']:
                critical_contingencies.append(outage)
            else:
                safe_contingencies.append(outage)

        # Sort critical by severity
        critical_contingencies.sort(
            key=lambda x: x['severity'].value if hasattr(x['severity'], 'value') else 0
        )

        summary = {
            'total_contingencies_analyzed': len(line_outages) + len(gen_outages),
            'critical_contingencies': len(critical_contingencies),
            'safe_contingencies': len(safe_contingencies),
            'convergence_success_rate': (
                sum(1 for o in line_outages + gen_outages if o['success']) /
                (len(line_outages) + len(gen_outages))
                if (line_outages or gen_outages) else 1.0
            )
        }

        return N1AnalysisResult(
            total_branches=len(branch),
            total_generators=len(gen),
            line_outages=line_outages,
            gen_outages=gen_outages,
            critical_contingencies=critical_contingencies,
            safe_contingencies=safe_contingencies,
            summary=summary
        )

    def _analyze_contingency(
        self,
        case_data: Dict,
        disturbance: DisturbanceConfig
    ) -> Dict[str, Any]:
        """Analyze a single N-1 contingency."""
        # Apply disturbance
        try:
            modified_case = self.disturbance_engine.apply_disturbance(case_data, disturbance)
        except ValueError as e:
            return {
                'convergence': False,
                'violations': [],
                'error': str(e)
            }

        # Run power flow
        try:
            pf_result = self.engine.run_power_flow(modified_case)
            convergence = pf_result.get('success', False)
        except Exception:
            convergence = False
            pf_result = {}

        # Detect violations
        violations = self.disturbance_engine.detect_violations(modified_case, pf_result)

        return {
            'convergence': convergence,
            'violations': violations
        }

    def _get_contingency_severity(self, violations: List) -> str:
        """Determine overall severity of a contingency."""
        if not violations:
            return 'none'

        has_critical = any(
            v.severity.value == 'critical' if hasattr(v.severity, 'value') else False
            for v in violations
        )
        has_high = any(
            v.severity.value == 'high' if hasattr(v.severity, 'value') else False
            for v in violations
        )

        if has_critical:
            return 'critical'
        elif has_high:
            return 'high'
        elif len(violations) > 3:
            return 'medium'
        else:
            return 'low'

    def run_sensitivity_analysis(
        self,
        case_data: Dict,
        parameter: str,
        target_type: str,
        target_index: int,
        range_vals: List[float],
        output_metrics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform sensitivity analysis by varying a parameter over a range.

        Args:
            case_data: Base MATPOWER case data
            parameter: Parameter to vary (e.g., 'pd', 'pg', 'vg')
            target_type: Type of target ('bus', 'gen', 'branch')
            target_index: Index of target element
            range_vals: List of parameter values to test
            output_metrics: List of metrics to record (defaults to common ones)

        Returns:
            List of results for each parameter value
        """
        if output_metrics is None:
            output_metrics = ['total_cost', 'max_loading', 'min_voltage', 'max_voltage']

        results = []

        for value in range_vals:
            # Create disturbance for this parameter value
            disturbance = DisturbanceConfig(
                disturbance_type=DisturbanceType.LOAD_CHANGE if parameter in ['pd', 'qd'] else DisturbanceType.GEN_OUTPUT_CHANGE,
                target_type=target_type,
                target_index=target_index,
                parameter=parameter,
                new_value=value
            )

            try:
                # Apply disturbance
                modified_case = self.disturbance_engine.apply_disturbance(case_data, disturbance)

                # Run power flow
                pf_result = self.engine.run_power_flow(modified_case)

                # Calculate metrics
                metrics = self._calculate_metrics(modified_case, pf_result, output_metrics)

                # Detect violations
                violations = self.disturbance_engine.detect_violations(modified_case, pf_result)

                results.append({
                    'parameter_value': value,
                    'convergence': pf_result.get('success', False),
                    'metrics': metrics,
                    'violations': [v.dict() if hasattr(v, 'dict') else v for v in violations],
                    'num_violations': len(violations)
                })

            except Exception as e:
                logger.error(f"Sensitivity point failed for value {value}: {e}")
                results.append({
                    'parameter_value': value,
                    'convergence': False,
                    'error': str(e)
                })

        return results

    def _calculate_metrics(
        self,
        case_data: Dict,
        pf_result: Dict,
        metrics: List[str]
    ) -> Dict[str, float]:
        """Calculate output metrics from power flow result."""
        calculated = {}

        bus = case_data.get('bus', np.array([]))
        gen = case_data.get('gen', np.array([]))
        branch = case_data.get('branch', np.array([]))

        if 'min_voltage' in metrics and len(bus) > 0:
            vm_idx = self.disturbance_engine.BUS_COLUMNS['vm']
            calculated['min_voltage'] = float(np.min(bus[:, vm_idx]))

        if 'max_voltage' in metrics and len(bus) > 0:
            vm_idx = self.disturbance_engine.BUS_COLUMNS['vm']
            calculated['max_voltage'] = float(np.max(bus[:, vm_idx]))

        if 'total_generation' in metrics and len(gen) > 0:
            pg_idx = self.disturbance_engine.GEN_COLUMNS['pg']
            calculated['total_generation'] = float(np.sum(gen[:, pg_idx]))

        if 'total_load' in metrics and len(bus) > 0:
            pd_idx = self.disturbance_engine.BUS_COLUMNS['pd']
            calculated['total_load'] = float(np.sum(bus[:, pd_idx]))

        if 'max_loading' in metrics and len(branch) > 0:
            rate_a_idx = self.disturbance_engine.BRANCH_COLUMNS['rate_a']
            max_loading = 0.0
            for br in branch:
                rate_a = float(br[rate_a_idx])
                if rate_a > 0:
                    # Placeholder - actual loading from pf_result
                    max_loading = max(max_loading, 0.0)
            calculated['max_loading'] = max_loading

        if 'total_cost' in metrics:
            # Simple quadratic cost function approximation
            if len(gen) > 0:
                pg_idx = self.disturbance_engine.GEN_COLUMNS['pg']
                total_cost = np.sum(gen[:, pg_idx] ** 2 * 0.01 + gen[:, pg_idx] * 10)
                calculated['total_cost'] = float(total_cost)

        # Add any metrics from pf_result
        for metric in metrics:
            if metric in pf_result:
                calculated[metric] = pf_result[metric]

        return calculated

    def run_monte_carlo(
        self,
        case_data: Dict,
        n_samples: int,
        params: Dict[str, Any],
        seed: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform Monte Carlo simulation with random parameter variations.

        Args:
            case_data: Base MATPOWER case data
            n_samples: Number of random samples to generate
            params: Dictionary specifying parameter distributions:
                    {'load_variation': (-0.2, 0.2), 'gen_outage_prob': 0.05, ...}
            seed: Random seed for reproducibility

        Returns:
            List of results for each sample
        """
        if seed is not None:
            np.random.seed(seed)

        results = []

        for i in range(n_samples):
            # Generate random disturbances based on distributions
            disturbances = self._generate_random_disturbances(case_data, params)

            try:
                # Apply disturbances
                modified_case = self.disturbance_engine.apply_multiple(case_data, disturbances)

                # Run power flow
                pf_result = self.engine.run_power_flow(modified_case)

                # Get summary
                summary = self.disturbance_engine.get_system_summary(modified_case, pf_result)

                # Detect violations
                violations = self.disturbance_engine.detect_violations(modified_case, pf_result)

                results.append({
                    'sample_id': i,
                    'disturbances': [d.dict() if hasattr(d, 'dict') else d for d in disturbances],
                    'convergence': pf_result.get('success', False),
                    'summary': summary,
                    'violations': [v.dict() if hasattr(v, 'dict') else v for v in violations],
                    'has_violations': len(violations) > 0
                })

            except Exception as e:
                logger.error(f"Monte Carlo sample {i} failed: {e}")
                results.append({
                    'sample_id': i,
                    'convergence': False,
                    'error': str(e)
                })

        # Calculate aggregate statistics
        successful = [r for r in results if r.get('convergence', False)]
        with_violations = [r for r in successful if r.get('has_violations', False)]

        aggregate_stats = {
            'total_samples': n_samples,
            'successful_samples': len(successful),
            'samples_with_violations': len(with_violations),
            'violation_probability': len(with_violations) / len(successful) if successful else 0,
            'convergence_rate': len(successful) / n_samples if n_samples > 0 else 0
        }

        # Add to last result or return separately
        return results, aggregate_stats

    def _generate_random_disturbances(
        self,
        case_data: Dict,
        params: Dict[str, Any]
    ) -> List[DisturbanceConfig]:
        """Generate random disturbances based on parameter distributions."""
        disturbances = []

        # Load variation
        if 'load_variation' in params:
            load_range = params['load_variation']
            for i in range(len(case_data.get('bus', []))):
                variation = np.random.uniform(load_range[0], load_range[1])
                if abs(variation) > 0.01:  # Only add if significant
                    disturbances.append(DisturbanceConfig(
                        disturbance_type=DisturbanceType.LOAD_INCREASE if variation > 0 else DisturbanceType.LOAD_DECREASE,
                        target_type='bus',
                        target_index=i,
                        parameter='pd',
                        change_percent=variation * 100
                    ))

        # Generator outages
        if 'gen_outage_prob' in params:
            outage_prob = params['gen_outage_prob']
            for i in range(len(case_data.get('gen', []))):
                if np.random.random() < outage_prob:
                    disturbances.append(DisturbanceConfig(
                        disturbance_type=DisturbanceType.GEN_OUTAGE,
                        target_type='gen',
                        target_index=i,
                        parameter='gen_status'
                    ))

        # Branch outages
        if 'branch_outage_prob' in params:
            outage_prob = params['branch_outage_prob']
            for i in range(len(case_data.get('branch', []))):
                if np.random.random() < outage_prob:
                    disturbances.append(DisturbanceConfig(
                        disturbance_type=DisturbanceType.LINE_OUTAGE,
                        target_type='branch',
                        target_index=i,
                        parameter='br_status'
                    ))

        return disturbances
