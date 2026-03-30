import axios from 'axios'
import type { SimulationRequest, SimulationResult, CaseInfo, Disturbance, DisturbanceRequest } from './types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 120000, // 2 minutes for simulations
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    console.error('[API] Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response:`, response.data)
    return response.data
  },
  (error) => {
    console.error('[API] Response error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default api

// API 接口函数
export const apiSimulation = {
  // 获取可用测试用例列表
  getCases: (): Promise<CaseInfo[]> => api.get('/api/cases'),

  // 获取指定用例的详细数据
  getCaseData: (name: string): Promise<any> => api.get(`/api/cases/${name}`),

  // 修改用例参数
  updateCaseParams: (name: string, params: {
    bus_modifications?: any[]
    gen_modifications?: any[]
    branch_modifications?: any[]
  }): Promise<any> => api.put(`/api/cases/${name}/params`, params),

  // 运行 AC 潮流
  runPowerFlow: (caseName: string, algorithm: string = 'NR', modifications?: any): Promise<SimulationResult> =>
    api.post('/api/simulation/pf', {
      case_name: caseName,
      sim_type: 'PF',
      algorithm,
      modifications
    }),

  // 运行 DC 潮流
  runDCPowerFlow: (caseName: string, modifications?: any): Promise<SimulationResult> =>
    api.post('/api/simulation/pf', {
      case_name: caseName,
      sim_type: 'DCPF',
      algorithm: 'NR',
      modifications
    }),

  // 运行最优潮流
  runOPF: (caseName: string, modifications?: any): Promise<SimulationResult> =>
    api.post('/api/simulation/opf', {
      case_name: caseName,
      sim_type: 'OPF',
      modifications
    }),

  // 运行带修正的OPF（扰动后）
  runOPFWithCorrection: (caseName: string, disturbance: DisturbanceRequest): Promise<SimulationResult> =>
    api.post('/api/simulation/opf-with-correction', {
      case_name: caseName,
      disturbance
    }),

  // 应用扰动
  applyDisturbance: (caseName: string, disturbance: DisturbanceRequest): Promise<SimulationResult> =>
    api.post('/api/simulation/disturbance', {
      case_name: caseName,
      disturbance
    }),

  // 获取仿真历史
  getHistory: (limit: number = 50, caseName?: string): Promise<any[]> =>
    api.get('/api/simulation/history', {
      params: { limit, case_name: caseName }
    }),

  // 清空历史
  clearHistory: (): Promise<any> => api.delete('/api/simulation/history'),

  // N-1 分析
  runN1Analysis: (caseName: string, contingencyType: string = 'branch'): Promise<any> =>
    api.post('/api/disturbance/n-1/contingency', null, {
      params: { case_name: caseName, contingency_type: contingencyType }
    })
}
