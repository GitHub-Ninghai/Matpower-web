import type { BusData, GenData, BranchData, SimulationResult, CaseInfo, SystemSummary, AlarmInfo } from '../api/types'

// 可用测试用例列表
export const mockCases: CaseInfo[] = [
  {
    name: 'ieee14',
    display_name: 'IEEE 14 母线系统',
    buses: 14,
    generators: 5,
    branches: 20,
    description: 'IEEE 14节点标准测试系统，常用于电力系统分析'
  },
  {
    name: 'ieee30',
    display_name: 'IEEE 30 母线系统',
    buses: 30,
    generators: 6,
    branches: 41,
    description: 'IEEE 30节点标准测试系统'
  },
  {
    name: 'ieee57',
    display_name: 'IEEE 57 母线系统',
    buses: 57,
    generators: 7,
    branches: 80,
    description: 'IEEE 57节点标准测试系统'
  },
  {
    name: 'ieee118',
    display_name: 'IEEE 118 母线系统',
    buses: 118,
    generators: 54,
    branches: 186,
    description: 'IEEE 118节点标准测试系统'
  }
]

// IEEE 14 母线系统数据
export const ieee14BusData: BusData[] = [
  { bus_i: 1, bus_type: 3, pd: 0, qd: 0, gs: 0, bs: 0, area: 1, vm: 1.06, va: 0, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 2, bus_type: 2, pd: 21.7, qd: 12.7, gs: 0, bs: 0, area: 1, vm: 1.045, va: -4.98, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 3, bus_type: 2, pd: 94.2, qd: 19.0, gs: 0, bs: 0, area: 1, vm: 1.01, va: -12.72, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 4, bus_type: 1, pd: 47.8, qd: -3.9, gs: 0, bs: 0, area: 1, vm: 1.019, va: -10.33, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 5, bus_type: 1, pd: 7.6, qd: 1.6, gs: 0, bs: 0, area: 1, vm: 1.02, va: -8.78, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 6, bus_type: 2, pd: 11.2, qd: 7.5, gs: 0, bs: 0, area: 1, vm: 1.07, va: -14.22, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 7, bus_type: 1, pd: 0, qd: 0, gs: 0, bs: 0, area: 1, vm: 1.062, va: -13.37, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 8, bus_type: 2, pd: 0, qd: 0, gs: 0, bs: 0, area: 1, vm: 1.09, va: -13.36, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 9, bus_type: 1, pd: 29.5, qd: 16.6, gs: 0, bs: 0, area: 1, vm: 1.056, va: -14.94, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 10, bus_type: 1, pd: 9, qd: 5.8, gs: 0, bs: 0, area: 1, vm: 1.051, va: -15.1, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 11, bus_type: 1, pd: 3.5, qd: 1.8, gs: 0, bs: 0, area: 1, vm: 1.057, va: -14.79, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 12, bus_type: 1, pd: 6.1, qd: 1.6, gs: 0, bs: 0, area: 1, vm: 1.055, va: -15.07, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 13, bus_type: 1, pd: 13.5, qd: 5.8, gs: 0, bs: 0, area: 1, vm: 1.05, va: -15.16, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 },
  { bus_i: 14, bus_type: 1, pd: 14.9, qd: 5.0, gs: 0, bs: 0, area: 1, vm: 1.036, va: -16.04, base_kv: 132, zone: 1, vmax: 1.05, vmin: 0.95 }
]

export const ieee14GenData: GenData[] = [
  { gen_bus: 1, pg: 232.4, qg: -16.9, qmax: 100, qmin: -20, vg: 1.06, mbase: 100, gen_status: 1, pmax: 615, pmin: 0 },
  { gen_bus: 2, pg: 40, qg: 44.4, qmax: 50, qmin: -40, vg: 1.045, mbase: 100, gen_status: 1, pmax: 100, pmin: 0 },
  { gen_bus: 3, pg: 0, qg: 24.2, qmax: 40, qmin: 0, vg: 1.01, mbase: 100, gen_status: 1, pmax: 100, pmin: 0 },
  { gen_bus: 6, pg: 0, qg: 12.7, qmax: 24, qmin: -6, vg: 1.07, mbase: 100, gen_status: 1, pmax: 100, pmin: 0 },
  { gen_bus: 8, pg: 0, qg: 17.3, qmax: 24, qmin: -6, vg: 1.09, mbase: 100, gen_status: 1, pmax: 100, pmin: 0 }
]

export const ieee14BranchData: BranchData[] = [
  { f_bus: 1, t_bus: 2, br_r: 0.01938, br_x: 0.05917, br_b: 0.0528, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 1, t_bus: 5, br_r: 0.05403, br_x: 0.22304, br_b: 0.0492, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 2, t_bus: 3, br_r: 0.04699, br_x: 0.19797, br_b: 0.0438, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 2, t_bus: 4, br_r: 0.05811, br_x: 0.17632, br_b: 0.0344, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 2, t_bus: 5, br_r: 0.05695, br_x: 0.17388, br_b: 0.034, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 3, t_bus: 4, br_r: 0.06701, br_x: 0.17103, br_b: 0.0128, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 4, t_bus: 5, br_r: 0.01335, br_x: 0.04211, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 4, t_bus: 7, br_r: 0, br_x: 0.20912, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 0.978, shift: 0, br_status: 1 },
  { f_bus: 4, t_bus: 9, br_r: 0, br_x: 0.55618, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 0.969, shift: 0, br_status: 1 },
  { f_bus: 5, t_bus: 6, br_r: 0, br_x: 0.25202, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 0.932, shift: 0, br_status: 1 },
  { f_bus: 6, t_bus: 11, br_r: 0.09498, br_x: 0.1989, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 6, t_bus: 12, br_r: 0.12291, br_x: 0.25581, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 6, t_bus: 13, br_r: 0.06615, br_x: 0.13027, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 7, t_bus: 8, br_r: 0, br_x: 0.17615, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 7, t_bus: 9, br_r: 0, br_x: 0.11001, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 9, t_bus: 10, br_r: 0.03181, br_x: 0.0845, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 9, t_bus: 14, br_r: 0.05116, br_x: 0.15504, br_b: 0.0236, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 10, t_bus: 11, br_r: 0.07534, br_x: 0.12392, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 12, t_bus: 13, br_r: 0.0937, br_x: 0.15585, br_b: 0, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 },
  { f_bus: 13, t_bus: 14, br_r: 0.05911, br_x: 0.09578, br_b: 0.0188, rate_a: 999, rate_b: 999, rate_c: 999, tap: 1, shift: 0, br_status: 1 }
]

// 仿真结果（带潮流数据）
export const mockSimulationResult: SimulationResult = {
  success: true,
  iterations: 4,
  et: 0.023,
  bus_results: ieee14BusData,
  gen_results: ieee14GenData,
  branch_results: ieee14BranchData.map((b, i) => ({
    ...b,
    pf: Math.round((Math.random() * 100 - 20) * 100) / 100,
    qf: Math.round((Math.random() * 50 - 10) * 100) / 100,
    pt: Math.round((Math.random() * 100 - 20) * 100) / 100,
    qt: Math.round((Math.random() * 50 - 10) * 100) / 100
  })),
  system_summary: {
    total_gen: 272.44,
    total_load: 259.0,
    total_loss: 13.44,
    max_voltage: { bus: 8, value: 1.09 },
    min_voltage: { bus: 14, value: 1.036 },
    total_cost: 8264.57,
    convergence: '正常收敛'
  },
  alarms: []
}

// 带告警的仿真结果
export const mockSimulationResultWithAlarms: SimulationResult = {
  ...mockSimulationResult,
  alarms: [
    {
      id: '1',
      type: 'voltage',
      level: 'warning',
      message: '母线 14 电压偏低',
      element_id: 14,
      element_type: 'bus',
      value: 0.92,
      limit: 0.95,
      timestamp: new Date().toISOString()
    },
    {
      id: '2',
      type: 'overload',
      level: 'critical',
      message: '线路 1-2 过载',
      element_id: 1,
      element_type: 'branch',
      value: 180.5,
      limit: 150,
      timestamp: new Date().toISOString()
    }
  ]
}

// 获取测试用例数据
export function getMockCaseData(caseName: string): {
  buses: BusData[]
  generators: GenData[]
  branches: BranchData[]
} {
  switch (caseName) {
    case 'ieee14':
    default:
      return {
        buses: ieee14BusData,
        generators: ieee14GenData,
        branches: ieee14BranchData
      }
  }
}

// 模拟仿真运行
export function runMockSimulation(
  caseName: string,
  mode: string,
  withAlarms: boolean = false
): Promise<SimulationResult> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(withAlarms ? mockSimulationResultWithAlarms : mockSimulationResult)
    }, 800)
  })
}

// 模拟扰动应用
export function applyMockDisturbance(
  disturbance: { type: string; target_id: number; new_value?: number }
): Promise<SimulationResult> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const result = { ...mockSimulationResultWithAlarms }
      // 根据扰动类型生成不同的告警
      if (disturbance.type === 'voltage_change') {
        result.alarms = [
          {
            id: '1',
            type: 'voltage',
            level: 'warning',
            message: `母线 ${disturbance.target_id} 电压越限`,
            element_id: disturbance.target_id,
            element_type: 'bus',
            value: disturbance.new_value || 0.9,
            limit: 0.95,
            timestamp: new Date().toISOString()
          }
        ]
      }
      resolve(result)
    }, 600)
  })
}
