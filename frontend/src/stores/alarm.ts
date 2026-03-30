import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { AlarmInfo } from '../api/types'

export const useAlarmStore = defineStore('alarm', () => {
  const alarms = ref<AlarmInfo[]>([])
  const acknowledgedAlarms = ref<Set<string>>(new Set())

  const activeAlarms = computed(() =>
    alarms.value.filter(a => !acknowledgedAlarms.value.has(a.id))
  )

  const criticalCount = computed(() =>
    activeAlarms.value.filter(a => a.level === 'critical').length
  )

  const warningCount = computed(() =>
    activeAlarms.value.filter(a => a.level === 'warning').length
  )

  function addAlarm(alarm: AlarmInfo) {
    alarms.value.push(alarm)
  }

  function addAlarms(newAlarms: AlarmInfo[]) {
    alarms.value.push(...newAlarms)
  }

  function acknowledgeAlarm(alarmId: string) {
    acknowledgedAlarms.value.add(alarmId)
  }

  function clearAlarm(alarmId: string) {
    alarms.value = alarms.value.filter(a => a.id !== alarmId)
    acknowledgedAlarms.value.delete(alarmId)
  }

  function clearAllAlarms() {
    alarms.value = []
    acknowledgedAlarms.value.clear()
  }

  function getAlarmsByType(type: 'voltage' | 'overload' | 'generation'): AlarmInfo[] {
    return activeAlarms.value.filter(a => a.type === type)
  }

  function getAlarmsByElement(elementId: number, elementType: 'bus' | 'branch' | 'gen'): AlarmInfo[] {
    return activeAlarms.value.filter(
      a => a.element_id === elementId && a.element_type === elementType
    )
  }

  return {
    alarms,
    activeAlarms,
    acknowledgedAlarms,
    criticalCount,
    warningCount,
    addAlarm,
    addAlarms,
    acknowledgeAlarm,
    clearAlarm,
    clearAllAlarms,
    getAlarmsByType,
    getAlarmsByElement
  }
})
