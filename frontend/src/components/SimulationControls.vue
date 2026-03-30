<template>
  <div class="simulation-controls">
    <a-select
      v-model:value="simMode"
      style="width: 100px"
      size="small"
      :options="modeOptions"
    />
    <a-select
      v-model:value="currentCase"
      style="width: 150px"
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
    <a-tag v-if="simulationStore.simResult" color="success">
      {{ simulationStore.simResult.iterations }} 次迭代
    </a-tag>
    <a-tag v-if="simulationStore.simResult">
      {{ (simulationStore.simResult.et * 1000).toFixed(0) }}ms
    </a-tag>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { useSimulationStore } from '../stores/simulation'
import { useCasesStore } from '../stores/cases'

const simulationStore = useSimulationStore()
const casesStore = useCasesStore()

const simMode = ref<'ac' | 'dc' | 'opf'>('ac')
const currentCase = ref('case14')

const modeOptions = [
  { label: 'AC 潮流', value: 'ac' },
  { label: 'DC 潮流', value: 'dc' },
  { label: 'OPF', value: 'opf' }
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
  await simulationStore.runSimulation(simMode.value)
}

async function handleCaseChange(caseName: string) {
  await simulationStore.loadCase(caseName)
  casesStore.setCurrentCase(caseName)
  await simulationStore.runSimulation(simMode.value)
}

async function handleReset() {
  simulationStore.reset()
  await simulationStore.loadCase(currentCase.value)
  await simulationStore.runSimulation(simMode.value)
}
</script>

<style scoped>
.simulation-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
