"""
硬件设备检测模块

负责检测和管理GPU/CPU计算设备，实现自动设备选择。

主要功能:
1. 检测CUDA GPU可用性
2. 自动选择最优计算设备
3. 设备内存管理
4. 设备信息查询

使用示例:
    from app.utils.device import get_device, DeviceInfo
    
    device = get_device()  # 自动选择GPU或CPU
    print(f"使用设备: {device}")
"""

import torch
from typing import Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from app.utils.config import config


@dataclass
class DeviceInfo:
    """
    设备信息数据类
    
    Attributes:
        device_type: 设备类型 (cuda/cpu)
        device_name: 设备名称
        total_memory: 总内存 (GB)
        available_memory: 可用内存 (GB)
        compute_capability: 计算能力 (GPU only)
    """
    device_type: str
    device_name: str
    total_memory: Optional[float] = None
    available_memory: Optional[float] = None
    compute_capability: Optional[Tuple[int, int]] = None


def check_cuda_available() -> bool:
    """
    检查CUDA是否可用
    
    Returns:
        bool: CUDA是否可用
    """
    return torch.cuda.is_available()


def get_gpu_count() -> int:
    """
    获取可用GPU数量
    
    Returns:
        int: GPU数量
    """
    return torch.cuda.device_count() if check_cuda_available() else 0


def get_gpu_info(device_id: int = 0) -> Optional[DeviceInfo]:
    """
    获取GPU设备信息
    
    Args:
        device_id: GPU设备ID，默认为0
        
    Returns:
        DeviceInfo: GPU设备信息，如果不可用返回None
    """
    if not check_cuda_available() or device_id >= get_gpu_count():
        return None
    
    props = torch.cuda.get_device_properties(device_id)
    total_memory = props.total_memory / (1024 ** 3)  # 转换为GB
    
    # 获取可用内存
    torch.cuda.set_device(device_id)
    available_memory = (props.total_memory - torch.cuda.memory_allocated(device_id)) / (1024 ** 3)
    
    return DeviceInfo(
        device_type='cuda',
        device_name=props.name,
        total_memory=round(total_memory, 2),
        available_memory=round(available_memory, 2),
        compute_capability=(props.major, props.minor)
    )


def get_cpu_info() -> DeviceInfo:
    """
    获取CPU设备信息
    
    Returns:
        DeviceInfo: CPU设备信息
    """
    import platform
    return DeviceInfo(
        device_type='cpu',
        device_name=platform.processor() or 'Unknown CPU'
    )


def get_device(prefer_gpu: Optional[bool] = None) -> torch.device:
    """
    获取最优计算设备
    
    自动检测GPU可用性，优先使用GPU。可通过配置或参数控制。
    
    Args:
        prefer_gpu: 是否优先使用GPU，None时使用配置值
        
    Returns:
        torch.device: 计算设备
    """
    if prefer_gpu is None:
        prefer_gpu = config.get('hardware.prefer_gpu', True)
    
    if prefer_gpu and check_cuda_available():
        device = torch.device('cuda:0')
        gpu_info = get_gpu_info(0)
        logger.info(f"使用GPU: {gpu_info.device_name}, 可用内存: {gpu_info.available_memory}GB")
    else:
        device = torch.device('cpu')
        cpu_info = get_cpu_info()
        logger.info(f"使用CPU: {cpu_info.device_name}")
    
    return device


def set_gpu_memory_fraction(fraction: float = 0.8) -> None:
    """
    设置GPU内存使用比例
    
    Args:
        fraction: 内存使用比例，0-1之间
    """
    if not check_cuda_available():
        return
    
    if fraction < 0 or fraction > 1:
        raise ValueError("内存比例必须在0-1之间")
    
    # PyTorch 2.0+ 使用环境变量控制
    import os
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = f'max_split_size_mb:{int(fraction * 1024)}'
    
    logger.info(f"GPU内存使用比例设置为: {fraction * 100}%")


def clear_gpu_cache() -> None:
    """
    清理GPU缓存
    """
    if check_cuda_available():
        torch.cuda.empty_cache()
        logger.debug("GPU缓存已清理")


def get_all_device_info() -> dict:
    """
    获取所有设备信息
    
    Returns:
        dict: 包含所有设备信息的字典
    """
    info = {
        'cpu': get_cpu_info().__dict__,
        'cuda_available': check_cuda_available(),
        'gpu_count': get_gpu_count(),
        'gpus': []
    }
    
    for i in range(get_gpu_count()):
        gpu_info = get_gpu_info(i)
        if gpu_info:
            info['gpus'].append(gpu_info.__dict__)
    
    return info
