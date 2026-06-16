<template>
  <div class="retest-form-page">
    <div class="form-content">
      <div v-if="workOrder" class="workorder-info">
        <div class="info-header">
          <span class="order-no">{{ workOrder.order_no }}</span>
          <span :class="['priority-badge', `priority-${workOrder.priority}`]">
            {{ priorityText(workOrder.priority) }}
          </span>
        </div>
        <h3 class="workorder-title">{{ workOrder.title }}</h3>
        <div class="info-row">
          <span class="info-label">节点</span>
          <span class="info-value">{{ workOrder.node_id || '-' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">风险评分</span>
          <span :class="['info-value', getRiskClass(workOrder.risk_score)]">
            {{ workOrder.risk_score?.toFixed(1) || '-' }}
          </span>
        </div>
      </div>

      <div class="form-section">
        <h3 class="section-title">复测结果</h3>
        <div class="result-options">
          <button
            v-for="option in resultOptions"
            :key="option.value"
            class="result-option"
            :class="{ active: formData.retest_result === option.value }"
            @click="formData.retest_result = option.value"
          >
            <span :class="['result-icon', `icon-${option.value}`]">{{ option.icon }}</span>
            <span class="result-label">{{ option.label }}</span>
          </button>
        </div>
      </div>

      <div class="form-section">
        <h3 class="section-title">
          测量值
          <span class="optional">(选填)</span>
        </h3>
        <div class="input-group">
          <input
            v-model.number="formData.measured_value"
            type="number"
            step="0.01"
            class="form-input"
            placeholder="请输入测量值"
          />
          <span class="input-suffix">kN</span>
        </div>
      </div>

      <div class="form-section">
        <h3 class="section-title">
          复测备注
          <span class="optional">(选填)</span>
        </h3>
        <textarea
          v-model="formData.retest_notes"
          class="form-textarea"
          placeholder="请输入复测备注信息..."
          rows="4"
        ></textarea>
      </div>

      <div class="form-section">
        <h3 class="section-title">
          现场照片
          <span class="optional">(选填)</span>
        </h3>
        <div class="photo-upload-area">
          <div v-for="(photo, index) in photos" :key="index" class="photo-item">
            <img :src="photo.url" class="photo-preview" />
            <button class="photo-remove" @click="removePhoto(index)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <button v-if="photos.length < 9" class="photo-add" @click="triggerPhotoInput">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
            <span>拍照/上传</span>
          </button>
        </div>
        <input
          ref="photoInput"
          type="file"
          accept="image/*"
          capture="environment"
          multiple
          class="hidden-input"
          @change="onPhotoSelected"
        />
      </div>

      <div class="form-section">
        <h3 class="section-title">
          语音备注
          <span class="optional">(选填)</span>
        </h3>
        <div class="voice-record-area">
          <button
            class="record-btn"
            :class="{ recording: isRecording }"
            @mousedown="startRecording"
            @touchstart.prevent="startRecording"
            @mouseup="stopRecording"
            @touchend.prevent="stopRecording"
            @mouseleave="stopRecording"
          >
            <div class="record-icon">
              <svg v-if="!isRecording" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                <line x1="12" y1="19" x2="12" y2="23"></line>
                <line x1="8" y1="23" x2="16" y2="23"></line>
              </svg>
              <svg v-else width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2"></rect>
              </svg>
            </div>
            <span class="record-text">
              {{ isRecording ? `松开结束 ${formatTime(recordDuration)}` : '按住说话' }}
            </span>
          </button>

          <div v-if="voiceNotes.length > 0" class="voice-list">
            <div v-for="(voice, index) in voiceNotes" :key="index" class="voice-item">
              <button class="play-btn" @click="playVoice(voice)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
              </button>
              <div class="voice-waveform">
                <span v-for="i in 20" :key="i" class="wave-bar" :style="{ height: getWaveHeight(i, voice) }"></span>
              </div>
              <span class="voice-duration">{{ formatTime(voice.duration) }}</span>
              <button class="voice-remove" @click="removeVoice(index)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="form-section">
        <label class="checkbox-item">
          <input v-model="formData.auto_repredict" type="checkbox" class="checkbox" />
          <span class="checkbox-label">自动再预测并对比结果</span>
        </label>
      </div>
    </div>

    <div class="form-footer">
      <button class="submit-btn" :disabled="submitting || !canSubmit" @click="handleSubmit">
        <span v-if="!submitting">提交复测</span>
        <span v-else class="loading-text">
          <span class="spinner"></span>
          提交中...
        </span>
      </button>
    </div>

    <div v-if="showSuccess" class="success-modal" @click="closeSuccess">
      <div class="success-content" @click.stop>
        <div class="success-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        </div>
        <h3 class="success-title">提交成功</h3>
        <p class="success-desc">复测记录已保存</p>
        <button class="success-btn" @click="goBack">返回工单详情</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchWorkOrderDetail, createRetestRecord, uploadFile } from '@/api'
import { useOfflineStore } from '@/stores/offline'
import { useUserStore } from '@/stores/user'
import type { WorkOrder } from '@/types'

const route = useRoute()
const router = useRouter()
const offlineStore = useOfflineStore()
const userStore = useUserStore()

const workOrder = ref<WorkOrder | null>(null)
const submitting = ref(false)
const showSuccess = ref(false)

const formData = reactive({
  retest_result: 'pending' as 'pass' | 'fail' | 'pending',
  measured_value: null as number | null,
  retest_notes: '',
  auto_repredict: true
})

const resultOptions = [
  { value: 'pass', label: '通过', icon: '✓' },
  { value: 'pending', label: '待确认', icon: '?' },
  { value: 'fail', label: '不通过', icon: '✗' }
]

const photos = ref<{ url: string; file?: File }[]>([])
const photoInput = ref<HTMLInputElement | null>(null)

const voiceNotes = ref<{ url: string; file?: File; duration: number; waveform: number[] }[]>([])
const isRecording = ref(false)
const recordDuration = ref(0)
let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let recordTimer: ReturnType<typeof setInterval> | null = null
let audioContext: AudioContext | null = null
let analyser: AnalyserNode | null = null
let waveformData: number[] = []

const workOrderId = computed(() => Number(route.params.id))

const canSubmit = computed(() => {
  return formData.retest_result !== 'pending'
})

async function loadWorkOrder() {
  try {
    workOrder.value = await fetchWorkOrderDetail(workOrderId.value)
  } catch (e) {
    console.error('加载工单失败:', e)
  }
}

function triggerPhotoInput() {
  photoInput.value?.click()
}

function onPhotoSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const files = input.files
  if (!files) return

  Array.from(files).forEach(file => {
    if (photos.value.length >= 9) return
    const url = URL.createObjectURL(file)
    photos.value.push({ url, file })
  })

  input.value = ''
}

function removePhoto(index: number) {
  const photo = photos.value[index]
  if (photo.url.startsWith('blob:')) {
    URL.revokeObjectURL(photo.url)
  }
  photos.value.splice(index, 1)
}

async function startRecording() {
  if (isRecording.value) return

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []
    waveformData = []
    recordDuration.value = 0

    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    const source = audioContext.createMediaStreamSource(stream)
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)

    mediaRecorder.ondataavailable = (e) => {
      audioChunks.push(e.data)
    }

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      const audioUrl = URL.createObjectURL(audioBlob)
      const audioFile = new File([audioBlob], `voice_${Date.now()}.webm`, { type: 'audio/webm' })

      const waveform = Array.from({ length: 20 }, (_, i) => {
        const start = Math.floor((i / 20) * waveformData.length)
        const end = Math.floor(((i + 1) / 20) * waveformData.length)
        const slice = waveformData.slice(start, end)
        return slice.length > 0 ? Math.max(...slice) / 255 : 0
      })

      voiceNotes.value.push({
        url: audioUrl,
        file: audioFile,
        duration: recordDuration.value,
        waveform
      })

      stream.getTracks().forEach(track => track.stop())
      audioContext?.close()
      audioContext = null
      analyser = null
    }

    mediaRecorder.start()
    isRecording.value = true

    recordTimer = setInterval(() => {
      recordDuration.value++
      if (analyser) {
        const dataArray = new Uint8Array(analyser.frequencyBinCount)
        analyser.getByteFrequencyData(dataArray)
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
        waveformData.push(avg)
      }
    }, 1000)
  } catch (e) {
    console.error('录音失败:', e)
    alert('无法访问麦克风，请检查权限设置')
  }
}

function stopRecording() {
  if (!isRecording.value || !mediaRecorder) return

  if (recordTimer) {
    clearInterval(recordTimer)
    recordTimer = null
  }

  mediaRecorder.stop()
  isRecording.value = false
}

function playVoice(voice: { url: string }) {
  const audio = new Audio(voice.url)
  audio.play()
}

function removeVoice(index: number) {
  const voice = voiceNotes.value[index]
  if (voice.url.startsWith('blob:')) {
    URL.revokeObjectURL(voice.url)
  }
  voiceNotes.value.splice(index, 1)
}

function getWaveHeight(i: number, voice: { waveform: number[] }): string {
  const height = voice.waveform[i - 1] || 0.3
  return `${Math.max(10, height * 40)}px`
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${String(secs).padStart(2, '0')}`
}

async function handleSubmit() {
  if (!canSubmit.value || submitting.value) return

  submitting.value = true

  try {
    const photoUrls: string[] = []
    for (const photo of photos.value) {
      if (photo.file) {
        try {
          const result = await uploadFile(photo.file, 'photo')
          photoUrls.push(result.url)
        } catch (e) {
          console.error('上传照片失败:', e)
        }
      } else if (photo.url) {
        photoUrls.push(photo.url)
      }
    }

    const voiceUrls: string[] = []
    for (const voice of voiceNotes.value) {
      if (voice.file) {
        try {
          const result = await uploadFile(voice.file, 'voice')
          voiceUrls.push(result.url)
        } catch (e) {
          console.error('上传语音失败:', e)
        }
      }
    }

    const retestData = {
      work_order_id: workOrderId.value,
      retest_result: formData.retest_result,
      measured_value: formData.measured_value,
      retest_notes: formData.retest_notes,
      photos: photoUrls,
      auto_repredict: formData.auto_repredict,
      retester_id: userStore.userInfo?.id,
      retester_name: userStore.userInfo?.name,
      extra_info: {
        voice_notes: voiceUrls
      }
    }

    if (offlineStore.isOnline) {
      await createRetestRecord(retestData)
    } else {
      offlineStore.addToQueue('retest', retestData)
    }

    showSuccess.value = true
  } catch (e: any) {
    console.error('提交失败:', e)
    alert(e.response?.data?.detail || '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

function closeSuccess() {
  showSuccess.value = false
}

function goBack() {
  router.back()
}

function priorityText(priority: string): string {
  const map: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高',
    urgent: '紧急'
  }
  return map[priority] || priority
}

function getRiskClass(riskScore?: number): string {
  if (!riskScore) return 'risk-normal'
  if (riskScore >= 70) return 'risk-critical'
  if (riskScore >= 40) return 'risk-warning'
  return 'risk-normal'
}

onMounted(() => {
  loadWorkOrder()
})

onUnmounted(() => {
  if (recordTimer) {
    clearInterval(recordTimer)
  }
  photos.value.forEach(p => {
    if (p.url.startsWith('blob:')) URL.revokeObjectURL(p.url)
  })
  voiceNotes.value.forEach(v => {
    if (v.url.startsWith('blob:')) URL.revokeObjectURL(v.url)
  })
})
</script>

<style scoped>
.retest-form-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.form-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  padding-bottom: 100px;
  -webkit-overflow-scrolling: touch;
}

.workorder-info {
  padding: 16px;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  margin-bottom: 16px;
}

.info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.order-no {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: monospace;
}

.priority-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.priority-urgent {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.priority-high {
  background: rgba(249, 115, 22, 0.15);
  color: #fb923c;
}

.priority-medium {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.priority-low {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.workorder-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.info-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.info-value {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.risk-normal { color: #4ade80; }
.risk-warning { color: #fbbf24; }
.risk-critical { color: #ef4444; }

.form-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.optional {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-tertiary);
}

.result-options {
  display: flex;
  gap: 10px;
}

.result-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  background: rgba(30, 41, 59, 0.6);
  border: 2px solid var(--border-light);
  border-radius: 12px;
  transition: all 0.2s;
}

.result-option.active {
  border-color: var(--primary-color);
  background: rgba(59, 130, 246, 0.1);
}

.result-icon {
  font-size: 24px;
  font-weight: 700;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(100, 116, 139, 0.2);
}

.result-option.active .icon-pass {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.result-option.active .icon-fail {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
}

.result-option.active .icon-pending {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
}

.result-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.result-option.active .result-label {
  color: var(--text-primary);
}

.input-group {
  position: relative;
  display: flex;
  align-items: center;
}

.form-input {
  width: 100%;
  height: 48px;
  padding: 0 60px 0 16px;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 15px;
  outline: none;
  transition: all 0.2s;
}

.form-input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.input-suffix {
  position: absolute;
  right: 16px;
  color: var(--text-tertiary);
  font-size: 14px;
}

.form-textarea {
  width: 100%;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.6;
  outline: none;
  resize: none;
  transition: all 0.2s;
}

.form-textarea:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.form-textarea::placeholder {
  color: var(--text-tertiary);
}

.photo-upload-area {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.photo-item {
  position: relative;
  width: calc(33.333% - 7px);
  aspect-ratio: 1;
}

.photo-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--border-light);
}

.photo-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(239, 68, 68, 0.9);
  color: white;
  border-radius: 50%;
  font-size: 12px;
}

.photo-add {
  width: calc(33.333% - 7px);
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: rgba(30, 41, 59, 0.6);
  border: 2px dashed var(--border-light);
  border-radius: 10px;
  color: var(--text-tertiary);
  transition: all 0.2s;
}

.photo-add:active {
  border-color: var(--primary-color);
  color: var(--primary-light);
}

.photo-add span {
  font-size: 11px;
}

.hidden-input {
  display: none;
}

.voice-record-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.record-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  background: rgba(30, 41, 59, 0.6);
  border: 2px solid var(--border-light);
  border-radius: 16px;
  color: var(--text-secondary);
  transition: all 0.2s;
  user-select: none;
  -webkit-user-select: none;
}

.record-btn.recording {
  border-color: var(--danger-color);
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
}

.record-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.15);
  border-radius: 50%;
  color: var(--primary-light);
}

.record-btn.recording .record-icon {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.record-text {
  font-size: 14px;
  font-weight: 500;
}

.voice-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.voice-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid var(--border-light);
  border-radius: 10px;
}

.play-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  flex-shrink: 0;
}

.voice-waveform {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 2px;
  height: 24px;
}

.wave-bar {
  flex: 1;
  background: var(--primary-color);
  border-radius: 2px;
  min-height: 4px;
  opacity: 0.6;
}

.voice-duration {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: monospace;
  flex-shrink: 0;
  width: 40px;
  text-align: right;
}

.voice-remove {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.checkbox {
  width: 20px;
  height: 20px;
  accent-color: var(--primary-color);
}

.checkbox-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.form-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  padding-bottom: calc(12px + var(--safe-area-bottom));
  background: rgba(15, 23, 42, 0.95);
  border-top: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
}

.submit-btn {
  width: 100%;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.submit-btn:active:not(:disabled) {
  transform: scale(0.98);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.success-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.success-content {
  width: 280px;
  padding: 32px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  text-align: center;
}

.success-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border-radius: 50%;
}

.success-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.success-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.success-btn {
  width: 100%;
  height: 44px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
}
</style>
