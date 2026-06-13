"""
知识库与案例推理 (CBR) 模块

提供基于案例的推理服务，包括：
- 案例录入、审核、版本管理
- 基于特征向量的相似度检索
- 推荐措施生成与 RAG 上下文构建
"""

from app.services.knowledge.knowledge_service import KnowledgeService, CaseSimilarityResult

__all__ = ['KnowledgeService', 'CaseSimilarityResult']
