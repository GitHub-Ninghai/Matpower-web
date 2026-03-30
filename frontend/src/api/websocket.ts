/**
 * WebSocket Client for MATPOWER Web Backend
 * Handles real-time communication with the backend
 */

import type { WSMessage } from './types'

export type WSMessageType = 'connected' | 'progress' | 'completed' | 'failed' | 'error' | 'alarm' | 'pong' | 'subscribed'

export interface WSProgressMessage extends WSMessage {
  type: 'progress'
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message: string
}

export interface WSAlarmMessage extends WSMessage {
  type: 'alarm'
  data: {
    level: 'warning' | 'critical'
    message: string
    element_type: 'bus' | 'branch' | 'gen'
    element_id: number
  }
}

export type WSEventHandler = (message: WSMessage) => void

export class SimulationWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private clientId: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 2000
  private handlers: Map<string, Set<WSEventHandler>> = new Map()
  private isManualClose = false

  constructor(clientId: string, baseUrl?: string) {
    this.clientId = clientId
    const wsProtocol = baseUrl?.startsWith('https') ? 'wss://' : 'ws://'
    const host = baseUrl?.replace(/^https?:\/\//, '') || 'localhost:8000'
    this.url = `${wsProtocol}${host}/ws/simulation/${clientId}`
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)
        this.isManualClose = false

        this.ws.onopen = () => {
          console.log(`[WS] Connected to ${this.url}`)
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (e) {
            console.error('[WS] Failed to parse message:', e)
          }
        }

        this.ws.onerror = (error) => {
          console.error('[WS] Error:', error)
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('[WS] Connection closed')
          if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnect()
          }
        }
      } catch (e) {
        reject(e)
      }
    })
  }

  disconnect() {
    this.isManualClose = true
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  private reconnect() {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

    setTimeout(() => {
      this.connect().catch(() => {
        // Failed, will retry automatically
      })
    }, delay)
  }

  private handleMessage(message: WSMessage) {
    const type = message.type || 'unknown'
    const handlers = this.handlers.get(type)

    if (handlers) {
      handlers.forEach(handler => handler(message))
    }

    // Also call wildcard handlers
    const wildcardHandlers = this.handlers.get('*')
    if (wildcardHandlers) {
      wildcardHandlers.forEach(handler => handler(message))
    }
  }

  on(type: WSMessageType | '*', handler: WSEventHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler)
  }

  off(type: WSMessageType | '*', handler: WSEventHandler) {
    const handlers = this.handlers.get(type)
    if (handlers) {
      handlers.delete(handler)
    }
  }

  send(type: string, data?: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data, timestamp: new Date().toISOString() }))
    }
  }

  subscribe(taskId: string) {
    this.send('subscribe', { task_id: taskId })
  }

  ping() {
    this.send('ping')
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

// Monitor WebSocket for system-wide events
export class MonitorWebSocket extends SimulationWebSocket {
  constructor(clientId: string, baseUrl?: string) {
    const wsProtocol = baseUrl?.startsWith('https') ? 'wss://' : 'ws://'
    const host = baseUrl?.replace(/^https?:\/\//, '') || 'localhost:8000'
    const url = `${wsProtocol}${host}/ws/monitor/${clientId}`
    super(clientId, baseUrl)
    ;(this as any).url = url
  }
}

// Singleton instances
let simulationWS: SimulationWebSocket | null = null
let monitorWS: MonitorWebSocket | null = null

export function getSimulationWebSocket(clientId?: string): SimulationWebSocket {
  if (!simulationWS) {
    simulationWS = new SimulationWebSocket(clientId || 'frontend-client')
  }
  return simulationWS
}

export function getMonitorWebSocket(clientId?: string): MonitorWebSocket {
  if (!monitorWS) {
    monitorWS = new MonitorWebSocket(clientId || 'monitor-client')
  }
  return monitorWS
}

export function disconnectAll() {
  if (simulationWS) {
    simulationWS.disconnect()
    simulationWS = null
  }
  if (monitorWS) {
    monitorWS.disconnect()
    monitorWS = null
  }
}
