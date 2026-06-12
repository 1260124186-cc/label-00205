"""
测试数据生成工具

生成各种场景的测试数据，便于测试和验证。

功能:
1. 正常数据生成
2. 异常数据生成（松动、过载、断裂）
3. 边界条件数据生成
4. 批量测试数据生成

使用示例:
    from tests.test_data_generator import TestDataGenerator
    
    generator = TestDataGenerator()
    normal_data = generator.generate_normal_bolt_data()
    fault_data = generator.generate_fault_data('loosening')
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import random
import json


@dataclass
class GeneratedData:
    """
    生成的测试数据
    
    Attributes:
        preload: 预紧力数据
        temperature: 温度数据
        timestamps: 时间戳
        labels: 标签
        scenario: 场景描述
    """
    preload: np.ndarray
    temperature: Optional[np.ndarray]
    timestamps: List[str]
    labels: Optional[np.ndarray]
    scenario: str
    expected_status: str


class TestDataGenerator:
    """
    测试数据生成器
    
    生成各种场景的模拟数据用于测试。
    """
    
    # 正常预紧力范围
    NORMAL_MIN = 400
    NORMAL_MAX = 800
    NORMAL_MEAN = 600
    NORMAL_STD = 20
    
    # 温度范围
    TEMP_MIN = -10
    TEMP_MAX = 60
    TEMP_MEAN = 25
    
    def __init__(self, seed: Optional[int] = None):
        """
        初始化数据生成器
        
        Args:
            seed: 随机种子
        """
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
    
    def generate_timestamps(
        self,
        n: int,
        start: Optional[datetime] = None,
        freq_minutes: int = 5
    ) -> List[str]:
        """
        生成时间戳序列
        
        Args:
            n: 数据点数量
            start: 起始时间
            freq_minutes: 采样频率（分钟）
            
        Returns:
            List[str]: 时间戳列表
        """
        if start is None:
            start = datetime.now() - timedelta(minutes=n * freq_minutes)
        
        timestamps = []
        for i in range(n):
            t = start + timedelta(minutes=i * freq_minutes)
            timestamps.append(t.strftime('%Y%m%d %H:%M:%S'))
        
        return timestamps
    
    def generate_normal_bolt_data(
        self,
        n: int = 100,
        include_temperature: bool = True,
        noise_level: float = 0.02
    ) -> GeneratedData:
        """
        生成正常螺栓数据
        
        Args:
            n: 数据点数量
            include_temperature: 是否包含温度
            noise_level: 噪声水平
            
        Returns:
            GeneratedData: 生成的数据
        """
        # 基础预紧力（带轻微波动）
        preload = np.random.normal(self.NORMAL_MEAN, self.NORMAL_STD, n)
        
        # 添加日周期波动
        t = np.linspace(0, 2 * np.pi, n)
        preload += 5 * np.sin(t)  # 日周期波动
        
        # 添加噪声
        preload += np.random.randn(n) * self.NORMAL_MEAN * noise_level
        
        # 温度
        temperature = None
        if include_temperature:
            temperature = np.random.normal(self.TEMP_MEAN, 5, n)
            # 日周期
            temperature += 10 * np.sin(t)
        
        return GeneratedData(
            preload=preload,
            temperature=temperature,
            timestamps=self.generate_timestamps(n),
            labels=np.zeros(n, dtype=int),  # 全部正常
            scenario="正常运行数据",
            expected_status="正常"
        )
    
    def generate_loosening_data(
        self,
        n: int = 100,
        decline_rate: float = 0.002
    ) -> GeneratedData:
        """
        生成松动场景数据
        
        特征：预紧力逐渐下降
        
        Args:
            n: 数据点数量
            decline_rate: 下降速率
            
        Returns:
            GeneratedData: 生成的数据
        """
        # 初始正常值
        initial = self.NORMAL_MEAN
        
        # 线性下降
        decline = np.linspace(0, -initial * decline_rate * n, n)
        preload = initial + decline
        
        # 添加噪声
        preload += np.random.randn(n) * self.NORMAL_STD * 0.5
        
        # 生成标签
        labels = np.zeros(n, dtype=int)
        # 后半段标记为异常
        labels[n // 2:] = 1  # 关注级
        labels[int(n * 0.75):] = 2  # 检查级
        
        return GeneratedData(
            preload=preload,
            temperature=np.random.normal(self.TEMP_MEAN, 5, n),
            timestamps=self.generate_timestamps(n),
            labels=labels,
            scenario="螺栓松动场景 - 预紧力持续下降",
            expected_status="关注级预警"
        )
    
    def generate_overload_data(
        self,
        n: int = 100,
        overload_ratio: float = 1.3
    ) -> GeneratedData:
        """
        生成过载场景数据
        
        特征：预紧力超过正常上限
        
        Args:
            n: 数据点数量
            overload_ratio: 过载比例
            
        Returns:
            GeneratedData: 生成的数据
        """
        # 前半段正常
        preload_normal = np.random.normal(self.NORMAL_MEAN, self.NORMAL_STD, n // 2)
        
        # 后半段过载
        overload_mean = self.NORMAL_MAX * overload_ratio
        preload_overload = np.random.normal(overload_mean, self.NORMAL_STD, n - n // 2)
        
        preload = np.concatenate([preload_normal, preload_overload])
        
        # 标签
        labels = np.zeros(n, dtype=int)
        labels[n // 2:] = 2  # 检查级
        
        return GeneratedData(
            preload=preload,
            temperature=np.random.normal(self.TEMP_MEAN, 5, n),
            timestamps=self.generate_timestamps(n),
            labels=labels,
            scenario="过载场景 - 预紧力超过正常上限",
            expected_status="检查级预警"
        )
    
    def generate_fracture_data(
        self,
        n: int = 100,
        fracture_point: float = 0.7
    ) -> GeneratedData:
        """
        生成断裂场景数据
        
        特征：预紧力急剧下降到极低值
        
        Args:
            n: 数据点数量
            fracture_point: 断裂发生点（比例）
            
        Returns:
            GeneratedData: 生成的数据
        """
        fracture_idx = int(n * fracture_point)
        
        # 断裂前正常
        preload_before = np.random.normal(self.NORMAL_MEAN, self.NORMAL_STD, fracture_idx)
        
        # 断裂后急剧下降
        preload_after = np.linspace(
            self.NORMAL_MEAN,
            self.NORMAL_MIN * 0.1,  # 降到正常最小值的10%
            n - fracture_idx
        )
        preload_after += np.random.randn(n - fracture_idx) * 10
        
        preload = np.concatenate([preload_before, preload_after])
        
        # 标签
        labels = np.zeros(n, dtype=int)
        labels[fracture_idx:] = 4  # 故障
        
        return GeneratedData(
            preload=preload,
            temperature=np.random.normal(self.TEMP_MEAN, 5, n),
            timestamps=self.generate_timestamps(n),
            labels=labels,
            scenario="断裂场景 - 预紧力急剧下降",
            expected_status="故障"
        )
    
    def generate_temperature_effect_data(
        self,
        n: int = 100,
        temp_coefficient: float = -0.5
    ) -> GeneratedData:
        """
        生成温度影响场景数据
        
        特征：预紧力与温度有明显相关性
        
        Args:
            n: 数据点数量
            temp_coefficient: 温度系数
            
        Returns:
            GeneratedData: 生成的数据
        """
        # 生成温度变化
        temperature = np.linspace(self.TEMP_MIN, self.TEMP_MAX, n)
        temperature += np.random.randn(n) * 3
        
        # 预紧力与温度相关
        preload = self.NORMAL_MEAN + temp_coefficient * (temperature - self.TEMP_MEAN)
        preload += np.random.randn(n) * self.NORMAL_STD * 0.5
        
        return GeneratedData(
            preload=preload,
            temperature=temperature,
            timestamps=self.generate_timestamps(n),
            labels=np.zeros(n, dtype=int),
            scenario="温度影响场景 - 预紧力与温度相关",
            expected_status="正常"
        )
    
    def generate_multi_bolt_data(
        self,
        n_bolts: int = 8,
        n_points: int = 100,
        correlation: float = 0.7
    ) -> List[GeneratedData]:
        """
        生成多螺栓（法兰面）数据
        
        Args:
            n_bolts: 螺栓数量
            n_points: 每个螺栓的数据点数
            correlation: 螺栓间相关性
            
        Returns:
            List[GeneratedData]: 各螺栓数据列表
        """
        # 生成基础信号（所有螺栓共享）
        base_signal = np.random.randn(n_points)
        
        bolt_data_list = []
        
        for i in range(n_bolts):
            # 共享部分 + 独立部分
            independent = np.random.randn(n_points)
            preload = self.NORMAL_MEAN + \
                      self.NORMAL_STD * (correlation * base_signal + 
                                         (1 - correlation) * independent)
            
            bolt_data_list.append(GeneratedData(
                preload=preload,
                temperature=np.random.normal(self.TEMP_MEAN, 5, n_points),
                timestamps=self.generate_timestamps(n_points),
                labels=np.zeros(n_points, dtype=int),
                scenario=f"法兰面螺栓{i+1}",
                expected_status="正常"
            ))
        
        return bolt_data_list
    
    def generate_boundary_data(self) -> Dict[str, GeneratedData]:
        """
        生成边界条件数据
        
        Returns:
            Dict[str, GeneratedData]: 各边界场景数据
        """
        return {
            'minimum_data': self._generate_minimum_data(),
            'maximum_length': self._generate_maximum_length_data(),
            'extreme_values': self._generate_extreme_values_data(),
            'all_same': self._generate_all_same_data(),
            'high_noise': self._generate_high_noise_data()
        }
    
    def _generate_minimum_data(self) -> GeneratedData:
        """最小数据量"""
        return GeneratedData(
            preload=np.array([self.NORMAL_MEAN]),
            temperature=np.array([self.TEMP_MEAN]),
            timestamps=self.generate_timestamps(1),
            labels=np.array([0]),
            scenario="最小数据量 - 单个数据点",
            expected_status="正常"
        )
    
    def _generate_maximum_length_data(self) -> GeneratedData:
        """最大数据量"""
        n = 10000
        return GeneratedData(
            preload=np.random.normal(self.NORMAL_MEAN, self.NORMAL_STD, n),
            temperature=np.random.normal(self.TEMP_MEAN, 5, n),
            timestamps=self.generate_timestamps(n, freq_minutes=1),
            labels=np.zeros(n, dtype=int),
            scenario="最大数据量 - 10000个数据点",
            expected_status="正常"
        )
    
    def _generate_extreme_values_data(self) -> GeneratedData:
        """极端值数据"""
        n = 100
        preload = np.random.normal(self.NORMAL_MEAN, self.NORMAL_STD, n)
        preload[10] = 0  # 极低
        preload[50] = 2000  # 极高
        preload[80] = -100  # 负值
        
        return GeneratedData(
            preload=preload,
            temperature=np.random.normal(self.TEMP_MEAN, 5, n),
            timestamps=self.generate_timestamps(n),
            labels=np.zeros(n, dtype=int),
            scenario="极端值数据 - 包含异常极值",
            expected_status="故障"
        )
    
    def _generate_all_same_data(self) -> GeneratedData:
        """全相同数据"""
        n = 100
        return GeneratedData(
            preload=np.full(n, self.NORMAL_MEAN),
            temperature=np.full(n, self.TEMP_MEAN),
            timestamps=self.generate_timestamps(n),
            labels=np.zeros(n, dtype=int),
            scenario="全相同数据 - 无波动",
            expected_status="正常"
        )
    
    def _generate_high_noise_data(self) -> GeneratedData:
        """高噪声数据"""
        n = 100
        return GeneratedData(
            preload=np.random.normal(self.NORMAL_MEAN, self.NORMAL_STD * 5, n),
            temperature=np.random.normal(self.TEMP_MEAN, 20, n),
            timestamps=self.generate_timestamps(n),
            labels=np.zeros(n, dtype=int),
            scenario="高噪声数据",
            expected_status="关注级预警"
        )
    
    def to_api_format(self, data: GeneratedData) -> List[List]:
        """
        转换为API请求格式
        
        Args:
            data: 生成的数据
            
        Returns:
            List: [[timestamp, preload], ...]
        """
        return [
            [ts, float(p)]
            for ts, p in zip(data.timestamps, data.preload)
        ]
    
    def to_csv(self, data: GeneratedData, filepath: str) -> None:
        """
        保存为CSV文件
        
        Args:
            data: 生成的数据
            filepath: 文件路径
        """
        df = pd.DataFrame({
            'timestamp': data.timestamps,
            'preload': data.preload
        })
        
        if data.temperature is not None:
            df['temperature'] = data.temperature
        
        if data.labels is not None:
            df['label'] = data.labels
        
        df.to_csv(filepath, index=False)
    
    def generate_test_suite(self) -> Dict[str, GeneratedData]:
        """
        生成完整测试套件
        
        Returns:
            Dict[str, GeneratedData]: 所有测试场景数据
        """
        suite = {
            'normal': self.generate_normal_bolt_data(),
            'loosening': self.generate_loosening_data(),
            'overload': self.generate_overload_data(),
            'fracture': self.generate_fracture_data(),
            'temperature_effect': self.generate_temperature_effect_data(),
        }
        
        # 添加边界条件
        suite.update(self.generate_boundary_data())
        
        return suite


if __name__ == '__main__':
    # 生成并保存测试数据
    generator = TestDataGenerator(seed=42)
    
    suite = generator.generate_test_suite()
    
    print("生成的测试场景:")
    for name, data in suite.items():
        print(f"  - {name}: {len(data.preload)}个数据点, 预期状态: {data.expected_status}")
