import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { SimulationResult, BusData, GenData, BranchData, AlarmInfo, SystemSummary } from '../api/types'
import { apiSimulation } from '../api/index'
import { getSimulationWebSocket, type WSProgressMessage } from '../api/websocket'
import api from '../api/index'

export const useSimulationStore = defineStore('simulation', () => {
  // 状态
  const currentCase = ref('case14')
  const caseData = ref<{
    base_mva: number
    buses: BusData[]
    generators: GenData[]
    branches: BranchData[]
  }>({ base_mva: 100, buses: [], generators: [], branches: [] })
  const simResult = ref<SimulationResult | null>(null)
  const simMode = ref<'PF' | 'DCPF' | 'OPF'>('PF')
  const isRunning = ref(false)
  const simulationProgress = ref(0)
  const simulationMessage = ref('')
  const simulationHistory = ref<SimulationResult[]>([])
  const alarms = ref<AlarmInfo[]>([])

  // WebSocket
  const wsConnected = ref(false)
  let ws: ReturnType<typeof getSimulationWebSocket> | null = null

  // 计算属性
  const hasResult = computed(() => simResult.value !== null)
  const systemSummary = computed((): SystemSummary | null => {
    if (!simResult.value?.system_summary) return null
    const summary = simResult.value.system_summary
    // Convert backend format to frontend format if needed
    if ('total_generation' in summary) {
      return summary as SystemSummary
    }
    // Legacy format conversion
    return {
      total_generation: summary.total_gen || 0,
      total_load: summary.total_load || 0,
      total_losses: summary.total_loss || 0,
      total_reactive_gen: 0,
      total_reactive_load: 0,
      min_voltage: summary.min_voltage?.value || 0,
      max_voltage: summary.max_voltage?.value || 0,
      min_voltage_bus: summary.min_voltage?.bus || 0,
      max_voltage_bus: summary.max_voltage?.bus || 0
    }
  })
  const hasAlarms = computed(() => alarms.value.length > 0)
  const criticalAlarms = computed(() => alarms.value.filter(a => a.level === 'critical'))
  const warningAlarms = computed(() => alarms.value.filter(a => a.level === 'warning'))

  // 方法
  async function loadCase(caseName: string) {
    currentCase.value = caseName
    try {
      const data = await apiSimulation.getCaseData(caseName)
      caseData.value = {
        base_mva: data.base_mva || 100,
        buses: data.bus || [],
        generators: data.gen || [],
        branches: data.branch || []
      }
      simResult.value = null
      alarms.value = []
      console.log('[Store] Case loaded:', caseName, 'with', caseData.value.buses.length, 'buses')
    } catch (error) {
      console.error('[Store] Failed to load case:', error)
      throw error
    }
  }

  async function runSimulation(mode?: 'PF' | 'DCPF' | 'OPF', modifications?: any) {
    if (mode) simMode.value = mode
    isRunning.value = true
    simulationProgress.value = 0
    simulationMessage.value = 'Starting simulation...'

    try {
      let result: SimulationResult

      if (mode === 'OPF') {
        result = await apiSimulation.runOPF(currentCase.value, modifications)
      } else if (mode === 'DCPF') {
        result = await apiSimulation.runDCPowerFlow(currentCase.value, modifications)
      } else {
        result = await apiSimulation.runPowerFlow(currentCase.value, 'NR', modifications)
      }

      simResult.value = result
      simulationProgress.value = 100
      simulationMessage.value = result.message || 'Simulation completed'

      // Always generate alarms from whatever data is available
      alarms.value = generateAlarms(result)

      simulationHistory.value.push(result)
      console.log('[Store] Simulation completed:', result.success, 'iterations:', result.iterations)
    } catch (error: any) {
      console.error('[Store] Simulation failed:', error)
      simulationMessage.value = error.response?.data?.detail || error.message || 'Simulation failed'
      throw error
    } finally {
      isRunning.value = false
    }
  }

  async function runSimulationWithWebSocket(mode?: 'PF' | 'DCPF' | 'OPF', modifications?: any) {
    if (!ws) {
      ws = getSimulationWebSocket('frontend')
      setupWebSocketHandlers()
    }

    if (!ws.isConnected()) {
      try {
        await ws.connect()
        wsConnected.value = true
      } catch (e) {
        console.warn('[Store] WS connection failed, falling back to HTTP')
        return runSimulation(mode, modifications)
      }
    }

    // Use the async run endpoint that returns task_id
    if (mode) simMode.value = mode
    isRunning.value = true
    simulationProgress.value = 0
    simulationMessage.value = 'Starting simulation...'

    try {
      const simModeValue = mode || simMode.value
      const modeMap: Record<string, 'PF' | 'DCPF' | 'OPF'> = {
        'ac': 'PF',
        'dc': 'DCPF',
        'opf': 'OPF'
      }

      const response = await api({
        url: '/api/simulation/run',
        method: 'POST',
        data: {
          case_name: currentCase.value,
          sim_type: modeMap[simModeValue] || 'PF',
          algorithm: 'NR',
          modifications
        }
      })

      // Subscribe to task updates
      if (ws.isConnected() && response.task_id) {
        ws.subscribe(response.task_id)
      }

      return response
    } catch (error: any) {
      console.error('[Store] Failed to start simulation:', error)
      simulationMessage.value = error.response?.data?.detail || error.message || 'Failed to start simulation'
      isRunning.value = false
      throw error
    }
  }

  function setupWebSocketHandlers() {
    if (!ws) return

    ws.on('progress', (message: WSProgressMessage) => {
      simulationProgress.value = message.progress || 0
      simulationMessage.value = message.message || ''
      if (message.status === 'completed' || message.status === 'failed') {
        isRunning.value = false
      }
    })

    ws.on('connected', () => {
      wsConnected.value = true
    })

    ws.on('subscribed', (message: any) => {
      console.log('[Store] Subscribed to task:', message.task_id)
    })

    ws.on('pong', () => {
      // Heartbeat response
    })

    ws.on('*', (message: any) => {
      console.log('[Store] WS message:', message)
    })
  }

  async function applyDisturbance(disturbance: {
    type: string
    target_id: number | any
    new_value?: number
  }) {
    isRunning.value = true
    simulationProgress.value = 0
    simulationMessage.value = 'Applying disturbance...'

    try {
      const result = await apiSimulation.applyDisturbance(
        currentCase.value,
        {
          disturbance_type: disturbance.type as any,
          target_id: disturbance.target_id,
          new_value: disturbance.new_value
        }
      )

      if (!result || typeof result !== 'object') {
        console.warn('[Store] Disturbance returned incomplete result')
        simulationMessage.value = 'Disturbance applied but result was incomplete'
        return
      }

      simResult.value = result
      simulationProgress.value = 100

      // Always generate alarms from whatever data is available
      alarms.value = generateAlarms(result)

      simulationHistory.value.push(result)
      console.log('[Store] Disturbance applied:', result.success)
    } catch (error: any) {
      console.error('[Store] Failed to apply disturbance:', error)
      simulationMessage.value = error.response?.data?.detail || error.message || 'Failed to apply disturbance'
      throw error
    } finally {
      isRunning.value = false
    }
  }

  async function runOPF() {
    return runSimulation('OPF')
  }

  async function runOPFWithCorrection(disturbance: any) {
    isRunning.value = true
    simulationProgress.value = 0
    simulationMessage.value = 'Running OPF with correction...'

    try {
      const result = await apiSimulation.runOPFWithCorrection(
        currentCase.value,
        disturbance
      )

      simResult.value = result
      simulationProgress.value = 100

      // Always generate alarms from whatever data is available
      alarms.value = generateAlarms(result)

      simulationHistory.value.push(result)
      console.log('[Store] OPF correction completed:', result.success)
    } catch (error: any) {
      console.error('[Store] OPF correction failed:', error)
      simulationMessage.value = error.response?.data?.detail || error.message || 'OPF correction failed'
      throw error
    } finally {
      isRunning.value = false
    }
  }

  function updateBusParam(busId: number, field: keyof BusData, value: number) {
    const bus = caseData.value.buses.find(b => b.bus_i === busId)
    if (bus) {
      ;(bus as any)[field] = value
    }
  }

  function updateGenParam(genBus: number, field: keyof GenData, value: number) {
    const gen = caseData.value.generators.find(g => g.gen_bus === genBus)
    if (gen) {
      ;(gen as any)[field] = value
    }
  }

  function updateBranchParam(index: number, field: keyof BranchData, value: number) {
    if (index >= 0 && index < caseData.value.branches.length) {
      ;(caseData.value.branches[index] as any)[field] = value
    }
  }

  function clearAlarms() {
    alarms.value = []
  }

  function reset() {
    simResult.value = null
    alarms.value = []
    simulationProgress.value = 0
    simulationMessage.value = ''
  }

  function generateAlarms(result: SimulationResult): AlarmInfo[] {
    const alarms: AlarmInfo[] = []
    const summary = result.system_summary

    // Summary-based voltage violation detection (when available)
    if (summary) {
      if (typeof summary.min_voltage === 'number' && summary.min_voltage < 0.95) {
        alarms.push({
          id: `vmin_summary_${Date.now()}`,
          type: 'voltage',
          level: summary.min_voltage < 0.9 ? 'critical' : 'warning',
          message: `Undervoltage at bus ${summary.min_voltage_bus || 'N/A'}: ${summary.min_voltage.toFixed(3)} p.u.`,
          element_id: summary.min_voltage_bus || 0,
          element_type: 'bus',
          value: summary.min_voltage,
          limit: 0.95,
          timestamp: new Date().toISOString()
        })
      }

      if (typeof summary.max_voltage === 'number' && summary.max_voltage > 1.05) {
        alarms.push({
          id: `vmax_summary_${Date.now()}`,
          type: 'voltage',
          level: summary.max_voltage > 1.1 ? 'critical' : 'warning',
          message: `Overvoltage at bus ${summary.max_voltage_bus || 'N/A'}: ${summary.max_voltage.toFixed(3)} p.u.`,
          element_id: summary.max_voltage_bus || 0,
          element_type: 'bus',
          value: summary.max_voltage,
          limit: 1.05,
          timestamp: new Date().toISOString()
        })
      }
    }

    // Per-bus voltage violation checks (always runs when bus_results exist)
    if (result.bus_results && result.bus_results.length > 0) {
      const summaryBusIds = new Set(
        alarms.filter(a => a.type === 'voltage').map(a => a.element_id)
      )

      result.bus_results.forEach((bus) => {
        // Skip buses already flagged by summary
        if (summaryBusIds.has(bus.bus_i)) return

        const vm = bus.vm
        const vmin = bus.vmin || 0.95
        const vmax = bus.vmax || 1.05

        if (vm < vmin) {
          alarms.push({
            id: `vmin_bus_${bus.bus_i}_${Date.now()}`,
            type: 'voltage',
            level: vm < vmin - 0.05 ? 'critical' : 'warning',
            message: `Undervoltage at bus ${bus.bus_i}: ${vm.toFixed(3)} p.u. (limit: ${vmin})`,
            element_id: bus.bus_i,
            element_type: 'bus',
            value: vm,
            limit: vmin,
            timestamp: new Date().toISOString()
          })
        } else if (vm > vmax) {
          alarms.push({
            id: `vmax_bus_${bus.bus_i}_${Date.now()}`,
            type: 'voltage',
            level: vm > vmax + 0.05 ? 'critical' : 'warning',
            message: `Overvoltage at bus ${bus.bus_i}: ${vm.toFixed(3)} p.u. (limit: ${vmax})`,
            element_id: bus.bus_i,
            element_type: 'bus',
            value: vm,
            limit: vmax,
            timestamp: new Date().toISOString()
          })
        }
      })
    }

    // Per-branch overload checks (always runs when branch_results exist)
    if (result.branch_results && result.branch_results.length > 0) {
      result.branch_results.forEach((branch, idx) => {
        if (branch.br_status !== 1) return
        if (branch.rate_a <= 0) return
        if (branch.pf === undefined && branch.pt === undefined) return

        // Use the higher of from/to apparent power
        const flowFrom = (branch.pf !== undefined && branch.qf !== undefined)
          ? Math.sqrt(branch.pf ** 2 + branch.qf ** 2)
          : 0
        const flowTo = (branch.pt !== undefined && branch.qt !== undefined)
          ? Math.sqrt(branch.pt ** 2 + branch.qt ** 2)
          : 0
        const flow = Math.max(flowFrom, flowTo)

        if (flow > branch.rate_a) {
          alarms.push({
            id: `ovl_${idx}_${Date.now()}`,
            type: 'overload',
            level: flow > branch.rate_a * 1.2 ? 'critical' : 'warning',
            message: `Line ${branch.f_bus}→${branch.t_bus} overload: ${flow.toFixed(1)} MVA > ${branch.rate_a} MVA`,
            element_id: idx,
            element_type: 'branch',
            value: flow,
            limit: branch.rate_a,
            timestamp: new Date().toISOString()
          })
        }
      })
    }

    return alarms
  }

  return {
    // 状态
    currentCase,
    caseData,
    simResult,
    simMode,
    isRunning,
    simulationProgress,
    simulationMessage,
    simulationHistory,
    alarms,
    wsConnected,
    // 计算属性
    hasResult,
    systemSummary,
    hasAlarms,
    criticalAlarms,
    warningAlarms,
    // 方法
    loadCase,
    runSimulation,
    runSimulationWithWebSocket,
    applyDisturbance,
    runOPF,
    runOPFWithCorrection,
    updateBusParam,
    updateGenParam,
    updateBranchParam,
    clearAlarms,
    reset,
    generateAlarms
  }
})
