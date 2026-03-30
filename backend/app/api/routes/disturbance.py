"""
API routes for disturbance injection and batch simulation.

This module provides REST endpoints for:
- Applying disturbances to power system cases
- Running batch simulations
- N-1 contingency analysis
- Automatic correction
- Time series simulation
- Scenario generation
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from ...services.disturbance import (
    DisturbanceConfig,
    DisturbanceResult,
    DisturbanceType,
    BatchSimulationResult,
    N1AnalysisResult,
    TimeSeriesResult,
    Violation
)
from ...services.disturbance_engine import DisturbanceEngine
from ...services.batch_simulation import BatchSimulator
from ...services.auto_correction import AutoCorrection, SimulationEngineInterface
from ...services.time_series_sim import TimeSeriesSimulator
from ...services.scenario_generator import ScenarioGenerator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/disturbance",
    tags=["disturbance"]
)

# Global instances (will be initialized with real simulation engine)
_disturbance_engine = None
_batch_simulator = None
_auto_correction = None
_time_series_simulator = None
_scenario_generator = None


def get_disturbance_engine():
    """Get disturbance engine instance."""
    global _disturbance_engine
    if _disturbance_engine is None:
        _disturbance_engine = DisturbanceEngine()
    return _disturbance_engine


def get_batch_simulator():
    """Get batch simulator instance."""
    global _batch_simulator
    if _batch_simulator is None:
        _batch_simulator = BatchSimulator()
    return _batch_simulator


def get_auto_correction():
    """Get auto correction instance."""
    global _auto_correction
    if _auto_correction is None:
        _auto_correction = AutoCorrection()
    return _auto_correction


def get_time_series_simulator():
    """Get time series simulator instance."""
    global _time_series_simulator
    if _time_series_simulator is None:
        _time_series_simulator = TimeSeriesSimulator()
    return _time_series_simulator


def get_scenario_generator():
    """Get scenario generator instance."""
    global _scenario_generator
    if _scenario_generator is None:
        _scenario_generator = ScenarioGenerator()
    return _scenario_generator


# Request/Response Models
class ApplyDisturbanceRequest(BaseModel):
    """Request to apply a single disturbance."""
    case_data: Dict[str, Any] = Field(..., description="MATPOWER case data")
    disturbance: DisturbanceConfig
    run_correction: bool = Field(False, description="Whether to run automatic correction")


class ApplyBatchDisturbancesRequest(BaseModel):
    """Request to apply multiple disturbance scenarios."""
    case_data: Dict[str, Any] = Field(..., description="MATPOWER case data")
    disturbances_list: List[List[DisturbanceConfig]] = Field(
        ...,
        description="List of disturbance scenarios (each scenario is a list)"
    )
    parallel: bool = Field(True, description="Run simulations in parallel")
    max_workers: int = Field(4, description="Maximum parallel workers")


class AutoCorrectRequest(BaseModel):
    """Request for automatic correction."""
    case_data: Dict[str, Any] = Field(..., description="Post-disturbance case data")
    disturbance_result: DisturbanceResult


class N1AnalysisRequest(BaseModel):
    """Request for N-1 contingency analysis."""
    case_data: Dict[str, Any] = Field(..., description="MATPOWER case data")
    analyze_line_outages: bool = Field(True, description="Analyze line outages")
    analyze_gen_outages: bool = Field(True, description="Analyze generator outages")
    parallel: bool = Field(True, description="Run in parallel")


class SensitivityAnalysisRequest(BaseModel):
    """Request for sensitivity analysis."""
    case_data: Dict[str, Any] = Field(..., description="MATPOWER case data")
    parameter: str = Field(..., description="Parameter to vary (e.g., 'pd', 'pg')")
    target_type: str = Field(..., description="Target element type ('bus', 'gen', 'branch')")
    target_index: int = Field(..., description="Target element index")
    range_values: List[float] = Field(..., description="List of parameter values to test")
    output_metrics: Optional[List[str]] = Field(None, description="Metrics to track")


class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo simulation."""
    case_data: Dict[str, Any] = Field(..., description="MATPOWER case data")
    n_samples: int = Field(..., ge=1, le=10000, description="Number of random samples")
    params: Dict[str, Any] = Field(..., description="Parameter distributions")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")


class TimeSeriesRequest(BaseModel):
    """Request for time series simulation."""
    case_data: Dict[str, Any] = Field(..., description="MATPOWER case data")
    load_profile: List[Dict[str, Any]] = Field(..., description="Load profile for time steps")
    run_opf: bool = Field(False, description="Run OPF at each step")
    track_metrics: Optional[List[str]] = Field(None, description="Metrics to track")


class GenerateScenariosRequest(BaseModel):
    """Request to generate random scenarios."""
    case_data: Dict[str, Any] = Field(..., description="MATPOWER case data")
    n_scenarios: int = Field(..., ge=1, le=1000, description="Number of scenarios")
    severity: str = Field("medium", description="Severity level ('light', 'medium', 'severe')")
    scenario_type: str = Field("random", description="Scenario type")
    allowed_types: Optional[List[DisturbanceType]] = Field(None, description="Allowed disturbance types")


class GenerateLoadProfileRequest(BaseModel):
    """Request to generate daily load profile."""
    base_loads: Dict[int, float] = Field(..., description="Base loads per bus (MW)")
    pattern: str = Field("typical", description="Load pattern ('typical', 'peak', 'valley')")
    resolution_minutes: int = Field(60, description="Time resolution in minutes")


class InjectEventRequest(BaseModel):
    """Request to inject event at specific time step."""
    case_data: Dict[str, Any] = Field(..., description="MATPOWER case data")
    load_profile: List[Dict[str, Any]] = Field(..., description="Load profile")
    event_step: int = Field(..., description="Time step for event injection")
    event: DisturbanceConfig
    apply_to_subsequent: bool = Field(False, description="Keep event for subsequent steps")


# Endpoints

@router.post("/apply", response_model=DisturbanceResult)
async def apply_disturbance(request: ApplyDisturbanceRequest):
    """
    Apply a single disturbance to a power system case.

    This endpoint:
    1. Validates the disturbance
    2. Applies it to the case data
    3. Runs power flow
    4. Detects violations
    5. Optionally runs automatic correction
    """
    engine = get_disturbance_engine()
    auto_corr = get_auto_correction()

    try:
        # Validate disturbance
        engine.validate_disturbance(request.case_data, request.disturbance)

        # Get pre-disturbance summary
        pre_summary = engine.get_system_summary(request.case_data)

        # Apply disturbance
        modified_case = engine.apply_disturbance(request.case_data, request.disturbance)

        # Run power flow (TODO: Replace with actual engine call)
        # pf_result = simulation_engine.run_power_flow(modified_case)
        pf_result = {'success': True}  # Placeholder

        # Get post-disturbance summary
        post_summary = engine.get_system_summary(modified_case, pf_result)

        # Detect violations
        violations = engine.detect_violations(modified_case, pf_result)

        # Create result
        result = DisturbanceResult(
            disturbance=request.disturbance,
            pre_disturbance_summary=pre_summary,
            post_disturbance_summary=post_summary,
            violations=violations,
            convergence=pf_result.get('success', False)
        )

        # Run auto-correction if requested
        if request.run_correction and violations:
            correction = auto_corr.correct_with_opf(modified_case, result)
            result.correction_applied = correction.get('success', False)
            result.correction_result = correction

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying disturbance: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/apply-batch", response_model=BatchSimulationResult)
async def apply_batch_disturbances(request: ApplyBatchDisturbancesRequest):
    """
    Apply multiple disturbance scenarios in batch.

    Runs power flow for each scenario and returns aggregated results.
    """
    simulator = get_batch_simulator()

    try:
        result = simulator.run_batch(
            request.case_data,
            request.disturbances_list,
            parallel=request.parallel,
            max_workers=request.max_workers
        )
        return result

    except Exception as e:
        logger.error(f"Error in batch simulation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/auto-correct")
async def auto_correct(request: AutoCorrectRequest):
    """
    Apply automatic OPF-based correction to a disturbed case.

    Attempts to resolve violations by re-optimizing generator dispatch.
    """
    auto_corr = get_auto_correction()

    try:
        result = auto_corr.correct_with_opf(
            request.case_data,
            request.disturbance_result
        )
        return result

    except Exception as e:
        logger.error(f"Error in auto correction: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/presets/{case_name}")
async def get_disturbance_presets(case_name: str):
    """
    Get predefined disturbance scenarios for a specific test case.

    Returns commonly used disturbances for IEEE test cases.
    """
    engine = get_disturbance_engine()

    try:
        presets = engine.get_disturbance_presets(case_name)
        return {
            'case_name': case_name,
            'presets': presets
        }

    except Exception as e:
        logger.error(f"Error getting presets: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/types")
async def get_disturbance_types():
    """
    Get list of supported disturbance types.

    Returns all disturbance types with descriptions.
    """
    disturbance_types = [
        {
            'type': DisturbanceType.LINE_OUTAGE,
            'description': 'Transmission line outage',
            'target_type': 'branch',
            'parameter': 'br_status'
        },
        {
            'type': DisturbanceType.GEN_OUTAGE,
            'description': 'Generator outage',
            'target_type': 'gen',
            'parameter': 'gen_status'
        },
        {
            'type': DisturbanceType.LOAD_INCREASE,
            'description': 'Load increase (percentage)',
            'target_type': 'bus',
            'parameter': 'pd'
        },
        {
            'type': DisturbanceType.LOAD_DECREASE,
            'description': 'Load decrease (percentage)',
            'target_type': 'bus',
            'parameter': 'pd'
        },
        {
            'type': DisturbanceType.LOAD_CHANGE,
            'description': 'Load change to absolute value',
            'target_type': 'bus',
            'parameter': 'pd'
        },
        {
            'type': DisturbanceType.VOLTAGE_SETPOINT_CHANGE,
            'description': 'Generator voltage setpoint change',
            'target_type': 'gen',
            'parameter': 'vg'
        },
        {
            'type': DisturbanceType.GEN_OUTPUT_CHANGE,
            'description': 'Generator output change',
            'target_type': 'gen',
            'parameter': 'pg'
        },
        {
            'type': DisturbanceType.LINE_PARAMETER_CHANGE,
            'description': 'Line parameter change (R, X, B)',
            'target_type': 'branch',
            'parameter': 'br_r/br_x/br_b'
        },
    ]

    return {'disturbance_types': disturbance_types}


# Simulation endpoints (separate router for clarity)
simulation_router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@simulation_router.post("/n1-analysis", response_model=N1AnalysisResult)
async def run_n1_analysis(request: N1AnalysisRequest):
    """
    Perform N-1 contingency analysis.

    Tests all single element outages to identify critical contingencies.
    """
    simulator = get_batch_simulator()

    try:
        result = simulator.run_n1_analysis(
            request.case_data,
            analyze_line_outages=request.analyze_line_outages,
            analyze_gen_outages=request.analyze_gen_outages,
            parallel=request.parallel
        )
        return result

    except Exception as e:
        logger.error(f"Error in N-1 analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@simulation_router.post("/sensitivity")
async def run_sensitivity_analysis(request: SensitivityAnalysisRequest):
    """
    Perform sensitivity analysis by varying a parameter.

    Returns system response across a range of parameter values.
    """
    simulator = get_batch_simulator()

    try:
        results = simulator.run_sensitivity_analysis(
            request.case_data,
            request.parameter,
            request.target_type,
            request.target_index,
            request.range_values,
            request.output_metrics
        )
        return {'results': results}

    except Exception as e:
        logger.error(f"Error in sensitivity analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@simulation_router.post("/monte-carlo")
async def run_monte_carlo(request: MonteCarloRequest):
    """
    Perform Monte Carlo simulation with random disturbances.

    Generates statistical results from multiple random scenarios.
    """
    simulator = get_batch_simulator()

    try:
        results, stats = simulator.run_monte_carlo(
            request.case_data,
            request.n_samples,
            request.params,
            request.seed
        )
        return {
            'results': results,
            'aggregate_statistics': stats
        }

    except Exception as e:
        logger.error(f"Error in Monte Carlo simulation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@simulation_router.post("/time-series", response_model=TimeSeriesResult)
async def run_time_series(request: TimeSeriesRequest):
    """
    Run time series simulation following a load profile.

    Simulates system behavior over multiple time steps.
    """
    simulator = get_time_series_simulator()

    try:
        result = simulator.run_time_series(
            request.case_data,
            request.load_profile,
            run_opf=request.run_opf,
            track_metrics=request.track_metrics
        )
        return result

    except Exception as e:
        logger.error(f"Error in time series simulation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@simulation_router.post("/generate-scenarios")
async def generate_scenarios(request: GenerateScenariosRequest):
    """
    Generate random disturbance scenarios.

    Creates scenarios for batch testing or training data.
    """
    generator = get_scenario_generator()

    try:
        if request.scenario_type == "random":
            scenarios = generator.generate_random_disturbances(
                request.case_data,
                request.n_scenarios,
                request.severity,
                request.allowed_types
            )
        elif request.scenario_type == "composite":
            scenarios = generator.generate_composite_scenarios(
                request.case_data,
                request.n_scenarios
            )
        elif request.scenario_type == "load_variation":
            scenarios = [generator.generate_load_variation_scenarios(
                request.case_data,
                request.n_scenarios
            )]
        elif request.scenario_type == "cascading":
            scenarios = generator.generate_cascading_scenarios(
                request.case_data,
                request.n_scenarios
            )
        elif request.scenario_type == "weather":
            # Default to storm for weather scenarios
            scenarios = generator.generate_weather_scenarios(
                request.case_data,
                "storm",
                request.n_scenarios
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown scenario type: {request.scenario_type}"
            )

        # Validate scenarios
        valid_scenarios = []
        invalid_count = 0

        for scenario in scenarios:
            is_valid, _ = generator.validate_scenario(request.case_data, scenario)
            if is_valid:
                valid_scenarios.append(scenario)
            else:
                invalid_count += 1

        return {
            'total_generated': len(scenarios),
            'valid_scenarios': len(valid_scenarios),
            'invalid_scenarios': invalid_count,
            'scenarios': valid_scenarios
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating scenarios: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@simulation_router.post("/generate-load-profile")
async def generate_load_profile(request: GenerateLoadProfileRequest):
    """
    Generate a daily load profile for time series simulation.

    Returns hourly load multipliers for each bus.
    """
    simulator = get_time_series_simulator()

    try:
        profile = simulator.generate_daily_load_profile(
            request.base_loads,
            pattern=request.pattern,
            resolution_minutes=request.resolution_minutes
        )
        return {
            'pattern': request.pattern,
            'resolution_minutes': request.resolution_minutes,
            'time_steps': len(profile),
            'profile': profile
        }

    except Exception as e:
        logger.error(f"Error generating load profile: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@simulation_router.post("/inject-event")
async def inject_event_at_step(request: InjectEventRequest):
    """
    Inject a disturbance event at a specific time step.

    Runs time series simulation with event injection.
    """
    simulator = get_time_series_simulator()

    try:
        results = simulator.inject_event_at_step(
            request.case_data,
            request.load_profile,
            request.event_step,
            request.event,
            request.apply_to_subsequent
        )
        return {
            'event_step': request.event_step,
            'apply_to_subsequent': request.apply_to_subsequent,
            'results': results
        }

    except Exception as e:
        logger.error(f"Error injecting event: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@simulation_router.get("/violation-severities")
async def get_violation_severities():
    """
    Get list of violation severity levels.

    Returns severity levels with descriptions and thresholds.
    """
    return {
        'severity_levels': [
            {
                'level': 'low',
                'description': 'Minor violation, may be acceptable for short periods',
                'voltage_threshold_percent': 2,
                'overload_threshold_percent': 10
            },
            {
                'level': 'medium',
                'description': 'Moderate violation, requires attention',
                'voltage_threshold_percent': 5,
                'overload_threshold_percent': 20
            },
            {
                'level': 'high',
                'description': 'Significant violation, requires immediate action',
                'voltage_threshold_percent': 10,
                'overload_threshold_percent': 50
            },
            {
                'level': 'critical',
                'description': 'Severe violation, system at risk',
                'voltage_threshold_percent': 10,
                'overload_threshold_percent': 50
            }
        ]
    }


# Export routers for app inclusion
__all__ = ['router', 'simulation_router']
