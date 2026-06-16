"""
合规与检验标准检查引擎

功能:
1. 标准模板库管理 - API 650 储罐法兰、ASME PCC-1 紧固规程等（可配置条目）
2. 按装置类型加载检查清单
3. 预测紧急预警时自动勾选必检项
4. 检验完成度评分
5. 未完成项阻止工单关闭
6. PDF 检验报告导出（含预测证据截图数据字段）
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from loguru import logger
from sqlalchemy import and_

from app.utils.database import get_db
from app.utils.config import config


BUILTIN_STANDARD_TEMPLATES = [
    {
        "code": "API_650",
        "name": "API 650 储罐法兰检验标准",
        "description": "适用于焊接储罐法兰连接的检验，涵盖螺栓预紧力、法兰密封面、垫片完好性等",
        "version": "12th Edition",
        "category": "storage_tank_flange",
        "checklist_items": [
            {"item_code": "API650-001", "content": "螺栓预紧力是否在设计范围内", "is_mandatory": True, "severity": "critical", "inspection_method": "力矩扳手/超声波测力", "acceptance_criteria": "预紧力偏差≤±10%标称值"},
            {"item_code": "API650-002", "content": "法兰密封面是否完好无损伤", "is_mandatory": True, "severity": "critical", "inspection_method": "目视/渗透检测", "acceptance_criteria": "无裂纹、划痕、腐蚀坑"},
            {"item_code": "API650-003", "content": "垫片类型及状态是否符合设计要求", "is_mandatory": True, "severity": "high", "inspection_method": "目视/尺寸测量", "acceptance_criteria": "垫片无压缩永久变形、无渗透泄漏"},
            {"item_code": "API650-004", "content": "螺栓材质及规格是否符合标准", "is_mandatory": False, "severity": "medium", "inspection_method": "材质报告核对", "acceptance_criteria": "符合ASTM A193 B7或等同标准"},
            {"item_code": "API650-005", "content": "法兰对中偏差检查", "is_mandatory": True, "severity": "high", "inspection_method": "直尺/间隙测量", "acceptance_criteria": "平行度偏差≤0.5mm"},
            {"item_code": "API650-006", "content": "紧固顺序是否符合十字交叉法", "is_mandatory": False, "severity": "medium", "inspection_method": "过程记录核查", "acceptance_criteria": "按标准紧固顺序执行"},
            {"item_code": "API650-007", "content": "储罐基础沉降监测数据", "is_mandatory": False, "severity": "low", "inspection_method": "水准仪测量", "acceptance_criteria": "沉降差≤设计允许值"},
            {"item_code": "API650-008", "content": "泄漏检测（气密性试验）", "is_mandatory": True, "severity": "critical", "inspection_method": "气密性试验/皂液检漏", "acceptance_criteria": "无可见泄漏"},
        ]
    },
    {
        "code": "ASME_PCC1",
        "name": "ASME PCC-1 紧固规程检验标准",
        "description": "适用于压力边界法兰螺栓连接的装配与检验，涵盖预紧力控制、紧固策略、螺栓润滑等",
        "version": "2019 Edition",
        "category": "pressure_flange_fastening",
        "checklist_items": [
            {"item_code": "PCC1-001", "content": "目标预紧力是否按PCC-1方法计算", "is_mandatory": True, "severity": "critical", "inspection_method": "计算书核查", "acceptance_criteria": "目标预紧力=设计压力×密封系数×安全裕度"},
            {"item_code": "PCC1-002", "content": "螺栓润滑剂是否按标准选用", "is_mandatory": True, "severity": "high", "inspection_method": "润滑剂型号核查", "acceptance_criteria": "摩擦系数一致性≤±10%"},
            {"item_code": "PCC1-003", "content": "紧固工具是否校准并在有效期内", "is_mandatory": True, "severity": "critical", "inspection_method": "校准证书核查", "acceptance_criteria": "力矩扳手/液压张拉器校准偏差≤±3%"},
            {"item_code": "PCC1-004", "content": "紧固策略是否按PCC-1附录执行", "is_mandatory": True, "severity": "high", "inspection_method": "过程记录核查", "acceptance_criteria": "符合交叉紧固+多步递增策略"},
            {"item_code": "PCC1-005", "content": "螺栓孔与螺栓配合间隙检查", "is_mandatory": False, "severity": "medium", "inspection_method": "塞尺测量", "acceptance_criteria": "配合间隙≤标准允许值"},
            {"item_code": "PCC1-006", "content": "法兰面粗糙度检查", "is_mandatory": False, "severity": "medium", "inspection_method": "粗糙度仪", "acceptance_criteria": "Ra≤3.2μm(金属垫片)或Ra≤6.3μm(非金属垫片)"},
            {"item_code": "PCC1-007", "content": "螺母旋转角度记录验证", "is_mandatory": True, "severity": "high", "inspection_method": "角度测量仪记录", "acceptance_criteria": "旋转角度偏差≤±5°"},
            {"item_code": "PCC1-008", "content": "装配后预紧力验证（超声波验证）", "is_mandatory": True, "severity": "critical", "inspection_method": "超声波测力仪", "acceptance_criteria": "预紧力偏差≤±15%目标值"},
        ]
    },
    {
        "code": "GB150",
        "name": "GB 150 压力容器法兰检验标准",
        "description": "适用于钢制压力容器法兰连接的检验，涵盖法兰强度、密封性、紧固件等",
        "version": "2011 Edition",
        "category": "pressure_vessel_flange",
        "checklist_items": [
            {"item_code": "GB150-001", "content": "法兰设计压力及温度校核", "is_mandatory": True, "severity": "critical", "inspection_method": "设计文件核查", "acceptance_criteria": "设计压力≥操作压力×安全系数"},
            {"item_code": "GB150-002", "content": "螺栓强度校核", "is_mandatory": True, "severity": "critical", "inspection_method": "强度计算核查", "acceptance_criteria": "螺栓应力≤许用应力"},
            {"item_code": "GB150-003", "content": "密封比压校核", "is_mandatory": True, "severity": "high", "inspection_method": "计算核查", "acceptance_criteria": "实际比压≥必需比压"},
            {"item_code": "GB150-004", "content": "法兰刚度校核", "is_mandatory": False, "severity": "medium", "inspection_method": "有限元/计算核查", "acceptance_criteria": "法兰转角≤0.3°"},
            {"item_code": "GB150-005", "content": "焊接接头无损检测", "is_mandatory": True, "severity": "critical", "inspection_method": "RT/UT/MT/PT", "acceptance_criteria": "符合NB/T 47013标准"},
        ]
    },
]


ALERT_LEVEL_TO_MANDATORY_ITEMS = {
    3: ["API650-001", "API650-002", "API650-008", "PCC1-001", "PCC1-003", "PCC1-008", "GB150-001", "GB150-002", "GB150-005"],
    4: ["API650-001", "API650-002", "API650-003", "API650-005", "API650-008", "PCC1-001", "PCC1-003", "PCC1-004", "PCC1-007", "PCC1-008", "GB150-001", "GB150-002", "GB150-003", "GB150-005"],
}


class ComplianceInspectionService:
    """
    合规与检验标准检查引擎

    核心职责:
    - 管理标准模板库（增删改查）
    - 按装置类型加载检查清单
    - 创建检验任务并跟踪完成情况
    - 预测紧急预警时自动勾选必检项
    - 检验完成度评分
    - 未完成必检项阻止工单关闭
    - PDF 检验报告导出
    """

    def __init__(self):
        compliance_config = config.get('compliance', {})
        self.min_completion_score_to_close = compliance_config.get(
            'min_completion_score_to_close', 80.0
        )
        self.auto_check_on_emergency = compliance_config.get(
            'auto_check_on_emergency', True
        )
        logger.info("合规检验检查引擎初始化完成")

    def list_standard_templates(self, category: str = None) -> List[Dict[str, Any]]:
        with get_db() as db:
            if db is None:
                return self._filter_builtin_templates(category)
            self._ensure_table(db)
            from app.utils.database import Base
            ComplianceStandardTemplate = Base.classes.get('sc_compliance_standard_templates')
            if ComplianceStandardTemplate is None:
                return self._filter_builtin_templates(category)
            query = db.query(ComplianceStandardTemplate).filter(
                ComplianceStandardTemplate.is_active == True
            )
            if category:
                query = query.filter(ComplianceStandardTemplate.category == category)
            templates = query.order_by(ComplianceStandardTemplate.create_time.desc()).all()
            if not templates:
                return self._filter_builtin_templates(category)
            result = []
            for t in templates:
                items = json.loads(t.checklist_items) if t.checklist_items else []
                result.append({
                    "id": t.id,
                    "code": t.code,
                    "name": t.name,
                    "description": t.description,
                    "version": t.version,
                    "category": t.category,
                    "checklist_items": items,
                    "create_time": t.create_time.isoformat() if t.create_time else None,
                    "update_time": t.update_time.isoformat() if t.update_time else None,
                })
            return result

    def get_standard_template(self, code: str) -> Optional[Dict[str, Any]]:
        templates = self.list_standard_templates()
        for t in templates:
            if t["code"] == code:
                return t
        return None

    def create_standard_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            if db is None:
                raise RuntimeError("数据库不可用")
            self._ensure_table(db)
            from app.utils.database import Base
            ComplianceStandardTemplate = Base.classes.get('sc_compliance_standard_templates')
            template = ComplianceStandardTemplate(
                code=data["code"],
                name=data["name"],
                description=data.get("description", ""),
                version=data.get("version", "1.0"),
                category=data.get("category", "general"),
                checklist_items=json.dumps(data.get("checklist_items", []), ensure_ascii=False),
                is_active=True,
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            items = json.loads(template.checklist_items) if template.checklist_items else []
            return {
                "id": template.id,
                "code": template.code,
                "name": template.name,
                "description": template.description,
                "version": template.version,
                "category": template.category,
                "checklist_items": items,
            }

    def update_standard_template(self, template_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            if db is None:
                return None
            self._ensure_table(db)
            from app.utils.database import Base
            ComplianceStandardTemplate = Base.classes.get('sc_compliance_standard_templates')
            template = db.query(ComplianceStandardTemplate).filter(
                ComplianceStandardTemplate.id == template_id
            ).first()
            if not template:
                return None
            for key in ["name", "description", "version", "category"]:
                if key in data:
                    setattr(template, key, data[key])
            if "checklist_items" in data:
                template.checklist_items = json.dumps(data["checklist_items"], ensure_ascii=False)
            db.commit()
            db.refresh(template)
            return self.get_standard_template(template.code)

    def delete_standard_template(self, template_id: int) -> bool:
        with get_db() as db:
            if db is None:
                return False
            self._ensure_table(db)
            from app.utils.database import Base
            ComplianceStandardTemplate = Base.classes.get('sc_compliance_standard_templates')
            template = db.query(ComplianceStandardTemplate).filter(
                ComplianceStandardTemplate.id == template_id
            ).first()
            if not template:
                return False
            template.is_active = False
            db.commit()
            return True

    def load_checklist_by_equipment_type(self, equipment_type: str) -> List[Dict[str, Any]]:
        category_map = {
            "storage_tank_flange": "storage_tank_flange",
            "pressure_flange_fastening": "pressure_flange_fastening",
            "pressure_vessel_flange": "pressure_vessel_flange",
            "bolt": "storage_tank_flange",
            "flange": "storage_tank_flange",
        }
        category = category_map.get(equipment_type, equipment_type)
        templates = self.list_standard_templates(category=category)
        if not templates:
            templates = self.list_standard_templates()
        all_items = []
        for template in templates:
            for item in template.get("checklist_items", []):
                all_items.append({
                    **item,
                    "standard_code": template["code"],
                    "standard_name": template["name"],
                })
        return all_items

    def create_inspection_task(
        self,
        work_order_id: int,
        equipment_type: str,
        standard_codes: List[str] = None,
        node_type: str = None,
        node_id: str = None,
        alert_level: int = None,
        auto_check_mandatory: bool = True,
    ) -> Dict[str, Any]:
        with get_db() as db:
            if db is None:
                raise RuntimeError("数据库不可用")
            self._ensure_inspection_table(db)

            task_no = f"INS{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"

            if standard_codes:
                templates = []
                all_templates = self.list_standard_templates()
                for code in standard_codes:
                    for t in all_templates:
                        if t["code"] == code:
                            templates.append(t)
            else:
                templates = self.list_standard_templates(
                    category=self._map_equipment_to_category(equipment_type)
                )
                if not templates:
                    templates = self.list_standard_templates()

            checklist_items = []
            for template in templates:
                for item in template.get("checklist_items", []):
                    checklist_items.append({
                        **item,
                        "standard_code": template["code"],
                        "standard_name": template["name"],
                        "checked": False,
                        "auto_checked": False,
                        "result": None,
                        "evidence": None,
                        "inspector_id": None,
                        "inspector_name": None,
                        "inspect_time": None,
                        "remarks": None,
                    })

            if auto_check_mandatory and alert_level and alert_level >= 3:
                mandatory_item_codes = ALERT_LEVEL_TO_MANDATORY_ITEMS.get(alert_level, [])
                for item in checklist_items:
                    if item.get("item_code") in mandatory_item_codes:
                        item["auto_checked"] = True
                        item["checked"] = True
                        item["result"] = "auto_required"
                        item["remarks"] = f"紧急预警(alert_level={alert_level})自动勾选必检项"

            from app.utils.database import Base
            ComplianceInspectionTask = Base.classes.get('sc_compliance_inspection_tasks')
            task = ComplianceInspectionTask(
                task_no=task_no,
                work_order_id=work_order_id,
                equipment_type=equipment_type,
                standard_codes=json.dumps([t["code"] for t in templates], ensure_ascii=False),
                checklist_items=json.dumps(checklist_items, ensure_ascii=False),
                node_type=node_type,
                node_id=node_id,
                alert_level=alert_level,
                completion_score=0.0,
                status="pending",
                auto_check_mandatory=auto_check_mandatory,
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            score = self._calculate_completion_score(checklist_items)
            task.completion_score = score
            db.commit()

            return self._task_to_dict(task)

    def get_inspection_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            if db is None:
                return None
            self._ensure_inspection_table(db)
            from app.utils.database import Base
            ComplianceInspectionTask = Base.classes.get('sc_compliance_inspection_tasks')
            task = db.query(ComplianceInspectionTask).filter(
                ComplianceInspectionTask.id == task_id
            ).first()
            if not task:
                return None
            return self._task_to_dict(task)

    def get_inspection_task_by_work_order(self, work_order_id: int) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            if db is None:
                return None
            self._ensure_inspection_table(db)
            from app.utils.database import Base
            ComplianceInspectionTask = Base.classes.get('sc_compliance_inspection_tasks')
            task = db.query(ComplianceInspectionTask).filter(
                ComplianceInspectionTask.work_order_id == work_order_id
            ).first()
            if not task:
                return None
            return self._task_to_dict(task)

    def list_inspection_tasks(
        self,
        status: str = None,
        equipment_type: str = None,
        work_order_id: int = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with get_db() as db:
            if db is None:
                return {"total": 0, "items": []}
            self._ensure_inspection_table(db)
            from app.utils.database import Base
            ComplianceInspectionTask = Base.classes.get('sc_compliance_inspection_tasks')
            query = db.query(ComplianceInspectionTask)
            if status:
                query = query.filter(ComplianceInspectionTask.status == status)
            if equipment_type:
                query = query.filter(ComplianceInspectionTask.equipment_type == equipment_type)
            if work_order_id:
                query = query.filter(ComplianceInspectionTask.work_order_id == work_order_id)
            total = query.count()
            tasks = query.order_by(
                ComplianceInspectionTask.create_time.desc()
            ).offset(offset).limit(limit).all()
            return {
                "total": total,
                "items": [self._task_to_dict(t) for t in tasks],
            }

    def check_inspection_item(
        self,
        task_id: int,
        item_code: str,
        result: str,
        inspector_id: str = None,
        inspector_name: str = None,
        evidence: Dict[str, Any] = None,
        remarks: str = None,
    ) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            if db is None:
                return None
            self._ensure_inspection_table(db)
            from app.utils.database import Base
            ComplianceInspectionTask = Base.classes.get('sc_compliance_inspection_tasks')
            task = db.query(ComplianceInspectionTask).filter(
                ComplianceInspectionTask.id == task_id
            ).first()
            if not task:
                return None

            checklist = json.loads(task.checklist_items) if task.checklist_items else []
            found = False
            for item in checklist:
                if item.get("item_code") == item_code:
                    item["checked"] = True
                    item["result"] = result
                    item["inspector_id"] = inspector_id
                    item["inspector_name"] = inspector_name
                    item["inspect_time"] = datetime.now().isoformat()
                    if evidence:
                        item["evidence"] = evidence
                    if remarks:
                        item["remarks"] = remarks
                    found = True
                    break

            if not found:
                return None

            task.checklist_items = json.dumps(checklist, ensure_ascii=False)
            score = self._calculate_completion_score(checklist)
            task.completion_score = score

            total_items = len(checklist)
            checked_items = sum(1 for i in checklist if i.get("checked"))
            all_mandatory_checked = all(
                i.get("checked") for i in checklist if i.get("is_mandatory")
            )

            if checked_items == total_items and all_mandatory_checked:
                task.status = "completed"
            elif checked_items > 0:
                task.status = "in_progress"

            db.commit()
            db.refresh(task)
            return self._task_to_dict(task)

    def auto_check_mandatory_items(
        self,
        task_id: int,
        alert_level: int,
        prediction_evidence: Dict[str, Any] = None,
    ) -> Optional[Dict[str, Any]]:
        with get_db() as db:
            if db is None:
                return None
            self._ensure_inspection_table(db)
            from app.utils.database import Base
            ComplianceInspectionTask = Base.classes.get('sc_compliance_inspection_tasks')
            task = db.query(ComplianceInspectionTask).filter(
                ComplianceInspectionTask.id == task_id
            ).first()
            if not task:
                return None

            mandatory_item_codes = ALERT_LEVEL_TO_MANDATORY_ITEMS.get(alert_level, [])
            checklist = json.loads(task.checklist_items) if task.checklist_items else []

            auto_checked_count = 0
            for item in checklist:
                if item.get("item_code") in mandatory_item_codes and not item.get("checked"):
                    item["auto_checked"] = True
                    item["checked"] = True
                    item["result"] = "auto_required"
                    item["remarks"] = f"紧急预警(alert_level={alert_level})自动勾选必检项"
                    if prediction_evidence:
                        item["evidence"] = {
                            "source": "prediction",
                            "alert_level": alert_level,
                            **prediction_evidence,
                        }
                    auto_checked_count += 1

            task.checklist_items = json.dumps(checklist, ensure_ascii=False)
            task.alert_level = alert_level
            score = self._calculate_completion_score(checklist)
            task.completion_score = score

            if auto_checked_count > 0:
                logger.info(
                    f"检验任务 {task.task_no}: 紧急预警自动勾选 {auto_checked_count} 项必检项"
                )

            db.commit()
            db.refresh(task)
            return self._task_to_dict(task)

    def calculate_completion_score(self, task_id: int) -> float:
        with get_db() as db:
            if db is None:
                return 0.0
            self._ensure_inspection_table(db)
            from app.utils.database import Base
            ComplianceInspectionTask = Base.classes.get('sc_compliance_inspection_tasks')
            task = db.query(ComplianceInspectionTask).filter(
                ComplianceInspectionTask.id == task_id
            ).first()
            if not task:
                return 0.0
            checklist = json.loads(task.checklist_items) if task.checklist_items else []
            return self._calculate_completion_score(checklist)

    def can_close_work_order(self, work_order_id: int) -> Dict[str, Any]:
        with get_db() as db:
            if db is None:
                return {"can_close": True, "reason": "数据库不可用，默认允许关闭"}
            self._ensure_inspection_table(db)
            from app.utils.database import Base
            ComplianceInspectionTask = Base.classes.get('sc_compliance_inspection_tasks')
            task = db.query(ComplianceInspectionTask).filter(
                ComplianceInspectionTask.work_order_id == work_order_id
            ).first()
            if not task:
                return {"can_close": True, "reason": "无关联检验任务"}

            checklist = json.loads(task.checklist_items) if task.checklist_items else []
            mandatory_unchecked = [
                {"item_code": i.get("item_code"), "content": i.get("content"), "severity": i.get("severity")}
                for i in checklist
                if i.get("is_mandatory") and not i.get("checked")
            ]

            score = self._calculate_completion_score(checklist)
            can_close = score >= self.min_completion_score_to_close and len(mandatory_unchecked) == 0

            return {
                "can_close": can_close,
                "completion_score": score,
                "min_required_score": self.min_completion_score_to_close,
                "mandatory_unchecked": mandatory_unchecked,
                "mandatory_unchecked_count": len(mandatory_unchecked),
                "reason": (
                    "检验完成度达标且必检项全部完成"
                    if can_close
                    else (
                        f"存在 {len(mandatory_unchecked)} 项未完成必检项"
                        if mandatory_unchecked
                        else f"完成度评分 {score:.1f}% 低于最低要求 {self.min_completion_score_to_close}%"
                    )
                ),
            }

    def export_pdf_data(self, task_id: int) -> Dict[str, Any]:
        task = self.get_inspection_task(task_id)
        if not task:
            return {}

        checklist = task.get("checklist_items", [])
        total = len(checklist)
        checked = sum(1 for i in checklist if i.get("checked"))
        mandatory_items = [i for i in checklist if i.get("is_mandatory")]
        mandatory_checked = sum(1 for i in mandatory_items if i.get("checked"))
        auto_checked = sum(1 for i in checklist if i.get("auto_checked"))

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for item in checklist:
            sev = item.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        result_counts = {"pass": 0, "fail": 0, "auto_required": 0, "na": 0, "pending": 0}
        for item in checklist:
            res = item.get("result")
            if res in result_counts:
                result_counts[res] += 1
            else:
                result_counts["pending"] += 1

        prediction_evidences = []
        for item in checklist:
            if item.get("evidence") and isinstance(item["evidence"], dict):
                prediction_evidences.append({
                    "item_code": item.get("item_code"),
                    "item_content": item.get("content"),
                    "evidence": item["evidence"],
                })

        return {
            "title": "合规检验报告",
            "task_no": task.get("task_no"),
            "equipment_type": task.get("equipment_type"),
            "standard_codes": task.get("standard_codes", []),
            "node_type": task.get("node_type"),
            "node_id": task.get("node_id"),
            "alert_level": task.get("alert_level"),
            "work_order_id": task.get("work_order_id"),
            "status": task.get("status"),
            "export_time": datetime.now().isoformat(),
            "summary": {
                "total_items": total,
                "checked_items": checked,
                "unchecked_items": total - checked,
                "mandatory_total": len(mandatory_items),
                "mandatory_checked": mandatory_checked,
                "mandatory_unchecked": len(mandatory_items) - mandatory_checked,
                "auto_checked_items": auto_checked,
                "completion_score": task.get("completion_score", 0.0),
                "severity_distribution": severity_counts,
                "result_distribution": result_counts,
            },
            "checklist_items": checklist,
            "prediction_evidences": prediction_evidences,
        }

    def generate_pdf_html(self, task_id: int) -> str:
        data = self.export_pdf_data(task_id)
        if not data:
            return "<html><body><h1>检验任务未找到</h1></body></html>"

        summary = data.get("summary", {})
        html_parts = [
            '<!DOCTYPE html>',
            '<html><head><meta charset="utf-8">',
            '<style>',
            'body { font-family: "SimSun", "Microsoft YaHei", serif; margin: 40px; color: #333; }',
            'h1 { text-align: center; color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; }',
            'h2 { color: #2c5282; border-bottom: 1px solid #bee3f8; padding-bottom: 5px; }',
            'h3 { color: #2b6cb0; }',
            'table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 11px; }',
            'th, td { border: 1px solid #a0aec0; padding: 6px 8px; text-align: left; }',
            'th { background: #ebf8ff; font-weight: bold; }',
            '.summary-box { background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 15px; margin: 15px 0; }',
            '.score { font-size: 24px; font-weight: bold; color: #2b6cb0; }',
            '.score-pass { color: #38a169; }',
            '.score-fail { color: #e53e3e; }',
            '.mandatory { color: #e53e3e; font-weight: bold; }',
            '.checked { color: #38a169; }',
            '.unchecked { color: #e53e3e; }',
            '.auto-checked { color: #d69e2e; }',
            '.evidence-box { background: #fffff0; border-left: 3px solid #d69e2e; padding: 8px 12px; margin: 5px 0; font-size: 10px; }',
            '.page-break { page-break-before: always; }',
            '</style>',
            '</head><body>',
            f'<h1>{data["title"]}</h1>',
            f'<p><strong>检验编号:</strong> {data.get("task_no", "")}</p>',
            f'<p><strong>装置类型:</strong> {data.get("equipment_type", "")}</p>',
            f'<p><strong>适用标准:</strong> {", ".join(data.get("standard_codes", []))}</p>',
            f'<p><strong>节点:</strong> {data.get("node_type", "")}/{data.get("node_id", "")}</p>',
            f'<p><strong>关联工单ID:</strong> {data.get("work_order_id", "")}</p>',
            f'<p><strong>预警级别:</strong> {data.get("alert_level", "")}</p>',
            f'<p><strong>导出时间:</strong> {data.get("export_time", "")}</p>',
        ]

        html_parts.append('<div class="summary-box">')
        html_parts.append('<h2>检验摘要</h2>')
        score = summary.get("completion_score", 0)
        score_class = "score-pass" if score >= 80 else "score-fail"
        html_parts.append(f'<p>完成度评分: <span class="score {score_class}">{score:.1f}%</span></p>')
        html_parts.append(f'<p>总检验项: {summary.get("total_items", 0)} | '
                          f'已完成: {summary.get("checked_items", 0)} | '
                          f'未完成: {summary.get("unchecked_items", 0)}</p>')
        html_parts.append(f'<p>必检项: {summary.get("mandatory_total", 0)} | '
                          f'已完成: {summary.get("mandatory_checked", 0)} | '
                          f'<span class="mandatory">未完成: {summary.get("mandatory_unchecked", 0)}</span></p>')
        html_parts.append(f'<p>自动勾选项: {summary.get("auto_checked_items", 0)}</p>')

        sev_dist = summary.get("severity_distribution", {})
        if sev_dist:
            html_parts.append('<p>严重度分布: ')
            sev_parts = []
            for sev, count in sev_dist.items():
                if count > 0:
                    sev_parts.append(f'{sev}={count}')
            html_parts.append(', '.join(sev_parts))
            html_parts.append('</p>')

        res_dist = summary.get("result_distribution", {})
        if res_dist:
            html_parts.append('<p>检验结果分布: ')
            res_parts = []
            for res, count in res_dist.items():
                if count > 0:
                    res_parts.append(f'{res}={count}')
            html_parts.append(', '.join(res_parts))
            html_parts.append('</p>')
        html_parts.append('</div>')

        checklist = data.get("checklist_items", [])
        if checklist:
            html_parts.append('<h2>检验清单明细</h2>')
            html_parts.append('<table>')
            html_parts.append('<tr><th>序号</th><th>检验项编码</th><th>检验内容</th>'
                              '<th>必检</th><th>严重度</th><th>检验方法</th><th>合格标准</th>'
                              '<th>状态</th><th>结果</th><th>检验人</th><th>检验时间</th></tr>')
            for idx, item in enumerate(checklist, 1):
                mandatory_text = '<span class="mandatory">是</span>' if item.get("is_mandatory") else '否'
                status_text = '<span class="checked">已检</span>' if item.get("checked") else '<span class="unchecked">未检</span>'
                if item.get("auto_checked"):
                    status_text = '<span class="auto-checked">自动勾选</span>'
                result_text = item.get("result", "-") or "-"
                html_parts.append(
                    f'<tr><td>{idx}</td><td>{item.get("item_code", "")}</td>'
                    f'<td>{item.get("content", "")}</td><td>{mandatory_text}</td>'
                    f'<td>{item.get("severity", "")}</td>'
                    f'<td>{item.get("inspection_method", "")}</td>'
                    f'<td>{item.get("acceptance_criteria", "")}</td>'
                    f'<td>{status_text}</td><td>{result_text}</td>'
                    f'<td>{item.get("inspector_name", "-") or "-"}</td>'
                    f'<td>{item.get("inspect_time", "-") or "-"}</td></tr>'
                )
            html_parts.append('</table>')

        prediction_evidences = data.get("prediction_evidences", [])
        if prediction_evidences:
            html_parts.append('<div class="page-break"></div>')
            html_parts.append('<h2>预测证据数据</h2>')
            for ev in prediction_evidences:
                html_parts.append(f'<h3>{ev.get("item_code", "")} - {ev.get("item_content", "")}</h3>')
                html_parts.append('<div class="evidence-box">')
                evidence = ev.get("evidence", {})
                html_parts.append(f'<p><strong>来源:</strong> {evidence.get("source", "")}</p>')
                if "alert_level" in evidence:
                    html_parts.append(f'<p><strong>预警级别:</strong> {evidence["alert_level"]}</p>')
                if "prediction_time" in evidence:
                    html_parts.append(f'<p><strong>预测时间:</strong> {evidence["prediction_time"]}</p>')
                if "status_code" in evidence:
                    html_parts.append(f'<p><strong>状态码:</strong> {evidence["status_code"]}</p>')
                if "confidence" in evidence:
                    html_parts.append(f'<p><strong>置信度:</strong> {evidence["confidence"]}</p>')
                if "risk_score" in evidence:
                    html_parts.append(f'<p><strong>风险评分:</strong> {evidence["risk_score"]}</p>')
                if "diagnosis" in evidence:
                    html_parts.append(f'<p><strong>诊断:</strong> {evidence["diagnosis"]}</p>')
                if "screenshot_data" in evidence:
                    html_parts.append(f'<p><strong>截图数据:</strong> {evidence["screenshot_data"]}</p>')
                html_parts.append('</div>')

        html_parts.append('</body></html>')
        return '\n'.join(html_parts)

    def _calculate_completion_score(self, checklist: List[Dict[str, Any]]) -> float:
        if not checklist:
            return 100.0
        total = len(checklist)
        checked = sum(1 for i in checklist if i.get("checked"))
        base_score = (checked / total) * 60.0
        mandatory_items = [i for i in checklist if i.get("is_mandatory")]
        if mandatory_items:
            mandatory_checked = sum(1 for i in mandatory_items if i.get("checked"))
            mandatory_ratio = mandatory_checked / len(mandatory_items)
            bonus = mandatory_ratio * 40.0
        else:
            bonus = 40.0
        return round(min(base_score + bonus, 100.0), 1)

    def _filter_builtin_templates(self, category: str = None) -> List[Dict[str, Any]]:
        result = []
        for t in BUILTIN_STANDARD_TEMPLATES:
            if category and t.get("category") != category:
                continue
            result.append({
                "id": None,
                "code": t["code"],
                "name": t["name"],
                "description": t["description"],
                "version": t["version"],
                "category": t["category"],
                "checklist_items": t["checklist_items"],
                "create_time": None,
                "update_time": None,
            })
        return result

    def _map_equipment_to_category(self, equipment_type: str) -> str:
        mapping = {
            "storage_tank_flange": "storage_tank_flange",
            "pressure_flange_fastening": "pressure_flange_fastening",
            "pressure_vessel_flange": "pressure_vessel_flange",
            "bolt": "storage_tank_flange",
            "flange": "storage_tank_flange",
        }
        return mapping.get(equipment_type, equipment_type)

    def _task_to_dict(self, task) -> Dict[str, Any]:
        checklist = json.loads(task.checklist_items) if task.checklist_items else []
        standard_codes = json.loads(task.standard_codes) if task.standard_codes else []
        return {
            "id": task.id,
            "task_no": task.task_no,
            "work_order_id": task.work_order_id,
            "equipment_type": task.equipment_type,
            "standard_codes": standard_codes,
            "checklist_items": checklist,
            "node_type": task.node_type,
            "node_id": task.node_id,
            "alert_level": task.alert_level,
            "completion_score": task.completion_score or 0.0,
            "status": task.status,
            "auto_check_mandatory": task.auto_check_mandatory if task.auto_check_mandatory is not None else True,
            "create_time": task.create_time.isoformat() if task.create_time else None,
            "update_time": task.update_time.isoformat() if task.update_time else None,
        }

    def _ensure_table(self, db):
        try:
            db.execute("SELECT 1 FROM sc_compliance_standard_templates LIMIT 1")
        except Exception:
            db.execute("""
                CREATE TABLE IF NOT EXISTS sc_compliance_standard_templates (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    code VARCHAR(64) NOT NULL UNIQUE,
                    name VARCHAR(256) NOT NULL,
                    description TEXT,
                    version VARCHAR(32),
                    category VARCHAR(64),
                    checklist_items TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_category (category),
                    INDEX idx_is_active (is_active)
                )
            """)
            db.commit()

    def _ensure_inspection_table(self, db):
        try:
            db.execute("SELECT 1 FROM sc_compliance_inspection_tasks LIMIT 1")
        except Exception:
            db.execute("""
                CREATE TABLE IF NOT EXISTS sc_compliance_inspection_tasks (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    task_no VARCHAR(64) NOT NULL UNIQUE,
                    work_order_id BIGINT,
                    equipment_type VARCHAR(64),
                    standard_codes TEXT,
                    checklist_items TEXT,
                    node_type VARCHAR(20),
                    node_id VARCHAR(100),
                    alert_level INTEGER,
                    completion_score FLOAT DEFAULT 0.0,
                    status VARCHAR(20) DEFAULT 'pending',
                    auto_check_mandatory BOOLEAN DEFAULT TRUE,
                    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_work_order (work_order_id),
                    INDEX idx_status (status),
                    INDEX idx_equipment_type (equipment_type)
                )
            """)
            db.commit()
