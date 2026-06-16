import axios from 'axios'
import type {
  BoltSkuMapping,
  BoltSkuMappingCreateRequest,
  BoltSkuMappingUpdateRequest,
  BoltSkuQueryRequest,
  BoltSkuMappingListResponse,
  SparePartInventory,
  SparePartInventoryListResponse,
  StockAvailabilityCheckResponse,
  SparePartDemand,
  SparePartDemandFromRulRequest,
  SparePartDemandListResponse,
  SparePartDemandApproveRequest,
  SparePartDemandFulfillRequest,
  SparePartRulScanRequest,
  SparePartRulScanResponse,
  SparePartDemandSummary,
  SparePartDemandSummaryRequest,
  SparePartDemandSummaryListResponse,
  PurchaseAnalysisResponse,
  PurchaseConfigSaveRequest,
  PurchaseConfigResponse,
  PurchaseConfigListResponse,
  PurchasePlanRequest,
  PurchasePlanResponse,
} from '@/types'

const USE_MOCK = false

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// ==================== 螺栓-SKU映射管理 ====================

export async function fetchBoltSkuMappingList(
  filters?: BoltSkuQueryRequest,
  page = 1,
  pageSize = 20
): Promise<BoltSkuMappingListResponse> {
  if (USE_MOCK) {
    return { total: 0, items: [] }
  }

  try {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (page - 1) * pageSize,
      ...filters
    }
    const res = await api.get<BoltSkuMappingListResponse>('/spare-parts/bolt-sku-mappings', { params })
    return res.data
  } catch (err) {
    console.error('获取螺栓-SKU映射列表失败:', err)
    return { total: 0, items: [] }
  }
}

export async function queryBoltSkuMappings(
  request: BoltSkuQueryRequest,
  page = 1,
  pageSize = 20
): Promise<BoltSkuMappingListResponse> {
  if (USE_MOCK) {
    return { total: 0, items: [] }
  }

  try {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (page - 1) * pageSize,
      ...request
    }
    const res = await api.post<BoltSkuMappingListResponse>('/spare-parts/bolt-sku-mappings/query', params)
    return res.data
  } catch (err) {
    console.error('查询螺栓-SKU映射失败:', err)
    return { total: 0, items: [] }
  }
}

export async function fetchBoltSkuMapping(id: number): Promise<BoltSkuMapping | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.get<BoltSkuMapping>(`/spare-parts/bolt-sku-mappings/${id}`)
    return res.data
  } catch (err) {
    console.error('获取螺栓-SKU映射详情失败:', err)
    return null
  }
}

export async function fetchSkuByBoltModel(boltModel: string): Promise<BoltSkuMapping | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.get<BoltSkuMapping>(`/spare-parts/bolt-sku-mappings/bolt-model/${encodeURIComponent(boltModel)}`)
    return res.data
  } catch (err) {
    console.error('根据螺栓型号查询SKU失败:', err)
    return null
  }
}

export async function createBoltSkuMapping(
  request: BoltSkuMappingCreateRequest
): Promise<BoltSkuMapping | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post<BoltSkuMapping>('/spare-parts/bolt-sku-mappings', request)
    return res.data
  } catch (err) {
    console.error('创建螺栓-SKU映射失败:', err)
    return null
  }
}

export async function updateBoltSkuMapping(
  id: number,
  request: BoltSkuMappingUpdateRequest
): Promise<BoltSkuMapping | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.put<BoltSkuMapping>(`/spare-parts/bolt-sku-mappings/${id}`, request)
    return res.data
  } catch (err) {
    console.error('更新螺栓-SKU映射失败:', err)
    return null
  }
}

export async function deleteBoltSkuMapping(id: number): Promise<boolean> {
  if (USE_MOCK) {
    return false
  }

  try {
    await api.delete(`/spare-parts/bolt-sku-mappings/${id}`)
    return true
  } catch (err) {
    console.error('删除螺栓-SKU映射失败:', err)
    return false
  }
}

// ==================== 库存查询管理 ====================

export async function fetchSparePartInventoryList(
  filters?: {
    sku_code?: string
    warehouse_code?: string
    stock_status?: string
    abc_category?: string
  },
  page = 1,
  pageSize = 20
): Promise<SparePartInventoryListResponse> {
  if (USE_MOCK) {
    return { total: 0, items: [] }
  }

  try {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (page - 1) * pageSize,
      ...filters
    }
    const res = await api.get<SparePartInventoryListResponse>('/spare-parts/inventory', { params })
    return res.data
  } catch (err) {
    console.error('获取备件库存列表失败:', err)
    return { total: 0, items: [] }
  }
}

export async function fetchSparePartInventory(skuCode: string): Promise<SparePartInventory | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.get<SparePartInventory>(`/spare-parts/inventory/${skuCode}`)
    return res.data
  } catch (err) {
    console.error('获取备件库存详情失败:', err)
    return null
  }
}

export async function checkStockAvailability(
  skuCode: string,
  requiredQuantity: number,
  warehouseCode?: string
): Promise<StockAvailabilityCheckResponse | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const params: Record<string, any> = {
      sku_code: skuCode,
      required_quantity: requiredQuantity,
      warehouse_code: warehouseCode
    }
    const res = await api.get<StockAvailabilityCheckResponse>('/spare-parts/inventory/availability/check', { params })
    return res.data
  } catch (err) {
    console.error('检查库存可用性失败:', err)
    return null
  }
}

// ==================== 备件需求管理 ====================

export async function generateDemandFromRul(
  request: SparePartDemandFromRulRequest
): Promise<SparePartDemand | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post<SparePartDemand>('/spare-parts/demands/from-rul', request)
    return res.data
  } catch (err) {
    console.error('根据RUL生成备件需求失败:', err)
    return null
  }
}

export async function scanRulAndGenerateDemands(
  request: SparePartRulScanRequest
): Promise<SparePartRulScanResponse | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post<SparePartRulScanResponse>('/spare-parts/demands/scan-rul', request)
    return res.data
  } catch (err) {
    console.error('批量扫描RUL生成需求失败:', err)
    return null
  }
}

export async function fetchSparePartDemandList(
  filters?: {
    device_id?: string
    sku_code?: string
    demand_status?: string
    urgency_level?: string
    start_date?: string
    end_date?: string
  },
  page = 1,
  pageSize = 20
): Promise<SparePartDemandListResponse> {
  if (USE_MOCK) {
    return { total: 0, items: [] }
  }

  try {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (page - 1) * pageSize,
      ...filters
    }
    const res = await api.get<SparePartDemandListResponse>('/spare-parts/demands', { params })
    return res.data
  } catch (err) {
    console.error('获取备件需求列表失败:', err)
    return { total: 0, items: [] }
  }
}

export async function fetchSparePartDemand(id: number): Promise<SparePartDemand | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.get<SparePartDemand>(`/spare-parts/demands/${id}`)
    return res.data
  } catch (err) {
    console.error('获取备件需求详情失败:', err)
    return null
  }
}

export async function approveSparePartDemand(
  id: number,
  request: SparePartDemandApproveRequest
): Promise<SparePartDemand | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post<SparePartDemand>(`/spare-parts/demands/${id}/approve`, request)
    return res.data
  } catch (err) {
    console.error('审批备件需求失败:', err)
    return null
  }
}

export async function fulfillSparePartDemand(
  id: number,
  request: SparePartDemandFulfillRequest
): Promise<SparePartDemand | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post<SparePartDemand>(`/spare-parts/demands/${id}/fulfill`, request)
    return res.data
  } catch (err) {
    console.error('完成备件需求失败:', err)
    return null
  }
}

export async function upgradeWorkOrderPriority(
  workOrderId: number,
  reason?: string
): Promise<{ success: boolean; new_priority: string; message: string } | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post(`/spare-parts/demands/work-order/${workOrderId}/upgrade-priority`, {
      reason
    })
    return res.data
  } catch (err) {
    console.error('升级工单优先级失败:', err)
    return null
  }
}

// ==================== 装置需求汇总报表 ====================

export async function generateDemandSummary(
  request: SparePartDemandSummaryRequest
): Promise<SparePartDemandSummary | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post<SparePartDemandSummary>('/spare-parts/demand-summaries/generate', request)
    return res.data
  } catch (err) {
    console.error('生成装置需求汇总报表失败:', err)
    return null
  }
}

export async function fetchDemandSummaryList(
  filters?: {
    device_id?: string
    report_period?: string
    report_status?: string
    start_date?: string
    end_date?: string
  },
  page = 1,
  pageSize = 20
): Promise<SparePartDemandSummaryListResponse> {
  if (USE_MOCK) {
    return { total: 0, items: [] }
  }

  try {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (page - 1) * pageSize,
      ...filters
    }
    const res = await api.get<SparePartDemandSummaryListResponse>('/spare-parts/demand-summaries', { params })
    return res.data
  } catch (err) {
    console.error('获取需求汇总报表列表失败:', err)
    return { total: 0, items: [] }
  }
}

export async function fetchDemandSummary(id: number): Promise<SparePartDemandSummary | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.get<SparePartDemandSummary>(`/spare-parts/demand-summaries/${id}`)
    return res.data
  } catch (err) {
    console.error('获取需求汇总报表详情失败:', err)
    return null
  }
}

// ==================== 采购周期与安全库存建议 ====================

export async function analyzeSkuPurchase(
  skuCode: string,
  historyDays?: number,
  serviceLevel?: number
): Promise<PurchaseAnalysisResponse | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const params: Record<string, any> = {
      sku_code: skuCode,
      history_days: historyDays,
      service_level: serviceLevel
    }
    const res = await api.get<PurchaseAnalysisResponse>('/spare-parts/purchase/analyze', { params })
    return res.data
  } catch (err) {
    console.error('SKU采购分析失败:', err)
    return null
  }
}

export async function savePurchaseConfig(
  request: PurchaseConfigSaveRequest
): Promise<PurchaseConfigResponse | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post<PurchaseConfigResponse>('/spare-parts/purchase/config', request)
    return res.data
  } catch (err) {
    console.error('保存采购配置失败:', err)
    return null
  }
}

export async function fetchPurchaseConfigList(
  filters?: {
    abc_category?: string
    sku_code?: string
  },
  page = 1,
  pageSize = 20
): Promise<PurchaseConfigListResponse> {
  if (USE_MOCK) {
    return { total: 0, items: [] }
  }

  try {
    const params: Record<string, any> = {
      limit: pageSize,
      offset: (page - 1) * pageSize,
      ...filters
    }
    const res = await api.get<PurchaseConfigListResponse>('/spare-parts/purchase/configs', { params })
    return res.data
  } catch (err) {
    console.error('获取采购配置列表失败:', err)
    return { total: 0, items: [] }
  }
}

export async function fetchPurchaseConfig(skuCode: string): Promise<PurchaseConfigResponse | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.get<PurchaseConfigResponse>(`/spare-parts/purchase/config/${skuCode}`)
    return res.data
  } catch (err) {
    console.error('获取采购配置失败:', err)
    return null
  }
}

export async function generatePurchasePlan(
  request: PurchasePlanRequest
): Promise<PurchasePlanResponse | null> {
  if (USE_MOCK) {
    return null
  }

  try {
    const res = await api.post<PurchasePlanResponse>('/spare-parts/purchase/plan/generate', request)
    return res.data
  } catch (err) {
    console.error('生成采购计划失败:', err)
    return null
  }
}
