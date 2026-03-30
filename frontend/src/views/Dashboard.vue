<template>
  <div class="dashboard">
    <!-- 顶部标题栏 -->
    <header class="dashboard-header">
      <div class="header-left">
        <h1 class="title">MATPOWER 电力系统仿真平台</h1>
        <span v-if="simulationStore.currentCase" class="case-badge">
          {{ casesStore.getCaseByName(simulationStore.currentCase)?.display_name }}
        </span>
      </div>
      <div class="header-right">
        <SimulationControls />
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="dashboard-main">
      <div class="grid-layout">
        <!-- 左侧：拓扑图 -->
        <div class="grid-item topology-panel">
          <TopologyGraph />
        </div>

        <!-- 中间：图表区域 -->
        <div class="grid-item charts-panel">
          <div class="chart-item">
            <VoltageChart />
          </div>
          <div class="chart-item">
            <PowerFlowChart />
          </div>
        </div>

        <!-- 右侧：数据表格和告警 -->
        <div class="grid-item data-panel">
          <a-tabs v-model:activeKey="activeTab" type="card" size="small">
            <a-tab-pane key="table" tab="数据表格">
              <DataTable />
            </a-tab-pane>
            <a-tab-pane key="alarm" tab="告警面板">
              <template #tab>
                <span>
                  告警面板
                  <a-badge
                    v-if="simulationStore.hasAlarms"
                    :count="simulationStore.criticalAlarms.length"
                    :overflow-count="99"
                    style="margin-left: 4px"
                  />
                </span>
              </template>
              <AlarmPanel />
            </a-tab-pane>
          </a-tabs>
        </div>
      </div>

      <!-- 底部：系统概要和控制 -->
      <div class="bottom-panel">
        <SystemSummary />
        <DisturbancePanel />
        <div class="log-panel">
          <div class="card-title">仿真日志</div>
          <div class="log-content">
            <div v-if="logs.length === 0" class="empty-state">暂无日志</div>
            <div v-for="(log, index) in logs.slice(-5)" :key="index" class="log-item">
              <span class="log-time">{{ log.time }}</span>
              <span :class="['log-message', `log-${log.level}`]">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useSimulationStore } from '../stores/simulation'
import { useCasesStore } from '../stores/cases'
import { getSimulationWebSocket } from '../api/websocket'
import TopologyGraph from '../components/TopologyGraph.vue'
import VoltageChart from '../components/VoltageChart.vue'
import PowerFlowChart from '../components/PowerFlowChart.vue'
import SystemSummary from '../components/SystemSummary.vue'
import DataTable from '../components/DataTable.vue'
import DisturbancePanel from '../components/DisturbancePanel.vue'
import AlarmPanel from '../components/AlarmPanel.vue'
import SimulationControls from '../components/SimulationControls.vue'

const simulationStore = useSimulationStore()
const casesStore = useCasesStore()
const activeTab = ref('table')

// WebSocket connection
let ws: ReturnType<typeof getSimulationWebSocket> | null = null

interface Log {
  time: string
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
}

const logs = ref<Log[]>([])

function addLog(level: 'info' | 'success' | 'warning' | 'error', message: string) {
  const now = new Date()
  logs.value.push({
    time: `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`,
    level,
    message
  })
}

async function initializeDashboard() {
  // Initialize WebSocket connection
  try {
    ws = getSimulationWebSocket('dashboard-client')
    await ws.connect()
    addLog('info', 'WebSocket 已连接')

    // Setup WebSocket message handlers
    ws.on('progress', (message: any) => {
      if (message.status === 'running') {
        addLog('info', message.message || '仿真运行中...')
      } else if (message.status === 'completed') {
        addLog('success', message.message || '仿真完成')
      } else if (message.status === 'failed') {
        addLog('error', message.message || '仿真失败')
      }
    })

    ws.on('alarm', (message: any) => {
      const data = message.data
      addLog(data.level === 'critical' ? 'error' : 'warning', data.message || '告警')
    })

    ws.on('connected', () => {
      addLog('info', 'WebSocket 已连接')
    })

    // Keep connection alive with ping
    setInterval(() => {
      if (ws?.isConnected()) {
        ws.ping()
      }
    }, 30000)
  } catch (e) {
    console.warn('WebSocket connection failed, falling back to HTTP polling')
    addLog('warning', 'WebSocket 连接失败，使用 HTTP 轮询')
  }

  // Load initial case
  casesStore.setCurrentCase('case14')
  try {
    await simulationStore.loadCase('case14')
    addLog('success', '加载 IEEE 14 母线系统')

    // Run initial power flow so charts have data to render
    await simulationStore.runSimulation('PF')
    addLog('success', '初始潮流计算完成')
  } catch (e) {
    addLog('error', '加载测试用例失败')
  }
}

onMounted(async () => {
  addLog('info', '系统初始化中...')
  await initializeDashboard()
})

onUnmounted(() => {
  // Disconnect WebSocket on unmount
  if (ws) {
    ws.disconnect()
    ws = null
  }
})
</script>

<style scoped>
.dashboard {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.dashboard-header {
  height: 60px;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.case-badge {
  padding: 4px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dashboard-main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 12px;
  gap: 12px;
}

.grid-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr;
  grid-template-rows: 1fr;
  gap: 12px;
  min-height: 0;
}

.grid-item {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.topology-panel {
  min-width: 0;
}

.charts-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-item {
  flex: 1;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  min-height: 0;
}

.data-panel {
  overflow: hidden;
}

.data-panel :deep(.ant-tabs) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.data-panel :deep(.ant-tabs-nav) {
  margin-bottom: 8px;
  padding: 0 8px;
}

.data-panel :deep(.ant-tabs-content-holder) {
  flex: 1;
  overflow: hidden;
}

.data-panel :deep(.ant-tabs-content) {
  height: 100%;
}

.data-panel :deep(.ant-tabs-tabpane) {
  height: 100;
}

.bottom-panel {
  height: 140px;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.log-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  margin-top: 8px;
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  font-size: 12px;
  border-bottom: 1px solid var(--bg-tertiary);
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: var(--text-muted);
  min-width: 60px;
}

.log-message {
  color: var(--text-secondary);
}

.log-info {
  color: var(--color-info);
}

.log-success {
  color: var(--color-success);
}

.log-warning {
  color: var(--color-warning);
}

.log-error {
  color: var(--color-danger);
}

@media (max-width: 1600px) {
  .grid-layout {
    grid-template-columns: 1fr 1fr;
  }

  .data-panel {
    grid-column: 1 / -1;
    height: 300px;
  }
}

@media (max-width: 1200px) {
  .grid-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
  }

  .bottom-panel {
    grid-template-columns: 1fr;
    height: auto;
  }
}
</style>
