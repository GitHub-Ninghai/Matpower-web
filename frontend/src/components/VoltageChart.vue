<template>
  <div class="voltage-chart">
    <div class="chart-header">
      <div class="card-title">电压监控</div>
      <a-tag color="blue" size="small">p.u.</a-tag>
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
  if (!simulationStore.simResult?.bus_results?.length) {
    chart?.clear()
    return
  }

  ensureChart()
  if (!chart) return

  const { bus_results } = simulationStore.simResult

  const busIds = bus_results.map(b => `Bus ${b.bus_i}`)
  const voltages = bus_results.map(b => b.vm)
  const vmins = bus_results.map(b => b.vmin)
  const vmaxs = bus_results.map(b => b.vmax)

  const colors = voltages.map((v, i) => {
    if (v < (vmins[i] || 0.95)) return '#ff4d4f'
    if (v > (vmaxs[i] || 1.05)) return '#faad14'
    if (v < (vmins[i] || 0.95) + 0.02 || v > (vmaxs[i] || 1.05) - 0.02) return '#faad14'
    return '#52c41a'
  })

  const option: echarts.EChartsOption = {
    grid: {
      left: '10%',
      right: '5%',
      top: '12%',
      bottom: '18%'
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
        const bus = bus_results[param.dataIndex]
        return `
          <div style="padding: 4px;">
            <div><strong>${param.name}</strong></div>
            <div>电压: ${param.value.toFixed(3)} p.u.</div>
            <div>范围: ${bus.vmin.toFixed(2)} ~ ${bus.vmax.toFixed(2)}</div>
            <div>相角: ${bus.va.toFixed(2)}&deg;</div>
          </div>
        `
      }
    },
    xAxis: {
      type: 'category',
      data: busIds,
      axisLabel: { color: '#8b949e', fontSize: 10 },
      axisLine: { lineStyle: { color: '#30363d' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0.9,
      max: 1.15,
      axisLabel: { color: '#8b949e', formatter: '{value}' },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#21262d', type: 'dashed' } }
    },
    series: [
      {
        name: '电压',
        type: 'bar',
        data: voltages.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i], borderRadius: [3, 3, 0, 0] }
        })),
        barWidth: '60%',
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { type: 'dashed', color: '#faad14', width: 1 },
          label: { color: '#8b949e', fontSize: 10 },
          data: [
            { yAxis: 1.05, label: { formatter: 'Vmax', position: 'insideEndTop' } },
            { yAxis: 0.95, label: { formatter: 'Vmin', position: 'insideEndTop' } }
          ]
        }
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
.voltage-chart {
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
