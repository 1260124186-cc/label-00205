<template>
  <div class="digital-twin-view">
    <div class="view-header">
      <div class="header-title">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polygon points="10 8 16 12 10 16 10 8"></polygon>
        </svg>
        <h2>3D数字孪生可视化</h2>
      </div>
      <div class="header-actions">
        <select v-model="selectedFlange" class="flange-select" @change="onFlangeChange">
          <option v-for="f in flangeOptions" :key="f.id" :value="f.id">
            {{ f.name }}
          </option>
        </select>
        <button class="export-btn" @click="showExportModal = true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          导出
        </button>
      </div>
    </div>

    <div class="view-content">
      <div class="viewer-section">
        <Flange3DViewer
          ref="viewerRef"
          :flange-id="selectedFlange"
          :bolt-data="currentBoltData"
          :bolt-count="currentBoltCount"
          :flange-params="flangeParams"
          :initial-mode="visualizationMode"
          @bolt-click="onBoltClick"
          @mode-change="onModeChange"
        />
      </div>

      <div class="sidebar-section">
        <div class="sidebar-card">
          <div class="card-header">
            <h3>法兰概览</h3>
          </div>
          <div class="card-content">
            <div class="stat-row">
              <span class="stat-label">法兰ID</span>
              <span class="stat-value">{{ selectedFlange }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">螺栓数量</span>
              <span class="stat-value">{{ currentBoltCount }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">整体健康度</span>
              <span class="stat-value hi-score" :class="getHiClass(overallHi)">
                {{ overallHi.toFixed(1) }}
              </span>
            </div>
            <div class="stat-row">
              <span class="stat-label">预警螺栓</span>
              <span class="stat-value warning">{{ warningBoltCount }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">危险螺栓</span>
              <span class="stat-value danger">{{ criticalBoltCount }}</span>
            </div>
          </div>
        </div>

        <div class="sidebar-card">
          <div class="card-header">
            <h3>显示模式</h3>
          </div>
          <div class="card-content">
            <div class="mode-options">
              <button
                v-for="mode in displayModes"
                :key="mode.value"
                :class="['mode-option', { active: visualizationMode === mode.value }]"
                @click="switchMode(mode.value)"
              >
                <span class="mode-icon">{{ mode.icon }}</span>
                <span class="mode-text">{{ mode.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <div class="sidebar-card">
          <div class="card-header">
            <h3>螺栓列表</h3>
            <span class="bolt-count-badge">{{ currentBoltCount }}</span>
          </div>
          <div class="card-content bolt-list-container">
            <div class="bolt-list">
              <div
                v-for="bolt in currentBoltData"
                :key="bolt.bolt_id"
                :class="['bolt-item', { selected: selectedBolt?.bolt_id === bolt.bolt_id }]"
                @click="selectBolt(bolt)"
              >
                <span
                  class="bolt-status-dot"
                  :style="{ background: getBoltColor(bolt) }"
                ></span>
                <span class="bolt-id">{{ bolt.bolt_id }}</span>
                <span class="bolt-hi">{{ bolt.hi_score?.toFixed(0) || '-' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Transition name="modal">
      <div v-if="showExportModal" class="modal-overlay" @click.self="showExportModal = false">
        <div class="modal-content">
          <div class="modal-header">
            <h3>导出3D场景</h3>
            <button class="modal-close" @click="showExportModal = false">×</button>
          </div>
          <div class="modal-body">
            <div class="export-formats">
              <div
                v-for="format in exportFormats"
                :key="format.value"
                class="format-card"
                @click="exportFormat = format.value"
              >
                <div :class="['format-icon', format.value]">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path :d="format.iconPath"></path>
                  </svg>
                </div>
                <div class="format-info">
                  <div class="format-name">{{ format.name }}</div>
                  <div class="format-desc">{{ format.description }}</div>
                </div>
                <div class="format-check" v-if="exportFormat === format.value">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </div>
              </div>
            </div>

            <div class="export-options">
              <div class="option-row">
                <label class="option-label">可视化模式</label>
                <select v-model="exportMode" class="option-select">
                  <option value="status">状态色</option>
                  <option value="hi">健康度HI</option>
                  <option value="risk">风险色</option>
                </select>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="showExportModal = false">取消</button>
            <button class="btn-confirm" @click="handleExport">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              导出
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import Flange3DViewer from './Flange3DViewer.vue';
import { colorMapper, type VisualizationMode, type BoltStatusData } from '../utils/colorMapper';

const viewerRef = ref<InstanceType<typeof Flange3DViewer> | null>(null);

const selectedFlange = ref('FL001');
const visualizationMode = ref<VisualizationMode>('status');
const selectedBolt = ref<BoltStatusData | null>(null);
const showExportModal = ref(false);
const exportFormat = ref('threejs');
const exportMode = ref<VisualizationMode>('status');

const flangeOptions = [
  { id: 'FL001', name: '100-A面法兰' },
  { id: 'FL002', name: '100-B面法兰' },
  { id: 'FL003', name: '96-地锚法兰' },
];

const displayModes = [
  { value: 'status' as const, label: '状态', icon: '●' },
  { value: 'hi' as const, label: '健康度', icon: '♥' },
  { value: 'risk' as const, label: '风险', icon: '⚠' },
];

const exportFormats = [
  {
    value: 'threejs',
    name: 'Three.js JSON',
    description: 'Three.js Object3D格式，可直接在Web中加载',
    iconPath: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  },
  {
    value: 'gltf',
    name: 'glTF 2.0',
    description: '标准glTF格式，支持大多数3D软件',
    iconPath: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z',
  },
  {
    value: 'unity',
    name: 'Unity 数据包',
    description: 'Unity专用数据包，含网格、材质和状态数据',
    iconPath: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  },
];

const flangeParams = {
  flange_outer_radius: 150,
  flange_inner_radius: 80,
  flange_thickness: 30,
  bolt_pcd_radius: 120,
  bolt_radius: 10,
  pipe_radius: 75,
  pipe_length: 100,
};

function generateMockBoltData(flangeId: string, count: number): BoltStatusData[] {
  const data: BoltStatusData[] = [];
  const statusWeights = [0.6, 0.2, 0.12, 0.05, 0.03];
  
  for (let i = 0; i < count; i++) {
    const rand = Math.random();
    let statusCode = 0;
    let cumulative = 0;
    for (let j = 0; j < statusWeights.length; j++) {
      cumulative += statusWeights[j];
      if (rand < cumulative) {
        statusCode = j;
        break;
      }
    }

    const hiScore = Math.max(0, Math.min(100, 95 - statusCode * 20 - Math.random() * 10));
    
    let riskLevel = 'low';
    if (statusCode >= 3) riskLevel = 'critical';
    else if (statusCode >= 2) riskLevel = 'high';
    else if (statusCode >= 1) riskLevel = 'medium';

    const statusNames = ['正常', '关注级预警', '检查级预警', '紧急级预警', '故障'];

    data.push({
      bolt_id: `B${(i + 1).toString().padStart(3, '0')}`,
      status_code: statusCode,
      status: statusNames[statusCode],
      hi_score: hiScore,
      hi_level: hiScore >= 90 ? 'excellent' : hiScore >= 70 ? 'good' : hiScore >= 50 ? 'fair' : hiScore >= 30 ? 'poor' : 'critical',
      risk_level: riskLevel,
      risk_score: 1 + statusCode * 2.2 + Math.random(),
      confidence: 0.75 + Math.random() * 0.25,
      diagnosis: statusCode === 0 ? '状态正常，运行稳定' : 
                 statusCode === 1 ? '预紧力略有波动，建议关注' :
                 statusCode === 2 ? '预紧力下降明显，建议近期检查' :
                 statusCode === 3 ? '预紧力严重不足，存在安全隐患' :
                 '螺栓已失效，需立即更换',
      recommendations: statusCode >= 2 ? ['安排检修', '紧固或更换螺栓', '分析劣化原因'] : ['继续监测'],
    });
  }

  return data;
}

const boltDataMap = ref<Record<string, BoltStatusData[]>>({});

function ensureBoltData(flangeId: string) {
  if (!boltDataMap.value[flangeId]) {
    const counts: Record<string, number> = {
      'FL001': 12,
      'FL002': 16,
      'FL003': 8,
    };
    const count = counts[flangeId] || 8;
    boltDataMap.value[flangeId] = generateMockBoltData(flangeId, count);
  }
}

const currentBoltData = computed(() => {
  ensureBoltData(selectedFlange.value);
  return boltDataMap.value[selectedFlange.value] || [];
});

const currentBoltCount = computed(() => currentBoltData.value.length);

const overallHi = computed(() => {
  if (currentBoltData.value.length === 0) return 100;
  const scores = currentBoltData.value.map((b) => b.hi_score || 100);
  const worst = Math.min(...scores);
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  return worst * 0.5 + avg * 0.5;
});

const warningBoltCount = computed(() => {
  return currentBoltData.value.filter((b) => (b.status_code || 0) === 1 || (b.status_code || 0) === 2).length;
});

const criticalBoltCount = computed(() => {
  return currentBoltData.value.filter((b) => (b.status_code || 0) >= 3).length;
});

function getHiClass(hi: number): string {
  if (hi >= 90) return 'excellent';
  if (hi >= 70) return 'good';
  if (hi >= 50) return 'fair';
  if (hi >= 30) return 'poor';
  return 'critical';
}

function getBoltColor(bolt: BoltStatusData): string {
  const color = colorMapper.getColor(visualizationMode.value, bolt);
  return colorMapper.rgbToHex(color);
}

function onFlangeChange() {
  ensureBoltData(selectedFlange.value);
  selectedBolt.value = null;
}

function switchMode(mode: VisualizationMode) {
  visualizationMode.value = mode;
  if (viewerRef.value) {
    viewerRef.value.switchMode(mode);
  }
}

function onModeChange(mode: VisualizationMode) {
  visualizationMode.value = mode;
}

function onBoltClick(bolt: BoltStatusData) {
  selectedBolt.value = bolt;
}

function selectBolt(bolt: BoltStatusData) {
  selectedBolt.value = bolt;
}

function handleExport() {
  console.log('导出格式:', exportFormat.value);
  console.log('可视化模式:', exportMode.value);
  console.log('法兰:', selectedFlange.value);
  showExportModal.value = false;
}

onMounted(() => {
  ensureBoltData(selectedFlange.value);
});
</script>

<style scoped>
.digital-twin-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(15, 23, 42, 0.85);
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  flex-shrink: 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-title svg {
  color: #60a5fa;
}

.header-title h2 {
  font-size: 18px;
  font-weight: 600;
  color: #f1f5f9;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.flange-select {
  padding: 8px 14px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.flange-select:hover {
  border-color: rgba(59, 130, 246, 0.6);
}

.export-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.export-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.view-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
  padding: 16px;
  min-height: 0;
  overflow: hidden;
}

.viewer-section {
  min-width: 0;
  min-height: 0;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: auto;
}

.sidebar-section::-webkit-scrollbar {
  width: 6px;
}

.sidebar-section::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.sidebar-card {
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(30, 41, 59, 0.6);
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
}

.card-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.bolt-count-badge {
  padding: 2px 8px;
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.card-content {
  padding: 16px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 13px;
}

.stat-label {
  color: #94a3b8;
}

.stat-value {
  color: #e2e8f0;
  font-weight: 500;
}

.stat-value.hi-score.excellent { color: #4ade80; }
.stat-value.hi-score.good { color: #22d3ee; }
.stat-value.hi-score.fair { color: #facc15; }
.stat-value.hi-score.poor { color: #fb923c; }
.stat-value.hi-score.critical { color: #f87171; }

.stat-value.warning {
  color: #facc15;
}

.stat-value.danger {
  color: #f87171;
}

.mode-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mode-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(71, 85, 105, 0.5);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  color: #cbd5e1;
  font-size: 13px;
}

.mode-option:hover {
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(30, 64, 175, 0.2);
}

.mode-option.active {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.6);
  color: #60a5fa;
}

.mode-icon {
  font-size: 16px;
  width: 24px;
  text-align: center;
}

.bolt-list-container {
  max-height: 300px;
  overflow: auto;
}

.bolt-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bolt-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.bolt-item:hover {
  background: rgba(30, 41, 59, 0.6);
}

.bolt-item.selected {
  background: rgba(59, 130, 246, 0.2);
}

.bolt-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.bolt-id {
  flex: 1;
  font-size: 12px;
  color: #cbd5e1;
}

.bolt-hi {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
}

.modal-overlay {
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
  backdrop-filter: blur(4px);
}

.modal-content {
  width: 520px;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
  margin: 0;
}

.modal-close {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.modal-close:hover {
  background: rgba(71, 85, 105, 0.5);
  color: #e2e8f0;
}

.modal-body {
  padding: 20px 24px;
}

.export-formats {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.format-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(71, 85, 105, 0.5);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.format-card:hover {
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(30, 64, 175, 0.15);
}

.format-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  color: #60a5fa;
  flex-shrink: 0;
}

.format-info {
  flex: 1;
  min-width: 0;
}

.format-name {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 2px;
}

.format-desc {
  font-size: 12px;
  color: #94a3b8;
}

.format-check {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4ade80;
  flex-shrink: 0;
}

.export-options {
  padding-top: 16px;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
}

.option-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.option-label {
  font-size: 13px;
  color: #94a3b8;
}

.option-select {
  padding: 6px 12px;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 4px;
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
  outline: none;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid rgba(59, 130, 246, 0.15);
}

.btn-cancel {
  padding: 8px 18px;
  background: transparent;
  border: 1px solid rgba(71, 85, 105, 0.6);
  border-radius: 6px;
  color: #cbd5e1;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: rgba(71, 85, 105, 0.4);
}

.btn-confirm {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.95) translateY(10px);
}
</style>
