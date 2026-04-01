<template>
  <div class="power-flow-chart">
    <div class="chart-header">
      <div class="card-title">潮流分布</div>
      <a-tag color="blue" size="small">MW</a-tag>
    </div>
    <div ref="chartRef" class="chart-content"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useSimulationStore } from '../stores/simulation'

const simulationStore = useSimulationStore()
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function handleResize() {
  chart?.resize()
}

function ensureChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value, 'dark', {
      renderer: 'canvas'
    })
  }
}

function updateChart() {
  if (!simulationStore.simResult?.branch_results?.length) {
    chart?.clear()
    return
  }

  ensureChart()
  if (!chart) return

  const { branch_results } = simulationStore.simResult

  // Filter to only connected branches for display
  const connected = branch_results.filter(b => b.br_status === 1)
  const labels = connected.map(b => `${b.f_bus}-${b.t_bus}`)
  const flows = connected.map(b => Math.abs(b.pf || 0))
  const losses = connected.map(b => Math.abs((b.pf || 0) - (b.pt || 0)))
  const capacities = connected.map(b => b.rate_a)

  // 计算负载率
  const utilizations = flows.map((f, i) => capacities[i] > 0 ? f / capacities[i] : 0)
  const colors = utilizations.map(u => {
    if (u > 0.9) return '#ff4d4f'
    if (u > 0.75) return '#faad14'
    return '#1890ff'
  })

  const option: echarts.EChartsOption = {
    grid: {
      left: '8%',
      right: '5%',
      top: '15%',
      bottom: '20%'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(22, 27, 34, 0.95)',
      borderColor: '#30363d',
      borderWidth: 1,
      textStyle: { color: '#c9d1d9', fontSize: 12 },
      formatter: (params: any) => {
        const param = params[0]
        const branch = connected[param.dataIndex]
        const flow = branch.pf || 0
        const capacity = branch.rate_a
        const utilization = capacity > 0 ? (Math.abs(flow) / capacity * 100) : 0
        return `
          <div style="padding: 4px;">
            <div><strong>线路 ${branch.f_bus}-${branch.t_bus}</strong></div>
            <div>有功潮流: ${flow.toFixed(2)} MW</div>
            <div>容量: ${capacity} MVA</div>
            <div>负载率: ${utilization.toFixed(1)}%</div>
            <div>损耗: ${losses[param.dataIndex].toFixed(2)} MW</div>
          </div>
        `
      }
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { color: '#8b949e', fontSize: 9, rotate: 45 },
      axisLine: { lineStyle: { color: '#30363d' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#8b949e', formatter: '{value}' },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#21262d', type: 'dashed' } }
    },
    series: [
      {
        name: '潮流',
        type: 'bar',
        data: flows.map((f, i) => ({
          value: f,
          itemStyle: { color: colors[i], borderRadius: [3, 3, 0, 0] }
        })),
        barWidth: '50%'
      }
    ],
    animationDuration: 400,
    animationEasing: 'cubicOut'
  }

  chart.setOption(option, true)
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

watch(() => simulationStore.simResult, () => {
  nextTick(() => {
    updateChart()
  })
}, { deep: true })
</script>

<style scoped>
.power-flow-chart {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color);
}

.chart-content {
  flex: 1;
  min-height: 0;
}
</style>
