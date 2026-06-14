import type {
  Bolt,
  Flange,
  Collector,
  Position,
  TopologyData,
  StatusCode,
  Statistics,
  AlertEvent,
  AlertStatus,
  AlertLevel,
  AlertStrategy,
  PreloadTrendPoint,
  ProphetForecast,
  StatusPrediction,
  TrendAnalysisData,
  ModelEntry,
  ModelVersion,
  TrainingSession,
  EpochMetrics,
  TrainingStatus
} from '@/types'

const collectorNames = ['一号采集器', '二号采集器', '三号采集器', '四号采集器', '五号采集器']
const positionNames = ['A面', 'B面', 'C面', 'D面', 'E面', '地锚', '法兰盘', '弯头']
const splitterNums = ['SP01', 'SP02', 'SP03', 'SP04', 'SP05']

function randomStatus(): StatusCode {
  const r = Math.random()
  if (r < 0.58) return 0
  if (r < 0.72) return 1
  if (r < 0.85) return 2
  if (r < 0.95) return 3
  return 4
}

function randomRiskLevel(code: StatusCode): 'low' | 'medium' | 'high' {
  if (code <= 1) return 'low'
  if (code <= 2) return 'medium'
  return 'high'
}

function generateCollectors(): Collector[] {
  const collectors: Collector[] = []
  for (let i = 0; i < 5; i++) {
    const id = `COL${String(i + 1).padStart(3, '0')}`
    const statusRoll = Math.random()
    collectors.push({
      collector_id: id,
      collector_name: collectorNames[i],
      location: i < 3 ? '主厂房东区' : '主厂房西区',
      status: statusRoll < 0.85 ? 'online' : statusRoll < 0.95 ? 'warning' : 'offline',
      last_heartbeat: new Date(Date.now() - Math.random() * 300000).toISOString(),
      flange_count: 0,
      bolt_count: 0
    })
  }
  return collectors
}

function generateTopology(): TopologyData {
  const collectors = generateCollectors()
  const flanges: Flange[] = []
  const bolts: Bolt[] = []
  const positionMap = new Map<string, Position>()

  let boltIdx = 0

  for (const collector of collectors) {
    const numPositions = 2 + Math.floor(Math.random() * 3)
    const usedPositions = new Set<string>()

    for (let p = 0; p < numPositions; p++) {
      let posName: string
      do {
        posName = positionNames[Math.floor(Math.random() * positionNames.length)]
      } while (usedPositions.has(posName))
      usedPositions.add(posName)

      const splitter = splitterNums[Math.floor(Math.random() * splitterNums.length)]
      const flangeId = `${collector.collector_id}-${splitter}-${posName}`
      const boltCount = 4 + Math.floor(Math.random() * 8)
      const flangeBolts: Bolt[] = []

      let worstStatusCode: StatusCode = 0
      let worstRiskScore = 0
      let worstBoltId = ''
      let worstBoltHi = 100

      for (let b = 0; b < boltCount; b++) {
        boltIdx++
        const boltId = `B${String(2700 + boltIdx).padStart(4, '0')}`
        const statusCode = randomStatus()
        const nominal = 400 + Math.random() * 400
        const preload = nominal * (0.85 + Math.random() * 0.25)
        const confidence = 0.7 + Math.random() * 0.3
        const riskScore = Math.max(1, Math.min(10, 10 - statusCode * 2 + (Math.random() - 0.5) * 1.5))
        const healthIdx = Math.max(0, Math.min(100, 100 - statusCode * 20 + (Math.random() - 0.5) * 10))

        const bolt: Bolt = {
          bolt_id: boltId,
          collector_id: collector.collector_id,
          splitter_num: splitter,
          position: posName,
          flange_id: flangeId,
          current_preload: Math.round(preload * 100) / 100,
          nominal_preload: Math.round(nominal * 100) / 100,
          status_code: statusCode,
          confidence: Math.round(confidence * 10000) / 10000,
          risk_score: Math.round(riskScore * 10) / 10,
          risk_level: randomRiskLevel(statusCode),
          diagnosis: generateDiagnosis(statusCode),
          recommendations: generateRecommendations(statusCode),
          last_update_time: new Date(Date.now() - Math.random() * 60000).toISOString(),
          health_index: Math.round(healthIdx * 10) / 10
        }
        flangeBolts.push(bolt)
        bolts.push(bolt)

        if (statusCode > worstStatusCode) {
          worstStatusCode = statusCode
        }
        if (riskScore < worstRiskScore || worstRiskScore === 0) {
          worstRiskScore = riskScore
        }
        if (healthIdx < worstBoltHi) {
          worstBoltHi = healthIdx
          worstBoltId = boltId
        }
      }

      const flangeStatus = worstStatusCode
      const flangeConfidence = flangeBolts.reduce((s, b) => s + b.confidence, 0) / flangeBolts.length
      const flangeRisk = flangeBolts.reduce((s, b) => s + b.risk_score, 0) / flangeBolts.length

      const flange: Flange = {
        flange_id: flangeId,
        flange_name: `${collector.collector_name.slice(0, 2)}-${posName}`,
        collector_id: collector.collector_id,
        splitter_num: splitter,
        position: posName,
        bolt_count: boltCount,
        status_code: flangeStatus,
        confidence: Math.round(flangeConfidence * 10000) / 10000,
        risk_score: Math.round(flangeRisk * 10) / 10,
        risk_level: randomRiskLevel(flangeStatus),
        diagnosis: generateDiagnosis(flangeStatus),
        recommendations: generateRecommendations(flangeStatus),
        attention_weights: flangeBolts.map(() => Math.round(Math.random() * 1000) / 1000),
        last_update_time: new Date(Date.now() - Math.random() * 60000).toISOString(),
        health_index: Math.round(flangeBolts.reduce((s, b) => s + (b.health_index || 0), 0) / flangeBolts.length * 10) / 10,
        worst_bolt_id: worstBoltId,
        worst_bolt_hi: Math.round(worstBoltHi * 10) / 10
      }
      flanges.push(flange)

      collector.flange_count++
      collector.bolt_count += boltCount

      const posKey = `${collector.collector_id}|${posName}`
      if (!positionMap.has(posKey)) {
        positionMap.set(posKey, {
          position: posName,
          collector_id: collector.collector_id,
          collector_name: collector.collector_name,
          flange_count: 0,
          bolt_count: 0
        })
      }
      const posEntry = positionMap.get(posKey)!
      posEntry.flange_count++
      posEntry.bolt_count += boltCount
    }
  }

  const positions = Array.from(positionMap.values())

  const statusDist: Record<StatusCode, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 }
  const flangeStatusDist: Record<StatusCode, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 }
  let riskDist = { low: 0, medium: 0, high: 0 }
  let online = 0
  let hiSum = 0

  for (const b of bolts) {
    statusDist[b.status_code]++
    if (b.risk_level === 'low') riskDist.low++
    else if (b.risk_level === 'medium') riskDist.medium++
    else riskDist.high++
    hiSum += b.health_index || 0
  }
  for (const f of flanges) {
    flangeStatusDist[f.status_code]++
  }
  for (const c of collectors) {
    if (c.status === 'online' || c.status === 'warning') online++
  }

  const stats: Statistics = {
    total_bolts: bolts.length,
    total_flanges: flanges.length,
    total_collectors: collectors.length,
    status_distribution: statusDist,
    flange_status_distribution: flangeStatusDist,
    risk_distribution: riskDist,
    online_collectors: online,
    avg_health_index: Math.round((hiSum / Math.max(1, bolts.length)) * 10) / 10
  }

  return {
    collectors,
    flanges,
    bolts,
    positions,
    stats,
    update_time: new Date().toISOString()
  }
}

function generateDiagnosis(code: StatusCode): string {
  const map: Record<StatusCode, string[]> = {
    0: ['预紧力稳定区间内波动', '状态良好，持续监测中'],
    1: ['预紧力趋势出现轻微偏离', '波动幅度略大于历史均值'],
    2: ['预紧力持续偏离正常区间超过3天', '存在松动趋势，建议现场检查'],
    3: ['预紧力显著下降，接近阈值', '存在过载或松动前兆，风险较高'],
    4: ['预紧力骤降，疑似断裂或严重松动', '必须立即停机处理']
  }
  const arr = map[code]
  return arr[Math.floor(Math.random() * arr.length)]
}

function generateRecommendations(code: StatusCode): string[] {
  const map: Record<StatusCode, string[]> = {
    0: ['继续正常监测周期'],
    1: ['加强监测频率至每日2次', '记录异常特征并跟踪趋势'],
    2: ['组织专业人员现场检查', '制定维护方案和备件准备'],
    3: ['立即实施扭矩复核', '准备应急处理方案，防止事故扩大'],
    4: ['立即停机检修', '更换螺栓并检查连接面损伤', '进行全面安全评估']
  }
  return map[code]
}

export function getMockTopology(): TopologyData {
  return generateTopology()
}

export function refreshMockStatus(data: TopologyData): TopologyData {
  for (const bolt of data.bolts) {
    if (Math.random() < 0.08) {
      const delta = Math.random() < 0.5 ? -1 : 1
      const newCode = Math.max(0, Math.min(4, bolt.status_code + delta)) as StatusCode
      bolt.status_code = newCode
      bolt.risk_level = randomRiskLevel(newCode)
      bolt.risk_score = Math.max(1, Math.min(10, 10 - newCode * 2 + (Math.random() - 0.5) * 1.5))
      bolt.risk_score = Math.round(bolt.risk_score * 10) / 10
      bolt.diagnosis = generateDiagnosis(newCode)
      bolt.recommendations = generateRecommendations(newCode)
      bolt.confidence = Math.round((0.7 + Math.random() * 0.3) * 10000) / 10000
      bolt.last_update_time = new Date().toISOString()
    }
    const drift = (Math.random() - 0.5) * bolt.nominal_preload * 0.02
    bolt.current_preload = Math.round((bolt.nominal_preload * (0.88 + Math.random() * 0.2) + drift) * 100) / 100
  }

  for (const flange of data.flanges) {
    const flangeBolts = data.bolts.filter(b => b.flange_id === flange.flange_id)
    let worst: StatusCode = 0
    let worstHi = 100
    let worstId = ''
    let riskSum = 0
    let confSum = 0
    let hiSum = 0

    for (const b of flangeBolts) {
      if (b.status_code > worst) worst = b.status_code
      if ((b.health_index || 100) < worstHi) {
        worstHi = b.health_index || 100
        worstId = b.bolt_id
      }
      riskSum += b.risk_score
      confSum += b.confidence
      hiSum += b.health_index || 0
    }

    flange.status_code = worst
    flange.risk_level = randomRiskLevel(worst)
    flange.risk_score = Math.round((riskSum / flangeBolts.length) * 10) / 10
    flange.confidence = Math.round((confSum / flangeBolts.length) * 10000) / 10000
    flange.health_index = Math.round((hiSum / flangeBolts.length) * 10) / 10
    flange.worst_bolt_id = worstId
    flange.worst_bolt_hi = Math.round(worstHi * 10) / 10
    flange.diagnosis = generateDiagnosis(worst)
    flange.recommendations = generateRecommendations(worst)
    flange.last_update_time = new Date().toISOString()
  }

  const statusDist: Record<StatusCode, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 }
  const flangeStatusDist: Record<StatusCode, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 }
  const riskDist = { low: 0, medium: 0, high: 0 }
  let hiSum = 0

  for (const b of data.bolts) {
    statusDist[b.status_code]++
    if (b.risk_level === 'low') riskDist.low++
    else if (b.risk_level === 'medium') riskDist.medium++
    else riskDist.high++
    hiSum += b.health_index || 0
  }
  for (const f of data.flanges) {
    flangeStatusDist[f.status_code]++
  }

  data.stats.status_distribution = statusDist
  data.stats.flange_status_distribution = flangeStatusDist
  data.stats.risk_distribution = riskDist
  data.stats.avg_health_index = Math.round((hiSum / Math.max(1, data.bolts.length)) * 10) / 10
  data.update_time = new Date().toISOString()

  return data
}

// ==================== 预警 Mock 数据 ====================

const alertTitles = [
  '螺栓预紧力异常下降',
  '法兰面密封泄漏预警',
  '预紧力波动异常',
  '螺栓松动风险预警',
  '密封性能下降',
  '预紧力超出安全阈值预警',
  '法兰面应力不均',
  '螺栓疲劳损伤预警'
]

const alertContents = [
  '检测到预紧力持续下降，已低于正常范围，建议尽快检查。',
  '法兰面螺栓预紧力分布不均，存在泄漏风险。',
  '近期预紧力波动较大，可能存在外部干扰或松动。',
  '基于趋势分析显示螺栓存在松动趋势，风险等级升高。',
  '密封性能指标下降，需关注密封状态。',
  '预紧力已接近安全阈值，需及时处理。',
  '法兰面各螺栓应力分布不均匀，建议复核。',
  '基于历史数据分析，螺栓存在疲劳损伤风险。'
]

function randomAlert(): AlertStatus {
  const r = Math.random()
  if (r < 0.4) return 'pending'
  if (r < 0.7) return 'processing'
  if (r < 0.9) return 'resolved'
  return 'ignored'
}

function randomLevel(): AlertLevel {
  const r = Math.random()
  if (r < 0.35) return 1
  if (r < 0.65) return 2
  if (r < 0.9) return 3
  return 4
}

function randomStrategy(): AlertStrategy {
  return Math.random() < 0.6 ? 1 : 2
}

function randomNodeType(): 'bolt' | 'flange' {
  return Math.random() < 0.7 ? 'bolt' : 'flange'
}

export function generateMockAlerts(count = 30): AlertEvent[] {
  const alerts: AlertEvent[] = []
  const now = Date.now()

  for (let i = 0; i < count; i++) {
    const level = randomLevel()
    const status = randomAlert()
    const nodeType = randomNodeType()
    const strategy = randomStrategy()
    const createTime = new Date(now - Math.random() * 7 * 24 * 60 * 60 * 1000)
    const titleIdx = Math.floor(Math.random() * alertTitles.length)

    const alert: AlertEvent = {
      id: i + 1,
      alert_no: `ALT${String(10000 + i)}`,
      rule_id: Math.floor(Math.random() * 10) + 1,
      alert_level: level,
      original_level: level > 1 ? (level - 1) as AlertLevel : null,
      node_type: nodeType,
      node_id: nodeType === 'bolt'
        ? `B${String(2700 + Math.floor(Math.random() * 50)).padStart(4, '0')}`
        : `F${String(100 + Math.floor(Math.random() * 20)).padStart(3, '0')}`,
      title: alertTitles[titleIdx],
      content: alertContents[titleIdx],
      confidence: Math.round((0.7 + Math.random() * 0.3) * 10000) / 10000,
      risk_score: Math.round((3 + Math.random() * 7) * 10) / 10,
      recommendations: generateRecommendations(level as unknown as StatusCode),
      status: status,
      handler_id: status !== 'pending' ? `user${Math.floor(Math.random() * 10)}` : null,
      handler_name: status !== 'pending' ? ['张三', '李四', '王五', '赵六'][Math.floor(Math.random() * 4)] : null,
      handle_time: status !== 'pending' ? new Date(createTime.getTime() + Math.random() * 2 * 60 * 60 * 1000).toISOString() : null,
      handle_note: status === 'resolved' ? '已现场检查并处理完毕' : status === 'processing' ? '正在处理中' : null,
      is_upgraded: Math.random() < 0.2,
      upgrade_count: Math.floor(Math.random() * 3),
      last_upgrade_time: Math.random() < 0.2 ? new Date(createTime.getTime() + Math.random() * 60 * 60 * 1000).toISOString() : null,
      work_order_id: status === 'processing' || status === 'resolved' ? Math.floor(Math.random() * 100) + 1 : null,
      source_prediction_id: Math.floor(Math.random() * 1000) + 1,
      silence_until: null,
      create_time: createTime.toISOString(),
      update_time: new Date(createTime.getTime() + Math.random() * 3600000).toISOString(),
      strategy_type: strategy
    }

    alerts.push(alert)
  }

  return alerts
}

export function generateMockTrendData(boltId: string, nominalPreload: number): TrendAnalysisData {
  const now = Date.now()
  const oneDayMs = 24 * 60 * 60 * 1000
  const historyDays = 60
  const forecastDays = 30

  const history: PreloadTrendPoint[] = []
  let currentValue = nominalPreload * (0.92 + Math.random() * 0.12)
  const driftPerDay = nominalPreload * (Math.random() < 0.3 ? -0.003 : -0.001)

  for (let i = historyDays; i >= 0; i--) {
    const ts = new Date(now - i * oneDayMs)
    const noise = (Math.random() - 0.5) * nominalPreload * 0.03
    const seasonal = Math.sin((i / 30) * Math.PI * 2) * nominalPreload * 0.01
    currentValue = currentValue + driftPerDay + noise + seasonal
    currentValue = Math.max(nominalPreload * 0.5, Math.min(nominalPreload * 1.2, currentValue))

    history.push({
      timestamp: ts.toISOString(),
      value: Math.round(currentValue * 100) / 100
    })
  }

  const lastValue = history[history.length - 1].value
  const forecast: ProphetForecast[] = []
  let yhat = lastValue
  const forecastDrift = driftPerDay * 1.2
  const uncertaintyBase = nominalPreload * 0.02

  for (let i = 1; i <= forecastDays; i++) {
    const ts = new Date(now + i * oneDayMs)
    yhat = yhat + forecastDrift + (Math.random() - 0.5) * nominalPreload * 0.005
    yhat = Math.max(nominalPreload * 0.4, yhat)
    const uncertainty = uncertaintyBase * (1 + i * 0.08)

    forecast.push({
      ds: ts.toISOString(),
      yhat: Math.round(yhat * 100) / 100,
      yhat_lower: Math.round((yhat - uncertainty) * 100) / 100,
      yhat_upper: Math.round((yhat + uncertainty) * 100) / 100,
      trend: Math.round((lastValue + forecastDrift * i) * 100) / 100
    })
  }

  const statusPredictions: StatusPrediction[] = []
  const thresholdNormal = nominalPreload * 0.9
  const thresholdAttention = nominalPreload * 0.85
  const thresholdCheck = nominalPreload * 0.8
  const thresholdEmergency = nominalPreload * 0.7

  for (let i = 1; i <= forecastDays; i += 3) {
    const ts = new Date(now + i * oneDayMs)
    const fc = forecast[i - 1]
    let predictedStatus: StatusCode = 0
    let riskLevel: 'low' | 'medium' | 'high' = 'low'

    if (fc.yhat >= thresholdNormal) {
      predictedStatus = 0
      riskLevel = 'low'
    } else if (fc.yhat >= thresholdAttention) {
      predictedStatus = 1
      riskLevel = 'low'
    } else if (fc.yhat >= thresholdCheck) {
      predictedStatus = 2
      riskLevel = 'medium'
    } else if (fc.yhat >= thresholdEmergency) {
      predictedStatus = 3
      riskLevel = 'high'
    } else {
      predictedStatus = 4
      riskLevel = 'high'
    }

    const confidence = Math.max(0.5, Math.min(0.99, 0.85 - i * 0.01 + Math.random() * 0.1))

    statusPredictions.push({
      timestamp: ts.toISOString(),
      predicted_status: predictedStatus,
      confidence: Math.round(confidence * 10000) / 10000,
      risk_level: riskLevel
    })
  }

  return {
    bolt_id: boltId,
    nominal_preload: nominalPreload,
    history,
    forecast,
    status_predictions: statusPredictions
  }
}

// ==================== 模型管理 Mock 数据 ====================

const modelDescriptions: Record<string, string> = {
  bolt_B001: 'B001螺栓LSTM状态预测模型',
  bolt_B002: 'B002螺栓LSTM状态预测模型',
  bolt_B003: 'B003螺栓LSTM状态预测模型',
  flange_F001: 'F001法兰注意力机制模型',
  flange_F002: 'F002法兰注意力机制模型',
  flange_F003: 'F003法兰注意力机制模型',
}

let mockModelEntries: ModelEntry[] | null = null
let mockVersionsMap: Record<string, ModelVersion[]> = {}
let mockSessionsMap: Record<string, TrainingSession[]> = {}

function randomTrainingStatus(): TrainingStatus {
  const r = Math.random()
  if (r < 0.5) return 'completed'
  if (r < 0.7) return 'running'
  if (r < 0.85) return 'failed'
  if (r < 0.95) return 'pending'
  return 'stopped'
}

function generateMockEpochMetrics(totalEpochs: number): EpochMetrics[] {
  const metrics: EpochMetrics[] = []
  let trainLoss = 1.5 + Math.random() * 0.5
  let valLoss = 1.8 + Math.random() * 0.5
  let trainAcc = 0.3 + Math.random() * 0.1
  let valAcc = 0.25 + Math.random() * 0.1
  const baseLr = 0.001

  for (let i = 1; i <= totalEpochs; i++) {
    trainLoss *= (0.92 + Math.random() * 0.05)
    valLoss *= (0.93 + Math.random() * 0.06)
    trainAcc += (0.005 + Math.random() * 0.012) * (1 - trainAcc)
    valAcc += (0.004 + Math.random() * 0.01) * (1 - valAcc)

    if (i === Math.floor(totalEpochs * 0.6)) {
      trainAcc += 0.02
      valAcc += 0.015
    }

    metrics.push({
      epoch: i,
      train_loss: Math.round(trainLoss * 10000) / 10000,
      val_loss: Math.round(valLoss * 10000) / 10000,
      train_acc: Math.round(Math.min(0.99, trainAcc) * 10000) / 10000,
      val_acc: Math.round(Math.min(0.98, valAcc) * 10000) / 10000,
      learning_rate: i < Math.floor(totalEpochs * 0.6) ? baseLr : baseLr * 0.1,
      duration_seconds: Math.round((1.5 + Math.random() * 3) * 100) / 100,
      timestamp: new Date(Date.now() - (totalEpochs - i) * 5000).toISOString()
    })
  }

  return metrics
}

function generateMockVersions(modelId: string, modelType: string): ModelVersion[] {
  const count = 2 + Math.floor(Math.random() * 4)
  const versions: ModelVersion[] = []
  const now = Date.now()

  for (let i = 0; i < count; i++) {
    const major = 1
    const minor = Math.floor(i / 3)
    const patch = i % 3
    const version = `v${major}.${minor}.${patch}`
    const isActive = i === count - 1
    const daysAgo = (count - i) * 3 + Math.floor(Math.random() * 5)
    const createdAt = new Date(now - daysAgo * 24 * 60 * 60 * 1000)

    const baseAcc = 0.75 + (i / count) * 0.15 + Math.random() * 0.05
    const baseLoss = 0.6 - (i / count) * 0.2 + (Math.random() - 0.5) * 0.1

    versions.push({
      version,
      model_id: modelId,
      model_type: modelType,
      created_at: createdAt.toISOString(),
      file_path: `./trained_models/${modelType}/${modelId}/${version}/${modelType}_${modelId}.pt`,
      file_hash: Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
      metrics: {
        val_acc: Math.round(Math.min(0.98, baseAcc) * 10000) / 10000,
        train_acc: Math.round(Math.min(0.99, baseAcc + 0.03) * 10000) / 10000,
        val_loss: Math.round(Math.max(0.1, baseLoss) * 10000) / 10000,
        train_loss: Math.round(Math.max(0.05, baseLoss - 0.05) * 10000) / 10000,
        f1_score: Math.round(Math.min(0.97, baseAcc - 0.02) * 10000) / 10000,
        precision: Math.round(Math.min(0.98, baseAcc + 0.01) * 10000) / 10000,
        recall: Math.round(Math.min(0.97, baseAcc - 0.01) * 10000) / 10000,
      },
      config: {
        epochs: 30 + Math.floor(Math.random() * 20),
        learning_rate: 0.001,
        batch_size: 32,
        hidden_size: modelType === 'bolt' ? 128 : 64,
        num_layers: modelType === 'bolt' ? 2 : 3,
        dropout: 0.2 + Math.random() * 0.1,
      },
      is_active: isActive,
      description: i === 0 ? '初始版本' : i === count - 1 ? '最新版本，性能优化' : '中间迭代版本'
    })
  }

  return versions
}

function generateMockSessions(modelId: string, modelType: string): TrainingSession[] {
  const count = 1 + Math.floor(Math.random() * 3)
  const sessions: TrainingSession[] = []
  const now = Date.now()

  for (let i = 0; i < count; i++) {
    const totalEpochs = 30 + Math.floor(Math.random() * 20)
    const daysAgo = i * 3 + Math.floor(Math.random() * 5)
    const startTime = new Date(now - daysAgo * 24 * 60 * 60 * 1000)
    const status: TrainingStatus = i === 0 && Math.random() < 0.3 ? 'running' : i === 0 && Math.random() < 0.05 ? 'failed' : 'completed'
    const currentEpoch = status === 'running' ? Math.floor(totalEpochs * (0.3 + Math.random() * 0.5)) : totalEpochs

    const metricsHistory = generateMockEpochMetrics(currentEpoch)
    const bestMetrics: Record<string, number> = {}
    if (metricsHistory.length > 0) {
      const bestEpoch = metricsHistory.reduce((best, m) =>
        (m.val_acc ?? 0) > (best.val_acc ?? 0) ? m : best, metricsHistory[0])
      bestMetrics.best_val_acc = bestEpoch.val_acc ?? 0
      bestMetrics.best_val_loss = bestEpoch.val_loss ?? 0
      bestMetrics.best_epoch = bestEpoch.epoch
    }

    sessions.push({
      session_id: `train_${startTime.toISOString().replace(/[-:T]/g, '').slice(0, 14)}_${i}`,
      model_id: modelId,
      model_type: modelType,
      status,
      start_time: startTime.toISOString(),
      end_time: status !== 'running' ? new Date(startTime.getTime() + totalEpochs * 3000).toISOString() : null,
      total_epochs: totalEpochs,
      current_epoch: currentEpoch,
      best_metrics: bestMetrics,
      metrics_history: metricsHistory,
      config: {
        epochs: totalEpochs,
        learning_rate: 0.001,
        batch_size: 32,
      },
      error_message: status === 'failed' ? '训练数据不足，无法收敛' : null
    })
  }

  return sessions
}

export function generateMockModelEntries(): ModelEntry[] {
  if (mockModelEntries) return mockModelEntries

  const boltIds = ['B001', 'B002', 'B003']
  const flangeIds = ['F001', 'F002', 'F003']

  const entries: ModelEntry[] = []
  mockVersionsMap = {}
  mockSessionsMap = {}

  for (const bid of boltIds) {
    const modelId = `bolt_${bid}`
    const versions = generateMockVersions(modelId, 'bolt')
    const sessions = generateMockSessions(modelId, 'bolt')
    mockVersionsMap[modelId] = versions
    mockSessionsMap[modelId] = sessions

    const activeVer = versions.find(v => v.is_active)
    const latestSession = sessions[0]
    const bestValAcc = versions.reduce((best, v) =>
      (v.metrics.val_acc ?? 0) > best ? (v.metrics.val_acc ?? 0) : best, 0)

    entries.push({
      model_id: modelId,
      model_type: 'bolt',
      display_name: modelDescriptions[modelId] || `${bid}螺栓模型`,
      is_trained: true,
      active_version: activeVer?.version ?? null,
      total_versions: versions.length,
      last_training_time: latestSession?.start_time ?? null,
      training_status: latestSession?.status ?? null,
      best_val_acc: bestValAcc > 0 ? bestValAcc : null,
      description: modelDescriptions[modelId] || ''
    })
  }

  for (const fid of flangeIds) {
    const modelId = `flange_${fid}`
    const versions = generateMockVersions(modelId, 'flange')
    const sessions = generateMockSessions(modelId, 'flange')
    mockVersionsMap[modelId] = versions
    mockSessionsMap[modelId] = sessions

    const activeVer = versions.find(v => v.is_active)
    const latestSession = sessions[0]
    const bestValAcc = versions.reduce((best, v) =>
      (v.metrics.val_acc ?? 0) > best ? (v.metrics.val_acc ?? 0) : best, 0)

    entries.push({
      model_id: modelId,
      model_type: 'flange',
      display_name: modelDescriptions[modelId] || `${fid}法兰模型`,
      is_trained: true,
      active_version: activeVer?.version ?? null,
      total_versions: versions.length,
      last_training_time: latestSession?.start_time ?? null,
      training_status: latestSession?.status ?? null,
      best_val_acc: bestValAcc > 0 ? bestValAcc : null,
      description: modelDescriptions[modelId] || ''
    })
  }

  mockModelEntries = entries
  return entries
}

export function getMockVersions(modelId: string): ModelVersion[] {
  if (!mockModelEntries) generateMockModelEntries()
  return mockVersionsMap[modelId] || []
}

export function getMockSessions(modelId: string): TrainingSession[] {
  if (!mockModelEntries) generateMockModelEntries()
  return mockSessionsMap[modelId] || []
}

export function mockActivateVersion(modelId: string, version: string): ModelVersion | null {
  const versions = mockVersionsMap[modelId]
  if (!versions) return null

  const target = versions.find(v => v.version === version)
  if (!target) return null

  for (const v of versions) {
    v.is_active = v.version === version
  }

  const entry = mockModelEntries?.find(e => e.model_id === modelId)
  if (entry) {
    entry.active_version = version
  }

  return { ...target, is_active: true }
}

export function mockRollbackVersion(modelId: string, version: string): ModelVersion | null {
  return mockActivateVersion(modelId, version)
}

export function mockTriggerTraining(modelType: string, modelId: string | null): TrainingSession {
  const targetId = modelId || (modelType === 'bolt' ? 'bolt_B001' : 'flange_F001')

  const session: TrainingSession = {
    session_id: `train_${Date.now()}`,
    model_id: targetId,
    model_type: modelType,
    status: 'running',
    start_time: new Date().toISOString(),
    end_time: null,
    total_epochs: 50,
    current_epoch: 0,
    best_metrics: {},
    metrics_history: [],
    config: {
      epochs: 50,
      learning_rate: 0.001,
      batch_size: 32,
    },
    error_message: null
  }

  if (!mockSessionsMap[targetId]) {
    mockSessionsMap[targetId] = []
  }
  mockSessionsMap[targetId].unshift(session)

  const entry = mockModelEntries?.find(e => e.model_id === targetId)
  if (entry) {
    entry.training_status = 'running'
  }

  simulateTrainingProgress(targetId, session)

  return session
}

function simulateTrainingProgress(modelId: string, session: TrainingSession) {
  let epoch = 0
  const total = session.total_epochs

  const interval = setInterval(() => {
    epoch++
    if (epoch > total) {
      clearInterval(interval)
      session.status = 'completed'
      session.end_time = new Date().toISOString()
      session.current_epoch = total

      const newVersion = `v1.${Math.floor((mockVersionsMap[modelId]?.length || 0) / 3) + 1}.${(mockVersionsMap[modelId]?.length || 0) % 3}`
      if (!mockVersionsMap[modelId]) mockVersionsMap[modelId] = []

      for (const v of mockVersionsMap[modelId]) {
        v.is_active = false
      }

      const lastMetrics = session.metrics_history[session.metrics_history.length - 1]
      mockVersionsMap[modelId].push({
        version: newVersion,
        model_id: modelId,
        model_type: session.model_type,
        created_at: new Date().toISOString(),
        file_path: `./trained_models/${session.model_type}/${modelId}/${newVersion}/${session.model_type}_${modelId}.pt`,
        file_hash: Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
        metrics: {
          val_acc: lastMetrics?.val_acc ?? 0.85,
          train_acc: lastMetrics?.train_acc ?? 0.9,
          val_loss: lastMetrics?.val_loss ?? 0.3,
          train_loss: lastMetrics?.train_loss ?? 0.2,
          f1_score: (lastMetrics?.val_acc ?? 0.85) - 0.02,
          precision: (lastMetrics?.val_acc ?? 0.85) + 0.01,
          recall: (lastMetrics?.val_acc ?? 0.85) - 0.01,
        },
        config: session.config,
        is_active: true,
        description: '自动训练完成版本'
      })

      const entry = mockModelEntries?.find(e => e.model_id === modelId)
      if (entry) {
        entry.training_status = 'completed'
        entry.active_version = newVersion
        entry.total_versions = mockVersionsMap[modelId].length
        entry.last_training_time = session.start_time
        entry.best_val_acc = lastMetrics?.val_acc ?? entry.best_val_acc
      }

      return
    }

    const progress = epoch / total
    const trainLoss = 1.2 * Math.exp(-3 * progress) + 0.05 + (Math.random() - 0.5) * 0.02
    const valLoss = 1.4 * Math.exp(-2.5 * progress) + 0.1 + (Math.random() - 0.5) * 0.03
    const trainAcc = Math.min(0.99, 0.4 + 0.58 * (1 - Math.exp(-4 * progress)))
    const valAcc = Math.min(0.97, 0.35 + 0.6 * (1 - Math.exp(-3.5 * progress)))
    const lr = progress < 0.6 ? 0.001 : 0.0001

    const m: EpochMetrics = {
      epoch,
      train_loss: Math.round(trainLoss * 10000) / 10000,
      val_loss: Math.round(valLoss * 10000) / 10000,
      train_acc: Math.round(trainAcc * 10000) / 10000,
      val_acc: Math.round(valAcc * 10000) / 10000,
      learning_rate: lr,
      duration_seconds: Math.round((1.5 + Math.random() * 3) * 100) / 100,
      timestamp: new Date().toISOString()
    }

    session.current_epoch = epoch
    session.metrics_history.push(m)

    if ((m.val_acc ?? 0) > (session.best_metrics.best_val_acc ?? 0)) {
      session.best_metrics.best_val_acc = m.val_acc ?? 0
      session.best_metrics.best_val_loss = m.val_loss ?? 0
      session.best_metrics.best_epoch = epoch
    }
  }, 800)
}

export function mockCompareVersions(
  modelId: string,
  version1: string,
  version2: string
): import('@/types').VersionCompareResult | null {
  const versions = mockVersionsMap[modelId]
  if (!versions) return null

  const v1 = versions.find(v => v.version === version1)
  const v2 = versions.find(v => v.version === version2)
  if (!v1 || !v2) return null

  const metricsComparison: Record<string, { v1: number; v2: number; diff: number; improved: boolean }> = {}
  const allKeys = new Set([...Object.keys(v1.metrics), ...Object.keys(v2.metrics)])

  for (const key of allKeys) {
    const val1 = v1.metrics[key] ?? 0
    const val2 = v2.metrics[key] ?? 0
    metricsComparison[key] = {
      v1: val1,
      v2: val2,
      diff: Math.round((val2 - val1) * 10000) / 10000,
      improved: key.includes('acc') || key.includes('f1') || key.includes('precision') || key.includes('recall')
        ? val2 > val1
        : val2 < val1
    }
  }

  return {
    model_id: modelId,
    version1,
    version2,
    metrics_comparison: metricsComparison,
    config_diff: {
      v1: v1.config,
      v2: v2.config
    }
  }
}
