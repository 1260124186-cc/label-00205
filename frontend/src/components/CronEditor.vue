<template>
  <div class="cron-editor">
    <div class="cron-display">
      <div class="cron-input-row">
        <div class="cron-field">
          <label>分</label>
          <input
            type="text"
            v-model="localParts[0]"
            @blur="onFieldBlur"
            class="cron-field-input"
            placeholder="*"
          />
        </div>
        <div class="cron-sep"></div>
        <div class="cron-field">
          <label>时</label>
          <input
            type="text"
            v-model="localParts[1]"
            @blur="onFieldBlur"
            class="cron-field-input"
            placeholder="*"
          />
        </div>
        <div class="cron-sep"></div>
        <div class="cron-field">
          <label>日</label>
          <input
            type="text"
            v-model="localParts[2]"
            @blur="onFieldBlur"
            class="cron-field-input"
            placeholder="*"
          />
        </div>
        <div class="cron-sep"></div>
        <div class="cron-field">
          <label>月</label>
          <input
            type="text"
            v-model="localParts[3]"
            @blur="onFieldBlur"
            class="cron-field-input"
            placeholder="*"
          />
        </div>
        <div class="cron-sep"></div>
        <div class="cron-field">
          <label>周</label>
          <input
            type="text"
            v-model="localParts[4]"
            @blur="onFieldBlur"
            class="cron-field-input"
            placeholder="*"
          />
        </div>
      </div>
      <div class="cron-preview">
        <span class="cron-label">Cron 表达式:</span>
        <code class="cron-expression">{{ cronExpression }}</code>
        <span class="cron-human">{{ humanReadable }}</span>
      </div>
    </div>

    <div class="cron-presets">
      <div class="presets-title">常用预设</div>
      <div class="presets-grid">
        <button
          v-for="preset in presets"
          :key="preset.value"
          class="preset-btn"
          :class="{ active: cronExpression === preset.value }"
          @click="applyPreset(preset.value)"
        >
          <span class="preset-name">{{ preset.label }}</span>
          <span class="preset-cron">{{ preset.value }}</span>
        </button>
      </div>
    </div>

    <div class="cron-builder">
      <div class="builder-title">可视化构建</div>
      <div class="builder-tabs">
        <button
          v-for="(tab, idx) in builderTabs"
          :key="idx"
          class="builder-tab"
          :class="{ active: activeTab === idx }"
          @click="activeTab = idx"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="builder-content">
        <!-- 分钟 -->
        <div v-if="activeTab === 0" class="builder-options">
          <label class="option-row">
            <input type="radio" v-model="minuteMode" value="every" @change="rebuildCron" />
            <span>每分钟</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="minuteMode" value="interval" @change="rebuildCron" />
            <span>每</span>
            <input
              type="number"
              v-model.number="minuteInterval"
              min="1"
              max="59"
              class="num-input"
              @change="rebuildCron"
            />
            <span>分钟执行</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="minuteMode" value="specific" @change="rebuildCron" />
            <span>指定分钟 (逗号分隔, 0-59)</span>
          </label>
          <input
            v-if="minuteMode === 'specific'"
            type="text"
            v-model="minuteSpecific"
            placeholder="例如: 0,15,30,45"
            class="text-input"
            @change="rebuildCron"
          />
        </div>
        <!-- 小时 -->
        <div v-if="activeTab === 1" class="builder-options">
          <label class="option-row">
            <input type="radio" v-model="hourMode" value="every" @change="rebuildCron" />
            <span>每小时</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="hourMode" value="interval" @change="rebuildCron" />
            <span>每</span>
            <input
              type="number"
              v-model.number="hourInterval"
              min="1"
              max="23"
              class="num-input"
              @change="rebuildCron"
            />
            <span>小时执行</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="hourMode" value="specific" @change="rebuildCron" />
            <span>指定小时 (逗号分隔, 0-23)</span>
          </label>
          <input
            v-if="hourMode === 'specific'"
            type="text"
            v-model="hourSpecific"
            placeholder="例如: 2,8,14,20"
            class="text-input"
            @change="rebuildCron"
          />
        </div>
        <!-- 日 -->
        <div v-if="activeTab === 2" class="builder-options">
          <label class="option-row">
            <input type="radio" v-model="dayMode" value="every" @change="rebuildCron" />
            <span>每天</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="dayMode" value="interval" @change="rebuildCron" />
            <span>每</span>
            <input
              type="number"
              v-model.number="dayInterval"
              min="1"
              max="31"
              class="num-input"
              @change="rebuildCron"
            />
            <span>天执行</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="dayMode" value="specific" @change="rebuildCron" />
            <span>指定日期 (逗号分隔, 1-31)</span>
          </label>
          <input
            v-if="dayMode === 'specific'"
            type="text"
            v-model="daySpecific"
            placeholder="例如: 1,15"
            class="text-input"
            @change="rebuildCron"
          />
        </div>
        <!-- 月 -->
        <div v-if="activeTab === 3" class="builder-options">
          <label class="option-row">
            <input type="radio" v-model="monthMode" value="every" @change="rebuildCron" />
            <span>每月</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="monthMode" value="interval" @change="rebuildCron" />
            <span>每</span>
            <input
              type="number"
              v-model.number="monthInterval"
              min="1"
              max="12"
              class="num-input"
              @change="rebuildCron"
            />
            <span>月执行</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="monthMode" value="specific" @change="rebuildCron" />
            <span>指定月份</span>
          </label>
          <div v-if="monthMode === 'specific'" class="month-checkboxes">
            <label v-for="m in 12" :key="m" class="month-check">
              <input
                type="checkbox"
                :value="m"
                v-model="monthSpecificArr"
                @change="rebuildCron"
              />
              {{ m }}月
            </label>
          </div>
        </div>
        <!-- 周 -->
        <div v-if="activeTab === 4" class="builder-options">
          <label class="option-row">
            <input type="radio" v-model="weekMode" value="every" @change="rebuildCron" />
            <span>每天 (不限制)</span>
          </label>
          <label class="option-row">
            <input type="radio" v-model="weekMode" value="specific" @change="rebuildCron" />
            <span>指定星期</span>
          </label>
          <div v-if="weekMode === 'specific'" class="week-checkboxes">
            <label v-for="(w, i) in weekNames" :key="i" class="week-check">
              <input
                type="checkbox"
                :value="i"
                v-model="weekSpecificArr"
                @change="rebuildCron"
              />
              {{ w }}
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const localParts = ref(['*', '*', '*', '*', '*'])

const presets = [
  { label: '每分钟', value: '* * * * *' },
  { label: '每5分钟', value: '*/5 * * * *' },
  { label: '每30分钟', value: '*/30 * * * *' },
  { label: '每小时', value: '0 * * * *' },
  { label: '每2小时', value: '0 */2 * * *' },
  { label: '每天凌晨2点', value: '0 2 * * *' },
  { label: '每天凌晨4点', value: '0 4 * * *' },
  { label: '每周日凌晨2点', value: '0 2 * * 0' },
  { label: '每月1日凌晨3点', value: '0 3 1 * *' },
  { label: '工作日9点', value: '0 9 * * 1-5' },
]

const builderTabs = [
  { label: '分钟', key: 'minute' },
  { label: '小时', key: 'hour' },
  { label: '日', key: 'day' },
  { label: '月', key: 'month' },
  { label: '周', key: 'week' },
]

const activeTab = ref(0)

const minuteMode = ref<'every' | 'interval' | 'specific'>('every')
const minuteInterval = ref(5)
const minuteSpecific = ref('')

const hourMode = ref<'every' | 'interval' | 'specific'>('every')
const hourInterval = ref(2)
const hourSpecific = ref('')

const dayMode = ref<'every' | 'interval' | 'specific'>('every')
const dayInterval = ref(1)
const daySpecific = ref('')

const monthMode = ref<'every' | 'interval' | 'specific'>('every')
const monthInterval = ref(1)
const monthSpecificArr = ref<number[]>([])

const weekMode = ref<'every' | 'specific'>('every')
const weekSpecificArr = ref<number[]>([])
const weekNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const cronExpression = computed(() => localParts.value.join(' '))

const humanReadable = computed(() => {
  const [m, h, dom, mon, dow] = localParts.value
  const parts: string[] = []

  if (m === '*') parts.push('每分钟')
  else if (m.startsWith('*/')) parts.push(`每${m.slice(2)}分钟`)
  else parts.push(`${m}分`)

  if (h === '*') parts.push('每小时')
  else if (h.startsWith('*/')) parts.push(`每${h.slice(2)}小时`)
  else parts.push(`${h}时`)

  if (dom !== '*') {
    if (dom.startsWith('*/')) parts.push(`每${dom.slice(2)}天`)
    else parts.push(`${dom}日`)
  }

  if (mon !== '*') {
    if (mon.startsWith('*/')) parts.push(`每${mon.slice(2)}月`)
    else parts.push(`${mon}月`)
  }

  if (dow !== '*') {
    const days = dow.split(',').map(d => {
      if (d.includes('-')) {
        const [s, e] = d.split('-').map(Number)
        const names: string[] = []
        for (let i = s; i <= e; i++) names.push(weekNames[i] || '')
        return names.join('到')
      }
      return weekNames[Number(d)] || d
    })
    parts.push(days.join('、'))
  }

  return parts.join(' ')
})

function onFieldBlur() {
  emit('update:modelValue', cronExpression.value)
}

function applyPreset(value: string) {
  localParts.value = value.split(' ')
  parseCronToBuilder(value)
  emit('update:modelValue', value)
}

function rebuildCron() {
  let m = '*', h = '*', dom = '*', mon = '*', dow = '*'

  if (minuteMode.value === 'interval') m = `*/${minuteInterval.value}`
  else if (minuteMode.value === 'specific' && minuteSpecific.value) m = minuteSpecific.value

  if (hourMode.value === 'interval') h = `*/${hourInterval.value}`
  else if (hourMode.value === 'specific' && hourSpecific.value) h = hourSpecific.value

  if (dayMode.value === 'interval') dom = `*/${dayInterval.value}`
  else if (dayMode.value === 'specific' && daySpecific.value) dom = daySpecific.value

  if (monthMode.value === 'interval') mon = `*/${monthInterval.value}`
  else if (monthMode.value === 'specific' && monthSpecificArr.value.length > 0) {
    mon = monthSpecificArr.value.slice().sort((a, b) => a - b).join(',')
  }

  if (weekMode.value === 'specific' && weekSpecificArr.value.length > 0) {
    dow = weekSpecificArr.value.slice().sort((a, b) => a - b).join(',')
  }

  localParts.value = [m, h, dom, mon, dow]
  emit('update:modelValue', cronExpression.value)
}

function parseCronToBuilder(cron: string) {
  const parts = cron.trim().split(/\s+/).concat(['*', '*', '*', '*', '*']).slice(0, 5)
  const [m, h, dom, mon, dow] = parts

  if (m === '*') minuteMode.value = 'every'
  else if (m.startsWith('*/')) {
    minuteMode.value = 'interval'
    minuteInterval.value = parseInt(m.slice(2)) || 5
  } else {
    minuteMode.value = 'specific'
    minuteSpecific.value = m
  }

  if (h === '*') hourMode.value = 'every'
  else if (h.startsWith('*/')) {
    hourMode.value = 'interval'
    hourInterval.value = parseInt(h.slice(2)) || 2
  } else {
    hourMode.value = 'specific'
    hourSpecific.value = h
  }

  if (dom === '*') dayMode.value = 'every'
  else if (dom.startsWith('*/')) {
    dayMode.value = 'interval'
    dayInterval.value = parseInt(dom.slice(2)) || 1
  } else {
    dayMode.value = 'specific'
    daySpecific.value = dom
  }

  if (mon === '*') monthMode.value = 'every'
  else if (mon.startsWith('*/')) {
    monthMode.value = 'interval'
    monthInterval.value = parseInt(mon.slice(2)) || 1
  } else {
    monthMode.value = 'specific'
    monthSpecificArr.value = mon.split(',').map(n => parseInt(n)).filter(n => !isNaN(n))
  }

  if (dow === '*') weekMode.value = 'every'
  else {
    weekMode.value = 'specific'
    weekSpecificArr.value = dow.split(',').map(n => parseInt(n)).filter(n => !isNaN(n))
  }
}

watch(
  () => props.modelValue,
  (val) => {
    if (val && val !== cronExpression.value) {
      const parts = val.trim().split(/\s+/).concat(['*', '*', '*', '*', '*']).slice(0, 5)
      localParts.value = parts
      parseCronToBuilder(val)
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (props.modelValue) {
    parseCronToBuilder(props.modelValue)
  }
})
</script>

<style scoped>
.cron-editor {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  padding: 20px;
  color: #e2e8f0;
}

.cron-display {
  margin-bottom: 20px;
}

.cron-input-row {
  display: flex;
  align-items: stretch;
  gap: 8px;
  margin-bottom: 12px;
}

.cron-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.cron-field label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.cron-field-input {
  width: 100%;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  padding: 8px 10px;
  color: #e2e8f0;
  font-size: 14px;
  font-family: 'Courier New', monospace;
  text-align: center;
  outline: none;
  transition: all 0.2s;
}

.cron-field-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.cron-sep {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #64748b;
  padding-top: 18px;
}

.cron-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 14px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
}

.cron-label {
  font-size: 13px;
  color: #94a3b8;
}

.cron-expression {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  padding: 4px 10px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.cron-human {
  font-size: 13px;
  color: #94a3b8;
}

.cron-presets {
  margin-bottom: 20px;
}

.presets-title,
.builder-title {
  font-size: 13px;
  font-weight: 600;
  color: #cbd5e1;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 8px;
}

.preset-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 12px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 8px;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.2s;
}

.preset-btn:hover {
  border-color: rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.08);
}

.preset-btn.active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(37, 99, 235, 0.25));
  border-color: #3b82f6;
}

.preset-name {
  font-size: 13px;
  font-weight: 500;
}

.preset-cron {
  font-size: 11px;
  color: #94a3b8;
  font-family: 'Courier New', monospace;
}

.builder-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.builder-tab {
  padding: 6px 14px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 6px;
  color: #94a3b8;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.builder-tab:hover {
  color: #cbd5e1;
  border-color: rgba(59, 130, 246, 0.3);
}

.builder-tab.active {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border-color: rgba(59, 130, 246, 0.5);
}

.builder-content {
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
  padding: 14px;
}

.builder-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #cbd5e1;
  cursor: pointer;
}

.option-row input[type="radio"] {
  accent-color: #3b82f6;
}

.num-input,
.text-input {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 4px;
  padding: 4px 8px;
  color: #e2e8f0;
  font-size: 13px;
  outline: none;
  width: 80px;
}

.text-input {
  width: 100%;
  margin-left: 24px;
}

.num-input:focus,
.text-input:focus {
  border-color: #3b82f6;
}

.month-checkboxes,
.week-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: 24px;
}

.month-check,
.week-check {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 4px;
  font-size: 12px;
  color: #cbd5e1;
  cursor: pointer;
}

.month-check input,
.week-check input {
  accent-color: #3b82f6;
}
</style>
