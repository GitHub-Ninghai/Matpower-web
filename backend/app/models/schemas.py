"""
Pydantic data models for MATPOWER Web Backend
Defines all request/response schemas for the API
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any, Union
from enum import IntEnum


class BusType(IntEnum):
    """Bus type enumeration per MATPOWER specification"""
    PQ = 1  # PQ bus (load bus)
    PV = 2  # PV bus (generator bus)
    REF = 3  # Reference bus
    ISOLATED = 4  # Isolated bus


class BusData(BaseModel):
    """Bus data model - corresponds to MATPOWER bus matrix columns"""
    # Input columns (1-13)
    bus_i: int = Field(..., description="Bus number (positive integer)")
    bus_type: BusType = Field(..., description="Bus type (1=PQ, 2=PV, 3=ref, 4=isolated)")
    pd: float = Field(default=0.0, description="Real power demand (MW)")
    qd: float = Field(default=0.0, description="Reactive power demand (MVAr)")
    gs: float = Field(default=0.0, description="Shunt conductance (MW at V = 1.0 p.u.)")
    bs: float = Field(default=0.0, description="Shunt susceptance (MVAr at V = 1.0 p.u.)")
    area: int = Field(default=1, description="Area number (positive integer)")
    vm: float = Field(default=1.0, description="Voltage magnitude (p.u.)")
    va: float = Field(default=0.0, description="Voltage angle (degrees)")
    base_kv: float = Field(default=0.0, description="Base voltage (kV)")
    zone: int = Field(default=1, description="Zone number (positive integer)")
    vmax: float = Field(default=1.1, description="Maximum voltage magnitude (p.u.)")
    vmin: float = Field(default=0.9, description="Minimum voltage magnitude (p.u.)")

    # Output columns (14-17) - populated after simulation
    lam_p: Optional[float] = Field(default=None, description="Lagrange multiplier on real power mismatch")
    lam_q: Optional[float] = Field(default=None, description="Lagrange multiplier on reactive power mismatch")
    mu_vmax: Optional[float] = Field(default=None, description="Lagrange multiplier on upper voltage limit")
    mu_vmin: Optional[float] = Field(default=None, description="Lagrange multiplier on lower voltage limit")

    # Additional columns for extended results
    lam_p_shift: Optional[float] = Field(default=None, alias="lam_p_shift", description="Angle shift limit Lagrange multiplier")


class GeneratorData(BaseModel):
    """Generator data model - corresponds to MATPOWER gen matrix columns"""
    # Input columns (1-21)
    gen_bus: int = Field(..., description="Bus number")
    pg: float = Field(default=0.0, description="Real power output (MW)")
    qg: float = Field(default=0.0, description="Reactive power output (MVAr)")
    qmax: float = Field(default=0.0, description="Maximum reactive power output (MVAr)")
    qmin: float = Field(default=0.0, description="Minimum reactive power output (MVAr)")
    vg: float = Field(default=1.0, description="Voltage magnitude setpoint (p.u.)")
    mbase: float = Field(default=100.0, description="Total MVA base of this machine")
    gen_status: int = Field(default=1, description="Status (1=in-service, 0=out-of-service)")
    pmax: float = Field(default=0.0, description="Maximum real power output (MW)")
    pmin: float = Field(default=0.0, description="Minimum real power output (MW)")
    pc1: Optional[float] = Field(default=0.0, description="Lower real power output of PQ capability curve")
    pc2: Optional[float] = Field(default=0.0, description="Upper real power output of PQ capability curve")
    qc1min: Optional[float] = Field(default=0.0, description="Minimum reactive power output at pc1")
    qc1max: Optional[float] = Field(default=0.0, description="Maximum reactive power output at pc1")
    qc2min: Optional[float] = Field(default=0.0, description="Minimum reactive power output at pc2")
    qc2max: Optional[float] = Field(default=0.0, description="Maximum reactive power output at pc2")
    ramp_agc: Optional[float] = Field(default=0.0, description="Ramp rate for load following/AGC (MW/min)")
    ramp_10: Optional[float] = Field(default=0.0, description="Ramp rate for 10 minute reserves (MW/min)")
    ramp_30: Optional[float] = Field(default=0.0, description="Ramp rate for 30 minute reserves (MW/min)")
    ramp_q: Optional[float] = Field(default=0.0, description="Ramp rate for reactive power (2 sec timescale)")

    # Output columns (22-23)
    apf: Optional[float] = Field(default=None, description="Participation factor (MW)")

    # Additional fields for OPF results
    mu_pmax: Optional[float] = Field(default=None, description="Lagrange multiplier on upper PG limit")
    mu_pmin: Optional[float] = Field(default=None, description="Lagrange multiplier on lower PG limit")
    mu_qmax: Optional[float] = Field(default=None, description="Lagrange multiplier on upper QG limit")
    mu_qmin: Optional[float] = Field(default=None, description="Lagrange multiplier on lower QG limit")


class BranchData(BaseModel):
    """Branch data model - corresponds to MATPOWER branch matrix columns"""
    # Input columns (1-13)
    f_bus: int = Field(..., description="From bus number")
    t_bus: int = Field(..., description="To bus number")
    br_r: float = Field(default=0.0, description="Resistance (p.u.)")
    br_x: float = Field(default=0.0, description="Reactance (p.u.)")
    br_b: float = Field(default=0.0, description="Total line charging susceptance (p.u.)")
    rate_a: float = Field(default=0.0, description="MVA rating A (long-term)")
    rate_b: float = Field(default=0.0, description="MVA rating B (short-term)")
    rate_c: float = Field(default=0.0, description="MVA rating C (emergency)")
    tap: float = Field(default=0.0, description="Transformer off-nominal turns ratio")
    shift: float = Field(default=0.0, description="Transformer phase shift angle (degrees)")
    br_status: int = Field(default=1, description="Branch status (1=in-service, 0=out-of-service)")
    angmin: float = Field(default=-360.0, description="Minimum angle difference (degrees)")
    angmax: float = Field(default=360.0, description="Maximum angle difference (degrees)")

    # Output columns (14-17) - populated after simulation
    pf: Optional[float] = Field(default=None, description="Real power flow at from bus (MW)")
    qf: Optional[float] = Field(default=None, description="Reactive power flow at from bus (MVAr)")
    pt: Optional[float] = Field(default=None, description="Real power flow at to bus (MW)")
    qt: Optional[float] = Field(default=None, description="Reactive power flow at to bus (MVAr)")

    # Additional fields
    mu_sf: Optional[float] = Field(default=None, description="Lagrange multiplier on flow limit at from bus")
    mu_st: Optional[float] = Field(default=None, description="Lagrange multiplier on flow limit at to bus")
    mu_angmin: Optional[float] = Field(default=None, description="Lagrange multiplier on angle difference lower limit")
    mu_angmax: Optional[float] = Field(default=None, description="Lagrange multiplier on angle difference upper limit")


class GeneratorCostData(BaseModel):
    """Generator cost data model - corresponds to MATPOWER gencost matrix"""
    model: int = Field(..., description="Cost model (1=piecewise linear, 2=polynomial)")
    startup: float = Field(default=0.0, description="Startup cost ($)")
    shutdown: float = Field(default=0.0, description="Shutdown cost ($)")
    ncost: int = Field(..., description="Number of cost coefficients")
    cost: List[float] = Field(..., description="Cost coefficients (for polynomial) or breakpoints (for piecewise)")


class CaseData(BaseModel):
    """Complete MATPOWER case data"""
    base_mva: float = Field(default=100.0, description="System MVA base")
    version: Optional[int] = Field(default=None, description="MATPOWER case version")
    bus: List[BusData] = Field(default_factory=list, description="Bus data")
    gen: List[GeneratorData] = Field(default_factory=list, description="Generator data")
    branch: List[BranchData] = Field(default_factory=list, description="Branch data")
    gencost: Optional[List[GeneratorCostData]] = Field(default=None, description="Generator cost data (for OPF)")
    area: Optional[List] = Field(default=None, description="Area data")
    gencoord: Optional[List] = Field(default=None, description="Generator coordinates")


class CaseListItem(BaseModel):
    """Summary item in case list response"""
    name: str = Field(..., description="Case name (e.g., 'case9', 'case14')")
    buses: int = Field(default=0, description="Number of buses")
    generators: int = Field(default=0, description="Number of generators")
    branches: int = Field(default=0, description="Number of branches")
    base_mva: float = Field(default=100.0, description="System MVA base")
    description: Optional[str] = Field(default=None, description="Case description from file comment")
    is_demo: bool = Field(default=False, description="Whether this case is in the web demo list")


class SimulationType(str):
    """Simulation type enumeration"""
    PF = "PF"       # AC Power Flow
    DCPF = "DCPF"   # DC Power Flow
    OPF = "OPF"     # Optimal Power Flow


class SimulationRequest(BaseModel):
    """Request to run a simulation"""
    case_name: str = Field(..., description="Name of the case to simulate")
    sim_type: Literal["PF", "DCPF", "OPF"] = Field(default="PF", description="Simulation type")
    algorithm: Optional[str] = Field(default="NR", description="Power flow algorithm (NR, FDXB, FDBX, GS, etc.)")
    modifications: Optional[Dict[str, Any]] = Field(default=None, description="Modifications to apply before simulation")


class DisturbanceType(str):
    """Disturbance type enumeration"""
    LINE_OUTAGE = "line_outage"
    GEN_OUTAGE = "gen_outage"
    LOAD_CHANGE = "load_change"
    VOLTAGE_CHANGE = "voltage_change"


class DisturbanceRequest(BaseModel):
    """Request to apply a disturbance"""
    case_name: str = Field(..., description="Name of the base case")
    disturbance_type: Literal["line_outage", "gen_outage", "load_change", "voltage_change", "voltage_adjust"] = Field(
        ..., description="Type of disturbance"
    )
    target_id: Union[Dict[str, Any], int] = Field(..., description="Target identifier (int index or dict with f_bus/t_bus)")
    new_value: Optional[float] = Field(default=None, description="New value for parameter change")


class SystemSummary(BaseModel):
    """System summary statistics"""
    total_generation: float = Field(..., description="Total real power generation (MW)")
    total_load: float = Field(..., description="Total real power load (MW)")
    total_losses: float = Field(..., description="Total real power losses (MW)")
    total_reactive_gen: float = Field(..., description="Total reactive power generation (MVAr)")
    total_reactive_load: float = Field(..., description="Total reactive power load (MVAr)")
    min_voltage: float = Field(..., description="Minimum voltage magnitude (p.u.)")
    max_voltage: float = Field(..., description="Maximum voltage magnitude (p.u.)")
    min_voltage_bus: int = Field(..., description="Bus with minimum voltage")
    max_voltage_bus: int = Field(..., description="Bus with maximum voltage")


class SimulationResult(BaseModel):
    """Complete simulation result"""
    success: bool = Field(..., description="Whether simulation succeeded")
    converged: Optional[bool] = Field(default=None, description="Whether the solver converged")
    iterations: Optional[int] = Field(default=None, description="Number of iterations")
    et: Optional[float] = Field(default=None, description="Elapsed time (seconds)")
    message: Optional[str] = Field(default=None, description="Status message or error description")

    # Result data
    bus_results: Optional[List[BusData]] = Field(default=None, description="Bus results")
    gen_results: Optional[List[GeneratorData]] = Field(default=None, description="Generator results")
    branch_results: Optional[List[BranchData]] = Field(default=None, description="Branch results")

    # Summary
    system_summary: Optional[SystemSummary] = Field(default=None, description="System summary statistics")

    # OPF specific
    total_cost: Optional[float] = Field(default=None, description="Total generation cost ($/hr) - OPF only")


class TaskStatus(BaseModel):
    """Simulation task status"""
    task_id: str = Field(..., description="Unique task identifier")
    status: Literal["pending", "running", "completed", "failed"] = Field(..., description="Task status")
    created_at: str = Field(..., description="ISO timestamp of task creation")
    completed_at: Optional[str] = Field(default=None, description="ISO timestamp of task completion")
    result: Optional[SimulationResult] = Field(default=None, description="Simulation result (if completed)")
    error: Optional[str] = Field(default=None, description="Error message (if failed)")


class SimulationProgress(BaseModel):
    """WebSocket simulation progress update"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Current status")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage")
    message: str = Field(default="", description="Status message")
    timestamp: str = Field(..., description="ISO timestamp")


class ModificationRequest(BaseModel):
    """Request to modify case data"""
    field: str = Field(..., description="Field to modify (bus, gen, branch)")
    index: int = Field(..., description="Index of the item to modify")
    column: str = Field(..., description="Column/field name to modify")
    value: float = Field(..., description="New value")


class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool = Field(..., description="Whether the request was successful")
    message: Optional[str] = Field(default=None, description="Response message")
    data: Optional[Any] = Field(default=None, description="Response data")
