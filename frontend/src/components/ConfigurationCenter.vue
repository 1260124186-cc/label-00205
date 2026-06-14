<template>
  <div class="config-center">
    <div class="config-header">
      <div class="config-title">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
        <h2>配置中心</h2>
      </div>
      <div class="header-tabs">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'strategy' }"
          @click="activeTab = 'strategy'"
        >预警策略</button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'threshold' }"
          @click="activeTab = 'threshold'"
        >阈值配置</button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'cron' }"
          @click="activeTab = 'cron'"
        >调度任务</button>
      </div>
      <div class="header-actions">
        <button v-if="activeTab === 'strategy'" class="btn btn-primary" @click="openNewRule">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          新建规则
        </button>
        <button v-if="activeTab === 'threshold'" class="btn btn-primary" @click="openNewPreset">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          新建方案
        </button>
        <button v-if="activeTab === 'cron'" class="btn btn-primary" @click="openNewCronTask">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          新建任务
        </button>
      </div>
    </div>

    <div class="config-content">
      <div v-if="activeTab === 'strategy'" class="tab-panel">
        <div class="rule-list-panel">
          <div class="panel-header">
            <span class="panel-title">规则列表</span>
            <span class="panel-count">{{ rules.length }} 条</span>
          </div>
          <div class="rule-list">
            <div
              v-for="rule in rules"
              :key="rule.id"
              class="rule-card"
              :class="{ selected: selectedRuleId === rule.id }"
              @click="selectRule(rule)"
            >
              <div class="rule-card-top">
                <span class="rule-name">{{ rule.name }}</span>
                <span
                  class="rule-status-dot"
                  :style="{ background: AlertRuleStatusColorMap[rule.status] }"
                ></span>
              </div>
              <div class="rule-card-badges">
                <span
                  class="badge strategy-badge"
                  :style="{ borderColor: rule.strategy_type === 1 ? '#3b82f6' : '#8b5cf6', color: rule.strategy_type === 1 ? '#60a5fa' : '#a78bfa' }"
                >{{ AlertStrategyMap[rule.strategy_type] }}</span>
                <span
                  class="badge level-badge"
                  :style="{ background: AlertLevelColorMap[rule.alert_level] }"
                >{{ AlertLevelMap[rule.alert_level] }}</span>
                <span
                  class="badge status-badge"
                  :style="{ borderColor: AlertRuleStatusColorMap[rule.status], color: AlertRuleStatusColorMap[rule.status] }"
                >{{ AlertRuleStatusMap[rule.status] }}</span>
              </div>
              <div class="rule-card-summary">
                {{ getConditionsSummary(rule.conditions) }}
              </div>
              <div class="rule-card-meta">
                <span>触发 {{ rule.trigger_count }} 次</span>
              </div>
            </div>
            <div v-if="rules.length === 0" class="empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              <div class="empty-title">暂无预警规则</div>
            </div>
          </div>
        </div>

        <div class="rule-edit-panel">
          <div v-if="!ruleForm" class="empty-edit">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            <div class="empty-title">选择或新建规则</div>
          </div>
          <div v-else class="edit-form">
            <div class="edit-form-scroll">
              <div class="form-group">
                <label class="form-label">规则名称</label>
                <input v-model="ruleForm.name" type="text" class="form-input" placeholder="请输入规则名称" />
              </div>
              <div class="form-group">
                <label class="form-label">描述</label>
                <textarea v-model="ruleForm.description" class="form-textarea" rows="3" placeholder="请输入规则描述"></textarea>
              </div>
              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">策略类型</label>
                  <select v-model="ruleForm.strategy_type" class="form-select">
                    <option :value="1">应报尽报</option>
                    <option :value="2">精准报警</option>
                  </select>
                </div>
                <div class="form-group flex-1">
                  <label class="form-label">预警等级</label>
                  <select v-model="ruleForm.alert_level" class="form-select">
                    <option v-for="lv in [1,2,3,4]" :key="lv" :value="lv">{{ AlertLevelMap[lv as AlertLevel] }}</option>
                  </select>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">触发条件</label>
                <div class="conditions-list">
                  <div v-for="(cond, idx) in ruleForm.conditions" :key="idx" class="condition-row">
                    <select v-model="cond.field" class="form-select cond-select">
                      <option v-for="(label, key) in ConditionFieldMap" :key="key" :value="key">{{ label }}</option>
                    </select>
                    <select v-model="cond.operator" class="form-select cond-select">
                      <option v-for="(label, key) in ConditionOperatorMap" :key="key" :value="key">{{ label }}</option>
                    </select>
                    <input v-model="cond.value" type="text" class="form-input cond-input" placeholder="值" />
                    <button class="btn-icon btn-remove" @click="removeCondition(idx)">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>
                  <button class="btn btn-secondary btn-sm" @click="addCondition">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="12" y1="5" x2="12" y2="19"></line>
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    添加条件
                  </button>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">逻辑运算</label>
                <div class="radio-group">
                  <label class="radio-option">
                    <input type="radio" v-model="ruleForm.logic_operator" value="and" />
                    <span>AND (全部满足)</span>
                  </label>
                  <label class="radio-option">
                    <input type="radio" v-model="ruleForm.logic_operator" value="or" />
                    <span>OR (任一满足)</span>
                  </label>
                </div>
              </div>
              <div class="form-row">
                <div class="form-group flex-1">
                  <label class="form-label">节点类型</label>
                  <select v-model="ruleForm.node_type" class="form-select">
                    <option value="bolt">螺栓</option>
                    <option value="flange">法兰</option>
                    <option value="both">全部</option>
                  </select>
                </div>
                <div class="form-group flex-1">
                  <label class="form-label">静默时间(分钟)</label>
                  <input v-model.number="ruleForm.silence_minutes" type="number" class="form-input" min="0" />
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">升级配置</label>
                <div class="upgrade-row">
                  <label class="checkbox-option">
                    <input type="checkbox" v-model="ruleForm.upgrade_enabled" />
                    <span>启用升级</span>
                  </label>
                  <div v-if="ruleForm.upgrade_enabled" class="form-group inline-group">
                    <label class="form-label">升级间隔(分钟)</label>
                    <input v-model.number="ruleForm.upgrade_interval_minutes" type="number" class="form-input" min="1" />
                  </div>
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">状态</label>
                <select v-model="ruleForm.status" class="form-select">
                  <option v-for="(label, key) in AlertRuleStatusMap" :key="key" :value="key">{{ label }}</option>
                </select>
              </div>
            </div>
            <div class="edit-form-actions">
              <button v-if="ruleForm.id" class="action-btn action-toggle" @click="handleToggleRule(ruleForm.id!)">
                {{ rules.find(r => r.id === ruleForm!.id)?.status === 'active' ? '停用' : '启用' }}
              </button>
              <button v-if="ruleForm.id" class="action-btn action-delete" @click="showRuleDeleteConfirm = true; deletingRuleId = ruleForm!.id ?? null">删除</button>
              <div style="flex:1"></div>
              <button class="btn btn-secondary" @click="cancelRuleEdit">取消</button>
              <button class="btn btn-primary" @click="saveRule" :disabled="savingRule">
                {{ savingRule ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="showRuleDeleteConfirm" class="modal-overlay" @click.self="showRuleDeleteConfirm = false">
          <div class="modal">
            <div class="modal-header">
              <h3>确认删除</h3>
              <button class="modal-close" @click="showRuleDeleteConfirm = false">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <p class="confirm-text">确定要删除该预警规则吗？此操作不可撤销。</p>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="showRuleDeleteConfirm = false">取消</button>
              <button class="btn btn-danger" @click="confirmDeleteRule">确认删除</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'threshold'" class="tab-panel threshold-panel">
        <div class="preset-grid">
          <div v-for="preset in presets" :key="preset.id" class="preset-card">
            <div class="preset-card-header">
              <div class="preset-info">
                <span class="preset-name">{{ preset.name }}</span>
                <span v-if="preset.is_default" class="badge default-badge">默认</span>
              </div>
              <div class="preset-actions">
                <button v-if="!preset.is_default" class="btn-text" @click="handleSetDefault(preset.id)">设为默认</button>
                <button class="btn-text" @click="openEditPreset(preset)">编辑</button>
                <button class="btn-text btn-text-danger" @click="confirmDeletePreset(preset.id)">删除</button>
              </div>
            </div>
            <div class="preset-desc">{{ preset.description }}</div>
            <div class="threshold-table-wrap">
              <table class="threshold-table">
                <thead>
                  <tr>
                    <th>等级</th>
                    <th>字段</th>
                    <th>操作</th>
                    <th>值</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, idx) in preset.thresholds" :key="idx">
                    <td>
                      <span class="badge level-badge-sm" :style="{ background: item.color }">{{ AlertLevelMap[item.level] }}</span>
                    </td>
                    <td>{{ ConditionFieldMap[item.field] || item.field }}</td>
                    <td>{{ ConditionOperatorMap[item.operator] || item.operator }}</td>
                    <td>{{ item.value }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-if="presets.length === 0" class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M12 20V10"></path>
              <path d="M18 20V4"></path>
              <path d="M6 20v-4"></path>
            </svg>
            <div class="empty-title">暂无阈值方案</div>
          </div>
        </div>

        <div v-if="showPresetModal" class="modal-overlay" @click.self="showPresetModal = false">
          <div class="modal modal-lg">
            <div class="modal-header">
              <h3>{{ presetFormId ? '编辑阈值方案' : '新建阈值方案' }}</h3>
              <button class="modal-close" @click="showPresetModal = false">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <div class="form-group">
                <label class="form-label">方案名称</label>
                <input v-model="presetForm.name" type="text" class="form-input" placeholder="请输入方案名称" />
              </div>
              <div class="form-group">
                <label class="form-label">描述</label>
                <textarea v-model="presetForm.description" class="form-textarea" rows="2" placeholder="请输入描述"></textarea>
              </div>
              <div class="form-group">
                <label class="form-label">阈值列表</label>
                <table class="threshold-edit-table">
                  <thead>
                    <tr>
                      <th>等级</th>
                      <th>字段</th>
                      <th>操作</th>
                      <th>值</th>
                      <th>颜色</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, idx) in presetForm.thresholds" :key="idx">
                      <td>
                        <select v-model="item.level" class="form-select">
                          <option v-for="lv in [1,2,3,4]" :key="lv" :value="lv">{{ AlertLevelMap[lv as AlertLevel] }}</option>
                        </select>
                      </td>
                      <td>
                        <select v-model="item.field" class="form-select">
                          <option v-for="(label, key) in ConditionFieldMap" :key="key" :value="key">{{ label }}</option>
                        </select>
                      </td>
                      <td>
                        <select v-model="item.operator" class="form-select">
                          <option value="gt">大于</option>
                          <option value="gte">大于等于</option>
                          <option value="lt">小于</option>
                          <option value="lte">小于等于</option>
                          <option value="eq">等于</option>
                        </select>
                      </td>
                      <td>
                        <input v-model.number="item.value" type="number" class="form-input" step="0.01" />
                      </td>
                      <td>
                        <input v-model="item.color" type="color" class="form-color" />
                      </td>
                      <td>
                        <button class="btn-icon btn-remove" @click="removePresetThreshold(idx)">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                          </svg>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <button class="btn btn-secondary btn-sm" @click="addPresetThreshold">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                  </svg>
                  添加阈值
                </button>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="showPresetModal = false">取消</button>
              <button class="btn btn-primary" @click="savePreset" :disabled="savingPreset">
                {{ savingPreset ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="showPresetDeleteConfirm" class="modal-overlay" @click.self="showPresetDeleteConfirm = false">
          <div class="modal">
            <div class="modal-header">
              <h3>确认删除</h3>
              <button class="modal-close" @click="showPresetDeleteConfirm = false">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <p class="confirm-text">确定要删除该阈值方案吗？此操作不可撤销。</p>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="showPresetDeleteConfirm = false">取消</button>
              <button class="btn btn-danger" @click="doDeletePreset">确认删除</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'cron'" class="tab-panel cron-panel">
        <div class="cron-list">
          <div
            v-for="task in cronTasks"
            :key="task.id"
            class="cron-card"
            :class="{ expanded: expandedCronId === task.id }"
          >
            <div class="cron-card-header" @click="toggleCronExpand(task.id)">
              <div class="cron-card-left">
                <span class="cron-task-name">{{ task.name }}</span>
                <span
                  class="badge type-badge"
                  :style="{ background: CronTaskTypeColorMap[task.task_type] + '20', color: CronTaskTypeColorMap[task.task_type], borderColor: CronTaskTypeColorMap[task.task_type] }"
                >{{ CronTaskTypeMap[task.task_type] }}</span>
                <span
                  class="badge status-badge"
                  :style="{ borderColor: CronTaskStatusColorMap[task.status], color: CronTaskStatusColorMap[task.status] }"
                >{{ CronTaskStatusMap[task.status] }}</span>
              </div>
              <div class="cron-card-right">
                <span class="cron-meta">{{ task.cron_expression }}</span>
                <span class="cron-meta">{{ task.cron_human }}</span>
                <svg class="expand-icon" :class="{ rotated: expandedCronId === task.id }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
            </div>
            <div class="cron-card-meta-row">
              <span class="cron-meta-item">上次执行: {{ formatTime(task.last_run_time) }}</span>
              <span class="cron-meta-item">下次执行: {{ formatTime(task.next_run_time) }}</span>
              <span class="cron-meta-item">执行次数: {{ task.run_count }}</span>
            </div>
            <div v-if="expandedCronId === task.id" class="cron-card-detail">
              <div class="detail-section">
                <div class="detail-title">描述</div>
                <div class="detail-content">{{ task.description || '-' }}</div>
              </div>
              <div class="detail-section">
                <div class="detail-title">配置</div>
                <pre class="detail-code">{{ JSON.stringify(task.config, null, 2) }}</pre>
              </div>
              <div v-if="task.last_error" class="detail-section">
                <div class="detail-title">最近错误</div>
                <div class="detail-content error-text">{{ task.last_error }}</div>
              </div>
              <div v-if="task.last_run_duration_ms != null" class="detail-section">
                <div class="detail-title">上次耗时</div>
                <div class="detail-content">{{ task.last_run_duration_ms }}ms</div>
              </div>
              <div class="cron-detail-actions">
                <button
                  class="action-btn"
                  :class="task.status === 'running' ? 'action-stop' : 'action-start'"
                  @click.stop="handleToggleCronTask(task)"
                >{{ task.status === 'running' ? '停止' : '启动' }}</button>
                <button class="action-btn action-run" @click.stop="handleRunCronNow(task)">立即执行</button>
                <button class="action-btn action-edit" @click.stop="openEditCronTask(task)">编辑</button>
                <button class="action-btn action-delete" @click.stop="confirmDeleteCronTask(task.id)">删除</button>
              </div>
            </div>
          </div>
          <div v-if="cronTasks.length === 0" class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <div class="empty-title">暂无调度任务</div>
          </div>
        </div>

        <div v-if="showCronModal" class="modal-overlay" @click.self="showCronModal = false">
          <div class="modal modal-lg">
            <div class="modal-header">
              <h3>{{ cronFormId ? '编辑调度任务' : '新建调度任务' }}</h3>
              <button class="modal-close" @click="showCronModal = false">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <div class="form-group">
                <label class="form-label">任务名称</label>
                <input v-model="cronForm.name" type="text" class="form-input" placeholder="请输入任务名称" />
              </div>
              <div class="form-group">
                <label class="form-label">描述</label>
                <textarea v-model="cronForm.description" class="form-textarea" rows="2" placeholder="请输入描述"></textarea>
              </div>
              <div class="form-group">
                <label class="form-label">任务类型</label>
                <select v-model="cronForm.task_type" class="form-select">
                  <option v-for="(label, key) in CronTaskTypeMap" :key="key" :value="key">{{ label }}</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Cron 表达式</label>
                <div class="cron-editor">
                  <div class="cron-visual">
                    <div class="form-row">
                      <div class="form-group flex-1">
                        <label class="form-label">频率</label>
                        <select v-model="cronFreq" class="form-select" @change="onCronFreqChange">
                          <option value="minute">每分钟</option>
                          <option value="hour">每小时</option>
                          <option value="day">每天</option>
                          <option value="week">每周</option>
                          <option value="month">每月</option>
                          <option value="custom">自定义</option>
                        </select>
                      </div>
                    </div>
                    <div v-if="cronFreq !== 'custom'" class="cron-freq-fields">
                      <div v-if="cronFreq === 'minute'" class="form-group">
                        <label class="form-label">每隔分钟数</label>
                        <input v-model.number="cronMinute" type="number" class="form-input" min="1" max="59" />
                      </div>
                      <div v-if="cronFreq === 'hour'" class="form-row">
                        <div class="form-group flex-1">
                          <label class="form-label">分钟</label>
                          <input v-model.number="cronMinute" type="number" class="form-input" min="0" max="59" />
                        </div>
                      </div>
                      <div v-if="cronFreq === 'day'" class="form-row">
                        <div class="form-group flex-1">
                          <label class="form-label">小时</label>
                          <input v-model.number="cronHour" type="number" class="form-input" min="0" max="23" />
                        </div>
                        <div class="form-group flex-1">
                          <label class="form-label">分钟</label>
                          <input v-model.number="cronMinute" type="number" class="form-input" min="0" max="59" />
                        </div>
                      </div>
                      <div v-if="cronFreq === 'week'" class="form-row">
                        <div class="form-group flex-1">
                          <label class="form-label">星期</label>
                          <select v-model.number="cronWeekday" class="form-select">
                            <option :value="0">周日</option>
                            <option :value="1">周一</option>
                            <option :value="2">周二</option>
                            <option :value="3">周三</option>
                            <option :value="4">周四</option>
                            <option :value="5">周五</option>
                            <option :value="6">周六</option>
                          </select>
                        </div>
                        <div class="form-group flex-1">
                          <label class="form-label">小时</label>
                          <input v-model.number="cronHour" type="number" class="form-input" min="0" max="23" />
                        </div>
                        <div class="form-group flex-1">
                          <label class="form-label">分钟</label>
                          <input v-model.number="cronMinute" type="number" class="form-input" min="0" max="59" />
                        </div>
                      </div>
                      <div v-if="cronFreq === 'month'" class="form-row">
                        <div class="form-group flex-1">
                          <label class="form-label">日</label>
                          <input v-model.number="cronDay" type="number" class="form-input" min="1" max="31" />
                        </div>
                        <div class="form-group flex-1">
                          <label class="form-label">小时</label>
                          <input v-model.number="cronHour" type="number" class="form-input" min="0" max="23" />
                        </div>
                        <div class="form-group flex-1">
                          <label class="form-label">分钟</label>
                          <input v-model.number="cronMinute" type="number" class="form-input" min="0" max="59" />
                        </div>
                      </div>
                    </div>
                    <div v-else class="form-group">
                      <label class="form-label">Cron 表达式</label>
                      <input v-model="cronForm.cron_expression" type="text" class="form-input" placeholder="*/5 * * * *" />
                    </div>
                    <div class="cron-preview">
                      <span class="cron-preview-label">生成表达式:</span>
                      <code class="cron-preview-code">{{ cronExpression || '-' }}</code>
                    </div>
                    <div class="cron-presets">
                      <span class="cron-presets-label">快捷预设:</span>
                      <button class="quick-btn" @click="applyCronPreset('*/5 * * * *')">每5分钟</button>
                      <button class="quick-btn" @click="applyCronPreset('*/10 * * * *')">每10分钟</button>
                      <button class="quick-btn" @click="applyCronPreset('*/30 * * * *')">每30分钟</button>
                      <button class="quick-btn" @click="applyCronPreset('0 * * * *')">每小时</button>
                      <button class="quick-btn" @click="applyCronPreset('0 8 * * *')">每天8:00</button>
                      <button class="quick-btn" @click="applyCronPreset('0 8 * * 1')">每周一</button>
                      <button class="quick-btn" @click="applyCronPreset('0 0 1 * *')">每月1日</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="showCronModal = false">取消</button>
              <button class="btn btn-primary" @click="saveCronTask" :disabled="savingCron">
                {{ savingCron ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="showCronDeleteConfirm" class="modal-overlay" @click.self="showCronDeleteConfirm = false">
          <div class="modal">
            <div class="modal-header">
              <h3>确认删除</h3>
              <button class="modal-close" @click="showCronDeleteConfirm = false">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <p class="confirm-text">确定要删除该调度任务吗？此操作不可撤销。</p>
            </div>
            <div class="modal-footer">
              <button class="btn btn-secondary" @click="showCronDeleteConfirm = false">取消</button>
              <button class="btn btn-danger" @click="doDeleteCronTask">确认删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  AlertLevelMap, AlertLevelColorMap, AlertStrategyMap,
  AlertRuleStatusMap, AlertRuleStatusColorMap,
  ConditionOperatorMap, ConditionFieldMap,
  CronTaskStatusMap, CronTaskStatusColorMap,
  CronTaskTypeMap, CronTaskTypeColorMap
} from '@/types'
import type {
  AlertRule, AlertRuleCondition, AlertRuleCreateRequest, AlertRuleUpdateRequest,
  AlertLevel, AlertStrategy, AlertRuleStatus,
  ThresholdPreset, ThresholdItem, ThresholdPresetCreateRequest,
  CronTask, CronTaskCreateRequest, CronTaskUpdateRequest
} from '@/types'
import {
  fetchAlertRules, createAlertRule, updateAlertRule, deleteAlertRule, toggleAlertRule,
  fetchThresholdPresets, createThresholdPreset, updateThresholdPreset, deleteThresholdPreset, setDefaultPreset,
  fetchCronTasks, createCronTask, updateCronTask, deleteCronTask, toggleCronTask, runCronTaskNow
} from '@/api/config'

const activeTab = ref<'strategy' | 'threshold' | 'cron'>('strategy')

const rules = ref<AlertRule[]>([])
const selectedRuleId = ref<number | null>(null)
const ruleForm = ref<(AlertRuleCreateRequest & { id?: number; status: AlertRuleStatus }) | null>(null)
const savingRule = ref(false)
const showRuleDeleteConfirm = ref(false)
const deletingRuleId = ref<number | null>(null)

const presets = ref<ThresholdPreset[]>([])
const presetFormId = ref<number | null>(null)
const presetForm = ref<{ name: string; description: string; thresholds: ThresholdItem[] }>({ name: '', description: '', thresholds: [] })
const savingPreset = ref(false)
const showPresetModal = ref(false)
const showPresetDeleteConfirm = ref(false)
const deletingPresetId = ref<number | null>(null)

const cronTasks = ref<CronTask[]>([])
const expandedCronId = ref<number | null>(null)
const cronFormId = ref<number | null>(null)
const cronForm = ref<CronTaskCreateRequest>({ name: '', task_type: 'data_collect', cron_expression: '' })
const savingCron = ref(false)
const showCronModal = ref(false)
const showCronDeleteConfirm = ref(false)
const deletingCronId = ref<number | null>(null)

const cronFreq = ref('minute')
const cronMinute = ref(5)
const cronHour = ref(0)
const cronDay = ref(1)
const cronWeekday = ref(1)

const cronExpression = computed(() => {
  if (cronFreq.value === 'custom') return cronForm.value.cron_expression
  return buildCronExpression(cronFreq.value, cronMinute.value, cronHour.value, cronDay.value, cronWeekday.value)
})

watch(cronExpression, (val) => {
  if (cronFreq.value !== 'custom') {
    cronForm.value.cron_expression = val
  }
})

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function buildCronExpression(freq: string, minute: number, hour: number, day: number, weekday: number): string {
  switch (freq) {
    case 'minute':
      return `*/${minute || 1} * * * *`
    case 'hour':
      return `${minute} * * * *`
    case 'day':
      return `${minute} ${hour} * * *`
    case 'week':
      return `${minute} ${hour} * * ${weekday}`
    case 'month':
      return `${minute} ${hour} ${day} * *`
    default:
      return cronForm.value.cron_expression
  }
}

function parseCronExpression(expr: string) {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) {
    cronFreq.value = 'custom'
    return
  }
  const [m, h, dom, mon, dow] = parts
  if (m.startsWith('*/') && h === '*' && dom === '*' && mon === '*' && dow === '*') {
    cronFreq.value = 'minute'
    cronMinute.value = parseInt(m.slice(2)) || 5
  } else if (!m.includes('/') && !m.includes(',') && !m.includes('-') && h === '*' && dom === '*' && mon === '*' && dow === '*') {
    cronFreq.value = 'hour'
    cronMinute.value = parseInt(m) || 0
  } else if (!m.includes('/') && !m.includes(',') && !m.includes('-') && !h.includes('/') && !h.includes(',') && !h.includes('-') && dom === '*' && mon === '*' && dow === '*') {
    cronFreq.value = 'day'
    cronMinute.value = parseInt(m) || 0
    cronHour.value = parseInt(h) || 0
  } else if (dom === '*' && mon === '*' && dow !== '*') {
    cronFreq.value = 'week'
    cronMinute.value = parseInt(m) || 0
    cronHour.value = parseInt(h) || 0
    cronWeekday.value = parseInt(dow) || 1
  } else if (dom !== '*' && mon === '*' && dow === '*') {
    cronFreq.value = 'month'
    cronMinute.value = parseInt(m) || 0
    cronHour.value = parseInt(h) || 0
    cronDay.value = parseInt(dom) || 1
  } else {
    cronFreq.value = 'custom'
  }
}

function getConditionsSummary(conditions: AlertRuleCondition[]): string {
  if (!conditions || conditions.length === 0) return '无条件'
  return conditions.map(c => `${ConditionFieldMap[c.field] || c.field} ${ConditionOperatorMap[c.operator] || c.operator} ${c.value}`).join(' & ')
}

async function loadRules() {
  try {
    rules.value = await fetchAlertRules()
  } catch (e) {
    console.error(e)
  }
}

function selectRule(rule: AlertRule) {
  selectedRuleId.value = rule.id
  ruleForm.value = {
    id: rule.id,
    name: rule.name,
    description: rule.description,
    strategy_type: rule.strategy_type,
    alert_level: rule.alert_level,
    conditions: rule.conditions.map(c => ({ ...c })),
    logic_operator: rule.logic_operator,
    node_type: rule.node_type,
    silence_minutes: rule.silence_minutes,
    upgrade_enabled: rule.upgrade_enabled,
    upgrade_interval_minutes: rule.upgrade_interval_minutes,
    status: rule.status
  }
}

function openNewRule() {
  selectedRuleId.value = null
  ruleForm.value = {
    name: '',
    description: '',
    strategy_type: 1,
    alert_level: 2 as AlertLevel,
    conditions: [{ field: 'risk_score', operator: 'gte', value: '0.7' }],
    logic_operator: 'and',
    node_type: 'both',
    silence_minutes: 30,
    upgrade_enabled: false,
    upgrade_interval_minutes: 60,
    status: 'draft'
  }
}

function cancelRuleEdit() {
  ruleForm.value = null
  selectedRuleId.value = null
}

function addCondition() {
  if (!ruleForm.value) return
  ruleForm.value.conditions.push({ field: 'risk_score', operator: 'gte', value: '' })
}

function removeCondition(idx: number) {
  if (!ruleForm.value) return
  ruleForm.value.conditions.splice(idx, 1)
}

async function saveRule() {
  if (!ruleForm.value) return
  savingRule.value = true
  try {
    if (ruleForm.value.id) {
      const { id, ...data } = ruleForm.value
      await updateAlertRule(id, data as AlertRuleUpdateRequest)
    } else {
      await createAlertRule(ruleForm.value as AlertRuleCreateRequest)
    }
    await loadRules()
    cancelRuleEdit()
  } catch (e) {
    console.error(e)
  } finally {
    savingRule.value = false
  }
}

async function handleToggleRule(id: number) {
  try {
    await toggleAlertRule(id)
    await loadRules()
    const rule = rules.value.find(r => r.id === id)
    if (rule && selectedRuleId.value === id) {
      selectRule(rule)
    }
  } catch (e) {
    console.error(e)
  }
}

function confirmDeleteRule() {
  if (deletingRuleId.value == null) return
  deleteAlertRule(deletingRuleId.value).then(() => {
    loadRules()
    if (selectedRuleId.value === deletingRuleId.value) {
      cancelRuleEdit()
    }
  }).catch(console.error).finally(() => {
    showRuleDeleteConfirm.value = false
    deletingRuleId.value = null
  })
}

async function loadPresets() {
  try {
    presets.value = await fetchThresholdPresets()
  } catch (e) {
    console.error(e)
  }
}

function openNewPreset() {
  presetFormId.value = null
  presetForm.value = { name: '', description: '', thresholds: [] }
  showPresetModal.value = true
}

function openEditPreset(preset: ThresholdPreset) {
  presetFormId.value = preset.id
  presetForm.value = {
    name: preset.name,
    description: preset.description,
    thresholds: preset.thresholds.map(t => ({ ...t }))
  }
  showPresetModal.value = true
}

function addPresetThreshold() {
  presetForm.value.thresholds.push({ level: 1 as AlertLevel, field: 'preload_ratio', operator: 'gte', value: 0, color: '#eab308' })
}

function removePresetThreshold(idx: number) {
  presetForm.value.thresholds.splice(idx, 1)
}

async function savePreset() {
  savingPreset.value = true
  try {
    const data: ThresholdPresetCreateRequest = {
      name: presetForm.value.name,
      description: presetForm.value.description,
      thresholds: presetForm.value.thresholds
    }
    if (presetFormId.value) {
      await updateThresholdPreset(presetFormId.value, data)
    } else {
      await createThresholdPreset(data)
    }
    await loadPresets()
    showPresetModal.value = false
  } catch (e) {
    console.error(e)
  } finally {
    savingPreset.value = false
  }
}

async function handleSetDefault(id: number) {
  try {
    await setDefaultPreset(id)
    await loadPresets()
  } catch (e) {
    console.error(e)
  }
}

function confirmDeletePreset(id: number) {
  deletingPresetId.value = id
  showPresetDeleteConfirm.value = true
}

function doDeletePreset() {
  if (deletingPresetId.value == null) return
  deleteThresholdPreset(deletingPresetId.value).then(() => {
    loadPresets()
  }).catch(console.error).finally(() => {
    showPresetDeleteConfirm.value = false
    deletingPresetId.value = null
  })
}

async function loadCronTasks() {
  try {
    cronTasks.value = await fetchCronTasks()
  } catch (e) {
    console.error(e)
  }
}

function toggleCronExpand(id: number) {
  expandedCronId.value = expandedCronId.value === id ? null : id
}

function openNewCronTask() {
  cronFormId.value = null
  cronForm.value = { name: '', task_type: 'data_collect', cron_expression: '*/5 * * * *' }
  cronFreq.value = 'minute'
  cronMinute.value = 5
  cronHour.value = 0
  cronDay.value = 1
  cronWeekday.value = 1
  showCronModal.value = true
}

function openEditCronTask(task: CronTask) {
  cronFormId.value = task.id
  cronForm.value = {
    name: task.name,
    description: task.description,
    task_type: task.task_type,
    cron_expression: task.cron_expression,
    config: task.config
  }
  parseCronExpression(task.cron_expression)
  showCronModal.value = true
}

function onCronFreqChange() {
  if (cronFreq.value === 'minute') {
    cronMinute.value = 5
  } else if (cronFreq.value === 'hour') {
    cronMinute.value = 0
  } else if (cronFreq.value === 'day') {
    cronHour.value = 8
    cronMinute.value = 0
  } else if (cronFreq.value === 'week') {
    cronWeekday.value = 1
    cronHour.value = 8
    cronMinute.value = 0
  } else if (cronFreq.value === 'month') {
    cronDay.value = 1
    cronHour.value = 0
    cronMinute.value = 0
  }
}

function applyCronPreset(expr: string) {
  cronFreq.value = 'custom'
  cronForm.value.cron_expression = expr
  parseCronExpression(expr)
}

async function saveCronTask() {
  savingCron.value = true
  try {
    const data: CronTaskCreateRequest = {
      name: cronForm.value.name,
      description: cronForm.value.description,
      task_type: cronForm.value.task_type,
      cron_expression: cronForm.value.cron_expression,
      config: cronForm.value.config
    }
    if (cronFormId.value) {
      await updateCronTask(cronFormId.value, data as CronTaskUpdateRequest)
    } else {
      await createCronTask(data)
    }
    await loadCronTasks()
    showCronModal.value = false
  } catch (e) {
    console.error(e)
  } finally {
    savingCron.value = false
  }
}

async function handleToggleCronTask(task: CronTask) {
  try {
    await toggleCronTask(task.id)
    await loadCronTasks()
  } catch (e) {
    console.error(e)
  }
}

async function handleRunCronNow(task: CronTask) {
  try {
    await runCronTaskNow(task.id)
    await loadCronTasks()
  } catch (e) {
    console.error(e)
  }
}

function confirmDeleteCronTask(id: number) {
  deletingCronId.value = id
  showCronDeleteConfirm.value = true
}

function doDeleteCronTask() {
  if (deletingCronId.value == null) return
  deleteCronTask(deletingCronId.value).then(() => {
    loadCronTasks()
  }).catch(console.error).finally(() => {
    showCronDeleteConfirm.value = false
    deletingCronId.value = null
  })
}

onMounted(() => {
  loadRules()
  loadPresets()
  loadCronTasks()
})
</script>

<style scoped>
.config-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.85);
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}

.config-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #e2e8f0;
}

.config-title svg {
  color: #8b5cf6;
}

.config-title h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.header-tabs {
  display: flex;
  gap: 4px;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  padding: 3px;
}

.tab-btn {
  padding: 7px 18px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
}

.tab-btn:not(.active):hover {
  color: #e2e8f0;
  background: rgba(59, 130, 246, 0.1);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: rgba(71, 85, 105, 0.6);
  color: #cbd5e1;
  border: 1px solid rgba(100, 116, 139, 0.4);
}

.btn-secondary:hover {
  background: rgba(71, 85, 105, 0.9);
}

.btn-danger {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.3);
}

.btn-sm {
  padding: 5px 10px;
  font-size: 12px;
}

.config-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: 16px 20px 20px;
}

.tab-panel {
  height: 100%;
  display: flex;
  gap: 16px;
  min-height: 0;
}

.threshold-panel,
.cron-panel {
  display: block;
  overflow-y: auto;
}

.rule-list-panel {
  width: 340px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  backdrop-filter: blur(8px);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
  flex-shrink: 0;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.panel-count {
  font-size: 12px;
  color: #64748b;
}

.rule-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-list::-webkit-scrollbar {
  width: 6px;
}

.rule-list::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.rule-card {
  padding: 12px;
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.rule-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
}

.rule-card.selected {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.08);
}

.rule-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.rule-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.rule-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.rule-card-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
}

.strategy-badge {
  border: 1px solid;
  background: transparent;
}

.level-badge {
  color: white;
}

.status-badge {
  border: 1px solid;
  background: transparent;
}

.default-badge {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.4);
}

.type-badge {
  border: 1px solid;
  background: transparent;
}

.level-badge-sm {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  color: white;
}

.rule-card-summary {
  font-size: 12px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.rule-card-meta {
  font-size: 11px;
  color: #64748b;
}

.rule-edit-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 10px;
  backdrop-filter: blur(8px);
}

.empty-edit {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #475569;
}

.edit-form {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.edit-form-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.edit-form-scroll::-webkit-scrollbar {
  width: 6px;
}

.edit-form-scroll::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.edit-form-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid rgba(59, 130, 246, 0.15);
  flex-shrink: 0;
}

.edit-form-actions .btn {
  flex: none;
  padding: 8px 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
  font-weight: 500;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.9);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
  font-family: inherit;
}

.form-input:hover,
.form-select:hover,
.form-textarea:hover,
.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: rgba(59, 130, 246, 0.7);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-color {
  width: 32px;
  height: 32px;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.9);
  cursor: pointer;
  padding: 2px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.flex-1 {
  flex: 1;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.condition-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.cond-select {
  width: 120px;
  flex-shrink: 0;
}

.cond-input {
  width: 80px;
  flex-shrink: 0;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-remove {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.btn-remove:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.4);
}

.radio-group {
  display: flex;
  gap: 16px;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #cbd5e1;
  cursor: pointer;
}

.radio-option input {
  accent-color: #3b82f6;
}

.checkbox-option {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #cbd5e1;
  cursor: pointer;
}

.checkbox-option input {
  accent-color: #3b82f6;
}

.upgrade-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.inline-group {
  margin-bottom: 0;
}

.inline-group .form-label {
  margin-bottom: 4px;
}

.inline-group .form-input {
  width: 120px;
}

.preset-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preset-card {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  padding: 16px;
  transition: all 0.2s;
}

.preset-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
}

.preset-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.preset-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preset-name {
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.preset-actions {
  display: flex;
  gap: 8px;
}

.btn-text {
  background: none;
  border: none;
  color: #60a5fa;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-text:hover {
  background: rgba(59, 130, 246, 0.15);
}

.btn-text-danger {
  color: #f87171;
}

.btn-text-danger:hover {
  background: rgba(239, 68, 68, 0.15);
}

.preset-desc {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 12px;
}

.threshold-table-wrap {
  overflow-x: auto;
}

.threshold-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.threshold-table th {
  text-align: left;
  padding: 6px 10px;
  color: #64748b;
  font-weight: 500;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
}

.threshold-table td {
  padding: 6px 10px;
  color: #cbd5e1;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
}

.threshold-edit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin-bottom: 10px;
}

.threshold-edit-table th {
  text-align: left;
  padding: 6px 8px;
  color: #64748b;
  font-weight: 500;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
}

.threshold-edit-table td {
  padding: 6px 8px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
}

.threshold-edit-table .form-select,
.threshold-edit-table .form-input {
  padding: 5px 8px;
  font-size: 12px;
}

.cron-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cron-card {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.cron-card:hover {
  border-color: rgba(59, 130, 246, 0.4);
}

.cron-card.expanded {
  border-color: rgba(59, 130, 246, 0.5);
}

.cron-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
}

.cron-card-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.cron-task-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cron-card-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.cron-meta {
  font-size: 12px;
  color: #64748b;
  font-family: monospace;
}

.expand-icon {
  color: #64748b;
  transition: transform 0.2s;
}

.expand-icon.rotated {
  transform: rotate(180deg);
}

.cron-card-meta-row {
  display: flex;
  gap: 16px;
  padding: 0 16px 10px;
  flex-wrap: wrap;
}

.cron-meta-item {
  font-size: 12px;
  color: #64748b;
}

.cron-card-detail {
  padding: 0 16px 16px;
  border-top: 1px solid rgba(59, 130, 246, 0.1);
  background: rgba(15, 23, 42, 0.4);
}

.detail-section {
  margin-top: 14px;
}

.detail-title {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  margin-bottom: 6px;
}

.detail-content {
  font-size: 13px;
  color: #cbd5e1;
  line-height: 1.6;
}

.detail-code {
  font-size: 12px;
  color: #94a3b8;
  background: rgba(15, 23, 42, 0.6);
  padding: 10px;
  border-radius: 6px;
  border: 1px solid rgba(59, 130, 246, 0.1);
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
}

.error-text {
  color: #f87171;
}

.cron-detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(59, 130, 246, 0.15);
}

.action-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.action-start {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.action-start:hover {
  background: rgba(34, 197, 94, 0.25);
}

.action-stop {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.action-stop:hover {
  background: rgba(239, 68, 68, 0.25);
}

.action-run {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.action-run:hover {
  background: rgba(59, 130, 246, 0.25);
}

.action-edit {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
  border: 1px solid rgba(139, 92, 246, 0.3);
}

.action-edit:hover {
  background: rgba(139, 92, 246, 0.25);
}

.action-delete {
  background: rgba(100, 116, 139, 0.2);
  color: #94a3b8;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.action-delete:hover {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.3);
}

.action-toggle {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.action-toggle:hover {
  background: rgba(59, 130, 246, 0.25);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #475569;
  gap: 12px;
}

.empty-title {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
}

.confirm-text {
  font-size: 14px;
  color: #cbd5e1;
  margin: 0;
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

.modal {
  width: 420px;
  max-width: 90vw;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-lg {
  width: 640px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.modal-close:hover {
  color: #e2e8f0;
}

.modal-body {
  padding: 20px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-body::-webkit-scrollbar {
  width: 6px;
}

.modal-body::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.4);
  border-radius: 3px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.2);
}

.modal-footer .btn {
  flex: none;
  padding: 8px 20px;
}

.cron-editor {
  margin-top: 4px;
}

.cron-visual {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cron-freq-fields {
  padding-left: 0;
}

.cron-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 6px;
}

.cron-preview-label {
  font-size: 12px;
  color: #64748b;
}

.cron-preview-code {
  font-size: 13px;
  color: #60a5fa;
  font-family: monospace;
  background: none;
  padding: 0;
}

.cron-presets {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.cron-presets-label {
  font-size: 12px;
  color: #64748b;
  margin-right: 4px;
}

.quick-btn {
  padding: 4px 8px;
  background: rgba(71, 85, 105, 0.5);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 4px;
  color: #94a3b8;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
  color: #60a5fa;
}
</style>