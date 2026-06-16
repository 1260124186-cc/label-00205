<template>
  <div class="scan-page">
    <div class="scan-container">
      <div class="camera-container" ref="cameraContainer">
        <div class="scan-frame">
          <div class="corner corner-tl"></div>
          <div class="corner corner-tr"></div>
          <div class="corner corner-bl"></div>
          <div class="corner corner-br"></div>
          <div class="scan-line" :class="{ animating: isScanning }"></div>
        </div>
        <div class="scan-tip">将二维码放入框内</div>
      </div>

      <div class="scan-controls">
        <button class="control-btn" @click="toggleFlash">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
          <span>{{ flashOn ? '关闭' : '开启' }}闪光灯</span>
        </button>
        <button class="control-btn" @click="switchCamera">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6"></path>
            <path d="M1 20v-6h6"></path>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"></path>
            <path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"></path>
          </svg>
          <span>切换摄像头</span>
        </button>
        <button class="control-btn" @click="selectFromAlbum">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
          </svg>
          <span>相册选择</span>
        </button>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          class="hidden-input"
          @change="onFileSelected"
        />
      </div>
    </div>

    <div class="scan-result" v-if="scanResult">
      <div class="result-card">
        <div class="result-header">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <span>扫描成功</span>
        </div>

        <div class="result-info">
          <div class="info-item">
            <span class="info-label">节点ID</span>
            <span class="info-value mono">{{ scanResult.org_node_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">节点类型</span>
            <span :class="['info-value', `type-${scanResult.node_type}`]">
              {{ nodeTypeText(scanResult.node_type) }}
            </span>
          </div>
          <div v-if="scanResult.node_name" class="info-item">
            <span class="info-label">节点名称</span>
            <span class="info-value">{{ scanResult.node_name }}</span>
          </div>
        </div>

        <div class="result-actions">
          <button class="action-btn secondary" @click="resetScan">
            重新扫描
          </button>
          <button class="action-btn primary" @click="goToNodeDetail">
            查看详情
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div v-if="scanError" class="scan-error">
      <div class="error-card">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <p>{{ scanError }}</p>
        <button class="retry-btn" @click="resetScan">重试</button>
      </div>
    </div>

    <div class="manual-input">
      <button class="manual-btn" @click="showManualInput = true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 20h9"></path>
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
        </svg>
        手动输入节点ID
      </button>
    </div>

    <div v-if="showManualInput" class="manual-modal" @click="showManualInput = false">
      <div class="modal-content" @click.stop>
        <h3 class="modal-title">输入节点ID</h3>
        <input
          v-model="manualNodeId"
          type="text"
          class="modal-input"
          placeholder="请输入节点ID"
          @keyup.enter="handleManualInput"
        />
        <div class="modal-actions">
          <button class="modal-btn secondary" @click="showManualInput = false">取消</button>
          <button class="modal-btn primary" @click="handleManualInput">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import type { ScanResult } from '@/types'

const router = useRouter()

const cameraContainer = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const isScanning = ref(true)
const flashOn = ref(false)
const scanResult = ref<ScanResult | null>(null)
const scanError = ref('')
const showManualInput = ref(false)
const manualNodeId = ref('')

let html5QrCode: any = null
let cameraFacing = 'environment'

async function initScanner() {
  try {
    const { Html5Qrcode } = await import('html5-qrcode')
    html5QrCode = new Html5Qrcode('qr-reader')

    await nextTick()

    const config = {
      fps: 10,
      qrbox: { width: 250, height: 250 },
      aspectRatio: 1.0
    }

    await html5QrCode.start(
      { facingMode: cameraFacing },
      config,
      onScanSuccess,
      onScanFailure
    )

    isScanning.value = true
  } catch (e: any) {
    console.error('初始化扫码失败:', e)
    scanError.value = '无法访问摄像头，请检查权限设置'
    isScanning.value = false
  }
}

function onScanSuccess(decodedText: string) {
  if (scanResult.value) return

  try {
    let result: ScanResult

    if (decodedText.startsWith('{')) {
      const parsed = JSON.parse(decodedText)
      result = {
        org_node_id: parsed.org_node_id || parsed.node_id || decodedText,
        node_type: parsed.node_type || 'bolt',
        node_name: parsed.node_name,
        location: parsed.location
      }
    } else {
      result = {
        org_node_id: decodedText,
        node_type: decodedText.includes('flange') ? 'flange' : 'bolt'
      }
    }

    scanResult.value = result
    isScanning.value = false
    stopScanner()

    if (navigator.vibrate) {
      navigator.vibrate(200)
    }
  } catch (e) {
    scanResult.value = {
      org_node_id: decodedText,
      node_type: 'bolt'
    }
    isScanning.value = false
    stopScanner()
  }
}

function onScanFailure(error: any) {
}

async function stopScanner() {
  if (html5QrCode && html5QrCode.isScanning) {
    try {
      await html5QrCode.stop()
    } catch (e) {
      console.error('停止扫描失败:', e)
    }
  }
}

async function toggleFlash() {
  if (!html5QrCode) return

  try {
    const capabilities = html5QrCode.getRunningTrackCameraCapabilities()
    if (capabilities && capabilities.torch) {
      flashOn.value = !flashOn.value
      await html5QrCode.applyVideoConstraints({
        advanced: [{ torch: flashOn.value }]
      })
    } else {
      alert('当前设备不支持闪光灯控制')
    }
  } catch (e) {
    console.error('切换闪光灯失败:', e)
  }
}

async function switchCamera() {
  if (!html5QrCode) return

  try {
    await stopScanner()
    cameraFacing = cameraFacing === 'environment' ? 'user' : 'environment'
    await initScanner()
  } catch (e) {
    console.error('切换摄像头失败:', e)
  }
}

function selectFromAlbum() {
  fileInput.value?.click()
}

async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  try {
    const { Html5Qrcode } = await import('html5-qrcode')
    const html5QrCode = new Html5Qrcode('qr-reader')

    const imageUrl = URL.createObjectURL(file)
    const decodedText = await html5QrCode.scanFile(imageUrl, true)
    URL.revokeObjectURL(imageUrl)

    onScanSuccess(decodedText)
  } catch (e) {
    scanError.value = '未能识别图片中的二维码'
    setTimeout(() => {
      scanError.value = ''
    }, 3000)
  }

  input.value = ''
}

function resetScan() {
  scanResult.value = null
  scanError.value = ''
  isScanning.value = true
  initScanner()
}

function goToNodeDetail() {
  if (scanResult.value) {
    router.push(`/node/${encodeURIComponent(scanResult.value.org_node_id)}`)
  }
}

function nodeTypeText(type: string): string {
  const map: Record<string, string> = {
    bolt: '螺栓',
    flange: '法兰面',
    production_line: '生产线'
  }
  return map[type] || type
}

function handleManualInput() {
  if (!manualNodeId.value.trim()) return

  scanResult.value = {
    org_node_id: manualNodeId.value.trim(),
    node_type: 'bolt'
  }
  showManualInput.value = false
  manualNodeId.value = ''
  isScanning.value = false
  stopScanner()
}

onMounted(() => {
  const readerDiv = document.createElement('div')
  readerDiv.id = 'qr-reader'
  readerDiv.style.width = '100%'
  readerDiv.style.height = '100%'
  if (cameraContainer.value) {
    cameraContainer.value.appendChild(readerDiv)
  }
  nextTick(() => {
    initScanner()
  })
})

onUnmounted(() => {
  stopScanner()
})
</script>

<style scoped>
.scan-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #000;
  position: relative;
}

.scan-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
}

.camera-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 300px;
}

.camera-container :deep(#qr-reader) {
  width: 100% !important;
  height: 100% !important;
}

.camera-container :deep(#qr-reader video) {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
}

.camera-container :deep(#qr-reader__dashboard) {
  display: none !important;
}

.scan-frame {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 260px;
  height: 260px;
  pointer-events: none;
  z-index: 10;
}

.corner {
  position: absolute;
  width: 28px;
  height: 28px;
  border: 3px solid #22c55e;
}

.corner-tl {
  top: 0;
  left: 0;
  border-right: none;
  border-bottom: none;
  border-top-left-radius: 8px;
}

.corner-tr {
  top: 0;
  right: 0;
  border-left: none;
  border-bottom: none;
  border-top-right-radius: 8px;
}

.corner-bl {
  bottom: 0;
  left: 0;
  border-right: none;
  border-top: none;
  border-bottom-left-radius: 8px;
}

.corner-br {
  bottom: 0;
  right: 0;
  border-left: none;
  border-top: none;
  border-bottom-right-radius: 8px;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 10px;
  right: 10px;
  height: 2px;
  background: linear-gradient(90deg, transparent, #22c55e, transparent);
  box-shadow: 0 0 8px #22c55e;
}

.scan-line.animating {
  animation: scan-move 2s ease-in-out infinite;
}

@keyframes scan-move {
  0% { top: 10%; }
  50% { top: 90%; }
  100% { top: 10%; }
}

.scan-tip {
  position: absolute;
  bottom: 30px;
  left: 0;
  right: 0;
  text-align: center;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  z-index: 10;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
}

.scan-controls {
  display: flex;
  justify-content: space-around;
  padding: 16px;
  background: rgba(15, 23, 42, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.control-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  color: #94a3b8;
  font-size: 12px;
  transition: color 0.2s;
}

.control-btn:active {
  color: #60a5fa;
}

.scan-result {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.7);
  z-index: 100;
}

.result-card {
  width: 100%;
  max-width: 340px;
  background: #1e293b;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  padding: 24px;
  animation: slide-up 0.3s ease-out;
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  color: #4ade80;
  font-size: 16px;
  font-weight: 600;
}

.result-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
  padding: 12px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 10px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 13px;
  color: #64748b;
}

.info-value {
  font-size: 13px;
  color: #e2e8f0;
  font-weight: 500;
}

.info-value.mono {
  font-family: monospace;
}

.info-value.type-bolt {
  color: #60a5fa;
}

.info-value.type-flange {
  color: #a78bfa;
}

.result-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 44px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.action-btn.secondary {
  background: rgba(71, 85, 105, 0.4);
  color: #cbd5e1;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.action-btn.primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
}

.scan-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 50;
}

.error-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: rgba(30, 41, 59, 0.95);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  color: #f87171;
  text-align: center;
}

.error-card p {
  font-size: 14px;
  color: #cbd5e1;
}

.retry-btn {
  padding: 8px 20px;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 8px;
  color: #60a5fa;
  font-size: 13px;
}

.manual-input {
  padding: 16px;
  background: rgba(15, 23, 42, 0.95);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  text-align: center;
}

.manual-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  color: #60a5fa;
  font-size: 14px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
}

.manual-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 24px;
}

.modal-content {
  width: 100%;
  max-width: 320px;
  background: #1e293b;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  padding: 24px;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #f8fafc;
  margin-bottom: 16px;
}

.modal-input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  color: #e2e8f0;
  font-size: 14px;
  outline: none;
  margin-bottom: 16px;
}

.modal-input:focus {
  border-color: #3b82f6;
}

.modal-actions {
  display: flex;
  gap: 10px;
}

.modal-btn {
  flex: 1;
  height: 40px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
}

.modal-btn.secondary {
  background: rgba(71, 85, 105, 0.4);
  color: #cbd5e1;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.modal-btn.primary {
  background: #3b82f6;
  color: white;
}

.hidden-input {
  display: none;
}
</style>
