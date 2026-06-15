<template>
  <div class="federated-learning">
    <div class="fl-header">
      <div class="fl-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
          <path d="M2 17l10 5 10-5"></path>
          <path d="M2 12l10 5 10-5"></path>
          <circle cx="12" cy="12" r="3"></circle>
        </svg>
        <h2>联邦学习管理</h2>
        <span class="subtitle">跨厂区模型协作平台</span>
      </div>
      <div class="header-actions">
        <button class="refresh-btn" @click="refreshAll">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <div class="fl-content">
      <div class="fl-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="fl-tab"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path :d="tab.icon" />
          </svg>
          {{ tab.name }}
        </button>
      </div>

      <div class="tab-content">
        <div v-if="activeTab === 'overview'" class="overview-panel">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon clients">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ serverStatus?.registered_clients || 0 }}</div>
                <div class="stat-label">注册客户端</div>
              </div>
              <div class="stat-sub">
                <span class="active-dot"></span>
                活跃: {{ serverStatus?.active_clients || 0 }}
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-icon rounds">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ serverStatus?.total_rounds || 0 }}</div>
                <div class="stat-label">总轮次数</div>
              </div>
              <div class="stat-sub success">
                完成: {{ serverStatus?.completed_rounds || 0 }}
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-icon models">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ serverStatus?.managed_models?.length || 0 }}</div>
                <div class="stat-label">管理模型</div>
              </div>
              <div class="stat-sub">
                聚合策略: {{ aggregationStrategyName }}
              </div>
            </div>

            <div class="stat-card">
              <div class="stat-icon privacy">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
              </div>
              <div class="stat-info">
                <div class="stat-value">DP + SecAgg</div>
                <div class="stat-label">隐私保护</div>
              </div>
              <div class="stat-sub">
                差分隐私 / 安全聚合可选
              </div>
            </div>
          </div>

          <div class="current-round-section" v-if="serverStatus?.current_round">
            <div class="section-header">
              <h3>进行中的轮次</h3>
              <span
                class="status-badge"
                :style="{ backgroundColor: roundStatusColor + '20', color: roundStatusColor, borderColor: roundStatusColor + '40' }"
              >
                {{ roundStatusName }}
              </span>
            </div>
            <div class="round-info">
              <div class="round-item">
                <span class="round-label">轮次ID</span>
                <span class="round-value">#{{ serverStatus.current_round.round_id }}</span>
              </div>
              <div class="round-item">
                <span class="round-label">模型</span>
                <span class="round-value">{{ serverStatus.current_round.model_type }} / {{ serverStatus.current_round.node_id }}</span>
              </div>
              <div class="round-item">
                <span class="round-label">开始时间</span>
                <span class="round-value">{{ formatTime(serverStatus.current_round.start_time) }}</span>
              </div>
              <div class="round-item">
                <span class="round-label">已接收更新</span>
                <span class="round-value">
                  {{ serverStatus.current_round.received_updates }} / {{ serverStatus.current_round.expected_clients.length }}
                </span>
              </div>
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: roundProgress + '%' }"
              ></div>
            </div>
          </div>

          <div class="two-level-arch-section">
            <div class="section-header">
              <h3>两层架构说明</h3>
            </div>
            <div class="arch-diagram">
              <div class="arch-layer global">
                <div class="layer-title">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <circle cx="12" cy="12" r="4"></circle>
                  </svg>
                  全局模型层
                </div>
                <div class="layer-desc">
                  由中心服务器聚合所有厂区数据训练得到，反映整体分布规律
                </div>
                <div class="layer-features">
                  <span class="feature-tag">FedAvg 聚合</span>
                  <span class="feature-tag">多厂区协同</span>
                  <span class="feature-tag">定期更新</span>
                </div>
              </div>
              <div class="arch-arrow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <polyline points="19 12 12 19 5 12"></polyline>
                </svg>
                <span>下发 &amp; 上传更新</span>
              </div>
              <div class="arch-layer local">
                <div class="layer-title">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                    <path d="M2 17l10 5 10-5"></path>
                  </svg>
                  本地微调层
                </div>
                <div class="layer-desc">
                  各厂区在全局模型基础上，使用本地数据微调，适应厂区特定分布
                </div>
                <div class="layer-features">
                  <span class="feature-tag">冻结底层</span>
                  <span class="feature-tag">只训练头部</span>
                  <span class="feature-tag">快速适配</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'clients'" class="clients-panel">
          <div class="panel-header">
            <h3>客户端管理</h3>
            <button class="btn btn-primary" @click="showRegisterModal = true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              注册客户端
            </button>
          </div>

          <div class="clients-grid">
            <div
              v-for="client in mockClients"
              :key="client.client_id"
              class="client-card"
              @click="selectClient(client.client_id)"
            >
              <div class="client-header">
                <div class="client-avatar" :class="{ active: client.is_active }">
                  {{ client.factory_name?.charAt(0) || client.client_id.charAt(0) }}
                </div>
                <div class="client-info">
                  <div class="client-name">{{ client.factory_name || client.client_id }}</div>
                  <div class="client-id">{{ client.client_id }}</div>
                </div>
                <span
                  class="status-dot-large"
                  :class="{ active: client.is_active }"
                ></span>
              </div>
              <div class="client-stats">
                <div class="client-stat">
                  <span class="stat-num">{{ client.rounds_participated }}</span>
                  <span class="stat-label">参与轮次</span>
                </div>
                <div class="client-stat">
                  <span class="stat-num">{{ formatNumber(client.total_samples) }}</span>
                  <span class="stat-label">总样本数</span>
                </div>
              </div>
              <div class="client-footer">
                <span class="location-tag" v-if="client.location">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                    <circle cx="12" cy="10" r="3"></circle>
                  </svg>
                  {{ client.location }}
                </span>
                <span class="last-seen">
                  最后活跃: {{ formatRelativeTime(client.last_seen) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'rounds'" class="rounds-panel">
          <div class="panel-header">
            <h3>轮次管理</h3>
            <div class="header-actions">
              <button class="btn btn-primary" @click="showStartRoundModal = true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
                开始新轮次
              </button>
              <button
                class="btn btn-success"
                @click="handleAggregate"
                :disabled="!serverStatus?.current_round"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2v6"></path>
                  <path d="M12 22v-6"></path>
                  <path d="M4.93 4.93l4.24 4.24"></path>
                  <path d="M14.83 14.83l4.24 4.24"></path>
                  <path d="M2 12h6"></path>
                  <path d="M16 12h6"></path>
                  <path d="M4.93 19.07l4.24-4.24"></path>
                  <path d="M14.83 9.17l4.24-4.24"></path>
                </svg>
                聚合并更新
              </button>
            </div>
          </div>

          <div class="round-form" v-if="showStartRoundModal">
            <div class="form-card">
              <div class="form-title">开始新联邦学习轮次</div>
              <div class="form-group">
                <label class="form-label">模型类型</label>
                <select v-model="startRoundForm.model_type" class="form-select">
                  <option value="bolt">螺栓模型</option>
                  <option value="flange">法兰面模型</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">节点ID</label>
                <input
                  v-model="startRoundForm.node_id"
                  type="text"
                  class="form-input"
                  placeholder="如: B001 或 F001"
                />
              </div>
              <div class="form-group">
                <label class="form-label">参与客户端（可选）</label>
                <div class="client-checkboxes">
                  <label
                    v-for="client in mockClients"
                    :key="client.client_id"
                    class="client-checkbox"
                  >
                    <input
                      type="checkbox"
                      :value="client.client_id"
                      v-model="startRoundForm.expected_clients"
                    />
                    <span>{{ client.factory_name || client.client_id }}</span>
                  </label>
                </div>
              </div>
              <div class="form-actions">
                <button class="btn btn-secondary" @click="showStartRoundModal = false">
                  取消
                </button>
                <button class="btn btn-primary" @click="handleStartRound">
                  开始轮次
                </button>
              </div>
            </div>
          </div>

          <div class="rounds-list">
            <div
              v-for="round in mockRounds"
              :key="round.round_id"
              class="round-item"
            >
              <div class="round-header">
                <div class="round-id">
                  <span class="round-num">轮次 #{{ round.round_id }}</span>
                  <span
                    class="status-badge small"
                    :style="{
                      backgroundColor: getRoundStatusColor(round.status) + '20',
                      color: getRoundStatusColor(round.status),
                      borderColor: getRoundStatusColor(round.status) + '40'
                    }"
                  >
                    {{ getRoundStatusName(round.status) }}
                  </span>
                </div>
                <div class="round-model">
                  {{ round.model_type }} / {{ round.node_id }}
                </div>
              </div>
              <div class="round-details">
                <div class="detail-item">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                    <circle cx="9" cy="7" r="4"></circle>
                  </svg>
                  {{ round.received_updates }} 个客户端参与
                </div>
                <div class="detail-item">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2v6"></path>
                    <path d="M12 22v-6"></path>
                    <path d="M4.93 4.93l4.24 4.24"></path>
                    <path d="M14.83 14.83l4.24 4.24"></path>
                    <path d="M2 12h6"></path>
                    <path d="M16 12h6"></path>
                  </svg>
                  验证准确率: {{ round.accuracy }}%
                </div>
                <div class="detail-item">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                  用时: {{ round.duration }}
                </div>
              </div>
              <div class="round-time">
                {{ formatTime(round.start_time) }}
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'models'" class="models-panel">
          <div class="panel-header">
            <h3>全局模型历史</h3>
            <div class="model-selector">
              <select v-model="selectedModelType" class="form-select small">
                <option value="bolt">螺栓模型</option>
                <option value="flange">法兰面模型</option>
              </select>
              <input
                v-model="selectedNodeId"
                type="text"
                class="form-input small"
                placeholder="节点ID"
              />
              <button class="btn btn-secondary small" @click="loadModelHistory">
                查询
              </button>
            </div>
          </div>

          <div class="model-chart" v-if="modelHistory">
            <div class="chart-title">验证准确率趋势</div>
            <div class="chart-placeholder">
              <div class="chart-bars">
                <div
                  v-for="ver in modelHistory.history.slice().reverse()"
                  :key="ver.version"
                  class="chart-bar-wrapper"
                >
                  <div
                    class="chart-bar"
                    :style="{ height: (ver.metrics.avg_val_acc * 100) + '%' }"
                  ></div>
                  <div class="chart-label">v{{ ver.version }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="versions-list">
            <div class="version-header">
              <span class="col-version">版本</span>
              <span class="col-round">轮次</span>
              <span class="col-clients">客户端数</span>
              <span class="col-samples">总样本</span>
              <span class="col-accuracy">准确率</span>
              <span class="col-time">创建时间</span>
            </div>
            <div
              v-for="ver in modelHistory?.history || []"
              :key="ver.version"
              class="version-row"
            >
              <span class="col-version">
                <span class="version-badge">v{{ ver.version }}</span>
              </span>
              <span class="col-round">#{{ ver.round_id }}</span>
              <span class="col-clients">{{ ver.num_clients }}</span>
              <span class="col-samples">{{ formatNumber(ver.metrics.total_samples || 0) }}</span>
              <span class="col-accuracy">
                <span class="accuracy-value">
                  {{ ((ver.metrics.avg_val_acc || 0) * 100).toFixed(1) }}%
                </span>
              </span>
              <span class="col-time">{{ formatTime(ver.created_at) }}</span>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'privacy'" class="privacy-panel">
          <div class="panel-header">
            <h3>隐私保护配置</h3>
          </div>

          <div class="privacy-options">
            <div
              v-for="option in privacyOptions"
              :key="option.id"
              class="privacy-card"
              :class="{ selected: selectedPrivacy === option.id }"
              @click="selectedPrivacy = option.id"
            >
              <div class="privacy-icon" :class="option.id">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path :d="option.icon" />
                </svg>
              </div>
              <div class="privacy-info">
                <div class="privacy-name">{{ option.name }}</div>
                <div class="privacy-desc">{{ option.description }}</div>
              </div>
              <div class="privacy-check">
                <svg v-if="selectedPrivacy === option.id" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </div>
            </div>
          </div>

          <div class="privacy-config" v-if="selectedPrivacy === 'dp'">
            <div class="config-section">
              <h4>差分隐私参数</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>隐私预算 (ε)</label>
                  <input type="number" v-model.number="dpConfig.epsilon" step="0.1" min="0.1" class="form-input" />
                  <div class="config-hint">ε越小，隐私保护越强，模型精度损失越大</div>
                </div>
                <div class="config-item">
                  <label>失败概率 (δ)</label>
                  <input type="number" v-model.number="dpConfig.delta" step="0.00001" class="form-input" />
                </div>
                <div class="config-item">
                  <label>噪声缩放</label>
                  <input type="number" v-model.number="dpConfig.noise_scale" step="0.01" min="0" class="form-input" />
                </div>
                <div class="config-item">
                  <label>梯度裁剪范数</label>
                  <input type="number" v-model.number="dpConfig.clip_norm" step="0.1" min="0.1" class="form-input" />
                </div>
              </div>
            </div>
          </div>

          <div class="privacy-config" v-if="selectedPrivacy === 'secagg'">
            <div class="config-section">
              <h4>安全聚合参数</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>参与方数量</label>
                  <input type="number" v-model.number="secAggConfig.num_parties" step="1" min="2" class="form-input" />
                </div>
                <div class="config-item">
                  <label>秘密共享阈值</label>
                  <input type="number" v-model.number="secAggConfig.secret_share_threshold" step="1" min="2" class="form-input" />
                  <div class="config-hint">至少需要多少方才能恢复聚合结果</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  fetchServerStatus,
  fetchClientStatus,
  fetchModelHistory,
  startRound,
  aggregateUpdates
} from '@/api/federated'
import {
  RoundStatusMap,
  RoundStatusColorMap,
  AggregationStrategyMap,
  PrivacyMechanismMap
} from '@/types'
import type {
  FederatedServerStatus,
  FederatedModelHistory,
  RoundStatus,
  PrivacyMechanism,
  AggregationStrategy
} from '@/types'

const activeTab = ref<'overview' | 'clients' | 'rounds' | 'models' | 'privacy'>('overview')

const tabs = [
  { id: 'overview', name: '总览', icon: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10' },
  { id: 'clients', name: '客户端', icon: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M9 7a4 4 0 1 1 8 0 4 4 0 0 1-8 0z M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75' },
  { id: 'rounds', name: '轮次管理', icon: 'M12 2v6 M12 22v-6 M4.93 4.93l4.24 4.24 M14.83 14.83l4.24 4.24 M2 12h6 M16 12h6 M4.93 19.07l4.24-4.24 M14.83 9.17l4.24-4.24' },
  { id: 'models', name: '模型历史', icon: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8' },
  { id: 'privacy', name: '隐私保护', icon: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z M12 12m-3 0a3 3 0 1 0 6 0 3 3 0 1 0 -6 0' }
] as const

const serverStatus = ref<FederatedServerStatus | null>(null)
const modelHistory = ref<FederatedModelHistory | null>(null)

const selectedClient = ref<string | null>(null)
const selectedModelType = ref('bolt')
const selectedNodeId = ref('B001')

const showRegisterModal = ref(false)
const showStartRoundModal = ref(false)

const startRoundForm = ref({
  model_type: 'bolt',
  node_id: 'B001',
  expected_clients: [] as string[]
})

const selectedPrivacy = ref<PrivacyMechanism>('none')

const dpConfig = ref({
  epsilon: 1.0,
  delta: 1e-5,
  noise_scale: 0.1,
  clip_norm: 1.0
})

const secAggConfig = ref({
  num_parties: 3,
  secret_share_threshold: 2
})

const privacyOptions = [
  {
    id: 'none' as PrivacyMechanism,
    name: '无保护',
    description: '明文传输模型更新，适用于可信环境',
    icon: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'
  },
  {
    id: 'dp' as PrivacyMechanism,
    name: '差分隐私 (DP)',
    description: '在梯度中加入噪声，保护单样本级隐私',
    icon: 'M12 2a10 10 0 1 0 10 10 10 10 0 0 0 -10-10zM10 10l4 4 M14 10l-4 4'
  },
  {
    id: 'secagg' as PrivacyMechanism,
    name: '安全聚合 (SecAgg)',
    description: '基于秘密共享，服务器无法看到单个客户端更新',
    icon: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z M12 12m-3 0a3 3 0 1 0 6 0 3 3 0 1 0 -6 0'
  },
  {
    id: 'combined' as PrivacyMechanism,
    name: '组合保护',
    description: '差分隐私 + 安全聚合，提供最强隐私保护',
    icon: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z'
  }
]

const mockClients = ref([
  {
    client_id: 'factory_001',
    factory_name: '北京一厂',
    location: '北京',
    registered_at: '2024-01-15T08:00:00Z',
    last_seen: new Date(Date.now() - 300000).toISOString(),
    rounds_participated: 12,
    total_samples: 15000,
    is_active: true,
    info: {}
  },
  {
    client_id: 'factory_002',
    factory_name: '上海二厂',
    location: '上海',
    registered_at: '2024-01-20T10:00:00Z',
    last_seen: new Date(Date.now() - 600000).toISOString(),
    rounds_participated: 10,
    total_samples: 12000,
    is_active: true,
    info: {}
  },
  {
    client_id: 'factory_003',
    factory_name: '广州三厂',
    location: '广州',
    registered_at: '2024-02-01T14:00:00Z',
    last_seen: new Date(Date.now() - 120000).toISOString(),
    rounds_participated: 8,
    total_samples: 8000,
    is_active: true,
    info: {}
  },
  {
    client_id: 'factory_004',
    factory_name: '深圳四厂',
    location: '深圳',
    registered_at: '2024-02-15T09:00:00Z',
    last_seen: new Date(Date.now() - 7200000).toISOString(),
    rounds_participated: 5,
    total_samples: 5000,
    is_active: false,
    info: {}
  },
  {
    client_id: 'factory_005',
    factory_name: '成都五厂',
    location: '成都',
    registered_at: '2024-03-01T11:00:00Z',
    last_seen: new Date(Date.now() - 180000).toISOString(),
    rounds_participated: 6,
    total_samples: 6500,
    is_active: true,
    info: {}
  }
])

const mockRounds = ref([
  { round_id: 12, model_type: 'bolt', node_id: 'B001', status: 'completed' as RoundStatus, received_updates: 5, accuracy: 92.3, duration: '12分30秒', start_time: '2024-06-10T08:00:00Z' },
  { round_id: 11, model_type: 'bolt', node_id: 'B001', status: 'completed' as RoundStatus, received_updates: 4, accuracy: 91.5, duration: '15分20秒', start_time: '2024-06-08T08:00:00Z' },
  { round_id: 10, model_type: 'bolt', node_id: 'B001', status: 'completed' as RoundStatus, received_updates: 5, accuracy: 90.8, duration: '11分45秒', start_time: '2024-06-05T08:00:00Z' },
  { round_id: 9, model_type: 'flange', node_id: 'F001', status: 'completed' as RoundStatus, received_updates: 3, accuracy: 88.2, duration: '18分10秒', start_time: '2024-06-03T08:00:00Z' },
  { round_id: 8, model_type: 'bolt', node_id: 'B001', status: 'failed' as RoundStatus, received_updates: 1, accuracy: 0, duration: '5分00秒', start_time: '2024-06-01T08:00:00Z' }
])

const aggregationStrategyName = computed(() => {
  const strategy = serverStatus.value?.aggregation_strategy as AggregationStrategy || 'weighted_avg'
  return AggregationStrategyMap[strategy] || strategy
})

const roundStatusName = computed(() => {
  const status = serverStatus.value?.current_round?.status
  if (!status) return '未知'
  return RoundStatusMap[status] || status
})

const roundStatusColor = computed(() => {
  const status = serverStatus.value?.current_round?.status
  if (!status) return '#64748b'
  return RoundStatusColorMap[status] || '#64748b'
})

const roundProgress = computed(() => {
  if (!serverStatus.value?.current_round) return 0
  const received = serverStatus.value.current_round.received_updates
  const total = serverStatus.value.current_round.expected_clients.length
  if (total === 0) return 0
  return (received / total) * 100
})

function formatTime(timeStr: string): string {
  const d = new Date(timeStr)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatRelativeTime(timeStr: string): string {
  const now = Date.now()
  const time = new Date(timeStr).getTime()
  const diff = now - time
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return Math.floor(diff / 86400000) + '天前'
}

function formatNumber(num: number): string {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
  return num.toString()
}

function getRoundStatusName(status: RoundStatus): string {
  return RoundStatusMap[status] || status
}

function getRoundStatusColor(status: RoundStatus): string {
  return RoundStatusColorMap[status] || '#64748b'
}

async function refreshAll() {
  await loadServerStatus()
  if (activeTab.value === 'models') {
    await loadModelHistory()
  }
}

async function loadServerStatus() {
  serverStatus.value = await fetchServerStatus()
}

async function loadModelHistory() {
  modelHistory.value = await fetchModelHistory(
    selectedModelType.value,
    selectedNodeId.value
  )
}

function selectClient(clientId: string) {
  selectedClient.value = clientId
}

async function handleStartRound() {
  const result = await startRound({
    model_type: startRoundForm.value.model_type,
    node_id: startRoundForm.value.node_id,
    expected_clients: startRoundForm.value.expected_clients.length > 0
      ? startRoundForm.value.expected_clients
      : undefined
  })
  
  if (result) {
    showStartRoundModal.value = false
    await loadServerStatus()
  }
}

async function handleAggregate() {
  if (!serverStatus.value?.current_round) return
  
  const result = await aggregateUpdates({
    model_type: serverStatus.value.current_round.model_type,
    node_id: serverStatus.value.current_round.node_id
  })
  
  if (result) {
    await loadServerStatus()
    await loadModelHistory()
  }
}

onMounted(() => {
  loadServerStatus()
  loadModelHistory()
})
</script>

<style scoped>
.federated-learning {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.5);
}

.fl-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(30, 41, 59, 0.6);
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  flex-shrink: 0;
}

.fl-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #60a5fa;
}

.fl-title h2 {
  font-size: 18px;
  font-weight: 600;
  color: #f1f5f9;
}

.fl-title .subtitle {
  font-size: 12px;
  color: #64748b;
  margin-left: 8px;
  padding-left: 12px;
  border-left: 1px solid rgba(100, 116, 139, 0.3);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #cbd5e1;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover {
  border-color: rgba(59, 130, 246, 0.6);
  color: #e2e8f0;
}

.fl-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 24px;
  gap: 16px;
}

.fl-tabs {
  display: flex;
  gap: 4px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  padding: 4px;
  flex-shrink: 0;
}

.fl-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.fl-tab:hover {
  color: #cbd5e1;
  background: rgba(71, 85, 105, 0.3);
}

.fl-tab.active {
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
}

.tab-content {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.tab-content::-webkit-scrollbar {
  width: 6px;
}

.tab-content::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.overview-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-icon.clients {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
}

.stat-icon.rounds {
  background: linear-gradient(135deg, #8b5cf6, #7c3aed);
}

.stat-icon.models {
  background: linear-gradient(135deg, #f97316, #ea580c);
}

.stat-icon.privacy {
  background: linear-gradient(135deg, #22c55e, #16a34a);
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.stat-sub {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-sub.success {
  color: #4ade80;
}

.active-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  display: inline-block;
}

.current-round-section,
.two-level-arch-section {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  padding: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: #f1f5f9;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid;
}

.status-badge.small {
  padding: 2px 8px;
  font-size: 11px;
}

.round-info {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.round-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.round-label {
  font-size: 12px;
  color: #64748b;
}

.round-value {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
}

.progress-bar {
  height: 8px;
  background: rgba(100, 116, 139, 0.2);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.arch-diagram {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.arch-layer {
  width: 100%;
  max-width: 500px;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  background: rgba(59, 130, 246, 0.05);
}

.arch-layer.local {
  border-color: rgba(139, 92, 246, 0.2);
  background: rgba(139, 92, 246, 0.05);
}

.layer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 8px;
}

.arch-layer.global .layer-title {
  color: #60a5fa;
}

.arch-layer.local .layer-title {
  color: #a78bfa;
}

.layer-desc {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 12px;
  line-height: 1.6;
}

.layer-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feature-tag {
  padding: 4px 10px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  font-size: 11px;
  color: #60a5fa;
}

.arch-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: #64748b;
  font-size: 11px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: #f1f5f9;
}

.btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
}

.btn-secondary {
  background: rgba(71, 85, 105, 0.5);
  color: #cbd5e1;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.btn-secondary:hover {
  background: rgba(71, 85, 105, 0.7);
}

.btn-success {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: white;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.35);
}

.btn-success:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.5);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn.small {
  padding: 6px 12px;
  font-size: 11px;
}

.clients-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.client-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.client-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.client-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.client-avatar {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background: #64748b;
}

.client-avatar.active {
  background: linear-gradient(135deg, #3b82f6, #6366f1);
}

.client-info {
  flex: 1;
  min-width: 0;
}

.client-name {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
}

.client-id {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.status-dot-large {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #64748b;
}

.status-dot-large.active {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
}

.client-stats {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  margin-bottom: 12px;
}

.client-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-num {
  font-size: 16px;
  font-weight: 600;
  color: #60a5fa;
}

.stat-label {
  font-size: 11px;
  color: #64748b;
}

.client-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #94a3b8;
}

.location-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 10px;
  color: #60a5fa;
}

.round-form {
  margin-bottom: 20px;
}

.form-card {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  padding: 20px;
}

.form-title {
  font-size: 15px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.form-select,
.form-input {
  width: 100%;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.form-select:focus,
.form-input:focus {
  border-color: rgba(59, 130, 246, 0.6);
}

.form-select.small,
.form-input.small {
  padding: 6px 10px;
  font-size: 12px;
}

.client-checkboxes {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  max-height: 120px;
  overflow: auto;
  padding: 8px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 6px;
}

.client-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #cbd5e1;
  cursor: pointer;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.rounds-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.round-item {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 10px;
  padding: 16px;
}

.round-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.round-id {
  display: flex;
  align-items: center;
  gap: 10px;
}

.round-num {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
}

.round-model {
  font-size: 12px;
  color: #64748b;
  font-family: monospace;
}

.round-details {
  display: flex;
  gap: 20px;
  margin-bottom: 8px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.round-time {
  font-size: 11px;
  color: #64748b;
}

.model-selector {
  display: flex;
  gap: 8px;
  align-items: center;
}

.model-chart {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.chart-title {
  font-size: 13px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 16px;
}

.chart-placeholder {
  height: 160px;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 140px;
  padding: 0 10px;
}

.chart-bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex: 1;
  height: 100%;
  justify-content: flex-end;
}

.chart-bar {
  width: 24px;
  background: linear-gradient(180deg, #3b82f6, #6366f1);
  border-radius: 4px 4px 0 0;
  transition: height 0.3s ease;
  min-height: 4px;
}

.chart-label {
  font-size: 10px;
  color: #64748b;
}

.versions-list {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  overflow: hidden;
}

.version-header,
.version-row {
  display: grid;
  grid-template-columns: 80px 80px 100px 120px 120px 1fr;
  gap: 12px;
  padding: 12px 16px;
  align-items: center;
}

.version-header {
  background: rgba(59, 130, 246, 0.1);
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.version-row {
  border-bottom: 1px solid rgba(59, 130, 246, 0.05);
  font-size: 13px;
  color: #cbd5e1;
}

.version-row:last-child {
  border-bottom: none;
}

.version-row:hover {
  background: rgba(59, 130, 246, 0.05);
}

.version-badge {
  display: inline-block;
  padding: 3px 8px;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: #60a5fa;
}

.accuracy-value {
  color: #4ade80;
  font-weight: 500;
}

.col-time {
  color: #64748b;
  font-size: 12px;
}

.privacy-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.privacy-card {
  background: rgba(30, 41, 59, 0.6);
  border: 2px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  gap: 16px;
  align-items: center;
}

.privacy-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
}

.privacy-card.selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.privacy-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.privacy-icon.none {
  background: linear-gradient(135deg, #64748b, #475569);
}

.privacy-icon.dp {
  background: linear-gradient(135deg, #3b82f6, #6366f1);
}

.privacy-icon.secagg {
  background: linear-gradient(135deg, #22c55e, #16a34a);
}

.privacy-icon.combined {
  background: linear-gradient(135deg, #f97316, #ef4444);
}

.privacy-info {
  flex: 1;
  min-width: 0;
}

.privacy-name {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 4px;
}

.privacy-desc {
  font-size: 11px;
  color: #94a3b8;
  line-height: 1.5;
}

.privacy-check {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
}

.privacy-config {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  padding: 20px;
}

.config-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 16px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.config-item label {
  font-size: 12px;
  color: #94a3b8;
}

.config-hint {
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
}
</style>