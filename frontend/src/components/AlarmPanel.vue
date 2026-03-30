<template>
  <div class="alarm-panel">
    <div class="alarm-header">
      <div class="card-title">告警列表</div>
      <a-space>
        <a-tag v-if="criticalCount > 0" color="error">
          严重: {{ criticalCount }}
        </a-tag>
        <a-tag v-if="warningCount > 0" color="warning">
          警告: {{ warningCount }}
        </a-tag>
        <a-button v-if="alarms.length > 0" type="link" size="small" @click="clearAll">
          清除全部
        </a-button>
      </a-space>
    </div>
    <div class="alarm-list">
      <div v-if="alarms.length === 0" class="empty-state">
        <CheckCircleOutlined style="font-size: 32px; color: var(--color-success)" />
        <div>暂无告警</div>
      </div>
      <div
        v-for="alarm in alarms"
        :key="alarm.id"
        :class="['alarm-item', `alarm-${alarm.level}`]"
        @click="handleAlarmClick(alarm)"
      >
        <div class="alarm-icon">
          <ExclamationCircleOutlined v-if="alarm.level === 'critical'" />
          <WarningOutlined v-else />
        </div>
        <div class="alarm-content">
          <div class="alarm-message">{{ alarm.message }}</div>
          <div class="alarm-detail">
            {{ getAlarmDetail(alarm) }}
          </div>
        </div>
        <div class="alarm-value">
          <span class="value-current">{{ typeof alarm.value === 'number' ? alarm.value.toFixed(2) : '-' }}</span>
          <span class="value-limit">/ {{ typeof alarm.limit === 'number' ? alarm.limit : '-' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ExclamationCircleOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import { useSimulationStore } from '../stores/simulation'
import type { AlarmInfo } from '../api/types'

const simulationStore = useSimulationStore()

const alarms = computed(() => simulationStore.alarms)
const criticalCount = computed(() => simulationStore.criticalAlarms.length)
const warningCount = computed(() => simulationStore.warningAlarms.length)

function getAlarmDetail(alarm: AlarmInfo): string {
  const typeMap = {
    voltage: '母线',
    overload: '线路',
    generation: '发电机'
  }
  return `${typeMap[alarm.type]} ${alarm.element_id}`
}

function handleAlarmClick(alarm: AlarmInfo) {
  // 触发跳转到拓扑图对应元素
  console.log('Navigate to element:', alarm.element_type, alarm.element_id)
}

function clearAll() {
  simulationStore.clearAlarms()
}
</script>

<style scoped>
.alarm-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.alarm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.alarm-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  gap: 12px;
}

.alarm-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  border-left: 3px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.alarm-item:hover {
  background: var(--border-color);
}

.alarm-item.alarm-critical {
  border-left-color: var(--color-danger);
}

.alarm-item.alarm-warning {
  border-left-color: var(--color-warning);
}

.alarm-icon {
  font-size: 18px;
}

.alarm-item.alarm-critical .alarm-icon {
  color: var(--color-danger);
}

.alarm-item.alarm-warning .alarm-icon {
  color: var(--color-warning);
}

.alarm-content {
  flex: 1;
}

.alarm-message {
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.alarm-detail {
  font-size: 11px;
  color: var(--text-muted);
}

.alarm-value {
  text-align: right;
}

.value-current {
  font-size: 14px;
  font-weight: 600;
  font-family: 'SF Mono', monospace;
}

.value-limit {
  font-size: 11px;
  color: var(--text-muted);
  margin-left: 4px;
}

.alarm-item.alarm-critical .value-current {
  color: var(--color-danger);
}

.alarm-item.alarm-warning .value-current {
  color: var(--color-warning);
}
</style>
