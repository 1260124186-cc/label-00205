"""
知识库核心服务模块

提供案例的增删改查、相似度检索、版本管理、审核流程等核心功能。

主要功能:
- create_case: 创建案例
- update_case: 更新案例（自动版本管理）
- search_similar_cases: 基于特征向量的 Top-K 相似度检索
- review_case: 案例审核
- get_case_versions: 获取版本历史
- generate_rag_context: 生成 RAG 上下文
- get_recommendations: 获取推荐措施

使用示例:
    from app.services.knowledge import KnowledgeService
    
    service = KnowledgeService()
    results = service.search_similar_cases(
        feature_vector=[...],
        top_k=5
    )
"""

import json
import re
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from loguru import logger

from app.utils.database import (
    get_db,
    KnowledgeCase,
    KnowledgeCaseVersion,
    KnowledgeCaseReview,
)
from app.utils.config import config
from app.services.feature_engineering import FeatureEngineer


@dataclass
class CaseSimilarityResult:
    """
    相似度检索结果数据类
    
    Attributes:
        case: 案例对象
        similarity_score: 相似度得分 (0-1)
        matching_features: 匹配的特征名称列表
    """
    case: KnowledgeCase
    similarity_score: float
    matching_features: List[str]


class KnowledgeService:
    """
    知识库服务类
    
    提供案例管理、相似度检索、审核和版本管理功能。
    """
    
    def __init__(self):
        """初始化知识库服务"""
        self.feature_engineer = FeatureEngineer()
        
        cbr_config = config.get('cbr', {})
        self.default_top_k = cbr_config.get('default_top_k', 5)
        self.min_similarity_threshold = cbr_config.get('min_similarity_threshold', 0.3)
        self.feature_weight = cbr_config.get('feature_weight', 0.7)
        self.fault_type_weight = cbr_config.get('fault_type_weight', 0.2)
        self.node_weight = cbr_config.get('node_weight', 0.1)
        self.enable_review = cbr_config.get('enable_review', True)
        self.review_required_level = cbr_config.get('review_required_level', 2)
        
        logger.info("知识库服务初始化完成")
    
    # ============================================================
    # 案例管理 - CRUD
    # ============================================================
    
    def create_case(
        self,
        case_title: str,
        node_type: str = None,
        node_id: str = None,
        fault_type: str = None,
        fault_level: int = None,
        working_condition: Dict[str, Any] = None,
        sensor_data: List[List[Any]] = None,
        sensor_features: Dict[str, float] = None,
        diagnosis: str = None,
        root_cause: str = None,
        treatment_plan: Dict[str, Any] = None,
        effect_evaluation: Dict[str, Any] = None,
        source_alert_id: int = None,
        source_prediction_id: int = None,
        tags: List[str] = None,
        creator_id: str = None,
        creator_name: str = None,
        tenant_id: int = None,
        submit_for_review: bool = False,
    ) -> Optional[KnowledgeCase]:
        """
        创建案例
        
        Args:
            case_title: 案例标题
            node_type: 节点类型
            node_id: 节点ID
            fault_type: 故障类型
            fault_level: 故障级别
            working_condition: 工况信息
            sensor_data: 传感器时序数据
            sensor_features: 传感器特征
            diagnosis: 诊断结论
            root_cause: 根本原因
            treatment_plan: 处置方案
            effect_evaluation: 效果评估
            source_alert_id: 来源告警ID
            source_prediction_id: 来源预测ID
            tags: 标签列表
            creator_id: 创建人ID
            creator_name: 创建人姓名
            tenant_id: 租户ID
            submit_for_review: 是否提交审核
            
        Returns:
            创建的案例对象
        """
        with get_db() as db:
            if db is None:
                logger.error("数据库不可用，无法创建案例")
                return None
            
            # 生成案例编号
            case_no = self._generate_case_no(db)
            
            # 提取特征向量
            feature_vector = None
            if sensor_data is not None and len(sensor_data) > 0:
                values = []
                for item in sensor_data:
                    if len(item) >= 2:
                        try:
                            values.append(float(item[1]))
                        except (ValueError, TypeError):
                            pass
                if len(values) >= 5:
                    try:
                        feature_set = self.feature_engineer.extract_features(np.array(values))
                        feature_vector = feature_set.combined_features
                        if sensor_features is None:
                            sensor_features = dict(zip(
                                feature_set.feature_names,
                                feature_set.combined_features.tolist()
                            ))
                    except Exception as e:
                        logger.warning(f"特征提取失败: {e}")
            
            # 如果提供了 sensor_features 但没有 feature_vector，尝试构建
            if feature_vector is None and sensor_features:
                try:
                    feature_vector = np.array(list(sensor_features.values()))
                except Exception:
                    pass
            
            # 归一化特征向量
            normalized_vector = None
            if feature_vector is not None and len(feature_vector) > 0:
                norm = np.linalg.norm(feature_vector)
                if norm > 0:
                    normalized_vector = (feature_vector / norm).tolist()
                else:
                    normalized_vector = feature_vector.tolist()
            
            # 计算效果评分
            effectiveness_score = None
            if effect_evaluation and 'effectiveness_score' in effect_evaluation:
                effectiveness_score = effect_evaluation['effectiveness_score']
            
            # 确定初始状态
            status = 'draft'
            if submit_for_review:
                status = 'pending_review'
            
            case = KnowledgeCase(
                case_no=case_no,
                case_title=case_title,
                node_type=node_type,
                node_id=str(node_id) if node_id else None,
                fault_type=fault_type,
                fault_level=fault_level,
                working_condition=json.dumps(working_condition or {}, ensure_ascii=False),
                sensor_features=json.dumps(sensor_features or {}, ensure_ascii=False),
                feature_vector=','.join(map(str, normalized_vector)) if normalized_vector else None,
                diagnosis=diagnosis,
                root_cause=root_cause,
                treatment_plan=json.dumps(treatment_plan or {}, ensure_ascii=False),
                effect_evaluation=json.dumps(effect_evaluation or {}, ensure_ascii=False),
                effectiveness_score=effectiveness_score,
                status=status,
                version=1,
                tenant_id=tenant_id,
                creator_id=creator_id,
                creator_name=creator_name,
                source_alert_id=source_alert_id,
                source_prediction_id=source_prediction_id,
                tags=json.dumps(tags or [], ensure_ascii=False),
            )
            
            db.add(case)
            db.flush()
            case_id = case.id
            
            # 创建初始版本记录
            self._create_version_record(
                db=db,
                case_id=case_id,
                version=1,
                case=case,
                change_summary='初始版本',
                operator_id=creator_id,
                operator_name=creator_name,
            )
            
            db.commit()
            
            created = db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
            logger.info(f"案例已创建: {case_no}, title={case_title}")
            return created
    
    def get_case(self, case_id: int) -> Optional[KnowledgeCase]:
        """获取案例详情"""
        with get_db() as db:
            if db is None:
                return None
            return db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
    
    def get_case_by_no(self, case_no: str) -> Optional[KnowledgeCase]:
        """根据案例编号获取案例"""
        with get_db() as db:
            if db is None:
                return None
            return db.query(KnowledgeCase).filter(KnowledgeCase.case_no == case_no).first()
    
    def list_cases(
        self,
        status: str = None,
        node_type: str = None,
        fault_type: str = None,
        fault_level: int = None,
        tenant_id: int = None,
        creator_id: str = None,
        tags: List[str] = None,
        keyword: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[int, List[KnowledgeCase]]:
        """
        查询案例列表
        
        Returns:
            (总数, 案例列表)
        """
        with get_db() as db:
            if db is None:
                return 0, []
            
            query = db.query(KnowledgeCase)
            
            if status:
                query = query.filter(KnowledgeCase.status == status)
            if node_type:
                query = query.filter(KnowledgeCase.node_type == node_type)
            if fault_type:
                query = query.filter(KnowledgeCase.fault_type == fault_type)
            if fault_level:
                query = query.filter(KnowledgeCase.fault_level == fault_level)
            if tenant_id:
                query = query.filter(KnowledgeCase.tenant_id == tenant_id)
            if creator_id:
                query = query.filter(KnowledgeCase.creator_id == creator_id)
            if keyword:
                like_keyword = f"%{keyword}%"
                query = query.filter(
                    db.or_(
                        KnowledgeCase.case_title.like(like_keyword),
                        KnowledgeCase.diagnosis.like(like_keyword),
                        KnowledgeCase.fault_type.like(like_keyword),
                    )
                )
            
            total = query.count()
            cases = query.order_by(
                KnowledgeCase.create_time.desc()
            ).offset(offset).limit(limit).all()
            
            return total, cases
    
    def update_case(
        self,
        case_id: int,
        case_title: str = None,
        fault_type: str = None,
        fault_level: int = None,
        working_condition: Dict[str, Any] = None,
        sensor_data: List[List[Any]] = None,
        sensor_features: Dict[str, float] = None,
        diagnosis: str = None,
        root_cause: str = None,
        treatment_plan: Dict[str, Any] = None,
        effect_evaluation: Dict[str, Any] = None,
        tags: List[str] = None,
        change_summary: str = None,
        submit_for_review: bool = False,
        operator_id: str = None,
        operator_name: str = None,
    ) -> Optional[KnowledgeCase]:
        """
        更新案例（自动创建新版本）
        
        Args:
            case_id: 案例ID
            ... 更新字段
            change_summary: 变更说明
            submit_for_review: 是否提交审核
            operator_id: 操作人ID
            operator_name: 操作人姓名
            
        Returns:
            更新后的案例对象
        """
        with get_db() as db:
            if db is None:
                return None
            
            case = db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
            if not case:
                return None
            
            old_version = case.version
            new_version = old_version + 1
            
            # 保存旧版本数据
            self._create_version_record(
                db=db,
                case_id=case_id,
                version=old_version,
                case=case,
                change_summary=change_summary or '更新案例',
                operator_id=operator_id,
                operator_name=operator_name,
            )
            
            # 更新字段
            if case_title is not None:
                case.case_title = case_title
            if fault_type is not None:
                case.fault_type = fault_type
            if fault_level is not None:
                case.fault_level = fault_level
            if working_condition is not None:
                case.working_condition = json.dumps(working_condition, ensure_ascii=False)
            if diagnosis is not None:
                case.diagnosis = diagnosis
            if root_cause is not None:
                case.root_cause = root_cause
            if treatment_plan is not None:
                case.treatment_plan = json.dumps(treatment_plan, ensure_ascii=False)
            if effect_evaluation is not None:
                case.effect_evaluation = json.dumps(effect_evaluation, ensure_ascii=False)
                if 'effectiveness_score' in effect_evaluation:
                    case.effectiveness_score = effect_evaluation['effectiveness_score']
            if tags is not None:
                case.tags = json.dumps(tags, ensure_ascii=False)
            
            # 更新特征向量
            if sensor_data is not None and len(sensor_data) > 0:
                values = []
                for item in sensor_data:
                    if len(item) >= 2:
                        try:
                            values.append(float(item[1]))
                        except (ValueError, TypeError):
                            pass
                if len(values) >= 5:
                    try:
                        feature_set = self.feature_engineer.extract_features(np.array(values))
                        feature_vector = feature_set.combined_features
                        norm = np.linalg.norm(feature_vector)
                        if norm > 0:
                            normalized = (feature_vector / norm).tolist()
                        else:
                            normalized = feature_vector.tolist()
                        case.feature_vector = ','.join(map(str, normalized))
                        if sensor_features is None:
                            sensor_features = dict(zip(
                                feature_set.feature_names,
                                feature_set.combined_features.tolist()
                            ))
                    except Exception as e:
                        logger.warning(f"特征提取失败: {e}")
            
            if sensor_features is not None:
                case.sensor_features = json.dumps(sensor_features, ensure_ascii=False)
                if case.feature_vector is None:
                    try:
                        vec = np.array(list(sensor_features.values()))
                        norm = np.linalg.norm(vec)
                        if norm > 0:
                            normalized = (vec / norm).tolist()
                        else:
                            normalized = vec.tolist()
                        case.feature_vector = ','.join(map(str, normalized))
                    except Exception:
                        pass
            
            # 更新版本号和状态
            case.version = new_version
            if submit_for_review and case.status != 'pending_review':
                case.status = 'pending_review'
            elif case.status == 'approved':
                # 已审核通过的案例修改后回到草稿状态
                case.status = 'draft'
            
            db.commit()
            
            updated = db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
            logger.info(f"案例已更新: {case.case_no}, version={new_version}")
            return updated
    
    def delete_case(self, case_id: int) -> bool:
        """删除案例"""
        with get_db() as db:
            if db is None:
                return False
            
            case = db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
            if not case:
                return False
            
            # 删除版本记录和审核记录
            db.query(KnowledgeCaseVersion).filter(
                KnowledgeCaseVersion.case_id == case_id
            ).delete()
            db.query(KnowledgeCaseReview).filter(
                KnowledgeCaseReview.case_id == case_id
            ).delete()
            
            db.delete(case)
            db.commit()
            
            logger.info(f"案例已删除: {case.case_no}")
            return True
    
    # ============================================================
    # 相似度检索
    # ============================================================
    
    def search_similar_cases(
        self,
        node_type: str = None,
        node_id: str = None,
        fault_type: str = None,
        fault_level: int = None,
        sensor_data: List[List[Any]] = None,
        sensor_features: Dict[str, float] = None,
        feature_vector: List[float] = None,
        tags: List[str] = None,
        top_k: int = None,
        min_similarity: float = None,
        only_approved: bool = True,
        tenant_id: int = None,
    ) -> List[CaseSimilarityResult]:
        """
        基于特征向量检索 Top-K 相似案例
        
        相似度计算方式:
        - 特征向量相似度 (余弦相似度): 权重 70%
        - 故障类型匹配: 权重 20%
        - 节点类型匹配: 权重 10%
        
        Args:
            node_type: 节点类型
            node_id: 节点ID
            fault_type: 故障类型
            fault_level: 故障级别
            sensor_data: 传感器时序数据
            sensor_features: 传感器特征
            feature_vector: 特征向量
            tags: 标签过滤
            top_k: 返回数量
            min_similarity: 最低相似度
            only_approved: 只返回已审核通过的
            tenant_id: 租户ID
            
        Returns:
            相似度结果列表（按相似度降序排列）
        """
        top_k = top_k or self.default_top_k
        min_similarity = min_similarity or self.min_similarity_threshold
        
        # 1. 构建查询特征向量
        query_vec = None
        
        if feature_vector is not None and len(feature_vector) > 0:
            query_vec = np.array(feature_vector)
        elif sensor_data is not None and len(sensor_data) > 0:
            values = []
            for item in sensor_data:
                if len(item) >= 2:
                    try:
                        values.append(float(item[1]))
                    except (ValueError, TypeError):
                        pass
            if len(values) >= 5:
                try:
                    feature_set = self.feature_engineer.extract_features(np.array(values))
                    query_vec = feature_set.combined_features
                except Exception as e:
                    logger.warning(f"查询特征提取失败: {e}")
        elif sensor_features is not None and len(sensor_features) > 0:
            try:
                query_vec = np.array(list(sensor_features.values()))
            except Exception:
                pass
        
        # 归一化查询向量
        if query_vec is not None and len(query_vec) > 0:
            norm = np.linalg.norm(query_vec)
            if norm > 0:
                query_vec = query_vec / norm
        
        # 2. 查询候选案例
        with get_db() as db:
            if db is None:
                return []
            
            query = db.query(KnowledgeCase)
            
            if only_approved:
                query = query.filter(KnowledgeCase.status == 'approved')
            if node_type:
                query = query.filter(KnowledgeCase.node_type == node_type)
            if fault_type:
                query = query.filter(KnowledgeCase.fault_type == fault_type)
            if fault_level:
                query = query.filter(KnowledgeCase.fault_level == fault_level)
            if tenant_id:
                query = query.filter(KnowledgeCase.tenant_id == tenant_id)
            
            # 只选择有特征向量的案例用于相似度计算
            query = query.filter(KnowledgeCase.feature_vector.isnot(None))
            
            # 限制候选集大小，避免过多计算
            candidates = query.order_by(
                KnowledgeCase.effectiveness_score.desc().nullslast(),
                KnowledgeCase.create_time.desc()
            ).limit(500).all()
            
            if not candidates:
                return []
            
            # 3. 计算相似度
            results = []
            
            for case in candidates:
                total_score = 0.0
                matching_features = []
                weights_used = 0.0
                
                # 特征向量相似度
                if query_vec is not None and case.feature_vector:
                    try:
                        case_vec = np.array([float(x) for x in case.feature_vector.split(',')])
                        if len(case_vec) == len(query_vec):
                            # 余弦相似度
                            cos_sim = float(np.dot(query_vec, case_vec))
                            cos_sim = max(0.0, min(1.0, cos_sim))
                            total_score += cos_sim * self.feature_weight
                            weights_used += self.feature_weight
                            
                            # 计算匹配的特征（值接近的特征）
                            if sensor_features:
                                try:
                                    case_features = json.loads(case.sensor_features) if case.sensor_features else {}
                                    for feat_name in list(sensor_features.keys())[:10]:
                                        if feat_name in case_features:
                                            matching_features.append(feat_name)
                                except Exception:
                                    pass
                    except Exception as e:
                        logger.debug(f"相似度计算失败: {e}")
                
                # 故障类型匹配
                if fault_type and case.fault_type == fault_type:
                    total_score += 1.0 * self.fault_type_weight
                    weights_used += self.fault_type_weight
                    matching_features.append('故障类型')
                
                # 故障级别匹配
                if fault_level and case.fault_level == fault_level:
                    total_score += 0.5 * self.fault_type_weight
                    weights_used += self.fault_type_weight * 0.5
                
                # 节点类型匹配
                if node_type and case.node_type == node_type:
                    total_score += 1.0 * self.node_weight
                    weights_used += self.node_weight
                    matching_features.append('节点类型')
                
                # 如果有权重未使用，归一化分数
                if weights_used > 0 and weights_used < 1.0:
                    total_score = total_score / weights_used
                
                # 效果评分加成
                if case.effectiveness_score:
                    effectiveness_bonus = (case.effectiveness_score / 100.0) * 0.1
                    total_score = min(1.0, total_score + effectiveness_bonus)
                
                if total_score >= min_similarity:
                    results.append(CaseSimilarityResult(
                        case=case,
                        similarity_score=round(total_score, 4),
                        matching_features=list(set(matching_features)),
                    ))
            
            # 按相似度排序，取 Top-K
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:top_k]
    
    # ============================================================
    # 审核流程
    # ============================================================
    
    def submit_for_review(
        self,
        case_id: int,
        operator_id: str = None,
        operator_name: str = None,
    ) -> Optional[KnowledgeCase]:
        """提交案例审核"""
        with get_db() as db:
            if db is None:
                return None
            
            case = db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
            if not case:
                return None
            
            if case.status in ('draft', 'rejected'):
                case.status = 'pending_review'
                db.commit()
                logger.info(f"案例已提交审核: {case.case_no}")
            
            return db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
    
    def review_case(
        self,
        case_id: int,
        review_result: str,
        review_comment: str = None,
        reviewer_id: str = None,
        reviewer_name: str = None,
        review_level: int = 1,
    ) -> Optional[KnowledgeCase]:
        """
        审核案例
        
        Args:
            case_id: 案例ID
            review_result: 审核结果 approved/rejected/revision_required
            review_comment: 审核意见
            reviewer_id: 审核人ID
            reviewer_name: 审核人姓名
            review_level: 审核级别
            
        Returns:
            审核后的案例
        """
        valid_results = ('approved', 'rejected', 'revision_required')
        if review_result not in valid_results:
            raise ValueError(f"无效的审核结果: {review_result}")
        
        with get_db() as db:
            if db is None:
                return None
            
            case = db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
            if not case:
                return None
            
            # 创建审核记录
            review = KnowledgeCaseReview(
                case_id=case_id,
                version=case.version,
                review_level=review_level,
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
                review_result=review_result,
                review_comment=review_comment,
            )
            db.add(review)
            
            # 更新案例状态
            if review_result == 'approved':
                case.status = 'approved'
                case.reviewer_id = reviewer_id
                case.reviewer_name = reviewer_name
                case.review_time = datetime.now()
                case.review_comment = review_comment
            elif review_result == 'rejected':
                case.status = 'rejected'
                case.reviewer_id = reviewer_id
                case.reviewer_name = reviewer_name
                case.review_time = datetime.now()
                case.review_comment = review_comment
            elif review_result == 'revision_required':
                case.status = 'draft'
                case.review_comment = review_comment
            
            db.commit()
            
            logger.info(
                f"案例审核完成: {case.case_no}, result={review_result}, "
                f"reviewer={reviewer_name}"
            )
            
            return db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
    
    def list_reviews(self, case_id: int) -> List[KnowledgeCaseReview]:
        """获取案例的审核记录列表"""
        with get_db() as db:
            if db is None:
                return []
            
            return db.query(KnowledgeCaseReview).filter(
                KnowledgeCaseReview.case_id == case_id
            ).order_by(KnowledgeCaseReview.create_time.desc()).all()
    
    # ============================================================
    # 版本管理
    # ============================================================
    
    def get_case_versions(self, case_id: int) -> List[KnowledgeCaseVersion]:
        """获取案例版本历史"""
        with get_db() as db:
            if db is None:
                return []
            
            return db.query(KnowledgeCaseVersion).filter(
                KnowledgeCaseVersion.case_id == case_id
            ).order_by(KnowledgeCaseVersion.version.desc()).all()
    
    def get_case_version(self, case_id: int, version: int) -> Optional[KnowledgeCaseVersion]:
        """获取指定版本的案例"""
        with get_db() as db:
            if db is None:
                return None
            
            return db.query(KnowledgeCaseVersion).filter(
                KnowledgeCaseVersion.case_id == case_id,
                KnowledgeCaseVersion.version == version,
            ).first()
    
    def compare_versions(
        self,
        case_id: int,
        version_from: int,
        version_to: int,
    ) -> Dict[str, Any]:
        """
        对比两个版本的差异
        
        Returns:
            差异字典 {字段名: {from: ..., to: ...}}
        """
        with get_db() as db:
            if db is None:
                return {}
            
            v1 = db.query(KnowledgeCaseVersion).filter(
                KnowledgeCaseVersion.case_id == case_id,
                KnowledgeCaseVersion.version == version_from,
            ).first()
            
            v2 = db.query(KnowledgeCaseVersion).filter(
                KnowledgeCaseVersion.case_id == case_id,
                KnowledgeCaseVersion.version == version_to,
            ).first()
            
            if not v1 or not v2:
                return {}
            
            changes = {}
            
            compare_fields = [
                ('case_title', '案例标题'),
                ('diagnosis', '诊断结论'),
                ('root_cause', '根本原因'),
                ('treatment_plan', '处置方案'),
                ('effect_evaluation', '效果评估'),
                ('effectiveness_score', '效果评分'),
            ]
            
            for field, label in compare_fields:
                val1 = getattr(v1, field)
                val2 = getattr(v2, field)
                if val1 != val2:
                    changes[label] = {'from': val1, 'to': val2}
            
            return {
                'case_id': case_id,
                'version_from': version_from,
                'version_to': version_to,
                'changes': changes,
            }
    
    def revert_to_version(
        self,
        case_id: int,
        target_version: int,
        operator_id: str = None,
        operator_name: str = None,
    ) -> Optional[KnowledgeCase]:
        """
        回退到指定版本（会创建新版本）
        
        Args:
            case_id: 案例ID
            target_version: 目标版本号
            operator_id: 操作人ID
            operator_name: 操作人姓名
            
        Returns:
            回退后的案例
        """
        with get_db() as db:
            if db is None:
                return None
            
            case = db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
            if not case:
                return None
            
            version_record = db.query(KnowledgeCaseVersion).filter(
                KnowledgeCaseVersion.case_id == case_id,
                KnowledgeCaseVersion.version == target_version,
            ).first()
            
            if not version_record:
                return None
            
            old_version = case.version
            new_version = old_version + 1
            
            # 保存当前版本
            self._create_version_record(
                db=db,
                case_id=case_id,
                version=old_version,
                case=case,
                change_summary=f'回退到版本 {target_version} 前的备份',
                operator_id=operator_id,
                operator_name=operator_name,
            )
            
            # 回退内容
            if version_record.case_title:
                case.case_title = version_record.case_title
            if version_record.diagnosis:
                case.diagnosis = version_record.diagnosis
            if version_record.root_cause:
                case.root_cause = version_record.root_cause
            if version_record.treatment_plan:
                case.treatment_plan = version_record.treatment_plan
            if version_record.effect_evaluation:
                case.effect_evaluation = version_record.effect_evaluation
            if version_record.effectiveness_score is not None:
                case.effectiveness_score = version_record.effectiveness_score
            if version_record.feature_vector:
                case.feature_vector = version_record.feature_vector
            
            case.version = new_version
            case.status = 'draft'  # 回退后回到草稿状态
            
            db.commit()
            
            logger.info(
                f"案例已回退: {case.case_no}, from v{old_version} to v{target_version} "
                f"(new version {new_version})"
            )
            
            return db.query(KnowledgeCase).filter(KnowledgeCase.id == case_id).first()
    
    # ============================================================
    # 推荐措施与 RAG 上下文
    # ============================================================
    
    def generate_recommendations(
        self,
        similar_cases: List[CaseSimilarityResult],
    ) -> List[str]:
        """
        基于相似案例生成推荐措施
        
        Args:
            similar_cases: 相似案例列表
            
        Returns:
            推荐措施列表
        """
        recommendations = []
        seen = set()
        
        for result in similar_cases:
            case = result.case
            
            # 从处置方案中提取措施
            try:
                treatment_plan = json.loads(case.treatment_plan) if case.treatment_plan else {}
                steps = treatment_plan.get('steps', [])
                for step in steps:
                    action = step.get('action', '')
                    if action and action not in seen:
                        seen.add(action)
                        recommendations.append(action)
            except Exception:
                pass
            
            # 如果处置方案为空，尝试从诊断中提取
            if not recommendations and case.diagnosis:
                rec = self._extract_recommendation_from_diagnosis(case.diagnosis)
                for r in rec:
                    if r not in seen:
                        seen.add(r)
                        recommendations.append(r)
        
        return recommendations
    
    def generate_rag_context(
        self,
        similar_cases: List[CaseSimilarityResult],
        max_cases: int = 3,
    ) -> str:
        """
        生成 RAG 上下文文本
        
        将相似案例格式化为适合 LLM 使用的上下文文本。
        
        Args:
            similar_cases: 相似案例列表
            max_cases: 最大案例数
            
        Returns:
            RAG 上下文字符串
        """
        if not similar_cases:
            return ""
        
        context_parts = []
        context_parts.append("## 历史相似故障案例\n")
        
        for i, result in enumerate(similar_cases[:max_cases], 1):
            case = result.case
            
            case_parts = [f"### 案例 {i}: {case.case_title}\n"]
            case_parts.append(f"- 相似度: {result.similarity_score:.2%}")
            case_parts.append(f"- 案例编号: {case.case_no}")
            
            if case.fault_type:
                case_parts.append(f"- 故障类型: {case.fault_type}")
            if case.fault_level:
                level_labels = {1: '关注级', 2: '检查级', 3: '紧急级', 4: '故障级'}
                case_parts.append(f"- 故障级别: {level_labels.get(case.fault_level, case.fault_level)}")
            if case.effectiveness_score:
                case_parts.append(f"- 效果评分: {case.effectiveness_score}/100")
            
            if case.diagnosis:
                case_parts.append(f"\n**诊断结论**: {case.diagnosis}")
            
            if case.root_cause:
                case_parts.append(f"\n**根本原因**: {case.root_cause}")
            
            # 处置方案
            try:
                treatment_plan = json.loads(case.treatment_plan) if case.treatment_plan else {}
                steps = treatment_plan.get('steps', [])
                if steps:
                    case_parts.append("\n**处置方案**:")
                    for step in steps:
                        step_order = step.get('step_order', '')
                        action = step.get('action', '')
                        desc = step.get('description', '')
                        if step_order:
                            case_parts.append(f"{step_order}. {action}")
                        else:
                            case_parts.append(f"- {action}")
                        if desc:
                            case_parts.append(f"  {desc}")
            except Exception:
                pass
            
            # 效果评估
            try:
                effect_eval = json.loads(case.effect_evaluation) if case.effect_evaluation else {}
                if effect_eval:
                    notes = effect_eval.get('notes', '')
                    if notes:
                        case_parts.append(f"\n**效果评估**: {notes}")
            except Exception:
                pass
            
            context_parts.append('\n'.join(case_parts))
        
        context_parts.append(
            "\n---\n"
            "请参考以上历史案例进行诊断和处置建议，结合当前实际情况综合判断。"
        )
        
        return '\n\n'.join(context_parts)
    
    def get_case_recommendations(
        self,
        node_type: str = None,
        node_id: str = None,
        fault_type: str = None,
        fault_level: int = None,
        sensor_data: List[List[Any]] = None,
        sensor_features: Dict[str, float] = None,
        feature_vector: List[float] = None,
        top_k: int = None,
        min_similarity: float = None,
        only_approved: bool = True,
        tenant_id: int = None,
    ) -> Dict[str, Any]:
        """
        获取案例推荐（包含推荐措施和 RAG 上下文）
        
        Args:
            ... 检索参数
            
        Returns:
            {
                'top_k': int,
                'total_matched': int,
                'cases': [...],
                'aggregated_recommendations': [...],
                'rag_context': '...',
                'confidence_score': float
            }
        """
        similar_cases = self.search_similar_cases(
            node_type=node_type,
            node_id=node_id,
            fault_type=fault_type,
            fault_level=fault_level,
            sensor_data=sensor_data,
            sensor_features=sensor_features,
            feature_vector=feature_vector,
            top_k=top_k,
            min_similarity=min_similarity,
            only_approved=only_approved,
            tenant_id=tenant_id,
        )
        
        recommendations = self.generate_recommendations(similar_cases)
        rag_context = self.generate_rag_context(similar_cases)
        
        # 计算置信度分数
        confidence_score = 0.0
        if similar_cases:
            avg_sim = sum(r.similarity_score for r in similar_cases) / len(similar_cases)
            top_sim = similar_cases[0].similarity_score
            confidence_score = round(avg_sim * 0.6 + top_sim * 0.4, 4)
        
        return {
            'top_k': top_k or self.default_top_k,
            'total_matched': len(similar_cases),
            'cases': [r.case for r in similar_cases],
            'aggregated_recommendations': recommendations,
            'rag_context': rag_context,
            'confidence_score': confidence_score,
        }
    
    # ============================================================
    # 内部方法
    # ============================================================
    
    def _generate_case_no(self, db) -> str:
        """生成唯一案例编号"""
        now = datetime.now()
        prefix = now.strftime('KCS%Y%m%d%H%M%S')
        for i in range(100):
            candidate = f"{prefix}{i:02d}"
            exists = db.query(KnowledgeCase).filter(
                KnowledgeCase.case_no == candidate
            ).first()
            if not exists:
                return candidate
        raise RuntimeError("生成案例编号失败")
    
    def _create_version_record(
        self,
        db,
        case_id: int,
        version: int,
        case,
        change_summary: str,
        operator_id: str = None,
        operator_name: str = None,
    ) -> None:
        """创建版本记录"""
        version_record = KnowledgeCaseVersion(
            case_id=case_id,
            version=version,
            case_title=case.case_title,
            diagnosis=case.diagnosis,
            root_cause=case.root_cause,
            treatment_plan=case.treatment_plan,
            effect_evaluation=case.effect_evaluation,
            effectiveness_score=case.effectiveness_score,
            feature_vector=case.feature_vector,
            change_summary=change_summary,
            operator_id=operator_id,
            operator_name=operator_name,
        )
        db.add(version_record)
    
    def _extract_recommendation_from_diagnosis(self, diagnosis: str) -> List[str]:
        """从诊断文本中提取推荐措施"""
        recommendations = []
        
        # 简单的关键词匹配
        patterns = [
            r'建议[：:](.*?)(?:。|$)',
            r'应[：:](.*?)(?:。|$)',
            r'需要[：:](.*?)(?:。|$)',
            r'推荐[：:](.*?)(?:。|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, diagnosis)
            for match in matches:
                recs = re.split(r'[；;、，,]', match)
                for rec in recs:
                    rec = rec.strip()
                    if rec and len(rec) > 2:
                        recommendations.append(rec)
        
        if not recommendations:
            # 如果没有提取到，返回通用建议
            recommendations.append('加强监测频率')
            recommendations.append('安排专业检查')
        
        return recommendations[:5]
    
    # ============================================================
    # 统计信息
    # ============================================================
    
    def get_statistics(self, tenant_id: int = None) -> Dict[str, Any]:
        """获取知识库统计信息"""
        with get_db() as db:
            if db is None:
                return {}
            
            query = db.query(KnowledgeCase)
            if tenant_id:
                query = query.filter(KnowledgeCase.tenant_id == tenant_id)
            
            total = query.count()
            
            approved = query.filter(KnowledgeCase.status == 'approved').count()
            pending = query.filter(KnowledgeCase.status == 'pending_review').count()
            draft = query.filter(KnowledgeCase.status == 'draft').count()
            rejected = query.filter(KnowledgeCase.status == 'rejected').count()
            
            # 按故障类型统计
            fault_types = {}
            try:
                from sqlalchemy import func
                results = db.query(
                    KnowledgeCase.fault_type,
                    func.count(KnowledgeCase.id)
                ).filter(
                    KnowledgeCase.fault_type.isnot(None)
                ).group_by(KnowledgeCase.fault_type).all()
                for ft, count in results:
                    fault_types[ft] = count
            except Exception:
                pass
            
            # 平均效果评分
            avg_effectiveness = None
            try:
                from sqlalchemy import func
                result = db.query(func.avg(KnowledgeCase.effectiveness_score)).filter(
                    KnowledgeCase.effectiveness_score.isnot(None)
                ).scalar()
                if result:
                    avg_effectiveness = round(float(result), 2)
            except Exception:
                pass
            
            return {
                'total': total,
                'by_status': {
                    'approved': approved,
                    'pending_review': pending,
                    'draft': draft,
                    'rejected': rejected,
                },
                'by_fault_type': fault_types,
                'avg_effectiveness_score': avg_effectiveness,
            }
