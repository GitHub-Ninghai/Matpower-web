<template>
  <div class="data-table">
    <a-tabs v-model:activeKey="activeTab" size="small" type="line">
      <a-tab-pane key="bus" tab="母线">
        <a-table
          :columns="busColumns"
          :data-source="busData"
          :pagination="{ pageSize: 10, size: 'small' }"
          :scroll="{ y: 300 }"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'vm'">
              <span
                :class="['value-display', getValueClass(record.vm, record.vmin, record.vmax)]"
              >
                {{ record.vm.toFixed(3) }}
              </span>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="editBus(record)">
                编辑
              </a-button>
            </template>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane key="gen" tab="发电机">
        <a-table
          :columns="genColumns"
          :data-source="genData"
          :pagination="{ pageSize: 10, size: 'small' }"
          :scroll="{ y: 300 }"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record, index }">
            <template v-if="column.key === 'status'">
              <a-tag :color="record.gen_status === 1 ? 'success' : 'default'">
                {{ record.gen_status === 1 ? '投入' : '退出' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="editGen(record, index)">
                编辑
              </a-button>
            </template>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane key="branch" tab="线路">
        <a-table
          :columns="branchColumns"
          :data-source="branchData"
          :pagination="{ pageSize: 10, size: 'small' }"
          :scroll="{ y: 300 }"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record, index }">
            <template v-if="column.key === 'status'">
              <a-tag :color="record.br_status === 1 ? 'success' : 'default'">
                {{ record.br_status === 1 ? '投入' : '退出' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'loading'">
              <span
                :class="['value-display', getLoadingClass(record.pf, record.rate_a)]"
              >
                {{ getLoadingPercent(record.pf, record.rate_a) }}%
              </span>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="editBranch(record, index)">
                编辑
              </a-button>
            </template>
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <!-- 编辑弹窗 -->
    <a-modal
      v-model:open="editModalVisible"
      title="编辑参数"
      @ok="handleEditOk"
      @cancel="editModalVisible = false"
    >
      <a-form :label-col="{ span: 8 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="类型">
          <a-input :value="editForm.type === 'bus' ? '母线' : editForm.type === 'gen' ? '发电机' : '线路'" disabled />
        </a-form-item>
        <a-form-item label="参数">
          <a-select v-model:value="editForm.field" style="width: 100%">
            <a-select-option v-for="opt in fieldOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="当前值">
          <a-input-number v-model:value="editForm.value" style="width: 100%" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { Modal, Form, InputNumber, message } from 'ant-design-vue'
import { useSimulationStore } from '../stores/simulation'
import type { BusData, GenData, BranchData } from '../api/types'

const simulationStore = useSimulationStore()
const activeTab = ref('bus')

const busColumns = [
  { title: '编号', dataIndex: 'bus_i', key: 'bus_i', width: 60 },
  { title: '类型', dataIndex: 'bus_type', key: 'bus_type', width: 60, customRender: ({ record }: { record: BusData }) => {
    const types = ['PQ', 'PV', '平衡']
    return types[record.bus_type - 1] || '-'
  }},
  { title: '电压(p.u.)', dataIndex: 'vm', key: 'vm', width: 80 },
  { title: '相角(°)', dataIndex: 'va', key: 'va', width: 70 },
  { title: '负荷(MW)', dataIndex: 'pd', key: 'pd', width: 80 },
  { title: '操作', key: 'action', width: 60 }
]

const genColumns = [
  { title: '母线', dataIndex: 'gen_bus', key: 'gen_bus', width: 60 },
  { title: '有功(MW)', dataIndex: 'pg', key: 'pg', width: 80 },
  { title: '无功(MVar)', dataIndex: 'qg', key: 'qg', width: 80 },
  { title: '电压设定', dataIndex: 'vg', key: 'vg', width: 80 },
  { title: '上限(MW)', dataIndex: 'pmax', key: 'pmax', width: 70 },
  { title: '状态', key: 'status', width: 60 },
  { title: '操作', key: 'action', width: 60 }
]

const branchColumns = [
  { title: '线路', key: 'branch', width: 80, customRender: ({ record }: { record: BranchData }) => `${record.f_bus}-${record.t_bus}` },
  { title: '有功(MW)', dataIndex: 'pf', key: 'pf', width: 70 },
  { title: '无功(MVar)', dataIndex: 'qf', key: 'qf', width: 70 },
  { title: '容量(MVA)', dataIndex: 'rate_a', key: 'rate_a', width: 80 },
  { title: '负载率', key: 'loading', width: 70 },
  { title: '状态', key: 'status', width: 60 },
  { title: '操作', key: 'action', width: 60 }
]

const busData = computed(() => simulationStore.caseData.buses)
const genData = computed(() => simulationStore.caseData.generators)
const branchData = computed(() => simulationStore.caseData.branches)

const editModalVisible = ref(false)
const editForm = ref<{
  type: 'bus' | 'gen' | 'branch'
  id: number
  field: string
  value: number
  index: number
}>({
  type: 'bus',
  id: 0,
  field: '',
  value: 0,
  index: 0
})

const fieldOptions = computed(() => {
  if (editForm.value.type === 'bus') {
    return [
      { label: '有功负荷 Pd (MW)', value: 'pd' },
      { label: '无功负荷 Qd (MVar)', value: 'qd' },
      { label: '电压 Vm (p.u.)', value: 'vm' },
      { label: '电压上限 Vmax', value: 'vmax' },
      { label: '电压下限 Vmin', value: 'vmin' }
    ]
  } else if (editForm.value.type === 'gen') {
    return [
      { label: '有功出力 Pg (MW)', value: 'pg' },
      { label: '无功出力 Qg (MVar)', value: 'qg' },
      { label: '电压设定 Vg (p.u.)', value: 'vg' },
      { label: '有功上限 Pmax', value: 'pmax' },
      { label: '有功下限 Pmin', value: 'pmin' },
      { label: '状态 (1=投入/0=退出)', value: 'gen_status' }
    ]
  } else {
    return [
      { label: '状态 (1=投入/0=退出)', value: 'br_status' },
      { label: '容量 Rate_A (MVA)', value: 'rate_a' }
    ]
  }
})

function getValueClass(vm: number, vmin: number, vmax: number): string {
  if (vm < vmin || vm > vmax) return 'value-danger'
  if (vm < vmin + 0.02 || vm > vmax - 0.02) return 'value-warning'
  return 'value-normal'
}

function getLoadingClass(pf?: number, rateA?: number): string {
  if (!pf || !rateA) return ''
  const loading = Math.abs(pf) / rateA
  if (loading > 0.9) return 'value-danger'
  if (loading > 0.75) return 'value-warning'
  return 'value-normal'
}

function getLoadingPercent(pf?: number, rateA?: number): string {
  if (!pf || !rateA) return '-'
  return ((Math.abs(pf) / rateA) * 100).toFixed(1)
}

function editBus(record: BusData) {
  const idx = busData.value.findIndex(b => b.bus_i === record.bus_i)
  editForm.value = {
    type: 'bus',
    id: record.bus_i,
    field: 'pd',
    value: record.pd,
    index: idx
  }
  editModalVisible.value = true
}

function editGen(record: GenData, index: number) {
  editForm.value = {
    type: 'gen',
    id: record.gen_bus,
    field: 'pg',
    value: record.pg,
    index
  }
  editModalVisible.value = true
}

function editBranch(record: BranchData, index: number) {
  editForm.value = {
    type: 'branch',
    id: record.f_bus,
    field: 'br_status',
    value: record.br_status,
    index
  }
  editModalVisible.value = true
}

async function handleEditOk() {
  const { type, field, value, index } = editForm.value

  // Build modifications in the format the backend expects
  const modifications: Record<string, Array<{ index: number; field: string; value: number }>> = {}

  if (type === 'bus') {
    // Update local caseData first
    simulationStore.updateBusParam(editForm.value.id, field as keyof BusData, value)
    modifications['bus'] = [{ index, field, value }]
  } else if (type === 'gen') {
    simulationStore.updateGenParam(editForm.value.id, field as keyof GenData, value)
    modifications['gen'] = [{ index, field, value }]
  } else if (type === 'branch') {
    simulationStore.updateBranchParam(index, field as keyof BranchData, value)
    modifications['branch'] = [{ index, field, value }]
  }

  editModalVisible.value = false
  message.success('参数已更新，正在重新仿真...')

  // Run simulation with modifications so backend uses the edited data
  await simulationStore.runSimulation(simulationStore.simMode, modifications)
}
</script>

<style scoped>
.data-table {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.data-table :deep(.ant-tabs) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.data-table :deep(.ant-tabs-content) {
  flex: 1;
}

.data-table :deep(.ant-tabs-tabpane) {
  height: 100%;
}

.value-normal {
  color: var(--color-success);
}

.value-warning {
  color: var(--color-warning);
}

.value-danger {
  color: var(--color-danger);
}
</style>
