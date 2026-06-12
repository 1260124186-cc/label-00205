"""
API接口单元测试

测试内容:
1. 健康检查接口
2. 螺栓预测接口
3. 法兰面预测接口
4. 风险评估接口
5. 参数验证
"""

import pytest
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestValidators:
    """验证器测试"""
    
    def test_bolt_request_valid(self):
        """测试有效的螺栓请求"""
        from app.api.validators import DataValidator
        
        validator = DataValidator()
        
        data = [
            [f"20250201 {i:02d}:00:00", 500 + np.random.randn() * 10]
            for i in range(100)
        ]
        
        result = validator.validate_bolt_prediction_request('B001', data)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_bolt_request_empty_id(self):
        """测试空螺栓ID"""
        from app.api.validators import DataValidator
        
        validator = DataValidator()
        
        data = [["20250201 00:00:00", 500]]
        
        result = validator.validate_bolt_prediction_request('', data)
        
        assert not result.is_valid
        assert any(e.field == 'bolt_id' for e in result.errors)
    
    def test_bolt_request_empty_data(self):
        """测试空数据"""
        from app.api.validators import DataValidator
        
        validator = DataValidator()
        
        result = validator.validate_bolt_prediction_request('B001', [])
        
        assert not result.is_valid
        assert any(e.field == 'data' for e in result.errors)
    
    def test_bolt_request_invalid_preload(self):
        """测试无效预紧力值"""
        from app.api.validators import DataValidator
        
        validator = DataValidator()
        
        data = [
            ["20250201 00:00:00", 500],
            ["20250201 00:01:00", "invalid"],  # 无效值
            ["20250201 00:02:00", 500]
        ]
        
        result = validator.validate_bolt_prediction_request('B001', data)
        
        assert not result.is_valid
    
    def test_flange_request_valid(self):
        """测试有效的法兰面请求"""
        from app.api.validators import DataValidator
        
        validator = DataValidator()
        
        # 3个螺栓，每个50个数据点
        data = [
            [
                [f"20250201 {i:02d}:00:00", 500 + np.random.randn() * 10]
                for i in range(50)
            ]
            for _ in range(3)
        ]
        
        result = validator.validate_flange_prediction_request('F001', data)
        
        assert result.is_valid
    
    def test_risk_request_valid(self):
        """测试有效的风险评估请求"""
        from app.api.validators import DataValidator
        
        validator = DataValidator()
        
        data = [["20250201 00:00:00", 500] for _ in range(50)]
        
        result = validator.validate_risk_assessment_request('B001', 'bolt', data)
        
        assert result.is_valid
    
    def test_risk_request_invalid_type(self):
        """测试无效节点类型"""
        from app.api.validators import DataValidator
        
        validator = DataValidator()
        
        data = [["20250201 00:00:00", 500]]
        
        result = validator.validate_risk_assessment_request('B001', 'invalid', data)
        
        assert not result.is_valid


class TestSchemas:
    """数据模型测试"""
    
    def test_bolt_prediction_request(self):
        """测试螺栓预测请求模型"""
        from app.api.schemas import BoltPredictionRequest
        
        request = BoltPredictionRequest(
            bolt_id='B001',
            data=[
                ["20250201 00:00:00", 500.0],
                ["20250201 00:01:00", 501.5]
            ]
        )
        
        assert request.bolt_id == 'B001'
        assert len(request.data) == 2
    
    def test_flange_prediction_request(self):
        """测试法兰面预测请求模型"""
        from app.api.schemas import FlangePredictionRequest
        
        request = FlangePredictionRequest(
            flange_id='F001',
            data=[
                [["20250201 00:00:00", 500.0], ["20250201 00:01:00", 501.0]],
                [["20250201 00:00:00", 505.0], ["20250201 00:01:00", 506.0]]
            ]
        )
        
        assert request.flange_id == 'F001'
        assert len(request.data) == 2


class TestAuth:
    """认证测试"""
    
    def test_api_key_generation(self):
        """测试API密钥生成"""
        from app.api.auth import APIKeyManager
        
        key1 = APIKeyManager.generate_api_key()
        key2 = APIKeyManager.generate_api_key()
        
        assert len(key1) == 32
        assert key1 != key2
    
    def test_rate_limiter(self):
        """测试速率限制器"""
        from app.api.auth import RateLimiter
        from unittest.mock import MagicMock
        
        limiter = RateLimiter(requests_per_minute=5)
        
        # 模拟请求
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = '127.0.0.1'
        
        # 前5次请求应该成功
        for _ in range(5):
            assert limiter.check_rate_limit(mock_request)
        
        # 第6次应该被限制
        with pytest.raises(Exception):  # HTTPException
            limiter.check_rate_limit(mock_request)


class TestContainer:
    """依赖注入容器测试"""
    
    def test_singleton_registration(self):
        """测试单例注册"""
        from app.core.container import Container, Lifetime
        
        container = Container()
        container.reset()
        
        class TestService:
            pass
        
        container.register_singleton('test', TestService)
        
        instance1 = container.resolve('test')
        instance2 = container.resolve('test')
        
        assert instance1 is instance2
    
    def test_transient_registration(self):
        """测试瞬态注册"""
        from app.core.container import Container
        
        container = Container()
        container.reset()
        
        class TestService:
            pass
        
        container.register_transient('test', TestService)
        
        instance1 = container.resolve('test')
        instance2 = container.resolve('test')
        
        assert instance1 is not instance2
    
    def test_instance_registration(self):
        """测试实例注册"""
        from app.core.container import Container
        
        container = Container()
        container.reset()
        
        instance = object()
        container.register_instance('test', instance)
        
        resolved = container.resolve('test')
        
        assert resolved is instance


class TestModelVersion:
    """模型版本管理测试"""
    
    def test_version_generation(self):
        """测试版本号生成"""
        from app.core.model_version import ModelVersionManager
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ModelVersionManager(base_path=tmpdir)
            
            version1 = manager._generate_version('test_model')
            
            assert version1 == 'v1.0.0'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
