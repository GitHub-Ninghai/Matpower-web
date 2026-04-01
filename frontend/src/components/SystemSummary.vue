<template>
  <div class="system-summary">
    <div class="card-title">系统概要</div>
    <div v-if="summary" class="summary-grid">
      <div class="summary-item summary-gen">
        <div class="item-icon">&#9889;</div>
        <div class="item-data">
          <div class="item-label">总发电</div>
          <div class="item-value value-display">{{ displayTotalGen }} <span class="item-unit">MW</span></div>
        </div>
      </div>
      <div class="summary-item summary-load">
        <div class="item-icon">&#9881;</div>
        <div class="item-data">
          <div class="item-label">总负荷</div>
          <div class="item-value value-display">{{ displayTotalLoad }} <span class="item-unit">MW</span></div>
        </div>
      </div>
      <div class="summary-item summary-loss">
        <div class="item-icon">&#128256;</div>
        <div class="item-data">
          <div class="item-label">总损耗</div>
          <div class="item-value value-display">{{ displayTotalLoss }} <span class="item-unit">MW</span></div>
        </div>
      </div>
      <div class="summary-item">
        <div class="item-data">
          <div class="item-label">最高电压</div>
          <div class="item-value value-display value-warning">{{ displayMaxVoltage }}</div>
          <div class="item-sub">Bus {{ displayMaxVoltageBus }}</div>
        </div>
      </div>
      <div class="summary-item">
        <div class="item-data">
          <div class="item-label">最低电压</div>
          <div class="item-value value-display value-normal">{{ displayMinVoltage }}</div>
          <div class="item-sub">Bus {{ displayMinVoltageBus }}</div>
        </div>
      </div>
      <div class="summary-item">
        <div class="item-data">
          <div class="item-label">运行成本</div>
          <div class="item-value value-display">${{ displayTotalCost }}</div>
        </div>
      </div>
      <div class="summary-item summary-status">
        <div class="item-data">
          <div class="item-label">收敛状态</div>
          <div class="status-indicator">
            <span class="status-dot" :class="convergenceClass"></span>
            <span class="status-text">{{ convergenceText }}</span>
          </div>
        </div>
      </div>
    </div>
    <a-spin v-else tip="加载中..." />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSimulationStore } from '../stores/simulation'

const simulationStore = useSimulationStore()
const summary = computed(() => simulationStore.systemSummary)

// 兼容新旧数据格式
const displayTotalGen = computed(() => {
  if (!summary.value) return '0.00'
  return (summary.value.total_gen ?? summary.value.total_generation ?? 0).toFixed(2)
})

const displayTotalLoad = computed(() => {
  if (!summary.value) return '0.00'
  return (summary.value.total_load ?? 0).toFixed(2)
})

const displayTotalLoss = computed(() => {
  if (!summary.value) return '0.00'
  return (summary.value.total_loss ?? summary.value.total_losses ?? 0).toFixed(2)
})

const displayMaxVoltage = computed(() => {
  if (!summary.value) return '0.000'
  return (summary.value.max_voltage ?? 1.0).toFixed(3)
})

const displayMaxVoltageBus = computed(() => {
  if (!summary.value) return '-'
  return summary.value.max_voltage_bus ?? '-'
})

const displayMinVoltage = computed(() => {
  if (!summary.value) return '0.000'
  return (summary.value.min_voltage ?? 1.0).toFixed(3)
})

const displayMinVoltageBus = computed(() => {
  if (!summary.value) return '-'
  return summary.value.min_voltage_bus ?? '-'
})

const displayTotalCost = computed(() => {
  if (!summary.value) return '0.00'
  return (summary.value.total_cost ?? 0).toFixed(2)
})

const convergenceText = computed(() => {
  if (!summary.value) return '-'
  return summary.value.convergence ?? (simulationStore.simResult?.converged ? '正常收敛' : '未收敛')
})

const convergenceClass = computed(() => {
  const converged = simulationStore.simResult?.converged ?? true
  return converged ? 'success' : 'danger'
})
</script>

<style scoped>
.system-summary {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  transition: border-color 0.3s;
}

.system-summary:hover {
  border-color: var(--border-glow);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
  margin-top: 8px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  min-width: 80px;
  transition: background-color 0.2s, transform 0.2s;
}

.summary-item:hover {
  background: var(--bg-hover);
  transform: translateY(-1px);
}

.item-icon {
  font-size: 16px;
  line-height: 1;
  flex-shrink: 0;
}

.item-data {
  display: flex;
  flex-direction: column;
}

.item-label {
  font-size: 10px;
  color: var(--text-muted);
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.item-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
}

.item-unit {
  font-size: 10px;
  color: var(--text-secondary);
  font-weight: 400;
}

.item-sub {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 1px;
}

.summary-status {
  justify-content: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.success {
  background-color: var(--color-success);
  box-shadow: 0 0 6px rgba(82, 196, 26, 0.4);
}

.status-dot.danger {
  background-color: var(--color-danger);
  box-shadow: 0 0 6px rgba(255, 77, 79, 0.4);
}

.status-text {
  color: var(--text-secondary);
  font-size: 12px;
}

.value-normal {
  color: var(--color-success);
}

.value-warning {
  color: var(--color-warning);
}

@media (max-width: 1400px) {
  .summary-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
