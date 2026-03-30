<template>
  <div class="power-flow-chart">
    <div class="chart-header">
      <div class="card-title">潮流分布</div>
      <a-tag color="blue">MW</a-tag>
    </div>
    <div v-if="!simulationStore.simResult?.branch_results" class="chart-empty">暂无数据</div>
    <div v-else ref="chartRef" class="chart-content"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useSimulationStore } from '../stores/simulation'

const simulationStore = useSimulationStore()
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function initChart() {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value, 'dark', {
    renderer: 'canvas',
    backgroundColor: 'transparent'
  })
}

function updateChart() {
  if (!chart || !simulationStore.simResult) return

  const { branch_results } = simulationStore.simResult

  if (!branch_results) return

  const labels = branch_results.map(b => `${b.f_bus}-${b.t_bus}`)
  const flows = branch_results.map(b => Math.abs(b.pf || 0))
  const losses = branch_results.map(b => Math.abs((b.pf || 0) - (b.pt || 0)))
  const capacities = branch_results.map(b => b.rate_a)

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
      bottom: '15%'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const param = params[0]
        const branch = branch_results[param.dataIndex]
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
      axisLabel: {
        color: '#8b949e',
        fontSize: 9,
        rotate: 45
      },
      axisLine: {
        lineStyle: {
          color: '#30363d'
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#8b949e',
        formatter: '{value}'
      },
      axisLine: {
        lineStyle: {
          color: '#30363d'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#30363d',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: '潮流',
        type: 'bar',
        data: flows.map((f, i) => ({
          value: f,
          itemStyle: { color: colors[i] }
        })),
        barWidth: '50%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  }

  chart.setOption(option)
}

onMounted(() => {
  initChart()
  nextTick(() => {
    updateChart()
  })

  window.addEventListener('resize', () => {
    chart?.resize()
  })
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
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.chart-content {
  flex: 1;
  min-height: 0;
}

.chart-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary, #8b949e);
  font-size: 14px;
}
</style>
