// 母线数据
export interface BusData {
  bus_i: number
  bus_type: number  // 1=PQ, 2=PV, 3=平衡节点
  pd: number        // 有功负荷 (MW)
  qd: number        // 无功负荷 (MVar)
  gs: number        // 并联电导
  bs: number        // 并联电纳
  area: number      // 区域编号
  vm: number        // 电压幅值 (p.u.)
  va: number        // 电压相角 (度)
  base_kv: number   // 基准电压 (kV)
  zone: number      // 分区编号
  vmax: number      // 电压上限 (p.u.)
  vmin: number      // 电压下限 (p.u.)
  // 结果字段
  lam_p?: number
  lam_q?: number
  mu_vmax?: number
  mu_vmin?: number
}

// 发电机数据
export interface GenData {
  gen_bus: number     // 连接母线
  pg: number          // 有功出力 (MW)
  qg: number          // 无功出力 (MVar)
  qmax: number        // 无功上限 (MVar)
  qmin: number        // 无功下限 (MVar)
  vg: number          // 电压设定值 (p.u.)
  mbase: number       // 基准容量 (MVA)
  gen_status: number  // 状态 (1=投入, 0=退出)
  pmax: number        // 有功上限 (MW)
  pmin: number        // 有功下限 (MW)
  // 扩展字段
  pc1?: number
  pc2?: number
  qc1min?: number
  qc1max?: number
  qc2min?: number
  qc2max?: number
  ramp_agc?: number
  ramp_10?: number
  ramp_30?: number
}

// 线路数据
export interface BranchData {
  f_bus: number       // 起始母线
  t_bus: number       // 终止母线
  br_r: number        // 电阻 (p.u.)
  br_x: number        // 电抗 (p.u.)
  br_b: number        // 电纳 (p.u.)
  rate_a: number      // 额定容量A (MVA)
  rate_b: number      // 额定容量B (MVA)
  rate_c: number      // 额定容量C (MVA)
  tap: number         // 变比
  shift: number       // 相角偏移 (度)
  br_status: number   // 状态 (1=投入, 0=退出)
  angmin: number      // 最小相角差
  angmax: number      // 最大相角差
  // 结果字段
  pf?: number         // 起端有功潮流 (MW)
  qf?: number         // 起端无功潮流 (MVar)
  pt?: number         // 终端有功潮流 (MW)
  qt?: number         // 终端无功潮流 (MVar)
}

// 仿真结果
export interface SimulationResult {
  success: boolean
  converged?: boolean
  iterations: number
  et: number          // 执行时间 (秒)
  message?: string
  bus_results?: BusData[]
  gen_results?: GenData[]
  branch_results?: BranchData[]
  system_summary?: SystemSummary
  alarms?: AlarmInfo[]
  total_cost?: number
}

// 系统概要
export interface SystemSummary {
  total_generation: number // 总发电量 (MW)
  total_load: number        // 总负荷 (MW)
  total_losses: number      // 总损耗 (MW)
  total_reactive_gen: number
  total_reactive_load: number
  min_voltage: number       // 最小电压 (p.u.)
  max_voltage: number       // 最大电压 (p.u.)
  min_voltage_bus: number
  max_voltage_bus: number
  // 兼容旧格式
  total_gen?: number
  total_loss?: number
  max_voltage?: { bus: number; value: number }
  min_voltage?: { bus: number; value: number }
  total_cost?: number
  convergence?: string
}

// 告警信息
export interface AlarmInfo {
  id?: string
  type: 'voltage' | 'overload' | 'generation'
  level: 'warning' | 'critical'
  message: string
  element_id: number
  element_type: 'bus' | 'branch' | 'gen'
  value: number
  limit: number
  timestamp: string
}

// 测试用例信息
export interface CaseInfo {
  name: string
  display_name?: string
  buses: number
  generators: number
  branches: number
  base_mva: number
  description?: string
  is_demo?: boolean
}

// 仿真请求
export interface SimulationRequest {
  case_name: string
  sim_type?: 'PF' | 'DCPF' | 'OPF'
  algorithm?: string
  modifications?: any
}

// 扰动类型
export type DisturbanceType = 'line_outage' | 'gen_outage' | 'load_change' | 'voltage_change'

// 扰动请求
export interface Disturbance {
  type: DisturbanceType
  target_id: number | any
  new_value?: number
  description?: string
}

// 扰动请求（后端格式）
export interface DisturbanceRequest {
  case_name: string
  disturbance_type: DisturbanceType
  target_id: any
  new_value?: number
}

// WebSocket 消息类型
export interface WSMessage {
  type: string
  task_id?: string
  status?: string
  progress?: number
  message?: string
  timestamp: string
  data?: any
}
