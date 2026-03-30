import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { CaseInfo } from '../api/types'
import { apiSimulation } from '../api/index'

export const useCasesStore = defineStore('cases', () => {
  const cases = ref<CaseInfo[]>([])
  const currentCase = ref<CaseInfo | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function loadCases() {
    isLoading.value = true
    error.value = null
    try {
      const data = await apiSimulation.getCases()
      // Transform backend data to frontend format, using real counts from backend
      cases.value = data.map((c: any) => ({
        name: c.name,
        display_name: formatDisplayName(c.name),
        buses: c.buses || 0,
        generators: c.generators || 0,
        branches: c.branches || 0,
        base_mva: c.base_mva || 100,
        description: getCaseDescription(c.name),
        is_demo: c.is_demo || false
      }))
      console.log('[Cases] Loaded', cases.value.length, 'cases')
    } catch (err: any) {
      error.value = err.message || 'Failed to load cases'
      console.error('[Cases] Failed to load:', err)
    } finally {
      isLoading.value = false
    }
  }

  function formatDisplayName(name: string): string {
    const map: Record<string, string> = {
      'case4gs': 'IEEE 4-Bus (Grainger & Stevenson)',
      'case5': '5-Bus System',
      'case6ww': 'IEEE 6-Bus (Wood & Wollenberg)',
      'case9': 'IEEE 9-Bus System',
      'case9Q': 'IEEE 9-Bus (with Q cost)',
      'case14': 'IEEE 14-Bus System',
      'case24_ieee_rts': 'IEEE 24-Bus RTS',
      'case30': 'IEEE 30-Bus System',
      'case30Q': 'IEEE 30-Bus (with Q cost)',
      'case39': 'IEEE 39-Bus (New England)',
      'case57': 'IEEE 57-Bus System',
      'case118': 'IEEE 118-Bus System',
      'case300': 'IEEE 300-Bus System'
    }
    return map[name] || name.charAt(0).toUpperCase() + name.slice(1)
  }

  function getCaseDescription(name: string): string {
    const map: Record<string, string> = {
      'case4gs': '4-bus example from Grainger & Stevenson textbook.',
      'case5': '5-bus test system.',
      'case6ww': '6-bus example from Wood & Wollenberg textbook.',
      'case9': 'Small test system with 9 buses, 3 generators, and 9 transmission lines.',
      'case9Q': 'IEEE 9-bus system with reactive power cost.',
      'case14': 'Standard IEEE test system with 14 buses, 5 generators, and 20 lines.',
      'case24_ieee_rts': 'IEEE 24-bus reliability test system.',
      'case30': 'Medium test system with 30 buses, 6 generators, and 41 lines.',
      'case30Q': 'IEEE 30-bus system with reactive power cost.',
      'case39': 'IEEE 39-bus New England test system.',
      'case57': 'Larger test system with 57 buses, 7 generators, and 80 lines.',
      'case118': 'Large test system with 118 buses, 54 generators, and 186 lines.',
      'case300': 'Very large test system with 300 buses, 69 generators, and 411 lines.'
    }
    return map[name] || `MATPOWER test case: ${name}`
  }

  function setCurrentCase(caseName: string) {
    const found = cases.value.find(c => c.name === caseName)
    if (found) {
      currentCase.value = found
    } else {
      // Try to load from backend
      loadCases().then(() => {
        const found = cases.value.find(c => c.name === caseName)
        if (found) currentCase.value = found
      })
    }
  }

  function getCaseByName(name: string): CaseInfo | undefined {
    return cases.value.find(c => c.name === name)
  }

  // Initialize on store creation
  loadCases()

  return {
    cases,
    currentCase,
    isLoading,
    error,
    loadCases,
    setCurrentCase,
    getCaseByName
  }
})
