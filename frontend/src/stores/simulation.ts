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

  // Accumulated modifications that persist across simulations
  const accumulatedModifications = ref<Record<string, Array<{ index: number; field: string; value: number }>>>({})

  // WebSocket
  const wsConnected = ref(false)
  let ws: ReturnType<typeof getSimulationWebSocket> | null = null

  // 计算属性
  const hasResult = computed(() => simResult.value !== null)
  const systemSummary = computed((): SystemSummary | null => {
    if (!simResult.value?.system_summary) return null
    const summary = simResult.value.system_summary
    // The backend already returns the correct SystemSummary format
    return summary as SystemSummary
  })
  const hasAlarms = computed(() => alarms.value.length > 0)
  const criticalAlarms = computed(() => alarms.value.filter(a => a.level === 'critical'))
  const warningAlarms = computed(() => alarms.value.filter(a => a.level === 'warning'))

  // Merge new modifications into the accumulated set
  function addModifications(modifications: Record<string, Array<{ index: number; field: string; value: number }>>) {
    for (const [type, modList] of Object.entries(modifications)) {
      if (!accumulatedModifications.value[type]) {
        accumulatedModifications.value[type] = []
      }
      for (const mod of modList) {
        // Replace any existing mod for same index+field, or append
        const existingIdx = accumulatedModifications.value[type].findIndex(
          m => m.index === mod.index && m.field === mod.field
        )
        if (existingIdx >= 0) {
          accumulatedModifications.value[type][existingIdx].value = mod.value
        } else {
          accumulatedModifications.value[type].push({ ...mod })
        }
      }
    }
  }

  // Get the merged modifications = accumulated + any extra
  function getMergedModifications(extra?: any): any {
    const merged: Record<string, Array<{ index: number; field: string; value: number }>> = {}
    // Copy accumulated
    for (const [type, modList] of Object.entries(accumulatedModifications.value)) {
      merged[type] = modList.map(m => ({ ...m }))
    }
    // Merge extra
    if (extra) {
      for (const [type, modList] of Object.entries(extra)) {
        if (!merged[type]) merged[type] = []
        for (const mod of modList as Array<{ index: number; field: string; value: number }>) {
          const existingIdx = merged[type].findIndex(
            (m: { index: number; field: string }) => m.index === mod.index && m.field === mod.field
          )
          if (existingIdx >= 0) {
            merged[type][existingIdx].value = mod.value
          } else {
            merged[type].push({ ...mod })
          }
        }
      }
    }
    return Object.keys(merged).length > 0 ? merged : undefined
  }

  // 方法
  async function loadCase(caseName: string) {
    currentCase.value = caseName
    accumulatedModifications.value = {} // Reset modifications on case change
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

    // Merge new modifications into accumulated set
    if (modifications) {
      addModifications(modifications)
    }

    // Always use accumulated modifications so all previous changes are preserved
    const finalModifications = getMergedModifications()

    try {
      let result: SimulationResult

      if (mode === 'OPF') {
        result = await apiSimulation.runOPF(currentCase.value, finalModifications)
      } else if (mode === 'DCPF') {
        result = await apiSimulation.runDCPowerFlow(currentCase.value, finalModifications)
      } else {
        result = await apiSimulation.runPowerFlow(currentCase.value, 'NR', finalModifications)
      }

      simResult.value = result
      simulationProgress.value = 100
      simulationMessage.value = result.message || 'Simulation completed'

      // Sync local caseData with simulation results
      syncCaseDataFromResult(result)

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

    // Build local modifications from the disturbance to accumulate
    if (disturbance.type === 'line_outage') {
      const branchIdx = typeof disturbance.target_id === 'number' ? disturbance.target_id : disturbance.target_id?.index
      if (branchIdx !== undefined) {
        addModifications({ branch: [{ index: branchIdx, field: 'br_status', value: 0 }] })
        updateBranchParam(branchIdx, 'br_status', 0)
      }
    } else if (disturbance.type === 'gen_outage') {
      const genBus = typeof disturbance.target_id === 'number' ? disturbance.target_id : disturbance.target_id?.gen_bus
      if (genBus !== undefined) {
        const genIdx = caseData.value.generators.findIndex(g => g.gen_bus === genBus)
        if (genIdx >= 0) {
          addModifications({
            gen: [
              { index: genIdx, field: 'gen_status', value: 0 },
              { index: genIdx, field: 'pg', value: 0 },
              { index: genIdx, field: 'qg', value: 0 }
            ]
          })
        }
      }
    } else if (disturbance.type === 'load_change') {
      const busId = typeof disturbance.target_id === 'number' ? disturbance.target_id : disturbance.target_id?.bus_i
      if (busId !== undefined) {
        const busIdx = caseData.value.buses.findIndex(b => b.bus_i === busId)
        if (busIdx >= 0) {
          const currentPd = caseData.value.buses[busIdx].pd
          const newPd = currentPd * (1 + (disturbance.new_value || 0) / 100)
          addModifications({ bus: [{ index: busIdx, field: 'pd', value: newPd }] })
          updateBusParam(busId, 'pd', newPd)
        }
      }
    } else if (disturbance.type === 'voltage_change') {
      const busId = typeof disturbance.target_id === 'number' ? disturbance.target_id : disturbance.target_id?.bus_i
      if (busId !== undefined) {
        const genIdx = caseData.value.generators.findIndex(g => g.gen_bus === busId)
        if (genIdx >= 0) {
          addModifications({ gen: [{ index: genIdx, field: 'vg', value: disturbance.new_value || 1.0 }] })
        }
      }
    }

    // Use accumulated modifications for the simulation
    const finalModifications = getMergedModifications()

    try {
      const result = await apiSimulation.runPowerFlow(
        currentCase.value,
        'NR',
        finalModifications
      )

      if (!result || typeof result !== 'object') {
        console.warn('[Store] Disturbance returned incomplete result')
        simulationMessage.value = 'Disturbance applied but result was incomplete'
        return
      }

      simResult.value = result
      simulationProgress.value = 100
      simulationMessage.value = result.message || 'Disturbance applied'

      // Sync local caseData with simulation results
      syncCaseDataFromResult(result)

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

  // Sync local caseData with simulation results so tables show latest data
  function syncCaseDataFromResult(result: SimulationResult) {
    if (result.bus_results) {
      for (const busResult of result.bus_results) {
        const bus = caseData.value.buses.find(b => b.bus_i === busResult.bus_i)
        if (bus) {
          bus.vm = busResult.vm
          bus.va = busResult.va
        }
      }
    }
    if (result.gen_results) {
      for (const genResult of result.gen_results) {
        const gen = caseData.value.generators.find(g => g.gen_bus === genResult.gen_bus)
        if (gen) {
          gen.pg = genResult.pg
          gen.qg = genResult.qg
          gen.gen_status = genResult.gen_status
        }
      }
    }
    if (result.branch_results) {
      for (let i = 0; i < result.branch_results.length && i < caseData.value.branches.length; i++) {
        const brResult = result.branch_results[i]
        const br = caseData.value.branches[i]
        br.br_status = brResult.br_status
        if (brResult.pf !== undefined) (br as any).pf = brResult.pf
        if (brResult.qf !== undefined) (br as any).qf = brResult.qf
        if (brResult.pt !== undefined) (br as any).pt = brResult.pt
        if (brResult.qt !== undefined) (br as any).qt = brResult.qt
      }
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
    accumulatedModifications.value = {}
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
    generateAlarms,
    addModifications,
    syncCaseDataFromResult
  }
})
