<template>
  <div class="disturbance-panel">
    <div class="card-title">扰动控制台</div>
    <a-form layout="inline" size="small" class="disturbance-form">
      <a-form-item label="类型">
        <a-select
          v-model:value="disturbanceType"
          style="width: 120px"
          :options="disturbanceOptions"
        />
      </a-form-item>
      <a-form-item label="目标">
        <a-select
          v-model:value="targetId"
          style="width: 100px"
          :options="targetOptions"
          placeholder="选择"
        />
      </a-form-item>
      <a-form-item v-if="showValueInput" label="数值">
        <a-input-number
          v-model:value="newValue"
          style="width: 100px"
          placeholder="数值"
        />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" :loading="simulationStore.isRunning" @click="applyDisturbance">
          注入扰动
        </a-button>
      </a-form-item>
      <a-form-item>
        <a-button type="default" :loading="simulationStore.isRunning" @click="runOPF">
          自动修正
        </a-button>
      </a-form-item>
    </a-form>
    <div class="quick-actions">
      <a-tag
        v-for="action in quickActions"
        :key="action.label"
        :color="action.color"
        style="cursor: pointer"
        @click="applyQuickAction(action)"
      >
        {{ action.label }}
      </a-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useSimulationStore } from '../stores/simulation'
import type { DisturbanceType } from '../api/types'

const simulationStore = useSimulationStore()

const disturbanceType = ref<DisturbanceType>('load_change')
const targetId = ref<number>()
const newValue = ref<number>(50)

const disturbanceOptions = [
  { label: '负荷变化', value: 'load_change' },
  { label: '线路断开', value: 'line_outage' },
  { label: '发电机跳闸', value: 'gen_outage' },
  { label: '电压变化', value: 'voltage_change' }
]

const showValueInput = computed(() => {
  return ['load_change', 'voltage_change'].includes(disturbanceType.value)
})

const targetOptions = computed(() => {
  if (disturbanceType.value === 'line_outage') {
    return simulationStore.caseData.branches.map((b, i) => ({
      label: `${b.f_bus}-${b.t_bus}${b.br_status === 0 ? ' (已断)' : ''}`,
      value: i
    }))
  }

  if (disturbanceType.value === 'gen_outage') {
    return simulationStore.caseData.generators.map(g => ({
      label: `Gen ${g.gen_bus}${g.gen_status === 0 ? ' (已退)' : ''}`,
      value: g.gen_bus
    }))
  }

  return simulationStore.caseData.buses.map(b => ({
    label: `Bus ${b.bus_i}`,
    value: b.bus_i
  }))
})

// Auto-select first valid target when type changes
watch(disturbanceType, () => {
  if (targetOptions.value.length > 0) {
    targetId.value = targetOptions.value[0].value
  }
})

const quickActions = computed(() => [
  {
    label: '重负荷',
    type: 'load_change' as DisturbanceType,
    value: 200,
    color: 'orange',
    targetId: simulationStore.caseData.buses.length > 0
      ? simulationStore.caseData.buses[simulationStore.caseData.buses.length - 1].bus_i
      : undefined
  },
  {
    label: '断线路',
    type: 'line_outage' as DisturbanceType,
    value: 0,
    color: 'red',
    targetId: 0
  },
  {
    label: '低电压',
    type: 'voltage_change' as DisturbanceType,
    value: 0.9,
    color: 'volcano',
    targetId: simulationStore.caseData.generators.length > 0
      ? simulationStore.caseData.generators[0].gen_bus
      : undefined
  }
])

async function applyDisturbance() {
  if (targetId.value === undefined) {
    message.warning('请选择目标')
    return
  }

  try {
    await simulationStore.applyDisturbance({
      type: disturbanceType.value,
      target_id: targetId.value,
      new_value: newValue.value
    })
    message.success('扰动已应用')
  } catch (e: any) {
    message.error('扰动应用失败: ' + (e.message || '未知错误'))
  }
}

async function runOPF() {
  try {
    await simulationStore.runOPF()
    message.success('OPF 修正完成')
  } catch (e: any) {
    message.error('OPF 修正失败: ' + (e.message || '未知错误'))
  }
}

function applyQuickAction(action: any) {
  disturbanceType.value = action.type
  targetId.value = action.targetId
  if (action.type !== 'line_outage') {
    newValue.value = action.value
  }
  applyDisturbance()
}
</script>

<style scoped>
.disturbance-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px 16px;
  transition: border-color 0.3s;
}

.disturbance-panel:hover {
  border-color: #40a9ff33;
}

.disturbance-form {
  margin-bottom: 8px;
}

.disturbance-panel :deep(.ant-form-item) {
  margin-bottom: 8px;
}

.quick-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-actions :deep(.ant-tag) {
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.quick-actions :deep(.ant-tag:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
</style>
