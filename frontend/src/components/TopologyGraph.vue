<template>
  <div class="topology-graph">
    <div class="graph-header">
      <div class="card-title">网络拓扑图</div>
      <div class="legend">
        <span class="legend-item">
          <span class="legend-dot" style="background: #52c41a"></span>
          正常
        </span>
        <span class="legend-item">
          <span class="legend-dot" style="background: #faad14"></span>
          警告
        </span>
        <span class="legend-item">
          <span class="legend-dot" style="background: #ff4d4f"></span>
          越限
        </span>
        <span class="legend-item">
          <span class="legend-icon">&#9650;</span>
          发电机
        </span>
      </div>
    </div>
    <div ref="containerRef" class="graph-container"></div>
    <transition name="info-slide">
      <div v-if="selectedElement" class="node-info">
        <div class="info-header">
          <span class="info-header-title">{{ elementType === 'bus' ? '母线信息' : '线路信息' }}</span>
          <a-button type="text" size="small" class="info-close-btn" @click="closeInfo">
            <CloseOutlined />
          </a-button>
        </div>
        <div class="info-content">
          <template v-if="elementType === 'bus'">
            <div class="info-row">
              <span class="info-label">编号</span>
              <span class="info-value value-display">{{ selectedElement.id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">类型</span>
              <span class="info-value">{{ getBusType(selectedElement.bus_type) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">电压</span>
              <span :class="['info-value', 'value-display', getValueClass(selectedElement.vm)]">
                {{ formatNumber(selectedElement.vm, 4) }} p.u.
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">相角</span>
              <span class="info-value value-display">{{ formatNumber(selectedElement.va, 2) }}&deg;</span>
            </div>
            <div class="info-row">
              <span class="info-label">有功负荷</span>
              <span class="info-value value-display">{{ formatNumber(selectedElement.pd, 2) }} MW</span>
            </div>
            <div class="info-row">
              <span class="info-label">无功负荷</span>
              <span class="info-value value-display">{{ formatNumber(selectedElement.qd, 2) }} MVar</span>
            </div>
          </template>
          <template v-else>
            <div class="info-row">
              <span class="info-label">线路</span>
              <span class="info-value value-display">{{ selectedElement.source }} &rarr; {{ selectedElement.target }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">有功(始端)</span>
              <span class="info-value value-display">{{ formatNumber(selectedElement.pf, 2) }} MW</span>
            </div>
            <div class="info-row">
              <span class="info-label">无功(始端)</span>
              <span class="info-value value-display">{{ formatNumber(selectedElement.qf, 2) }} MVar</span>
            </div>
            <div class="info-row">
              <span class="info-label">有功(终端)</span>
              <span class="info-value value-display">{{ formatNumber(selectedElement.pt, 2) }} MW</span>
            </div>
            <div class="info-row">
              <span class="info-label">无功(终端)</span>
              <span class="info-value value-display">{{ formatNumber(selectedElement.qt, 2) }} MVar</span>
            </div>
            <div class="info-row">
              <span class="info-label">容量</span>
              <span class="info-value value-display">{{ selectedElement.rate_a }} MVA</span>
            </div>
            <div class="info-row">
              <span class="info-label">负载率</span>
              <span :class="['info-value', 'value-display', getLoadingClass(selectedElement)]">
                {{ getLoadingPercent(selectedElement) }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">状态</span>
              <span class="info-value">
                <a-tag :color="selectedElement.br_status === 1 ? 'success' : 'default'" size="small">
                  {{ selectedElement.br_status === 1 ? '投入' : '断开' }}
                </a-tag>
              </span>
            </div>
          </template>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import cytoscape, { type Core } from 'cytoscape'
import { CloseOutlined } from '@ant-design/icons-vue'
import { useSimulationStore } from '../stores/simulation'
// Types used via the simulation store

const simulationStore = useSimulationStore()
const containerRef = ref<HTMLElement>()
let cy: Core | null = null

const selectedElement = ref<any>(null)
const elementType = ref<'bus' | 'branch'>('bus')

// Store the selected bus/branch ID so info panel can track latest data
const selectedBusId = ref<number | null>(null)
const selectedEdgeId = ref<string | null>(null)

function getBusType(type: number): string {
  switch (type) {
    case 1:
      return 'PQ 节点'
    case 2:
      return 'PV 节点'
    case 3:
      return '平衡节点'
    default:
      return '未知'
  }
}

function getValueClass(vm?: number): string {
  if (!vm) return ''
  if (vm < 0.95 || vm > 1.05) return 'value-danger'
  if (vm < 0.97 || vm > 1.03) return 'value-warning'
  return 'value-normal'
}

function getLoadingClass(el: any): string {
  if (!el.pf || !el.rate_a) return ''
  const pct = Math.abs(el.pf) / el.rate_a
  if (pct > 0.9) return 'value-danger'
  if (pct > 0.75) return 'value-warning'
  return 'value-normal'
}

function getLoadingPercent(el: any): string {
  if (!el.pf || !el.rate_a) return '-'
  return ((Math.abs(el.pf) / el.rate_a) * 100).toFixed(1) + '%'
}

function formatNumber(val: number | undefined, decimals: number): string {
  if (val === undefined || val === null) return '-'
  return val.toFixed(decimals)
}

function getNodeColor(vm: number): string {
  if (vm < 0.95) return '#ff4d4f'
  if (vm > 1.05) return '#faad14'
  return '#52c41a'
}

function getNodeSize(load: number): number {
  return Math.max(20, Math.min(50, 20 + load / 5))
}

function getEdgeWidth(flow?: number): number {
  if (!flow) return 2
  return Math.max(1, Math.min(8, Math.abs(flow) / 20))
}

// Refresh the info panel data from the latest simResult
function refreshSelectedInfo() {
  if (!simulationStore.simResult) return

  if (elementType.value === 'bus' && selectedBusId.value !== null) {
    const busResult = simulationStore.simResult.bus_results?.find(
      b => b.bus_i === selectedBusId.value
    )
    if (busResult) {
      selectedElement.value = {
        id: selectedBusId.value.toString(),
        bus_type: busResult.bus_type,
        vm: busResult.vm,
        va: busResult.va,
        pd: busResult.pd,
        qd: busResult.qd,
        vmin: busResult.vmin,
        vmax: busResult.vmax
      }
    }
  } else if (elementType.value === 'branch' && selectedEdgeId.value !== null) {
    const parts = selectedEdgeId.value.split('-')
    const source = parseInt(parts[0])
    const target = parseInt(parts[1])
    const branchResult = simulationStore.simResult.branch_results?.find(
      b => b.f_bus === source && b.t_bus === target
    )
    if (branchResult) {
      selectedElement.value = {
        source,
        target,
        ...branchResult
      }
    }
  }
}

function initGraph() {
  if (!containerRef.value) return

  cy = cytoscape({
    container: containerRef.value,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)',
          'label': 'data(label)',
          'width': 'data(size)',
          'height': 'data(size)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'font-size': '12px',
          'color': '#c9d1d9',
          'text-margin-y': 4,
          'border-width': 2,
          'border-color': '#30363d',
          'transition-property': 'background-color, border-color, border-width',
          'transition-duration': 0.3
        }
      },
      {
        selector: 'node[hasGen="true"]',
        style: {
          'shape': 'triangle'
        }
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 4,
          'border-color': '#1890ff'
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 'data(width)',
          'line-color': 'data(color)',
          'target-arrow-color': 'data(color)',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 0.8,
          'transition-property': 'line-color, width',
          'transition-duration': 0.3
        }
      },
      {
        selector: 'edge:selected',
        style: {
          'line-color': '#1890ff',
          'target-arrow-color': '#1890ff',
          'width': 6
        }
      },
      {
        selector: '.disconnected-edge',
        style: {
          'line-style': 'dashed',
          'line-color': '#6e7681',
          'target-arrow-color': '#6e7681',
          'opacity': 0.4
        }
      }
    ],
    layout: {
      name: 'cose',
      animate: false,
      nodeRepulsion: 8000,
      idealEdgeLength: 80,
      edgeElasticity: 100,
      nestingFactor: 5,
      gravity: 1,
      numIter: 1000,
      initialTemp: 200,
      coolingFactor: 0.95,
      minTemp: 1.0
    },
    minZoom: 0.3,
    maxZoom: 3
  })

  cy.on('tap', 'node', (evt) => {
    const node = evt.target
    const busId = parseInt(node.id())
    selectedBusId.value = busId
    selectedEdgeId.value = null
    elementType.value = 'bus'
    refreshSelectedInfo()
  })

  cy.on('tap', 'edge', (evt) => {
    const edge = evt.target
    const sourceId = edge.source().id()
    const targetId = edge.target().id()
    selectedEdgeId.value = `${sourceId}-${targetId}`
    selectedBusId.value = null
    elementType.value = 'branch'
    refreshSelectedInfo()
  })

  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      closeInfo()
    }
  })
}

function updateGraph() {
  if (!cy || !simulationStore.simResult) return

  const { bus_results, branch_results, gen_results } = simulationStore.simResult

  if (!bus_results || !branch_results || !gen_results) return

  // 获取有发电机的母线集合
  const genBuses = new Set(gen_results.map(g => g.gen_bus.toString()))

  // Save current layout positions
  const positions: Record<string, { x: number; y: number }> = {}
  cy.nodes().forEach(node => {
    positions[node.id()] = { x: node.position().x, y: node.position().y }
  })

  // 创建节点
  const nodes = bus_results.map((bus) => {
    const color = getNodeColor(bus.vm)
    const size = getNodeSize(bus.pd)
    const hasGen = genBuses.has(bus.bus_i.toString())

    return {
      data: {
        id: bus.bus_i.toString(),
        label: `Bus ${bus.bus_i}`,
        color,
        size,
        hasGen: hasGen ? 'true' : 'false'
      },
      position: positions[bus.bus_i.toString()] // Preserve position if exists
    }
  })

  // 创建边 - include disconnected lines as dashed
  const edges = branch_results.map((branch, index) => {
    const width = getEdgeWidth(branch.pf)
    const flow = Math.abs(branch.pf || 0)
    const capacity = branch.rate_a
    const utilization = capacity > 0 ? flow / capacity : 0

    const isConnected = branch.br_status === 1

    let color = '#52c41a'
    if (!isConnected) {
      color = '#6e7681'
    } else if (utilization > 0.9) {
      color = '#ff4d4f'
    } else if (utilization > 0.75) {
      color = '#faad14'
    }

    return {
      data: {
        id: `edge${index}`,
        source: branch.f_bus.toString(),
        target: branch.t_bus.toString(),
        color,
        width: isConnected ? width : 1,
      },
      classes: isConnected ? '' : 'disconnected-edge'
    }
  })

  cy?.elements().remove()
  cy?.add({ nodes, edges })

  // Only run layout if we don't have saved positions
  if (Object.keys(positions).length === 0) {
    cy?.layout({
      name: 'cose',
      animate: true,
      animationDuration: 500,
      nodeRepulsion: 8000,
      idealEdgeLength: 80,
      edgeElasticity: 100
    }).run()
  }

  cy?.fit(undefined, 30)

  // Refresh info panel if something is selected
  refreshSelectedInfo()
}

function closeInfo() {
  selectedElement.value = null
  selectedBusId.value = null
  selectedEdgeId.value = null
  cy?.$('node, edge').unselect()
}

onMounted(() => {
  initGraph()
  nextTick(() => {
    updateGraph()
  })
})

watch(() => simulationStore.simResult, () => {
  nextTick(() => {
    updateGraph()
  })
}, { deep: true })
</script>

<style scoped>
.topology-graph {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.legend {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-icon {
  color: var(--color-success);
  font-size: 12px;
}

.graph-container {
  flex: 1;
  background: var(--bg-primary);
  position: relative;
}

/* Info panel with slide-in animation */
.node-info {
  position: absolute;
  top: 60px;
  right: 16px;
  width: 240px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 10;
  backdrop-filter: blur(8px);
}

.info-slide-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.info-slide-leave-active {
  transition: all 0.2s ease-in;
}
.info-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.info-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.info-header-title {
  font-size: 13px;
  color: var(--text-primary);
}

.info-close-btn {
  color: var(--text-muted) !important;
  transition: color 0.2s;
}
.info-close-btn:hover {
  color: var(--text-primary) !important;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(48, 54, 61, 0.5);
}
.info-row:last-child {
  border-bottom: none;
}

.info-label {
  color: var(--text-secondary);
  font-size: 12px;
}

.info-value {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
}

.value-normal {
  color: var(--color-success);
}

.value-warning {
  color: var(--color-warning);
}

.value-danger {
  color: var(--color-danger);
}
</style>
