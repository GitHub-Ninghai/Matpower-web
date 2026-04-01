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
                {{ record.vm?.toFixed(3) ?? '-' }}
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
              <a-tag :color="record.gen_status === 1 ? 'success' : 'default'" size="small">
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
              <a-tag :color="record.br_status === 1 ? 'success' : 'default'" size="small">
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
      :title="undefined"
      :footer="null"
      :width="420"
      :centered="true"
      class="edit-modal"
      @cancel="editModalVisible = false"
    >
      <div class="edit-modal-header">
        <div class="edit-modal-icon" :class="`edit-modal-icon-${editForm.type}`">
          {{ editForm.type === 'bus' ? '母线' : editForm.type === 'gen' ? '发电机' : '线路' }}
        </div>
        <div class="edit-modal-subtitle">
          {{ editForm.type === 'bus' ? `Bus ${editForm.id}` :
             editForm.type === 'gen' ? `Gen Bus ${editForm.id}` :
             `Branch ${editForm.branchLabel}` }}
        </div>
      </div>
      <a-form :label-col="{ span: 8 }" :wrapper-col="{ span: 16 }" class="edit-form">
        <a-form-item label="参数">
          <a-select v-model:value="editForm.field" style="width: 100%">
            <a-select-option v-for="opt in fieldOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="当前值">
          <a-input-number
            v-model:value="editForm.value"
            style="width: 100%"
            :step="editForm.field === 'br_status' || editForm.field === 'gen_status' ? 1 : 0.1"
            :min="editForm.field === 'br_status' || editForm.field === 'gen_status' ? 0 : undefined"
            :max="editForm.field === 'br_status' || editForm.field === 'gen_status' ? 1 : undefined"
          />
        </a-form-item>
      </a-form>
      <div class="edit-modal-footer">
        <a-button @click="editModalVisible = false">取消</a-button>
        <a-button type="primary" :loading="simulationStore.isRunning" @click="handleEditOk">
          应用并仿真
        </a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
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
  { title: '相角(deg)', dataIndex: 'va', key: 'va', width: 70, customRender: ({ record }: { record: BusData }) => {
    return record.va?.toFixed(2) ?? '-'
  }},
  { title: '有功负荷(MW)', dataIndex: 'pd', key: 'pd', width: 90 },
  { title: '无功负荷(MVar)', dataIndex: 'qd', key: 'qd', width: 90 },
  { title: '操作', key: 'action', width: 60 }
]

const genColumns = [
  { title: '母线', dataIndex: 'gen_bus', key: 'gen_bus', width: 60 },
  { title: '有功(MW)', dataIndex: 'pg', key: 'pg', width: 80, customRender: ({ record }: { record: GenData }) => record.pg?.toFixed(2) ?? '-' },
  { title: '无功(MVar)', dataIndex: 'qg', key: 'qg', width: 80, customRender: ({ record }: { record: GenData }) => record.qg?.toFixed(2) ?? '-' },
  { title: '电压设定', dataIndex: 'vg', key: 'vg', width: 80, customRender: ({ record }: { record: GenData }) => record.vg?.toFixed(3) ?? '-' },
  { title: '上限(MW)', dataIndex: 'pmax', key: 'pmax', width: 70 },
  { title: '状态', key: 'status', width: 60 },
  { title: '操作', key: 'action', width: 60 }
]

const branchColumns = [
  { title: '线路', key: 'branch', width: 80, customRender: ({ record }: { record: BranchData }) => `${record.f_bus}-${record.t_bus}` },
  { title: '有功(MW)', dataIndex: 'pf', key: 'pf', width: 70, customRender: ({ record }: { record: BranchData }) => record.pf?.toFixed(2) ?? '-' },
  { title: '无功(MVar)', dataIndex: 'qf', key: 'qf', width: 70, customRender: ({ record }: { record: BranchData }) => record.qf?.toFixed(2) ?? '-' },
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
  branchLabel: string
}>({
  type: 'bus',
  id: 0,
  field: '',
  value: 0,
  index: 0,
  branchLabel: ''
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
    index: idx,
    branchLabel: ''
  }
  editModalVisible.value = true
}

function editGen(record: GenData, index: number) {
  editForm.value = {
    type: 'gen',
    id: record.gen_bus,
    field: 'pg',
    value: record.pg,
    index,
    branchLabel: ''
  }
  editModalVisible.value = true
}

function editBranch(record: BranchData, index: number) {
  editForm.value = {
    type: 'branch',
    id: record.f_bus,
    field: 'br_status',
    value: record.br_status,
    index,
    branchLabel: `${record.f_bus}-${record.t_bus}`
  }
  editModalVisible.value = true
}

async function handleEditOk() {
  const { type, field, value, index } = editForm.value

  const modifications: Record<string, Array<{ index: number; field: string; value: number }>> = {}

  if (type === 'bus') {
    modifications['bus'] = [{ index, field, value }]
  } else if (type === 'gen') {
    modifications['gen'] = [{ index, field, value }]
  } else if (type === 'branch') {
    modifications['branch'] = [{ index, field, value }]
  }

  editModalVisible.value = false
  message.loading({ content: '参数已更新，正在重新仿真...', key: 'edit-sim', duration: 0 })

  try {
    await simulationStore.runSimulation(simulationStore.simMode, modifications)
    message.success({ content: '仿真完成', key: 'edit-sim' })
  } catch (e: any) {
    message.error({ content: '仿真失败: ' + (e.message || '未知错误'), key: 'edit-sim' })
  }
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

/* Edit modal styles */
.edit-modal-header {
  text-align: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.edit-modal-icon {
  display: inline-block;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.edit-modal-icon-bus {
  background: rgba(24, 144, 255, 0.15);
  color: var(--color-primary);
}

.edit-modal-icon-gen {
  background: rgba(82, 196, 26, 0.15);
  color: var(--color-success);
}

.edit-modal-icon-branch {
  background: rgba(250, 173, 20, 0.15);
  color: var(--color-warning);
}

.edit-modal-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
}

.edit-form {
  margin-bottom: 16px;
}

.edit-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}
</style>
