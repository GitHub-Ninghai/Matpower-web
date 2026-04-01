<template>
  <div class="simulation-controls">
    <a-select
      v-model:value="simMode"
      style="width: 110px"
      size="small"
      :options="modeOptions"
    />
    <a-select
      v-model:value="currentCase"
      style="width: 180px"
      size="small"
      :options="caseOptions"
      @change="handleCaseChange"
    />
    <a-button
      type="primary"
      size="small"
      :loading="simulationStore.isRunning"
      @click="runSimulation"
    >
      <template #icon>
        <PlayCircleOutlined />
      </template>
      运行
    </a-button>
    <a-button
      size="small"
      @click="handleReset"
    >
      <template #icon>
        <ReloadOutlined />
      </template>
      重置
    </a-button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { useSimulationStore } from '../stores/simulation'
import { useCasesStore } from '../stores/cases'

const simulationStore = useSimulationStore()
const casesStore = useCasesStore()

const simMode = ref<'PF' | 'DCPF' | 'OPF'>('PF')
const currentCase = ref('case14')

const modeOptions = [
  { label: 'AC 潮流', value: 'PF' },
  { label: 'DC 潮流', value: 'DCPF' },
  { label: 'OPF', value: 'OPF' }
]

const caseOptions = computed(() =>
  casesStore.cases
    .filter(c => c.is_demo !== false)
    .map(c => ({
      label: `${c.display_name} (${c.buses}母线)`,
      value: c.name
    }))
)

watch(simMode, (newMode) => {
  simulationStore.simMode = newMode
})

async function runSimulation() {
  try {
    await simulationStore.runSimulation(simMode.value)
    message.success('仿真完成')
  } catch (e: any) {
    message.error('仿真失败: ' + (e.message || '未知错误'))
  }
}

async function handleCaseChange(caseName: string) {
  try {
    await simulationStore.loadCase(caseName)
    casesStore.setCurrentCase(caseName)
    await simulationStore.runSimulation(simMode.value)
    message.success('切换用例并仿真完成')
  } catch (e: any) {
    message.error('切换用例失败: ' + (e.message || '未知错误'))
  }
}

async function handleReset() {
  try {
    simulationStore.reset()
    await simulationStore.loadCase(currentCase.value)
    await simulationStore.runSimulation(simMode.value)
    message.success('已重置')
  } catch (e: any) {
    message.error('重置失败: ' + (e.message || '未知错误'))
  }
}
</script>

<style scoped>
.simulation-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
