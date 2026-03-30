<template>
  <div class="system-summary">
    <div class="card-title">系统概要</div>
    <div v-if="summary" class="summary-grid">
      <div class="summary-item">
        <div class="item-label">总发电</div>
        <div class="item-value value-display">{{ displayTotalGen }}</div>
        <div class="item-unit">MW</div>
      </div>
      <div class="summary-item">
        <div class="item-label">总负荷</div>
        <div class="item-value value-display">{{ displayTotalLoad }}</div>
        <div class="item-unit">MW</div>
      </div>
      <div class="summary-item">
        <div class="item-label">总损耗</div>
        <div class="item-value value-display">{{ displayTotalLoss }}</div>
        <div class="item-unit">MW</div>
      </div>
      <div class="summary-item">
        <div class="item-label">最高电压</div>
        <div class="item-value value-display value-warning">
          {{ displayMaxVoltage }}
        </div>
        <div class="item-unit">Bus {{ displayMaxVoltageBus }}</div>
      </div>
      <div class="summary-item">
        <div class="item-label">最低电压</div>
        <div class="item-value value-display value-normal">
          {{ displayMinVoltage }}
        </div>
        <div class="item-unit">Bus {{ displayMinVoltageBus }}</div>
      </div>
      <div class="summary-item">
        <div class="item-label">运行成本</div>
        <div class="item-value value-display">$</div>
        <div class="item-unit">{{ displayTotalCost }}</div>
      </div>
      <div class="summary-item status-item">
        <div class="item-label">收敛状态</div>
        <div class="status-indicator">
          <span class="status-dot" :class="convergenceClass"></span>
          <span>{{ convergenceText }}</span>
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
  // 新格式
  if (summary.value.max_voltage !== undefined) {
    if (typeof summary.value.max_voltage === 'object') {
      return summary.value.max_voltage.value.toFixed(3)
    }
    return summary.value.max_voltage.toFixed(3)
  }
  return (summary.value.max_voltage ?? 1.0).toFixed(3)
})

const displayMaxVoltageBus = computed(() => {
  if (!summary.value) return '-'
  if (typeof summary.value.max_voltage === 'object') {
    return summary.value.max_voltage.bus
  }
  return summary.value.max_voltage_bus ?? '-'
})

const displayMinVoltage = computed(() => {
  if (!summary.value) return '0.000'
  if (summary.value.min_voltage !== undefined) {
    if (typeof summary.value.min_voltage === 'object') {
      return summary.value.min_voltage.value.toFixed(3)
    }
    return summary.value.min_voltage.toFixed(3)
  }
  return (summary.value.min_voltage ?? 1.0).toFixed(3)
})

const displayMinVoltageBus = computed(() => {
  if (!summary.value) return '-'
  if (typeof summary.value.min_voltage === 'object') {
    return summary.value.min_voltage.bus
  }
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
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 12px;
  margin-top: 8px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  min-width: 80px;
}

.item-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.item-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.item-unit {
  font-size: 10px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.status-item {
  justify-content: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.success {
  background-color: var(--color-success);
}

.status-dot.danger {
  background-color: var(--color-danger);
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
