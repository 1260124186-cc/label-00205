import axios from 'axios'
import type {
  StandardTemplate,
  StandardTemplateListResponse,
  InspectionTask,
  InspectionTaskListResponse,
  InspectionTaskCreateRequest,
  WorkOrderCloseCheck,
  InspectionPdfExportResponse,
  ChecklistItem,
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export async function fetchStandardTemplates(category?: string): Promise<StandardTemplateListResponse> {
  const params: Record<string, string> = {}
  if (category) params.category = category
  const { data } = await api.get('/compliance/templates', { params })
  return data
}

export async function fetchStandardTemplate(code: string): Promise<StandardTemplate> {
  const { data } = await api.get(`/compliance/templates/${code}`)
  return data
}

export async function createStandardTemplate(template: Partial<StandardTemplate>): Promise<StandardTemplate> {
  const { data } = await api.post('/compliance/templates', template)
  return data
}

export async function updateStandardTemplate(templateId: number, template: Partial<StandardTemplate>): Promise<StandardTemplate> {
  const { data } = await api.put(`/compliance/templates/${templateId}`, template)
  return data
}

export async function deleteStandardTemplate(templateId: number): Promise<void> {
  await api.delete(`/compliance/templates/${templateId}`)
}

export async function fetchChecklistByEquipmentType(equipmentType: string): Promise<{ equipment_type: string; items: ChecklistItem[]; total: number }> {
  const { data } = await api.get(`/compliance/checklist/${equipmentType}`)
  return data
}

export async function createInspectionTask(request: InspectionTaskCreateRequest): Promise<InspectionTask> {
  const { data } = await api.post('/compliance/inspection/tasks', request)
  return data
}

export async function fetchInspectionTasks(params?: {
  status?: string
  equipment_type?: string
  work_order_id?: number
  limit?: number
  offset?: number
}): Promise<InspectionTaskListResponse> {
  const { data } = await api.get('/compliance/inspection/tasks', { params })
  return data
}

export async function fetchInspectionTask(taskId: number): Promise<InspectionTask> {
  const { data } = await api.get(`/compliance/inspection/tasks/${taskId}`)
  return data
}

export async function fetchInspectionTaskByWorkOrder(workOrderId: number): Promise<InspectionTask> {
  const { data } = await api.get(`/compliance/inspection/work-order/${workOrderId}`)
  return data
}

export async function checkInspectionItem(
  taskId: number,
  itemCode: string,
  result: string,
  inspectorId?: string,
  inspectorName?: string,
  evidence?: Record<string, any>,
  remarks?: string,
): Promise<InspectionTask> {
  const { data } = await api.post(`/compliance/inspection/tasks/${taskId}/check`, {
    item_code: itemCode,
    result,
    inspector_id: inspectorId,
    inspector_name: inspectorName,
    evidence,
    remarks,
  })
  return data
}

export async function autoCheckMandatoryItems(
  taskId: number,
  alertLevel: number,
  predictionEvidence?: Record<string, any>,
): Promise<InspectionTask> {
  const { data } = await api.post(`/compliance/inspection/tasks/${taskId}/auto-check`, {
    alert_level: alertLevel,
    prediction_evidence: predictionEvidence,
  })
  return data
}

export async function fetchCompletionScore(taskId: number): Promise<{ task_id: number; completion_score: number }> {
  const { data } = await api.get(`/compliance/inspection/tasks/${taskId}/score`)
  return data
}

export async function checkWorkOrderClose(workOrderId: number): Promise<WorkOrderCloseCheck> {
  const { data } = await api.get(`/compliance/work-order/${workOrderId}/close-check`)
  return data
}

export async function exportInspectionPdf(taskId: number): Promise<InspectionPdfExportResponse> {
  const { data } = await api.get(`/compliance/inspection/tasks/${taskId}/export-pdf`)
  return data
}
