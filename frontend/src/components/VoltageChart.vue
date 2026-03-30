<template>
  <div class="voltage-chart">
    <div class="chart-header">
      <div class="card-title">电压监控</div>
      <a-tag color="blue">p.u.</a-tag>
    </div>
    <div v-if="!simulationStore.simResult?.bus_results" class="chart-empty">暂无数据</div>
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

  const { bus_results } = simulationStore.simResult

  if (!bus_results) return

  const busIds = bus_results.map(b => `Bus ${b.bus_i}`)
  const voltages = bus_results.map(b => b.vm)
  const vmins = bus_results.map(b => b.vmin)
  const vmaxs = bus_results.map(b => b.vmax)

  // 判断是否越限
  const colors = voltages.map(v => {
    if (v < 0.95) return '#ff4d4f'
    if (v > 1.05) return '#faad14'
    return '#52c41a'
  })

  const option: echarts.EChartsOption = {
    grid: {
      left: '10%',
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
        const bus = bus_results[param.dataIndex]
        return `
          <div style="padding: 4px;">
            <div><strong>${param.name}</strong></div>
            <div>电压: ${param.value.toFixed(3)} p.u.</div>
            <div>范围: ${bus.vmin.toFixed(2)} ~ ${bus.vmax.toFixed(2)}</div>
            <div>相角: ${bus.va.toFixed(2)}°</div>
          </div>
        `
      }
    },
    xAxis: {
      type: 'category',
      data: busIds,
      axisLabel: {
        color: '#8b949e',
        fontSize: 10
      },
      axisLine: {
        lineStyle: {
          color: '#30363d'
        }
      }
    },
    yAxis: {
      type: 'value',
      min: 0.9,
      max: 1.15,
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
        name: '电压',
        type: 'bar',
        data: voltages.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i] }
        })),
        barWidth: '60%',
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: {
            type: 'dashed',
            color: '#faad14'
          },
          data: [
            { yAxis: 1.05, label: { formatter: 'Vmax' } },
            { yAxis: 0.95, label: { formatter: 'Vmin' } }
          ]
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
