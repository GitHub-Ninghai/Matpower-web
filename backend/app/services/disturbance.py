"""
Disturbance type definitions and parameter validation for MATPOWER Web platform.

This module defines all disturbance types that can be injected into the power system,
along with their configuration schemas and validation rules.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import numpy as np


class DisturbanceType(str, Enum):
    """Enumeration of all supported disturbance types."""
    LINE_OUTAGE = "line_outage"
    GEN_OUTAGE = "gen_outage"
    LOAD_INCREASE = "load_increase"
    LOAD_DECREASE = "load_decrease"
    LOAD_CHANGE = "load_change"
    VOLTAGE_SETPOINT_CHANGE = "voltage_setpoint_change"
    LINE_PARAMETER_CHANGE = "line_param_change"
    GEN_OUTPUT_CHANGE = "gen_output_change"


class DisturbanceConfig(BaseModel):
    """
    Configuration for a single disturbance event.

    Attributes:
        disturbance_type: Type of disturbance to apply
        target_type: Type of target element ("bus", "gen", "branch")
        target_index: Row index in the respective matrix (0-based)
        parameter: Parameter name to modify (e.g., "pd", "pg", "br_status")
        old_value: Original value (auto-detected if None)
        new_value: New absolute value to set
        change_percent: Percentage change (e.g., +50 for 50% increase)
        description: Human-readable description
    """
    disturbance_type: DisturbanceType
    target_type: str = Field(..., pattern="^(bus|gen|branch)$")
    target_index: int = Field(..., ge=0)
    parameter: Optional[str] = None
    old_value: Optional[float] = None
    new_value: Optional[float] = None
    change_percent: Optional[float] = None
    description: Optional[str] = None

    @field_validator('disturbance_type', 'target_type', mode='before')
    @classmethod
    def lowercase_strings(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator('target_type')
    @classmethod
    def validate_target_type_match(cls, v, info):
        """Ensure target_type matches disturbance_type requirements."""
        disturbance_type = info.data.get('disturbance_type')
        if disturbance_type is None:
            return v

        requirements = {
            DisturbanceType.LINE_OUTAGE: 'branch',
            DisturbanceType.GEN_OUTAGE: 'gen',
            DisturbanceType.LOAD_INCREASE: 'bus',
            DisturbanceType.LOAD_DECREASE: 'bus',
            DisturbanceType.LOAD_CHANGE: 'bus',
            DisturbanceType.VOLTAGE_SETPOINT_CHANGE: 'gen',
            DisturbanceType.GEN_OUTPUT_CHANGE: 'gen',
            DisturbanceType.LINE_PARAMETER_CHANGE: 'branch',
        }

        required = requirements.get(disturbance_type)
        if required and v != required:
            raise ValueError(
                f"Disturbance type {disturbance_type} requires target_type='{required}', got '{v}'"
            )
        return v

    @field_validator('parameter')
    @classmethod
    def validate_parameter(cls, v, info):
        """Validate parameter name based on disturbance type."""
        disturbance_type = info.data.get('disturbance_type')
        target_type = info.data.get('target_type')

        if disturbance_type is None or target_type is None:
            return v

        valid_params = {
            ('bus', 'load_change'): ['pd', 'qd', 'p_load', 'q_load'],
            ('bus', 'load_increase'): ['pd', 'qd', 'p_load', 'q_load'],
            ('bus', 'load_decrease'): ['pd', 'qd', 'p_load', 'q_load'],
            ('gen', 'voltage_setpoint_change'): ['vg', 'v_setpoint'],
            ('gen', 'gen_output_change'): ['pg', 'qg', 'p_gen', 'q_gen'],
            ('branch', 'line_param_change'): ['br_r', 'br_x', 'br_b', 'r', 'x', 'b'],
            ('branch', 'line_outage'): ['br_status', 'status'],
            ('gen', 'gen_outage'): ['gen_status', 'status'],
        }

        key = (target_type, disturbance_type)
        if key in valid_params and v is not None:
            if v.lower() not in [p.lower() for p in valid_params[key]]:
                raise ValueError(
                    f"Invalid parameter '{v}' for {disturbance_type} on {target_type}. "
                    f"Valid options: {valid_params[key]}"
                )
        return v

    @field_validator('change_percent')
    @classmethod
    def validate_change_percent(cls, v):
        """Validate percentage change is within reasonable bounds."""
        if v is not None and abs(v) > 200:
            raise ValueError("change_percent must be between -200% and +200%")
        return v


class ViolationSeverity(str, Enum):
    """Severity levels for constraint violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Violation(BaseModel):
    """Represents a single constraint violation."""
    type: str = Field(..., description="Type of violation: 'voltage', 'line_overload', 'gen_limit'")
    target_type: str = Field(..., description="Type of element: 'bus', 'branch', 'gen'")
    target_index: int = Field(..., description="Index of violating element")
    parameter: str = Field(..., description="Parameter that violated limits")
    current_value: float = Field(..., description="Current value of the parameter")
    limit_value: float = Field(..., description="Limit value that was exceeded")
    severity: ViolationSeverity = Field(..., description="Severity of the violation")
    violation_percent: float = Field(..., description="Percentage over/under limit")

    class Config:
        use_enum_values = True


class DisturbanceResult(BaseModel):
    """
    Result of applying a disturbance to a power system case.

    Contains pre and post-disturbance system summaries, detected violations,
    convergence status, and optional correction results.
    """
    disturbance: DisturbanceConfig
    pre_disturbance_summary: Dict[str, Any]
    post_disturbance_summary: Dict[str, Any]
    violations: List[Violation]
    convergence: bool
    correction_applied: bool = False
    correction_result: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class BatchSimulationResult(BaseModel):
    """Result of a batch simulation with multiple disturbances."""
    total_scenarios: int
    successful_scenarios: int
    failed_scenarios: int
    results: List[DisturbanceResult]
    summary: Dict[str, Any]


class N1AnalysisResult(BaseModel):
    """Result of N-1 contingency analysis."""
    total_branches: int
    total_generators: int
    line_outages: List[Dict[str, Any]]
    gen_outages: List[Dict[str, Any]]
    critical_contingencies: List[Dict[str, Any]]
    safe_contingencies: List[Dict[str, Any]]
    summary: Dict[str, Any]


class TimeSeriesResult(BaseModel):
    """Result of time series simulation."""
    time_steps: int
    results: List[Dict[str, Any]]
    aggregate_statistics: Dict[str, Any]
    max_violations: List[Violation]
    total_cost: Optional[float] = None
