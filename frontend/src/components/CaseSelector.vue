<template>
  <div class="case-selector">
    <a-select
      v-model:value="selectedCase"
      style="width: 240px"
      size="large"
      :options="caseOptions"
      :loading="casesStore.isLoading"
      placeholder="选择测试用例"
      @change="handleCaseChange"
    >
      <template #suffixIcon>
        <BranchesOutlined />
      </template>
    </a-select>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { BranchesOutlined } from '@ant-design/icons-vue'
import { useCasesStore } from '../stores/cases'
import { useSimulationStore } from '../stores/simulation'

const casesStore = useCasesStore()
const simulationStore = useSimulationStore()

const selectedCase = ref('')

const caseOptions = computed(() =>
  casesStore.cases.map(c => ({
    label: `${c.display_name} (${c.buses} 母线)`,
    value: c.name
  }))
)

async function handleCaseChange(caseName: string) {
  casesStore.setCurrentCase(caseName)
  await simulationStore.loadCase(caseName)
  await simulationStore.runSimulation()
}

// Initialize: load cases if not already loaded, then pick a default
onMounted(async () => {
  if (casesStore.cases.length === 0) {
    await casesStore.loadCases()
  }
  if (!selectedCase.value && casesStore.cases.length > 0) {
    // Pick case14 if available, otherwise first case
    const defaultCase = casesStore.cases.find(c => c.name === 'case14') || casesStore.cases[0]
    selectedCase.value = defaultCase.name
  }
})
</script>

<style scoped>
.case-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
