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
  AlertStrategy
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
