<template>
  <div class="config-center">
    <div class="config-header">
      <div class="config-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
        <h2>配置中心</h2>
      </div>
      <div class="header-actions">
        <span v-if="lastUpdated" class="last-updated">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          最近更新: {{ formatTime(lastUpdated) }}
        </span>
        <button class="refresh-btn" @click="loadConfig" :disabled="loading">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <div class="config-tabs">
      <button
        v-for="(tab, idx) in tabs"
        :key="idx"
        class="config-tab"
        :class="{ active: activeTab === idx }"
        @click="activeTab = idx"
      >
        <span class="tab-icon" v-html="tab.icon"></span>
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <div class="config-content">
      <div v-if="activeTab === 0" class="tab-panel strategy-panel">
        <div class="section-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          预警策略配置
          <span v-if="effectiveStrategy" class="version-badge">v{{ effectiveStrategy.version }}</span>
        </div>

        <div class="scope-selector">
          <div class="scope-row">
            <label class="scope-label">策略作用域</label>
            <div class="scope-options">
              <button
                v-for="s in scopeOptions"
                :key="s.value"
                class="scope-btn"
                :class="{ active: strategyScope === s.value }"
                @click="onScopeChange(s.value)"
              >
                <span class="scope-dot" :style="{ background: s.color }"></span>
                {{ s.label }}
              </button>
            </div>
          </div>
          <div v-if="strategyScope !== 'global'" class="scope-row">
            <label class="scope-label">{{ strategyScope === 'production_line' ? '产线' : (strategyScope === 'bolt' ? '螺栓' : '法兰面') }} ID</label>
            <input
              v-model="strategyNodeId"
              type="text"
              class="form-input node-id-input"
              :placeholder="strategyScope === 'production_line' ? '输入产线编号' : (strategyScope === 'bolt' ? '输入螺栓编号' : '输入法兰面编号')"
            />
          </div>
        </div>

        <div v-if="effectiveStrategy" class="effective-info">
          <div class="info-chip" :style="{ borderColor: getScopeColor(effectiveStrategy.scope) }">
            <span class="chip-dot" :style="{ background: getScopeColor(effectiveStrategy.scope) }"></span>
            当前生效: {{ getScopeLabel(effectiveStrategy.scope) }}
            <template v-if="effectiveStrategy.node_id"> / {{ effectiveStrategy.node_id }}</template>
            <span class="chip-sep">|</span>
            {{ effectiveStrategy.strategy_type === 1 ? '应报尽报' : '精准报警' }}
            <span class="chip-sep">|</span>
            置信度 {{ effectiveStrategy.confidence_threshold }}
          </div>
        </div>

        <div class="strategy-selector">
          <div
            v-for="strategy in strategyOptions"
            :key="strategy.type"
            class="strategy-card"
            :class="{ active: strategyForm.strategy_type === strategy.type }"
            @click="strategyForm.strategy_type = strategy.type"
          >
            <div class="strategy-badge" :style="{ background: strategy.color }">
              <span v-html="strategy.icon"></span>
            </div>
            <div class="strategy-info">
              <div class="strategy-name">{{ strategy.name }}</div>
              <div class="strategy-desc">{{ strategy.desc }}</div>
            </div>
            <div class="strategy-check" v-if="strategyForm.strategy_type === strategy.type">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </div>
          </div>
        </div>

        <div class="threshold-groups">
          <div class="threshold-group">
            <div class="group-title">
              <span class="group-dot" style="background: #3b82f6"></span>
              策略一: 应报尽报阈值
            </div>
            <div class="form-grid">
              <div class="form-item">
                <label>置信度阈值</label>
                <div class="slider-row">
                  <input
                    type="range"
                    v-model.number="strategyForm.confidence_threshold_1"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-slider"
                  />
                  <input
                    type="number"
                    v-model.number="strategyForm.confidence_threshold_1"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-num"
                  />
                </div>
                <div class="form-hint">达到此置信度才输出预警（默认 0.7）</div>
              </div>
              <div class="form-item">
                <label>误报率阈值</label>
                <div class="slider-row">
                  <input
                    type="range"
                    v-model.number="strategyForm.false_positive_threshold"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-slider"
                  />
                  <input
                    type="number"
                    v-model.number="strategyForm.false_positive_threshold"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-num"
                  />
                </div>
                <div class="form-hint">可接受的误报率上限（默认 0.05）</div>
              </div>
            </div>
          </div>

          <div class="threshold-group">
            <div class="group-title">
              <span class="group-dot" style="background: #8b5cf6"></span>
              策略二: 精准报警阈值
            </div>
            <div class="form-grid">
              <div class="form-item">
                <label>高置信度阈值</label>
                <div class="slider-row">
                  <input
                    type="range"
                    v-model.number="strategyForm.confidence_threshold_2"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-slider"
                  />
                  <input
                    type="number"
                    v-model.number="strategyForm.confidence_threshold_2"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-num"
                  />
                </div>
                <div class="form-hint">极高置信度才输出预警（默认 0.95）</div>
              </div>
              <div class="form-item">
                <label>漏报率阈值</label>
                <div class="slider-row">
                  <input
                    type="range"
                    v-model.number="strategyForm.false_negative_threshold"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-slider"
                  />
                  <input
                    type="number"
                    v-model.number="strategyForm.false_negative_threshold"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-num"
                  />
                </div>
                <div class="form-hint">可接受的漏报率上限（默认 0.10）</div>
              </div>
            </div>
          </div>
        </div>

        <div class="form-item" style="margin-bottom: 16px;">
          <label>变更说明</label>
          <input
            v-model="strategyForm.description"
            type="text"
            class="form-input"
            placeholder="本次策略变更说明（可选）"
          />
        </div>

        <div class="form-actions">
          <button class="btn btn-secondary" @click="resetStrategy">重置</button>
          <button class="btn btn-primary" @click="saveStrategy" :disabled="savingStrategy">
            <svg v-if="savingStrategy" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
            </svg>
            {{ savingStrategy ? '保存中...' : '保存策略配置' }}
          </button>
        </div>

        <div class="strategy-extra-sections">
          <div class="sub-section">
            <div class="sub-section-header" @click="showVersionHistory = !showVersionHistory">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="1 4 1 10 7 10"></polyline>
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
              </svg>
              版本历史与回滚
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chevron" :class="{ open: showVersionHistory }">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>
            <div v-if="showVersionHistory" class="sub-section-body">
              <div v-if="versionLoading" class="empty-hint">加载中...</div>
              <div v-else-if="versionList.length === 0" class="empty-hint">暂无历史版本</div>
              <div v-else class="version-list">
                <div
                  v-for="v in versionList"
                  :key="v.id"
                  class="version-item"
                  :class="{ current: v.is_active }"
                >
                  <div class="version-left">
                    <span class="version-tag">v{{ v.version }}</span>
                    <span class="version-scope-dot" :style="{ background: getScopeColor(v.scope) }"></span>
                    <span class="version-label">{{ getScopeLabel(v.scope) }}{{ v.node_id ? ' / ' + v.node_id : '' }}</span>
                    <span class="version-strategy">{{ v.strategy_type === 1 ? '应报尽报' : '精准报警' }}</span>
                    <span class="version-time">{{ formatTime(v.create_time) }}</span>
                  </div>
                  <div class="version-right">
                    <span v-if="v.is_active" class="version-active">当前</span>
                    <button
                      v-else
                      class="btn btn-xs btn-secondary"
                      @click="handleRollback(v)"
                      :disabled="rollingBack"
                    >
                      回滚
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="sub-section">
            <div class="sub-section-header" @click="showAuditLog = !showAuditLog">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
              审计日志
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chevron" :class="{ open: showAuditLog }">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </div>
            <div v-if="showAuditLog" class="sub-section-body">
              <div v-if="auditLoading" class="empty-hint">加载中...</div>
              <div v-else-if="auditLogs.length === 0" class="empty-hint">暂无审计记录</div>
              <div v-else class="audit-list">
                <div v-for="log in auditLogs" :key="log.id" class="audit-item">
                  <div class="audit-left">
                    <span class="audit-action" :class="'action-' + log.action">{{ getActionLabel(log.action) }}</span>
                    <span class="audit-scope">{{ getScopeLabel(log.scope) }}{{ log.node_id ? ' / ' + log.node_id : '' }}</span>
                    <span class="audit-version">v{{ log.version_before }} → v{{ log.version_after }}</span>
                  </div>
                  <div class="audit-right">
                    <span v-if="log.operator_name" class="audit-operator">{{ log.operator_name }}</span>
                    <span class="audit-time">{{ formatTime(log.create_time) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="strategyScope !== 'global' && effectiveStrategy && effectiveStrategy.scope !== 'global'" class="sub-section danger-section">
            <div class="sub-section-header danger-header" @click="handleDeleteOverride">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
              删除此节点覆盖（回退到全局策略）
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 1" class="tab-panel threshold-panel">
        <div class="section-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
          阈值配置
        </div>

        <div class="threshold-groups">
          <div class="threshold-group">
            <div class="group-title">
              <span class="group-dot" style="background: #ef4444"></span>
              风险等级阈值
            </div>
            <div class="form-grid">
              <div class="form-item">
                <label>高风险阈值</label>
                <input
                  type="number"
                  v-model.number="thresholdForm.high_risk_threshold"
                  min="1"
                  max="10"
                  class="form-input"
                />
                <div class="form-hint">评分 ≤ 此值判定为高风险 (默认 3)</div>
              </div>
              <div class="form-item">
                <label>中风险阈值</label>
                <input
                  type="number"
                  v-model.number="thresholdForm.medium_risk_threshold"
                  min="1"
                  max="10"
                  class="form-input"
                />
                <div class="form-hint">评分 ≤ 此值判定为中风险 (默认 7)</div>
              </div>
            </div>
          </div>

          <div class="threshold-group">
            <div class="group-title">
              <span class="group-dot" style="background: #f59e0b"></span>
              预紧力阈值
            </div>
            <div class="form-grid">
              <div class="form-item">
                <label>正常最小值 (kN)</label>
                <input
                  type="number"
                  v-model.number="thresholdForm.min_normal_preload"
                  min="0"
                  class="form-input"
                />
                <div class="form-hint">预紧力正常范围下限 (默认 400)</div>
              </div>
              <div class="form-item">
                <label>正常最大值 (kN)</label>
                <input
                  type="number"
                  v-model.number="thresholdForm.max_normal_preload"
                  min="0"
                  class="form-input"
                />
                <div class="form-hint">预紧力正常范围上限 (默认 800)</div>
              </div>
              <div class="form-item">
                <label>预警偏差比例</label>
                <div class="slider-row">
                  <input
                    type="range"
                    v-model.number="thresholdForm.warning_deviation"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-slider"
                  />
                  <input
                    type="number"
                    v-model.number="thresholdForm.warning_deviation"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-num"
                  />
                </div>
                <div class="form-hint">超出此比例触发预警 (默认 0.1)</div>
              </div>
              <div class="form-item">
                <label>紧急偏差比例</label>
                <div class="slider-row">
                  <input
                    type="range"
                    v-model.number="thresholdForm.critical_deviation"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-slider"
                  />
                  <input
                    type="number"
                    v-model.number="thresholdForm.critical_deviation"
                    min="0"
                    max="1"
                    step="0.01"
                    class="form-num"
                  />
                </div>
                <div class="form-hint">超出此比例触发紧急告警 (默认 0.2)</div>
              </div>
            </div>
          </div>

          <div class="threshold-group">
            <div class="group-title">
              <span class="group-dot" style="background: #22c55e"></span>
              告警自动处理
            </div>
            <div class="form-grid">
              <div class="form-item">
                <label>自动创建工单级别</label>
                <select v-model.number="thresholdForm.auto_create_work_order_level" class="form-select">
                  <option :value="1">1 - 关注级</option>
                  <option :value="2">2 - 检查级</option>
                  <option :value="3">3 - 紧急级</option>
                  <option :value="4">4 - 故障级</option>
                </select>
                <div class="form-hint">达到此级别及以上自动创建工单</div>
              </div>
              <div class="form-item">
                <label>默认升级时间 (分钟)</label>
                <input
                  type="number"
                  v-model.number="thresholdForm.default_upgrade_minutes"
                  min="0"
                  class="form-input"
                />
                <div class="form-hint">超时未处理自动升级的时间</div>
              </div>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button class="btn btn-secondary" @click="resetThresholds">重置</button>
          <button class="btn btn-primary" @click="saveThresholds" :disabled="savingThresholds">
            <svg v-if="savingThresholds" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
            </svg>
            {{ savingThresholds ? '保存中...' : '保存阈值配置' }}
          </button>
        </div>
      </div>

      <div v-if="activeTab === 2" class="tab-panel scheduler-panel">
        <div class="section-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          调度任务管理
        </div>

        <div class="jobs-list">
          <div
            v-for="job in scheduledJobs"
            :key="job.id"
            class="job-card"
            :class="{ disabled: !job.enabled }"
          >
            <div class="job-header">
              <div class="job-icon" :class="getJobIconClass(job.id)">
                <span v-html="getJobIcon(job.id)"></span>
              </div>
              <div class="job-main">
                <div class="job-name">
                  {{ job.name }}
                  <span class="job-status" :class="job.enabled ? 'status-enabled' : 'status-disabled'">
                    {{ job.enabled ? '已启用' : '已停用' }}
                  </span>
                </div>
                <div class="job-desc">{{ job.description }}</div>
              </div>
              <div class="job-actions">
                <label class="toggle-switch">
                  <input
                    type="checkbox"
                    :checked="job.enabled"
                    @change="toggleJob(job)"
                  />
                  <span class="toggle-slider"></span>
                </label>
                <button
                  class="icon-btn"
                  title="立即执行"
                  @click="triggerJob(job)"
                  :disabled="triggeringJob === job.id"
                >
                  <svg v-if="triggeringJob === job.id" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                  </svg>
                  <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                  </svg>
                </button>
                <button
                  class="icon-btn"
                  title="编辑 Cron"
                  @click="openJobEditor(job)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                  </svg>
                </button>
              </div>
            </div>
            <div class="job-meta">
              <div class="meta-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="16" y1="2" x2="16" y2="6"></line>
                  <line x1="8" y1="2" x2="8" y2="6"></line>
                  <line x1="3" y1="10" x2="21" y2="10"></line>
                </svg>
                <code class="cron-tag">{{ job.cron }}</code>
              </div>
              <div v-if="job.next_run" class="meta-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                下次执行: {{ formatTime(job.next_run) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showCronModal" class="modal-overlay" @click.self="showCronModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>编辑调度任务 - {{ editingJob?.name }}</h3>
          <button class="close-btn" @click="showCronModal = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <CronEditor v-model="tempCron" />
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showCronModal = false">取消</button>
          <button class="btn btn-primary" @click="saveJobCron" :disabled="savingCron">
            <svg v-if="savingCron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
            </svg>
            {{ savingCron ? '保存中...' : '确认保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import type {
  WarningStrategyConfig,
  ThresholdConfig,
  ScheduledJob,
  ConfigCenterResponse,
  AlertStrategy,
  StrategyConfigItem,
  StrategyAuditLog
} from '@/types'
import {
  fetchConfigCenter,
  updateWarningStrategy,
  updateThresholds,
  updateSchedulerJob,
  triggerSchedulerJob,
  fetchEffectiveStrategy,
  updateStrategyConfig,
  listStrategyConfigs,
  rollbackStrategy,
  fetchStrategyAuditLogs,
  deleteStrategyOverride
} from '@/api/config'
import CronEditor from './CronEditor.vue'

const activeTab = ref(0)
const loading = ref(false)
const lastUpdated = ref<string>('')

const tabs = [
  { label: '预警策略', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>' },
  { label: '阈值配置', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>' },
  { label: '调度任务', icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>' }
]

interface StrategyOption {
  type: AlertStrategy
  name: string
  desc: string
  color: string
  icon: string
}

const strategyOptions: StrategyOption[] = [
  {
    type: 1,
    name: '应报尽报',
    desc: '降低置信度阈值，尽可能多地捕捉异常；不满足阈值时降一级输出',
    color: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
  },
  {
    type: 2,
    name: '精准报警',
    desc: '高置信度阈值，仅当确定性极高时输出预警；否则报告正常',
    color: 'linear-gradient(135deg, #8b5cf6, #6d28d9)',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
  }
]

const scopeOptions = [
  { value: 'global' as const, label: '全局', color: '#3b82f6' },
  { value: 'bolt' as const, label: '螺栓', color: '#8b5cf6' },
  { value: 'flange' as const, label: '法兰面', color: '#f97316' },
  { value: 'production_line' as const, label: '产线', color: '#22c55e' }
]

const strategyScope = ref<'global' | 'bolt' | 'flange' | 'production_line'>('global')
const strategyNodeId = ref('')
const effectiveStrategy = ref<StrategyConfigItem | null>(null)

const strategyForm = reactive({
  strategy_type: 1 as AlertStrategy,
  confidence_threshold_1: 0.7,
  false_positive_threshold: 0.05,
  confidence_threshold_2: 0.95,
  false_negative_threshold: 0.10,
  description: ''
})

const thresholdForm = reactive<ThresholdConfig>({
  high_risk_threshold: 3,
  medium_risk_threshold: 7,
  min_normal_preload: 400,
  max_normal_preload: 800,
  warning_deviation: 0.1,
  critical_deviation: 0.2,
  auto_create_work_order_level: 3,
  default_upgrade_minutes: 30
})

let originalStrategy: WarningStrategyConfig | null = null
let originalThresholds: ThresholdConfig | null = null

const scheduledJobs = ref<ScheduledJob[]>([])
const savingStrategy = ref(false)
const savingThresholds = ref(false)
const savingCron = ref(false)
const triggeringJob = ref<string | null>(null)

const showCronModal = ref(false)
const editingJob = ref<ScheduledJob | null>(null)
const tempCron = ref('')

const showVersionHistory = ref(false)
const showAuditLog = ref(false)
const versionLoading = ref(false)
const versionList = ref<StrategyConfigItem[]>([])
const auditLoading = ref(false)
const auditLogs = ref<StrategyAuditLog[]>([])
const rollingBack = ref(false)

const scopeMap: Record<string, string> = {
  global: '全局',
  bolt: '螺栓',
  flange: '法兰面',
  production_line: '产线'
}

const scopeColorMap: Record<string, string> = {
  global: '#3b82f6',
  bolt: '#8b5cf6',
  flange: '#f97316',
  production_line: '#22c55e'
}

function getScopeLabel(scope: string): string {
  return scopeMap[scope] || scope
}

function getScopeColor(scope: string): string {
  return scopeColorMap[scope] || '#3b82f6'
}

function getActionLabel(action: string): string {
  const map: Record<string, string> = {
    create: '创建',
    update: '更新',
    rollback: '回滚',
    delete: '删除'
  }
  return map[action] || action
}

function formatTime(t: string | null | undefined): string {
  if (!t) return '-'
  try {
    const d = new Date(t)
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return t
  }
}

function getJobIcon(jobId: string): string {
  const icons: Record<string, string> = {
    training_job: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>',
    prediction_job: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>',
    monthly_prediction_job: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
    alert_upgrade_job: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>',
    audit_cleanup_job: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>'
  }
  return icons[jobId] || icons.prediction_job
}

function getJobIconClass(jobId: string): string {
  const cls: Record<string, string> = {
    training_job: 'icon-training',
    prediction_job: 'icon-prediction',
    monthly_prediction_job: 'icon-monthly',
    alert_upgrade_job: 'icon-alert',
    audit_cleanup_job: 'icon-cleanup'
  }
  return cls[jobId] || 'icon-default'
}

async function loadStrategyConfig() {
  try {
    const nodeType = strategyScope.value === 'global' ? undefined : strategyScope.value
    const nodeId = strategyScope.value === 'global' ? undefined : strategyNodeId.value || undefined
    const resp = await fetchEffectiveStrategy(nodeType, nodeId)
    if (resp) {
      effectiveStrategy.value = resp.effective
      const e = resp.effective
      strategyForm.strategy_type = e.strategy_type
      if (e.strategy_type === 1) {
        strategyForm.confidence_threshold_1 = e.confidence_threshold
        strategyForm.false_positive_threshold = e.false_positive_threshold ?? 0.05
      } else {
        strategyForm.confidence_threshold_2 = e.confidence_threshold
        strategyForm.false_negative_threshold = e.false_negative_threshold ?? 0.10
      }
    }
  } catch (e) {
    console.error('加载策略配置失败:', e)
  }
}

async function loadVersionHistory() {
  if (!showVersionHistory.value) return
  versionLoading.value = true
  try {
    const scope = strategyScope.value === 'global' ? undefined : strategyScope.value
    const nodeType = scope
    const nodeId = strategyScope.value === 'global' ? undefined : strategyNodeId.value || undefined
    const result = await listStrategyConfigs(scope, nodeType, nodeId)
    versionList.value = result.items
  } catch (e) {
    console.error('加载版本历史失败:', e)
  } finally {
    versionLoading.value = false
  }
}

async function loadAuditLogs() {
  if (!showAuditLog.value) return
  auditLoading.value = true
  try {
    const scope = strategyScope.value === 'global' ? undefined : strategyScope.value
    const nodeType = scope
    const nodeId = strategyScope.value === 'global' ? undefined : strategyNodeId.value || undefined
    const result = await fetchStrategyAuditLogs(scope, nodeType, nodeId)
    auditLogs.value = result.items
  } catch (e) {
    console.error('加载审计日志失败:', e)
  } finally {
    auditLoading.value = false
  }
}

watch(showVersionHistory, loadVersionHistory)
watch(showAuditLog, loadAuditLogs)

function onScopeChange(scope: 'global' | 'bolt' | 'flange' | 'production_line') {
  strategyScope.value = scope
  loadStrategyConfig()
}

async function loadConfig() {
  loading.value = true
  try {
    const data: ConfigCenterResponse = await fetchConfigCenter()
    Object.assign(thresholdForm, data.thresholds)
    scheduledJobs.value = [...data.scheduled_jobs]
    lastUpdated.value = data.updated_at
    originalThresholds = { ...data.thresholds }
    if (data.warning_strategy) {
      originalStrategy = { ...data.warning_strategy }
    }
    await loadStrategyConfig()
  } catch (e) {
    console.error('加载配置失败:', e)
  } finally {
    loading.value = false
  }
}

function resetStrategy() {
  if (effectiveStrategy.value) {
    const e = effectiveStrategy.value
    strategyForm.strategy_type = e.strategy_type
    if (e.strategy_type === 1) {
      strategyForm.confidence_threshold_1 = e.confidence_threshold
      strategyForm.false_positive_threshold = e.false_positive_threshold ?? 0.05
    } else {
      strategyForm.confidence_threshold_2 = e.confidence_threshold
      strategyForm.false_negative_threshold = e.false_negative_threshold ?? 0.10
    }
    strategyForm.description = ''
  }
}

function resetThresholds() {
  if (originalThresholds) {
    Object.assign(thresholdForm, originalThresholds)
  }
}

async function saveStrategy() {
  savingStrategy.value = true
  try {
    const isType1 = strategyForm.strategy_type === 1
    const req = {
      scope: strategyScope.value,
      node_type: strategyScope.value === 'global' ? null : strategyScope.value,
      node_id: strategyScope.value === 'global' ? null : strategyNodeId.value || null,
      strategy_type: strategyForm.strategy_type,
      confidence_threshold: isType1 ? strategyForm.confidence_threshold_1 : strategyForm.confidence_threshold_2,
      false_positive_threshold: isType1 ? strategyForm.false_positive_threshold : null,
      false_negative_threshold: isType1 ? null : strategyForm.false_negative_threshold,
      description: strategyForm.description || null
    }
    const result = await updateStrategyConfig(req)
    if (result) {
      effectiveStrategy.value = result
      lastUpdated.value = new Date().toISOString()
      strategyForm.description = ''
      if (showVersionHistory.value) loadVersionHistory()
      if (showAuditLog.value) loadAuditLogs()
    }
  } catch (e) {
    console.error('保存策略失败:', e)
  } finally {
    savingStrategy.value = false
  }
}

async function saveThresholds() {
  savingThresholds.value = true
  try {
    const result = await updateThresholds({ ...thresholdForm })
    if (result) {
      originalThresholds = { ...result }
      lastUpdated.value = new Date().toISOString()
    }
  } catch (e) {
    console.error('保存阈值失败:', e)
  } finally {
    savingThresholds.value = false
  }
}

async function toggleJob(job: ScheduledJob) {
  const newValue = !job.enabled
  const result = await updateSchedulerJob(job.id, { enabled: newValue })
  if (result) {
    job.enabled = result.enabled
    lastUpdated.value = new Date().toISOString()
  }
}

async function triggerJob(job: ScheduledJob) {
  triggeringJob.value = job.id
  try {
    await triggerSchedulerJob(job.id)
  } catch (e) {
    console.error('触发任务失败:', e)
  } finally {
    triggeringJob.value = null
  }
}

function openJobEditor(job: ScheduledJob) {
  editingJob.value = job
  tempCron.value = job.cron
  showCronModal.value = true
}

async function saveJobCron() {
  if (!editingJob.value) return
  savingCron.value = true
  try {
    const result = await updateSchedulerJob(editingJob.value.id, { cron: tempCron.value })
    if (result) {
      const job = scheduledJobs.value.find(j => j.id === editingJob.value!.id)
      if (job) job.cron = result.cron
      lastUpdated.value = new Date().toISOString()
    }
    showCronModal.value = false
  } catch (e) {
    console.error('保存 Cron 失败:', e)
  } finally {
    savingCron.value = false
  }
}

async function handleRollback(item: StrategyConfigItem) {
  rollingBack.value = true
  try {
    const result = await rollbackStrategy({
      target_version: item.version,
      scope: strategyScope.value,
      node_type: strategyScope.value === 'global' ? null : strategyScope.value,
      node_id: strategyScope.value === 'global' ? null : strategyNodeId.value || null
    })
    if (result) {
      effectiveStrategy.value = result
      lastUpdated.value = new Date().toISOString()
      loadVersionHistory()
      if (showAuditLog.value) loadAuditLogs()
    }
  } catch (e) {
    console.error('策略回滚失败:', e)
  } finally {
    rollingBack.value = false
  }
}

async function handleDeleteOverride() {
  if (!strategyNodeId.value) return
  const ok = await deleteStrategyOverride(strategyScope.value, strategyNodeId.value)
  if (ok) {
    strategyScope.value = 'global'
    strategyNodeId.value = ''
    await loadStrategyConfig()
    lastUpdated.value = new Date().toISOString()
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.config-center {
  padding: 16px;
  color: #e2e8f0;
  height: 100%;
  overflow-y: auto;
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.config-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #60a5fa;
}

.config-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, #60a5fa, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.last-updated {
  font-size: 12px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  color: #60a5fa;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.25);
  border-color: rgba(59, 130, 246, 0.5);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.config-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
  padding: 4px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 10px;
  border: 1px solid rgba(59, 130, 246, 0.15);
}

.config-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.config-tab:hover {
  color: #cbd5e1;
}

.config-tab.active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(37, 99, 235, 0.25));
  color: #60a5fa;
}

.tab-icon {
  display: flex;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #cbd5e1;
  margin-bottom: 16px;
}

.threshold-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

.threshold-group {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 10px;
  padding: 16px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #cbd5e1;
  margin-bottom: 14px;
}

.group-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-item label {
  font-size: 13px;
  color: #94a3b8;
}

.form-input,
.form-select {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  padding: 8px 12px;
  color: #e2e8f0;
  font-size: 14px;
  outline: none;
  transition: all 0.2s;
}

.form-input:focus,
.form-select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.form-slider {
  flex: 1;
  accent-color: #3b82f6;
  height: 4px;
}

.form-num {
  width: 70px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  padding: 6px 8px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  text-align: center;
}

.form-hint {
  font-size: 11px;
  color: #64748b;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
}

.btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #94a3b8;
}

.btn-secondary:hover {
  background: rgba(59, 130, 246, 0.2);
  color: #cbd5e1;
}

.strategy-selector {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}

.strategy-card {
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 16px;
  background: rgba(15, 23, 42, 0.6);
  border: 2px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.strategy-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
  transform: translateY(-2px);
}

.strategy-card.active {
  border-color: #3b82f6;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(37, 99, 235, 0.08));
}

.strategy-badge {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.strategy-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.strategy-name {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.strategy-desc {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
}

.strategy-check {
  color: #3b82f6;
  display: flex;
  align-items: center;
}

.jobs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.2s;
}

.job-card.disabled {
  opacity: 0.6;
}

.job-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}

.job-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-training { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
.icon-prediction { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
.icon-monthly { background: rgba(168, 85, 247, 0.2); color: #c084fc; }
.icon-alert { background: rgba(239, 68, 68, 0.2); color: #f87171; }
.icon-cleanup { background: rgba(100, 116, 139, 0.2); color: #94a3b8; }
.icon-default { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }

.job-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.job-name {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.job-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.status-enabled {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-disabled {
  background: rgba(100, 116, 139, 0.15);
  color: #94a3b8;
}

.job-desc {
  font-size: 12px;
  color: #94a3b8;
}

.job-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(100, 116, 139, 0.4);
  transition: 0.3s;
  border-radius: 22px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: #fff;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #3b82f6;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(18px);
}

.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.icon-btn:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border-color: rgba(59, 130, 246, 0.4);
}

.icon-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.job-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.cron-tag {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  padding: 3px 8px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 16px;
  width: 90%;
  max-width: 640px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  color: #e2e8f0;
  font-weight: 600;
}

.close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: rgba(59, 130, 246, 0.15);
  color: #e2e8f0;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.15);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.version-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  font-weight: 500;
  margin-left: 8px;
}

.scope-selector {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}

.scope-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.scope-row + .scope-row {
  margin-top: 12px;
}

.scope-label {
  font-size: 13px;
  color: #94a3b8;
  white-space: nowrap;
  min-width: 80px;
}

.scope-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.scope-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  background: rgba(15, 23, 42, 0.8);
  color: #94a3b8;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.scope-btn:hover {
  border-color: rgba(59, 130, 246, 0.4);
  color: #cbd5e1;
}

.scope-btn.active {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.scope-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.node-id-input {
  flex: 1;
  max-width: 300px;
}

.effective-info {
  margin-bottom: 16px;
}

.info-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.3);
  background: rgba(15, 23, 42, 0.6);
  font-size: 13px;
  color: #cbd5e1;
}

.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.chip-sep {
  color: #475569;
}

.strategy-extra-sections {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sub-section {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 10px;
  overflow: hidden;
}

.sub-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #cbd5e1;
  cursor: pointer;
  transition: background 0.2s;
}

.sub-section-header:hover {
  background: rgba(59, 130, 246, 0.08);
}

.sub-section-header .chevron {
  margin-left: auto;
  transition: transform 0.2s;
}

.sub-section-header .chevron.open {
  transform: rotate(180deg);
}

.sub-section-body {
  padding: 12px 16px;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
}

.empty-hint {
  font-size: 12px;
  color: #64748b;
  text-align: center;
  padding: 12px;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 240px;
  overflow-y: auto;
}

.version-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.1);
}

.version-item.current {
  border-color: rgba(34, 197, 94, 0.3);
  background: rgba(34, 197, 94, 0.06);
}

.version-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94a3b8;
  flex-wrap: wrap;
}

.version-tag {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 11px;
}

.version-scope-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.version-label {
  color: #cbd5e1;
}

.version-strategy {
  color: #a78bfa;
}

.version-time {
  color: #64748b;
  font-size: 11px;
}

.version-right {
  display: flex;
  align-items: center;
}

.version-active {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.btn-xs {
  padding: 4px 10px;
  font-size: 11px;
  border-radius: 4px;
}

.audit-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 240px;
  overflow-y: auto;
}

.audit-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.4);
  font-size: 12px;
}

.audit-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  flex-wrap: wrap;
}

.audit-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.audit-action {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
}

.action-create {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.action-update {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.action-rollback {
  background: rgba(249, 115, 22, 0.15);
  color: #fb923c;
}

.action-delete {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.audit-scope {
  color: #cbd5e1;
}

.audit-version {
  color: #a78bfa;
  font-family: monospace;
  font-size: 11px;
}

.audit-operator {
  color: #94a3b8;
}

.audit-time {
  color: #64748b;
  font-size: 11px;
}

.danger-section {
  border-color: rgba(239, 68, 68, 0.3);
}

.danger-header {
  color: #f87171;
}

.danger-header:hover {
  background: rgba(239, 68, 68, 0.08);
}
</style>
