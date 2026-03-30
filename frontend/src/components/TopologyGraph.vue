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
          <span class="legend-icon">▲</span>
          发电机
        </span>
      </div>
    </div>
    <div ref="containerRef" class="graph-container"></div>
    <div v-if="selectedElement" class="node-info">
      <div class="info-header">
        <span>{{ elementType === 'bus' ? '母线' : '线路' }}信息</span>
        <a-button type="text" size="small" @click="closeInfo">
          <CloseOutlined />
        </a-button>
      </div>
      <div class="info-content">
        <template v-if="elementType === 'bus'">
          <div class="info-row">
            <span>编号:</span>
            <span class="value-display">{{ selectedElement.id }}</span>
          </div>
          <div class="info-row">
            <span>类型:</span>
            <span>{{ getBusType(selectedElement.bus_type) }}</span>
          </div>
          <div class="info-row">
            <span>电压:</span>
            <span :class="['value-display', getValueClass(selectedElement.vm)]">
              {{ selectedElement.vm?.toFixed(3) }} p.u.
            </span>
          </div>
          <div class="info-row">
            <span>相角:</span>
            <span class="value-display">{{ selectedElement.va?.toFixed(2) }}°</span>
          </div>
          <div class="info-row">
            <span>负荷:</span>
            <span class="value-display">{{ selectedElement.pd }} MW</span>
          </div>
        </template>
        <template v-else>
          <div class="info-row">
            <span>线路:</span>
            <span class="value-display">{{ selectedElement.source }} → {{ selectedElement.target }}</span>
          </div>
          <div class="info-row">
            <span>有功:</span>
            <span class="value-display">{{ selectedElement.pf?.toFixed(2) }} MW</span>
          </div>
          <div class="info-row">
            <span>无功:</span>
            <span class="value-display">{{ selectedElement.qf?.toFixed(2) }} MVar</span>
          </div>
          <div class="info-row">
            <span>容量:</span>
            <span class="value-display">{{ selectedElement.rate_a }} MVA</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import cytoscape, { type Core, type NodeSingular } from 'cytoscape'
import { CloseOutlined } from '@ant-design/icons-vue'
import { useSimulationStore } from '../stores/simulation'
import type { BusData, BranchData } from '../api/types'

const simulationStore = useSimulationStore()
const containerRef = ref<HTMLElement>()
let cy: Core | null = null

const selectedElement = ref<any>(null)
const elementType = ref<'bus' | 'branch'>('bus')

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
          'border-color': '#30363d'
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
          'arrow-scale': 0.8
        }
      },
      {
        selector: 'edge:selected',
        style: {
          'line-color': '#1890ff',
          'target-arrow-color': '#1890ff',
          'width': 6
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
    const busData = node.data('busData') as BusData
    selectedElement.value = {
      id: node.id(),
      ...busData
    }
    elementType.value = 'bus'
  })

  cy.on('tap', 'edge', (evt) => {
    const edge = evt.target
    const branchData = edge.data('branchData') as BranchData
    selectedElement.value = {
      source: edge.source().id(),
      target: edge.target().id(),
      ...branchData
    }
    elementType.value = 'branch'
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
        hasGen: hasGen ? 'true' : 'false',
        busData: bus
      }
    }
  })

  // 创建边
  const edges = branch_results
    .filter(b => b.br_status === 1)
    .map((branch, index) => {
      const width = getEdgeWidth(branch.pf)
      const flow = Math.abs(branch.pf || 0)
      const capacity = branch.rate_a
      const utilization = capacity > 0 ? flow / capacity : 0

      let color = '#52c41a'
      if (utilization > 0.9) color = '#ff4d4f'
      else if (utilization > 0.75) color = '#faad14'

      return {
        data: {
          id: `edge${index}`,
          source: branch.f_bus.toString(),
          target: branch.t_bus.toString(),
          color,
          width,
          branchData: branch
        }
      }
    })

  cy?.elements().remove()
  cy?.add({ nodes, edges })
  cy?.layout({
    name: 'cose',
    animate: true,
    animationDuration: 500,
    nodeRepulsion: 8000,
    idealEdgeLength: 80,
    edgeElasticity: 100
  }).run()

  cy?.fit(undefined, 30)
}

function closeInfo() {
  selectedElement.value = null
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

.node-info {
  position: absolute;
  top: 60px;
  right: 16px;
  width: 220px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 10;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.info-row span:first-child {
  color: var(--text-secondary);
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
