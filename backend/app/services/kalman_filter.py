"""
卡尔曼滤波服务模块

提供完整的卡尔曼滤波数据平滑处理功能：
1. 一维卡尔曼滤波
2. 扩展卡尔曼滤波
3. 自适应卡尔曼滤波
4. 批量数据处理

使用示例:
    from app.services.kalman_filter import KalmanFilterService
    
    service = KalmanFilterService()
    smoothed_data = service.smooth(raw_data)
"""

import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
from loguru import logger

from app.utils.config import config


@dataclass
class KalmanState:
    """
    卡尔曼滤波器状态
    
    Attributes:
        estimate: 状态估计值
        error_covariance: 估计误差协方差
        kalman_gain: 卡尔曼增益
        innovation: 新息（测量残差）
    """
    estimate: float
    error_covariance: float
    kalman_gain: float
    innovation: float


@dataclass
class KalmanFilterResult:
    """
    卡尔曼滤波结果
    
    Attributes:
        smoothed_data: 平滑后的数据
        estimates: 状态估计序列
        error_covariances: 误差协方差序列
        kalman_gains: 卡尔曼增益序列
        innovations: 新息序列
    """
    smoothed_data: np.ndarray
    estimates: np.ndarray
    error_covariances: np.ndarray
    kalman_gains: np.ndarray
    innovations: np.ndarray


class KalmanFilter1D:
    """
    一维卡尔曼滤波器
    
    用于单变量时间序列的平滑处理。
    
    状态方程: x_k = x_{k-1} + w_k
    观测方程: z_k = x_k + v_k
    
    其中:
        w_k ~ N(0, Q) 过程噪声
        v_k ~ N(0, R) 测量噪声
    
    Attributes:
        process_noise: 过程噪声协方差 Q
        measurement_noise: 测量噪声协方差 R
        estimate: 当前状态估计
        error_covariance: 当前估计误差协方差 P
    """
    
    def __init__(
        self,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1,
        initial_estimate: Optional[float] = None,
        initial_error_covariance: float = 1.0
    ):
        """
        初始化一维卡尔曼滤波器
        
        Args:
            process_noise: 过程噪声协方差 Q，控制模型对系统动态变化的信任
            measurement_noise: 测量噪声协方差 R，控制对测量值的信任
            initial_estimate: 初始状态估计
            initial_error_covariance: 初始误差协方差
        """
        self.Q = process_noise
        self.R = measurement_noise
        self.x = initial_estimate  # 状态估计
        self.P = initial_error_covariance  # 误差协方差
        
        self._initialized = initial_estimate is not None
        
    def reset(self, initial_estimate: Optional[float] = None) -> None:
        """
        重置滤波器状态
        
        Args:
            initial_estimate: 初始状态估计
        """
        self.x = initial_estimate
        self.P = 1.0
        self._initialized = initial_estimate is not None
        
    def predict(self) -> Tuple[float, float]:
        """
        预测步骤
        
        Returns:
            Tuple: (预测状态, 预测误差协方差)
        """
        # 状态预测: x_k|k-1 = x_k-1|k-1 (恒定模型)
        x_pred = self.x
        
        # 误差协方差预测: P_k|k-1 = P_k-1|k-1 + Q
        P_pred = self.P + self.Q
        
        return x_pred, P_pred
    
    def update(self, measurement: float) -> KalmanState:
        """
        更新步骤
        
        Args:
            measurement: 测量值
            
        Returns:
            KalmanState: 更新后的状态
        """
        if not self._initialized:
            # 使用第一个测量值初始化
            self.x = measurement
            self.P = 1.0
            self._initialized = True
            return KalmanState(
                estimate=self.x,
                error_covariance=self.P,
                kalman_gain=1.0,
                innovation=0.0
            )
        
        # 预测
        x_pred, P_pred = self.predict()
        
        # 计算卡尔曼增益: K = P_pred / (P_pred + R)
        K = P_pred / (P_pred + self.R)
        
        # 计算新息（测量残差）
        innovation = measurement - x_pred
        
        # 状态更新: x = x_pred + K * innovation
        self.x = x_pred + K * innovation
        
        # 误差协方差更新: P = (1 - K) * P_pred
        self.P = (1 - K) * P_pred
        
        return KalmanState(
            estimate=self.x,
            error_covariance=self.P,
            kalman_gain=K,
            innovation=innovation
        )
    
    def filter(self, measurements: np.ndarray) -> KalmanFilterResult:
        """
        对整个测量序列进行滤波
        
        Args:
            measurements: 测量值数组
            
        Returns:
            KalmanFilterResult: 滤波结果
        """
        n = len(measurements)
        
        estimates = np.zeros(n)
        error_covariances = np.zeros(n)
        kalman_gains = np.zeros(n)
        innovations = np.zeros(n)
        
        # 重置滤波器
        self.reset()
        
        for i, z in enumerate(measurements):
            state = self.update(z)
            estimates[i] = state.estimate
            error_covariances[i] = state.error_covariance
            kalman_gains[i] = state.kalman_gain
            innovations[i] = state.innovation
        
        return KalmanFilterResult(
            smoothed_data=estimates,
            estimates=estimates,
            error_covariances=error_covariances,
            kalman_gains=kalman_gains,
            innovations=innovations
        )


class AdaptiveKalmanFilter:
    """
    自适应卡尔曼滤波器
    
    根据新息自适应调整过程噪声和测量噪声。
    
    Attributes:
        base_Q: 基础过程噪声
        base_R: 基础测量噪声
        adaptation_rate: 自适应率
        innovation_window: 新息窗口大小
    """
    
    def __init__(
        self,
        base_process_noise: float = 0.01,
        base_measurement_noise: float = 0.1,
        adaptation_rate: float = 0.1,
        innovation_window: int = 10
    ):
        """
        初始化自适应卡尔曼滤波器
        
        Args:
            base_process_noise: 基础过程噪声
            base_measurement_noise: 基础测量噪声
            adaptation_rate: 自适应率 (0-1)
            innovation_window: 新息窗口大小
        """
        self.base_Q = base_process_noise
        self.base_R = base_measurement_noise
        self.alpha = adaptation_rate
        self.window_size = innovation_window
        
        self.Q = base_process_noise
        self.R = base_measurement_noise
        self.x = None
        self.P = 1.0
        
        self._innovations: List[float] = []
        self._initialized = False
        
    def reset(self) -> None:
        """重置滤波器"""
        self.x = None
        self.P = 1.0
        self.Q = self.base_Q
        self.R = self.base_R
        self._innovations = []
        self._initialized = False
        
    def _adapt_noise(self) -> None:
        """
        根据新息序列自适应调整噪声参数
        """
        if len(self._innovations) < self.window_size:
            return
        
        # 计算新息的方差
        recent_innovations = self._innovations[-self.window_size:]
        innovation_var = np.var(recent_innovations)
        
        # 理论上，新息方差应该等于 P_pred + R
        expected_var = self.P + self.R
        
        # 根据新息方差调整 R
        if innovation_var > expected_var * 1.5:
            # 新息方差过大，增加 R
            self.R = self.R + self.alpha * (innovation_var - expected_var)
        elif innovation_var < expected_var * 0.5:
            # 新息方差过小，减少 R
            self.R = max(self.base_R * 0.1, self.R - self.alpha * (expected_var - innovation_var))
            
    def update(self, measurement: float) -> KalmanState:
        """
        更新步骤（带自适应）
        
        Args:
            measurement: 测量值
            
        Returns:
            KalmanState: 更新后的状态
        """
        if not self._initialized:
            self.x = measurement
            self.P = 1.0
            self._initialized = True
            return KalmanState(
                estimate=self.x,
                error_covariance=self.P,
                kalman_gain=1.0,
                innovation=0.0
            )
        
        # 预测
        x_pred = self.x
        P_pred = self.P + self.Q
        
        # 计算卡尔曼增益
        K = P_pred / (P_pred + self.R)
        
        # 计算新息
        innovation = measurement - x_pred
        self._innovations.append(innovation)
        
        # 自适应调整噪声
        self._adapt_noise()
        
        # 状态更新
        self.x = x_pred + K * innovation
        self.P = (1 - K) * P_pred
        
        return KalmanState(
            estimate=self.x,
            error_covariance=self.P,
            kalman_gain=K,
            innovation=innovation
        )
    
    def filter(self, measurements: np.ndarray) -> KalmanFilterResult:
        """
        对整个测量序列进行自适应滤波
        
        Args:
            measurements: 测量值数组
            
        Returns:
            KalmanFilterResult: 滤波结果
        """
        n = len(measurements)
        
        estimates = np.zeros(n)
        error_covariances = np.zeros(n)
        kalman_gains = np.zeros(n)
        innovations = np.zeros(n)
        
        self.reset()
        
        for i, z in enumerate(measurements):
            state = self.update(z)
            estimates[i] = state.estimate
            error_covariances[i] = state.error_covariance
            kalman_gains[i] = state.kalman_gain
            innovations[i] = state.innovation
        
        return KalmanFilterResult(
            smoothed_data=estimates,
            estimates=estimates,
            error_covariances=error_covariances,
            kalman_gains=kalman_gains,
            innovations=innovations
        )


class RauchTungStriebelSmoother:
    """
    Rauch-Tung-Striebel 平滑器
    
    双向卡尔曼滤波，提供更平滑的估计结果。
    先前向滤波，再后向平滑。
    """
    
    def __init__(
        self,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1
    ):
        """
        初始化RTS平滑器
        
        Args:
            process_noise: 过程噪声
            measurement_noise: 测量噪声
        """
        self.Q = process_noise
        self.R = measurement_noise
        
    def smooth(self, measurements: np.ndarray) -> np.ndarray:
        """
        双向平滑
        
        Args:
            measurements: 测量值数组
            
        Returns:
            np.ndarray: 平滑后的数据
        """
        n = len(measurements)
        
        if n == 0:
            return measurements
        
        # 前向滤波
        x_forward = np.zeros(n)
        P_forward = np.zeros(n)
        
        x = measurements[0]
        P = 1.0
        
        for i in range(n):
            # 预测
            x_pred = x
            P_pred = P + self.Q
            
            # 更新
            K = P_pred / (P_pred + self.R)
            x = x_pred + K * (measurements[i] - x_pred)
            P = (1 - K) * P_pred
            
            x_forward[i] = x
            P_forward[i] = P
        
        # 后向平滑
        x_smooth = np.zeros(n)
        x_smooth[-1] = x_forward[-1]
        
        for i in range(n - 2, -1, -1):
            # 预测的状态和协方差
            P_pred = P_forward[i] + self.Q
            
            # 平滑增益
            J = P_forward[i] / P_pred
            
            # 平滑状态
            x_smooth[i] = x_forward[i] + J * (x_smooth[i + 1] - x_forward[i])
        
        return x_smooth


class KalmanFilterService:
    """
    卡尔曼滤波服务
    
    提供统一的卡尔曼滤波接口。
    
    Attributes:
        standard_filter: 标准卡尔曼滤波器
        adaptive_filter: 自适应卡尔曼滤波器
        rts_smoother: RTS平滑器
    """
    
    def __init__(self):
        """
        初始化卡尔曼滤波服务
        """
        kalman_config = config.get('preprocessing.kalman_filter', {})
        
        process_noise = kalman_config.get('process_noise', 0.01)
        measurement_noise = kalman_config.get('measurement_noise', 0.1)
        
        self.standard_filter = KalmanFilter1D(
            process_noise=process_noise,
            measurement_noise=measurement_noise
        )
        
        self.adaptive_filter = AdaptiveKalmanFilter(
            base_process_noise=process_noise,
            base_measurement_noise=measurement_noise
        )
        
        self.rts_smoother = RauchTungStriebelSmoother(
            process_noise=process_noise,
            measurement_noise=measurement_noise
        )
        
        logger.info("卡尔曼滤波服务初始化完成")
    
    def smooth(
        self,
        data: np.ndarray,
        method: str = 'standard'
    ) -> np.ndarray:
        """
        数据平滑
        
        Args:
            data: 原始数据
            method: 平滑方法
                - 'standard': 标准卡尔曼滤波
                - 'adaptive': 自适应卡尔曼滤波
                - 'rts': RTS双向平滑
                
        Returns:
            np.ndarray: 平滑后的数据
        """
        if len(data) == 0:
            return data
        
        if method == 'standard':
            result = self.standard_filter.filter(data)
            return result.smoothed_data
        elif method == 'adaptive':
            result = self.adaptive_filter.filter(data)
            return result.smoothed_data
        elif method == 'rts':
            return self.rts_smoother.smooth(data)
        else:
            logger.warning(f"未知的平滑方法: {method}，使用标准方法")
            result = self.standard_filter.filter(data)
            return result.smoothed_data
    
    def smooth_with_details(
        self,
        data: np.ndarray,
        method: str = 'standard'
    ) -> KalmanFilterResult:
        """
        数据平滑（带详细信息）
        
        Args:
            data: 原始数据
            method: 平滑方法
            
        Returns:
            KalmanFilterResult: 详细滤波结果
        """
        if method == 'standard':
            return self.standard_filter.filter(data)
        elif method == 'adaptive':
            return self.adaptive_filter.filter(data)
        else:
            return self.standard_filter.filter(data)
