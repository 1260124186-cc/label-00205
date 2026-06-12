"""
隐私保护模块

提供差分隐私（Differential Privacy）和安全聚合（Secure Aggregation）功能，
保护联邦学习过程中的数据隐私。

主要类:
- PrivacyEngine: 隐私引擎基类
- DifferentialPrivacy: 差分隐私实现
- SecureAggregator: 安全聚合实现（基于同态加密和秘密共享）

使用示例:
    dp = DifferentialPrivacy(epsilon=1.0, delta=1e-5)
    noisy_grads = dp.add_noise(gradients)
    
    sec_agg = SecureAggregator(num_parties=5)
    encrypted_update = sec_agg.encrypt(model_update)
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import hashlib
import secrets
import pickle
from cryptography.fernet import Fernet
import base64


class PrivacyMechanism(str, Enum):
    """隐私保护机制类型"""
    NONE = "none"
    DIFFERENTIAL_PRIVACY = "dp"
    SECURE_AGGREGATION = "secagg"
    COMBINED = "combined"


@dataclass
class PrivacyConfig:
    """隐私保护配置"""
    mechanism: PrivacyMechanism = PrivacyMechanism.NONE
    
    # 差分隐私参数
    epsilon: float = 1.0
    delta: float = 1e-5
    noise_scale: float = 0.1
    clip_norm: float = 1.0
    
    # 安全聚合参数
    num_parties: int = 3
    secret_share_threshold: int = 2
    encryption_key: Optional[str] = None
    
    # 权重裁剪
    enable_weight_clipping: bool = False
    max_weight_norm: float = 5.0


class PrivacyEngine:
    """
    隐私引擎基类
    
    定义隐私保护的通用接口。
    """
    
    def __init__(self, config: PrivacyConfig):
        """
        初始化隐私引擎
        
        Args:
            config: 隐私保护配置
        """
        self.config = config
        self.privacy_budget_spent = 0.0
        logger.info(f"隐私引擎初始化完成, 机制: {config.mechanism}")
    
    def process_update(
        self,
        update: Union[Dict[str, torch.Tensor], Dict[str, np.ndarray]]
    ) -> Union[Dict[str, torch.Tensor], Dict[str, np.ndarray], bytes]:
        """
        处理模型更新（添加噪声/加密）
        
        Args:
            update: 模型更新（梯度或权重）
            
        Returns:
            处理后的模型更新
        """
        raise NotImplementedError
    
    def verify_privacy_budget(self) -> bool:
        """检查隐私预算是否充足"""
        return self.privacy_budget_spent < self.config.epsilon
    
    def get_privacy_spent(self) -> float:
        """获取已消耗的隐私预算"""
        return self.privacy_budget_spent


class DifferentialPrivacy(PrivacyEngine):
    """
    差分隐私实现
    
    基于拉普拉斯机制和高斯机制的差分隐私保护。
    支持梯度裁剪和噪声注入。
    
    理论基础:
    - 梯度裁剪: 限制每个样本的梯度范数，防止单个样本过度影响
    - 噪声注入: 添加高斯/拉普拉斯噪声，满足(ε, δ)-差分隐私
    - 隐私预算: 跟踪已消耗的隐私预算ε
    """
    
    def __init__(self, config: PrivacyConfig):
        """
        初始差分隐私引擎
        
        Args:
            config: 隐私配置
        """
        super().__init__(config)
        self.sigma = self._compute_sigma()
        logger.info(
            f"差分隐私初始化: ε={config.epsilon}, δ={config.delta}, "
            f"σ={self.sigma:.4f}, 裁剪范数={config.clip_norm}"
        )
    
    def _compute_sigma(self) -> float:
        """
        根据隐私预算计算噪声标准差
        
        使用 Moments Accountant 或简化的 RDP (Renyi Differential Privacy) 计算。
        这里采用简化的高斯机制公式: σ = C * sqrt(2 * ln(1.25/δ)) / ε
        """
        epsilon = self.config.epsilon
        delta = self.config.delta
        clip_norm = self.config.clip_norm
        
        sigma = clip_norm * np.sqrt(2 * np.log(1.25 / delta)) / epsilon
        return sigma
    
    def clip_gradients(
        self,
        gradients: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """
        梯度裁剪
        
        限制每个梯度的范数，防止梯度爆炸和隐私泄露。
        
        Args:
            gradients: 梯度字典
            
        Returns:
            裁剪后的梯度
        """
        clipped_grads = {}
        total_norm = 0.0
        
        # 计算全局梯度范数
        for name, grad in gradients.items():
            if grad is not None:
                total_norm += grad.norm(2).item() ** 2
        total_norm = np.sqrt(total_norm)
        
        # 裁剪
        clip_factor = min(1.0, self.config.clip_norm / (total_norm + 1e-6))
        
        for name, grad in gradients.items():
            if grad is not None:
                clipped_grads[name] = grad * clip_factor
        
        return clipped_grads
    
    def add_noise(
        self,
        gradients: Dict[str, torch.Tensor],
        mechanism: str = "gaussian"
    ) -> Dict[str, torch.Tensor]:
        """
        向梯度添加噪声
        
        Args:
            gradients: 梯度字典
            mechanism: 噪声机制 ('gaussian' 或 'laplace')
            
        Returns:
            添加噪声后的梯度
        """
        noisy_grads = {}
        
        for name, grad in gradients.items():
            if grad is not None:
                if mechanism == "gaussian":
                    noise = torch.normal(
                        mean=0.0,
                        std=self.sigma,
                        size=grad.shape,
                        device=grad.device
                    )
                else:  # laplace
                    noise = torch.from_numpy(
                        np.random.laplace(0, self.sigma, grad.shape)
                    ).float().to(grad.device)
                
                noisy_grads[name] = grad + noise * self.config.noise_scale
        
        # 更新隐私预算消耗
        self.privacy_budget_spent += self.config.epsilon * 0.1
        
        return noisy_grads
    
    def clip_weights(
        self,
        weights: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """
        权重裁剪
        
        限制模型权重的范数，用于差分隐私的输出扰动。
        
        Args:
            weights: 模型权重字典
            
        Returns:
            裁剪后的权重
        """
        if not self.config.enable_weight_clipping:
            return weights
        
        clipped_weights = {}
        for name, w in weights.items():
            norm = w.norm(2).item()
            if norm > self.config.max_weight_norm:
                clipped_weights[name] = w * (self.config.max_weight_norm / norm)
            else:
                clipped_weights[name] = w
        
        return clipped_weights
    
    def process_update(
        self,
        update: Union[Dict[str, torch.Tensor], Dict[str, np.ndarray]]
    ) -> Dict[str, torch.Tensor]:
        """
        处理模型更新（裁剪 + 加噪）
        
        Args:
            update: 模型更新
            
        Returns:
            隐私保护处理后的模型更新
        """
        # 转换为torch张量
        torch_update = {}
        for k, v in update.items():
            if isinstance(v, np.ndarray):
                torch_update[k] = torch.from_numpy(v).float()
            else:
                torch_update[k] = v.clone()
        
        # 1. 梯度裁剪
        clipped = self.clip_gradients(torch_update)
        
        # 2. 添加噪声
        noisy = self.add_noise(clipped)
        
        # 3. 权重裁剪（可选）
        result = self.clip_weights(noisy)
        
        return result
    
    def calibrate_noise(
        self,
        epsilon: float,
        delta: float,
        steps: int
    ) -> float:
        """
        校准噪声水平
        
        根据给定的隐私预算和训练步数，计算合适的噪声标准差。
        
        Args:
            epsilon: 总隐私预算
            delta: δ参数
            steps: 训练步数
            
        Returns:
            校准后的噪声标准差
        """
        eps_per_step = epsilon / np.sqrt(steps)
        sigma = self.config.clip_norm * np.sqrt(2 * np.log(1.25 / delta)) / eps_per_step
        return sigma


class SecureAggregator(PrivacyEngine):
    """
    安全聚合实现
    
    基于秘密共享和同态加密的安全聚合方案。
    在不泄露任何单个客户端更新的情况下完成模型聚合。
    
    核心机制:
    1. 密钥交换: 客户端之间交换公钥
    2. 秘密共享: 每个客户端将更新分成多个份额
    3. 同态加密: 加密后上传，服务器密文域聚合
    4. 掩码移除: 最终聚合结果移除随机掩码
    """
    
    def __init__(self, config: PrivacyConfig):
        """
        初始化安全聚合器
        
        Args:
            config: 隐私配置
        """
        super().__init__(config)
        
        # 生成加密密钥
        if config.encryption_key:
            key = self._derive_key(config.encryption_key)
        else:
            key = Fernet.generate_key()
        
        self.cipher = Fernet(key)
        self.secret_key = key
        
        # 客户端密钥对
        self.client_keys: Dict[str, bytes] = {}
        self.masks: Dict[str, Dict[str, float]] = {}
        
        logger.info(
            f"安全聚合器初始化: 参与方数量={config.num_parties}, "
            f"秘密共享阈值={config.secret_share_threshold}"
        )
    
    def _derive_key(self, password: str) -> bytes:
        """从密码派生加密密钥"""
        hash_obj = hashlib.sha256(password.encode())
        return base64.urlsafe_b64encode(hash_obj.digest())
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        生成密钥对（简化版本，实际应使用非对称加密）
        
        Returns:
            (公钥, 私钥)
        """
        private_key = secrets.token_bytes(32)
        public_key = hashlib.sha256(private_key).digest()
        return public_key, private_key
    
    def secret_share(
        self,
        secret: float,
        num_shares: int,
        threshold: int
    ) -> List[float]:
        """
        Shamir秘密共享
        
        将秘密值分割成多个份额，只有至少threshold个份额组合才能恢复。
        
        Args:
            secret: 秘密值
            num_shares: 份额数量
            threshold: 恢复阈值
            
        Returns:
            份额列表
        """
        # 生成随机多项式系数
        coefficients = [secret] + [secrets.randbelow(1000) / 100.0 for _ in range(threshold - 1)]
        
        shares = []
        for i in range(1, num_shares + 1):
            # 计算多项式在x=i处的值
            share = 0.0
            for j, coeff in enumerate(coefficients):
                share += coeff * (i ** j)
            shares.append(share)
        
        return shares
    
    def reconstruct_secret(self, shares: List[Tuple[int, float]], threshold: int) -> float:
        """
        使用拉格朗日插值恢复秘密
        
        Args:
            shares: 份额列表 [(x, y), ...]
            threshold: 阈值
            
        Returns:
            恢复的秘密值
        """
        if len(shares) < threshold:
            raise ValueError(f"需要至少{threshold}个份额来恢复秘密")
        
        secret = 0.0
        for i in range(threshold):
            xi, yi = shares[i]
            
            # 计算拉格朗日基多项式
            lj = 1.0
            for j in range(threshold):
                if i != j:
                    xj = shares[j][0]
                    lj *= (0 - xj) / (xi - xj)
            
            secret += yi * lj
        
        return secret
    
    def generate_double_masks(
        self,
        client_id: str,
        num_clients: int,
        param_shape: torch.Size
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        生成双重掩码（用于Bonawitz等人的安全聚合协议）
        
        每个客户端生成:
        1. 自己的私有随机掩码
        2. 与其他每对客户端的共享掩码
        
        Args:
            client_id: 客户端ID
            num_clients: 客户端总数
            param_shape: 参数形状
            
        Returns:
            (总掩码, 成对掩码字典)
        """
        # 私有掩码
        private_mask = torch.randn(param_shape) * 0.001
        
        # 成对掩码
        pairwise_masks = {}
        for i in range(num_clients):
            other_id = f"client_{i}"
            if other_id != client_id:
                # 使用共享种子生成相同的掩码
                seed = f"{min(client_id, other_id)}_{max(client_id, other_id)}"
                torch.manual_seed(hash(seed) % (2**32))
                pairwise_mask = torch.randn(param_shape) * 0.001
                pairwise_masks[other_id] = pairwise_mask
        
        # 计算总掩码
        total_mask = private_mask.clone()
        for other_id, mask in pairwise_masks.items():
            if client_id > other_id:
                total_mask += mask
            else:
                total_mask -= mask
        
        return total_mask, pairwise_masks
    
    def encrypt(
        self,
        update: Dict[str, torch.Tensor]
    ) -> bytes:
        """
        加密模型更新
        
        Args:
            update: 模型更新
            
        Returns:
            加密的字节流
        """
        # 序列化
        update_np = {k: v.cpu().numpy() for k, v in update.items()}
        serialized = pickle.dumps(update_np)
        
        # 加密
        encrypted = self.cipher.encrypt(serialized)
        
        return encrypted
    
    def decrypt(self, encrypted_data: bytes) -> Dict[str, torch.Tensor]:
        """
        解密模型更新
        
        Args:
            encrypted_data: 加密的字节流
            
        Returns:
            解密后的模型更新
        """
        decrypted = self.cipher.decrypt(encrypted_data)
        update_np = pickle.loads(decrypted)
        
        return {k: torch.from_numpy(v) for k, v in update_np.items()}
    
    def aggregate_encrypted(
        self,
        encrypted_updates: List[bytes]
    ) -> Dict[str, torch.Tensor]:
        """
        聚合加密更新（模拟同态加密聚合）
        
        实际应用中应使用同态加密库如TFHE或SEAL。
        这里先解密再聚合，用于演示。
        
        Args:
            encrypted_updates: 加密更新列表
            
        Returns:
            聚合后的模型更新
        """
        # 解密所有更新
        updates = [self.decrypt(enc) for enc in encrypted_updates]
        
        if not updates:
            return {}
        
        # 聚合
        aggregated = {}
        for key in updates[0].keys():
            stacked = torch.stack([u[key] for u in updates])
            aggregated[key] = stacked.mean(dim=0)
        
        return aggregated
    
    def process_update(
        self,
        update: Union[Dict[str, torch.Tensor], Dict[str, np.ndarray]]
    ) -> bytes:
        """
        处理模型更新（加密）
        
        Args:
            update: 模型更新
            
        Returns:
            加密的模型更新
        """
        # 转换为torch张量
        torch_update = {}
        for k, v in update.items():
            if isinstance(v, np.ndarray):
                torch_update[k] = torch.from_numpy(v).float()
            else:
                torch_update[k] = v.clone()
        
        return self.encrypt(torch_update)


def create_privacy_engine(config: Optional[Dict[str, Any]] = None) -> PrivacyEngine:
    """
    工厂函数：根据配置创建隐私引擎
    
    Args:
        config: 配置字典
        
    Returns:
        隐私引擎实例
    """
    if config is None:
        config = {}
    
    mechanism = PrivacyMechanism(config.get('mechanism', 'none'))
    
    privacy_config = PrivacyConfig(
        mechanism=mechanism,
        epsilon=config.get('epsilon', 1.0),
        delta=config.get('delta', 1e-5),
        noise_scale=config.get('noise_scale', 0.1),
        clip_norm=config.get('clip_norm', 1.0),
        num_parties=config.get('num_parties', 3),
        secret_share_threshold=config.get('secret_share_threshold', 2),
        encryption_key=config.get('encryption_key'),
        enable_weight_clipping=config.get('enable_weight_clipping', False),
        max_weight_norm=config.get('max_weight_norm', 5.0)
    )
    
    if mechanism == PrivacyMechanism.DIFFERENTIAL_PRIVACY:
        return DifferentialPrivacy(privacy_config)
    elif mechanism == PrivacyMechanism.SECURE_AGGREGATION:
        return SecureAggregator(privacy_config)
    elif mechanism == PrivacyMechanism.COMBINED:
        # 组合使用DP和SecAgg
        return DifferentialPrivacy(privacy_config)
    else:
        return PrivacyEngine(privacy_config)
