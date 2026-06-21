"""
卡尔曼滤波服务模块（高级模式）

提供完整的卡尔曼滤波数据平滑处理功能：
1. Simple (标准一维卡尔曼滤波)
2. Adaptive (自适应卡尔曼滤波 - 根据新息动态调整 measurement_noise)
3. Extended (扩展卡尔曼滤波 - 支持线性漂移等非线性状态转移)
4. 批量数据处理 + 流式增量处理
5. Per-sensor 参数覆盖
6. 诊断信息输出（增益序列、新息、估计误差协方差）

使用示例:
    from app.services.kalman_filter import KalmanFilterFactory, KalmanDiagnostics

    factory = KalmanFilterFactory()
    kf = factory.create_filter(sensor_id="BOLT-001")
    result = kf.filter_with_diagnostics(data)
    diagnostics = result.diagnostics
"""

import numpy as np
from typing import Optional, Tuple, List, Dict, Any, Callable
from dataclasses import dataclass, field
from collections import deque
from abc import ABC, abstractmethod
from loguru import logger

from app.utils.config import config


@dataclass
class KalmanDiagnostics:
    """
    卡尔曼滤波诊断信息

    供可解释性报告引用，包含滤波过程的完整内部状态序列。

    Attributes:
        kalman_gains: 卡尔曼增益序列 K_k
        innovations: 新息（测量残差）序列 ν_k = z_k - x̂_k|k-1
        error_covariances: 估计误差协方差序列 P_k|k
        predicted_covariances: 预测误差协方差序列 P_k|k-1
        measurement_noise: 测量噪声 R 序列（自适应模式会变化）
        process_noise: 过程噪声 Q 序列
        mode: 滤波模式 simple/adaptive/extended
        sensor_id: 关联的传感器ID
    """
    kalman_gains: List[float] = field(default_factory=list)
    innovations: List[float] = field(default_factory=list)
    error_covariances: List[float] = field(default_factory=list)
    predicted_covariances: List[float] = field(default_factory=list)
    measurement_noise: List[float] = field(default_factory=list)
    process_noise: List[float] = field(default_factory=list)
    mode: str = "simple"
    sensor_id: Optional[str] = None

    def append(
        self,
        gain: float,
        innovation: float,
        error_cov: float,
        pred_cov: float,
        r: float,
        q: float,
    ) -> None:
        """追加一条诊断记录"""
        self.kalman_gains.append(float(gain))
        self.innovations.append(float(innovation))
        self.error_covariances.append(float(error_cov))
        self.predicted_covariances.append(float(pred_cov))
        self.measurement_noise.append(float(r))
        self.process_noise.append(float(q))

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化字典"""
        return {
            "mode": self.mode,
            "sensor_id": self.sensor_id,
            "kalman_gains": self.kalman_gains,
            "innovations": self.innovations,
            "error_covariances": self.error_covariances,
            "predicted_covariances": self.predicted_covariances,
            "measurement_noise": self.measurement_noise,
            "process_noise": self.process_noise,
            "innovation_std": float(np.std(self.innovations)) if self.innovations else 0.0,
            "mean_gain": float(np.mean(self.kalman_gains)) if self.kalman_gains else 0.0,
            "final_error_covariance": self.error_covariances[-1] if self.error_covariances else 0.0,
        }

    def summary(self) -> Dict[str, float]:
        """返回数值摘要（用于报告）"""
        d = self.to_dict()
        return {k: v for k, v in d.items() if isinstance(v, (int, float))}


@dataclass
class KalmanState:
    """
    卡尔曼滤波器单步状态

    Attributes:
        estimate: 状态估计值 x̂_k|k
        error_covariance: 估计误差协方差 P_k|k
        kalman_gain: 卡尔曼增益 K_k
        innovation: 新息（测量残差）ν_k
        predicted_state: 预测状态 x̂_k|k-1
        predicted_covariance: 预测误差协方差 P_k|k-1
    """
    estimate: float
    error_covariance: float
    kalman_gain: float
    innovation: float
    predicted_state: float
    predicted_covariance: float


@dataclass
class KalmanFilterResult:
    """
    卡尔曼滤波结果（批量）

    Attributes:
        smoothed_data: 平滑后的数据
        estimates: 状态估计序列
        error_covariances: 误差协方差序列
        kalman_gains: 卡尔曼增益序列
        innovations: 新息序列
        diagnostics: 完整诊断信息（可选）
    """
    smoothed_data: np.ndarray
    estimates: np.ndarray
    error_covariances: np.ndarray
    kalman_gains: np.ndarray
    innovations: np.ndarray
    diagnostics: Optional[KalmanDiagnostics] = None


@dataclass
class KalmanStreamingState:
    """
    流式增量卡尔曼的持久化状态

    与 SlidingWindowManager 配合，可序列化后与窗口数据一并存储。
    """
    estimate: float
    error_covariance: float
    process_noise: float
    measurement_noise: float
    mode: str
    innovations_history: List[float] = field(default_factory=list)
    initialized: bool = False
    sensor_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "estimate": self.estimate,
            "error_covariance": self.error_covariance,
            "process_noise": self.process_noise,
            "measurement_noise": self.measurement_noise,
            "mode": self.mode,
            "innovations_history": self.innovations_history,
            "initialized": self.initialized,
            "sensor_id": self.sensor_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KalmanStreamingState":
        return cls(
            estimate=float(data.get("estimate", 0.0)),
            error_covariance=float(data.get("error_covariance", 1.0)),
            process_noise=float(data.get("process_noise", 0.01)),
            measurement_noise=float(data.get("measurement_noise", 0.1)),
            mode=str(data.get("mode", "simple")),
            innovations_history=list(data.get("innovations_history", [])),
            initialized=bool(data.get("initialized", False)),
            sensor_id=data.get("sensor_id"),
        )


# ====================================================================
# 滤波器基类与具体实现
# ====================================================================

class BaseKalmanFilter(ABC):
    """
    卡尔曼滤波器抽象基类
    """

    mode: str = "simple"

    def __init__(
        self,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1,
        initial_estimate: Optional[float] = None,
        initial_error_covariance: float = 1.0,
        sensor_id: Optional[str] = None,
    ):
        self.Q = process_noise
        self.base_Q = process_noise
        self.R = measurement_noise
        self.base_R = measurement_noise
        self.x = initial_estimate
        self.P = initial_error_covariance
        self.initial_P = initial_error_covariance
        self.sensor_id = sensor_id
        self._initialized = initial_estimate is not None
        self._diagnostics: Optional[KalmanDiagnostics] = None

    def enable_diagnostics(self) -> None:
        """开启诊断信息收集"""
        self._diagnostics = KalmanDiagnostics(mode=self.mode, sensor_id=self.sensor_id)

    def disable_diagnostics(self) -> None:
        """关闭诊断信息收集"""
        self._diagnostics = None

    def get_diagnostics(self) -> Optional[KalmanDiagnostics]:
        return self._diagnostics

    def reset(self, initial_estimate: Optional[float] = None) -> None:
        """重置滤波器状态"""
        self.x = initial_estimate
        self.P = self.initial_P
        self.Q = self.base_Q
        self.R = self.base_R
        self._initialized = initial_estimate is not None
        if self._diagnostics is not None:
            self._diagnostics = KalmanDiagnostics(mode=self.mode, sensor_id=self.sensor_id)

    def _record_diagnostics(
        self,
        gain: float,
        innovation: float,
        error_cov: float,
        pred_cov: float,
    ) -> None:
        if self._diagnostics is not None:
            self._diagnostics.append(gain, innovation, error_cov, pred_cov, self.R, self.Q)

    @abstractmethod
    def predict(self) -> Tuple[float, float]:
        """预测步骤: 返回 (x_pred, P_pred)"""
        ...

    @abstractmethod
    def update(self, measurement: float) -> KalmanState:
        """更新步骤"""
        ...

    def filter(
        self,
        measurements: np.ndarray,
        collect_diagnostics: bool = False,
    ) -> KalmanFilterResult:
        """
        对整个测量序列进行滤波

        Args:
            measurements: 测量值数组
            collect_diagnostics: 是否收集诊断信息

        Returns:
            KalmanFilterResult
        """
        n = len(measurements)
        estimates = np.zeros(n)
        error_covariances = np.zeros(n)
        kalman_gains = np.zeros(n)
        innovations = np.zeros(n)

        prev_diag = self._diagnostics
        if collect_diagnostics:
            self.enable_diagnostics()

        self.reset()

        for i, z in enumerate(measurements):
            state = self.update(float(z))
            estimates[i] = state.estimate
            error_covariances[i] = state.error_covariance
            kalman_gains[i] = state.kalman_gain
            innovations[i] = state.innovation

        diag = self._diagnostics if collect_diagnostics else None
        self._diagnostics = prev_diag

        return KalmanFilterResult(
            smoothed_data=estimates,
            estimates=estimates,
            error_covariances=error_covariances,
            kalman_gains=kalman_gains,
            innovations=innovations,
            diagnostics=diag,
        )

    def filter_with_diagnostics(self, measurements: np.ndarray) -> KalmanFilterResult:
        """便捷方法：滤波并收集诊断信息"""
        return self.filter(measurements, collect_diagnostics=True)

    # ---------- 流式增量接口 ----------

    def save_state(self) -> KalmanStreamingState:
        """保存当前流式状态（用于窗口持久化）"""
        return KalmanStreamingState(
            estimate=float(self.x) if self.x is not None else 0.0,
            error_covariance=float(self.P),
            process_noise=float(self.Q),
            measurement_noise=float(self.R),
            mode=self.mode,
            innovations_history=list(self._get_innovation_history()),
            initialized=bool(self._initialized),
            sensor_id=self.sensor_id,
        )

    def load_state(self, state: KalmanStreamingState) -> None:
        """从持久化状态恢复（流式场景）"""
        self.x = state.estimate if state.initialized else None
        self.P = state.error_covariance
        self.Q = state.process_noise
        self.R = state.measurement_noise
        self._initialized = state.initialized
        self._set_innovation_history(state.innovations_history)
        if self._diagnostics is not None:
            self._diagnostics.mode = state.mode
            self._diagnostics.sensor_id = state.sensor_id

    def _get_innovation_history(self) -> List[float]:
        """子类可覆写：返回新息历史（用于持久化自适应状态）"""
        return []

    def _set_innovation_history(self, history: List[float]) -> None:
        """子类可覆写：恢复新息历史"""
        pass


class SimpleKalmanFilter(BaseKalmanFilter):
    """
    标准一维卡尔曼滤波器（Simple 模式）

    状态方程: x_k = x_{k-1} + w_k  (恒定模型)
    观测方程: z_k = x_k + v_k
    """

    mode = "simple"

    def predict(self) -> Tuple[float, float]:
        if not self._initialized:
            return 0.0, self.initial_P
        x_pred = self.x
        P_pred = self.P + self.Q
        return x_pred, P_pred

    def update(self, measurement: float) -> KalmanState:
        if not self._initialized:
            self.x = measurement
            self.P = self.initial_P
            self._initialized = True
            state = KalmanState(
                estimate=self.x,
                error_covariance=self.P,
                kalman_gain=1.0,
                innovation=0.0,
                predicted_state=measurement,
                predicted_covariance=self.initial_P,
            )
            self._record_diagnostics(1.0, 0.0, self.P, self.initial_P)
            return state

        x_pred, P_pred = self.predict()
        K = P_pred / (P_pred + self.R)
        innovation = measurement - x_pred
        self.x = x_pred + K * innovation
        self.P = (1 - K) * P_pred

        self._record_diagnostics(K, innovation, self.P, P_pred)

        return KalmanState(
            estimate=self.x,
            error_covariance=self.P,
            kalman_gain=K,
            innovation=innovation,
            predicted_state=x_pred,
            predicted_covariance=P_pred,
        )


class AdaptiveKalmanFilter(BaseKalmanFilter):
    """
    自适应卡尔曼滤波器（Adaptive 模式）

    根据新息（innovation）序列的统计特性动态调整 measurement_noise R：
    - 新息方差显著高于预期 → 增大 R（信任模型更多）
    - 新息方差显著低于预期 → 减小 R（信任测量更多）
    """

    mode = "adaptive"

    def __init__(
        self,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1,
        adaptation_rate: float = 0.1,
        innovation_window: int = 10,
        upper_threshold: float = 1.5,
        lower_threshold: float = 0.5,
        min_measurement_noise_ratio: float = 0.1,
        initial_estimate: Optional[float] = None,
        initial_error_covariance: float = 1.0,
        sensor_id: Optional[str] = None,
    ):
        super().__init__(
            process_noise=process_noise,
            measurement_noise=measurement_noise,
            initial_estimate=initial_estimate,
            initial_error_covariance=initial_error_covariance,
            sensor_id=sensor_id,
        )
        self.alpha = adaptation_rate
        self.window_size = innovation_window
        self.upper_threshold = upper_threshold
        self.lower_threshold = lower_threshold
        self.min_R_ratio = min_measurement_noise_ratio
        self._innovations: deque = deque(maxlen=innovation_window)

    def reset(self, initial_estimate: Optional[float] = None) -> None:
        super().reset(initial_estimate)
        self._innovations.clear()

    def _get_innovation_history(self) -> List[float]:
        return list(self._innovations)

    def _set_innovation_history(self, history: List[float]) -> None:
        self._innovations.clear()
        for v in history[-self.window_size:]:
            self._innovations.append(float(v))

    def _adapt_noise(self, P_pred: float) -> None:
        if len(self._innovations) < self.window_size:
            return

        innovation_var = float(np.var(list(self._innovations)))
        expected_var = P_pred + self.R

        if innovation_var > expected_var * self.upper_threshold:
            delta = self.alpha * (innovation_var - expected_var)
            self.R = self.R + delta
        elif innovation_var < expected_var * self.lower_threshold:
            delta = self.alpha * (expected_var - innovation_var)
            min_R = self.base_R * self.min_R_ratio
            self.R = max(min_R, self.R - delta)

    def predict(self) -> Tuple[float, float]:
        if not self._initialized:
            return 0.0, self.initial_P
        return self.x, self.P + self.Q

    def update(self, measurement: float) -> KalmanState:
        if not self._initialized:
            self.x = measurement
            self.P = self.initial_P
            self._initialized = True
            self._record_diagnostics(1.0, 0.0, self.P, self.initial_P)
            return KalmanState(
                estimate=self.x,
                error_covariance=self.P,
                kalman_gain=1.0,
                innovation=0.0,
                predicted_state=measurement,
                predicted_covariance=self.initial_P,
            )

        x_pred, P_pred = self.predict()
        K = P_pred / (P_pred + self.R)
        innovation = measurement - x_pred

        self._innovations.append(innovation)
        self._adapt_noise(P_pred)
        K = P_pred / (P_pred + self.R)

        self.x = x_pred + K * innovation
        self.P = (1 - K) * P_pred

        self._record_diagnostics(K, innovation, self.P, P_pred)

        return KalmanState(
            estimate=self.x,
            error_covariance=self.P,
            kalman_gain=K,
            innovation=innovation,
            predicted_state=x_pred,
            predicted_covariance=P_pred,
        )


class ExtendedKalmanFilter(BaseKalmanFilter):
    """
    扩展卡尔曼滤波器（Extended 模式）

    支持非恒定状态转移函数：
    - constant:   x_k = x_{k-1} + w_k              (等同于 Simple)
    - linear_drift: x_k = x_{k-1} + drift_rate + w_k (带线性漂移的随机游走)
    - custom:     由调用方提供 state_transition_fn

    观测函数目前为线性 h(x)=x（可按需扩展为非线性）。
    """

    mode = "extended"

    def __init__(
        self,
        process_noise: float = 0.01,
        measurement_noise: float = 0.1,
        state_transition: str = "constant",
        drift_rate: float = 0.0,
        state_transition_fn: Optional[Callable[[float], Tuple[float, float]]] = None,
        initial_estimate: Optional[float] = None,
        initial_error_covariance: float = 1.0,
        sensor_id: Optional[str] = None,
    ):
        super().__init__(
            process_noise=process_noise,
            measurement_noise=measurement_noise,
            initial_estimate=initial_estimate,
            initial_error_covariance=initial_error_covariance,
            sensor_id=sensor_id,
        )
        self.state_transition = state_transition
        self.drift_rate = drift_rate
        self.custom_transition_fn = state_transition_fn

    def _state_transition(self, x_prev: float) -> Tuple[float, float]:
        """
        状态转移函数

        Returns:
            (x_pred, F_Jacobian)  - 预测状态和状态转移雅可比
        """
        if self.custom_transition_fn is not None:
            return self.custom_transition_fn(x_prev)

        if self.state_transition == "linear_drift":
            return x_prev + self.drift_rate, 1.0
        else:  # constant
            return x_prev, 1.0

    def predict(self) -> Tuple[float, float]:
        if not self._initialized:
            return 0.0, self.initial_P
        x_pred, F = self._state_transition(self.x)
        P_pred = F * self.P * F + self.Q
        return x_pred, P_pred

    def update(self, measurement: float) -> KalmanState:
        if not self._initialized:
            self.x = measurement
            self.P = self.initial_P
            self._initialized = True
            self._record_diagnostics(1.0, 0.0, self.P, self.initial_P)
            return KalmanState(
                estimate=self.x,
                error_covariance=self.P,
                kalman_gain=1.0,
                innovation=0.0,
                predicted_state=measurement,
                predicted_covariance=self.initial_P,
            )

        x_pred, P_pred = self.predict()

        # 观测函数 h(x) = x，雅可比 H = 1
        H = 1.0
        innovation = measurement - x_pred  # h(x_pred) = x_pred
        S = H * P_pred * H + self.R       # 新息协方差
        K = P_pred * H / S                 # 卡尔曼增益

        self.x = x_pred + K * innovation
        self.P = (1 - K * H) * P_pred

        self._record_diagnostics(K, innovation, self.P, P_pred)

        return KalmanState(
            estimate=self.x,
            error_covariance=self.P,
            kalman_gain=K,
            innovation=innovation,
            predicted_state=x_pred,
            predicted_covariance=P_pred,
        )


# ====================================================================
# Rauch-Tung-Striebel 双向平滑器（保留兼容）
# ====================================================================

class RauchTungStriebelSmoother:
    """
    Rauch-Tung-Striebel 平滑器（双向卡尔曼滤波）
    """

    def __init__(self, process_noise: float = 0.01, measurement_noise: float = 0.1):
        self.Q = process_noise
        self.R = measurement_noise

    def smooth(self, measurements: np.ndarray) -> np.ndarray:
        n = len(measurements)
        if n == 0:
            return measurements

        x_forward = np.zeros(n)
        P_forward = np.zeros(n)

        x = measurements[0]
        P = 1.0

        for i in range(n):
            x_pred = x
            P_pred = P + self.Q
            K = P_pred / (P_pred + self.R)
            x = x_pred + K * (measurements[i] - x_pred)
            P = (1 - K) * P_pred
            x_forward[i] = x
            P_forward[i] = P

        x_smooth = np.zeros(n)
        x_smooth[-1] = x_forward[-1]

        for i in range(n - 2, -1, -1):
            P_pred = P_forward[i] + self.Q
            J = P_forward[i] / P_pred
            x_smooth[i] = x_forward[i] + J * (x_smooth[i + 1] - x_forward[i])

        return x_smooth


# ====================================================================
# 滤波器工厂：按 mode + sensor_id 创建滤波器实例
# ====================================================================

class KalmanFilterFactory:
    """
    卡尔曼滤波器工厂

    负责:
    1. 读取配置 preprocessing.kalman.*
    2. 合并 per-sensor 覆盖参数
    3. 根据 mode 选择 simple/adaptive/extended 实现
    4. 兼容旧版 preprocessing.kalman_filter 配置
    """

    VALID_MODES = {"simple", "adaptive", "extended"}

    def __init__(self):
        self._load_config()

    def _load_config(self) -> None:
        kalman_cfg = config.get("preprocessing.kalman", {})
        legacy_cfg = config.get("preprocessing.kalman_filter", {})

        self.default_mode = str(kalman_cfg.get("mode", "simple")).lower()
        if self.default_mode not in self.VALID_MODES:
            logger.warning(f"无效的 kalman.mode={self.default_mode}，回退为 simple")
            self.default_mode = "simple"

        self.enable_diagnostics = bool(kalman_cfg.get("enable_diagnostics", True))

        base = kalman_cfg.get("base", {})
        self.default_Q = float(base.get("process_noise", legacy_cfg.get("process_noise", 0.01)))
        self.default_R = float(base.get("measurement_noise", legacy_cfg.get("measurement_noise", 0.1)))
        self.default_P0 = float(base.get("initial_error_covariance", 1.0))

        self.adaptive_cfg = kalman_cfg.get("adaptive", {})
        self.extended_cfg = kalman_cfg.get("extended", {})
        self.sensor_overrides: Dict[str, Dict[str, Any]] = kalman_cfg.get("sensor_overrides", {}) or {}

        streaming = kalman_cfg.get("streaming", {})
        self.streaming_enabled = bool(streaming.get("enabled", True))
        self.streaming_state_ttl = int(streaming.get("state_ttl_seconds", 3600))

    def reload_config(self) -> None:
        """热重载配置"""
        self._load_config()
        logger.info("KalmanFilterFactory 配置已重新加载")

    def _resolve_sensor_config(self, sensor_id: Optional[str]) -> Dict[str, Any]:
        """
        根据 sensor_id 合并最终配置（全局默认 + per-sensor 覆盖）
        """
        cfg: Dict[str, Any] = {
            "mode": self.default_mode,
            "process_noise": self.default_Q,
            "measurement_noise": self.default_R,
            "initial_error_covariance": self.default_P0,
            "adaptive": dict(self.adaptive_cfg),
            "extended": dict(self.extended_cfg),
        }

        if sensor_id and sensor_id in self.sensor_overrides:
            override = self.sensor_overrides[sensor_id] or {}
            for k, v in override.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
            mode_val = str(cfg.get("mode", self.default_mode)).lower()
            if mode_val in self.VALID_MODES:
                cfg["mode"] = mode_val
            else:
                logger.warning(
                    f"sensor={sensor_id} 覆盖了无效 mode={mode_val}，使用默认 {self.default_mode}"
                )
                cfg["mode"] = self.default_mode

        return cfg

    def create_filter(
        self,
        sensor_id: Optional[str] = None,
        mode: Optional[str] = None,
        collect_diagnostics: Optional[bool] = None,
    ) -> BaseKalmanFilter:
        """
        创建卡尔曼滤波器实例

        Args:
            sensor_id: 传感器ID，用于查找 per-sensor 覆盖
            mode: 强制指定模式（优先于配置与覆盖）
            collect_diagnostics: 是否开启诊断，None 则使用配置值
        """
        cfg = self._resolve_sensor_config(sensor_id)
        final_mode = (mode or cfg["mode"]).lower()
        if final_mode not in self.VALID_MODES:
            final_mode = self.default_mode

        Q = float(cfg["process_noise"])
        R = float(cfg["measurement_noise"])
        P0 = float(cfg["initial_error_covariance"])

        if final_mode == "adaptive":
            adapt = cfg.get("adaptive", {}) or {}
            kf: BaseKalmanFilter = AdaptiveKalmanFilter(
                process_noise=Q,
                measurement_noise=R,
                adaptation_rate=float(adapt.get("adaptation_rate", 0.1)),
                innovation_window=int(adapt.get("innovation_window", 10)),
                upper_threshold=float(adapt.get("upper_threshold", 1.5)),
                lower_threshold=float(adapt.get("lower_threshold", 0.5)),
                min_measurement_noise_ratio=float(adapt.get("min_measurement_noise_ratio", 0.1)),
                initial_error_covariance=P0,
                sensor_id=sensor_id,
            )
        elif final_mode == "extended":
            ext = cfg.get("extended", {}) or {}
            kf = ExtendedKalmanFilter(
                process_noise=Q,
                measurement_noise=R,
                state_transition=str(ext.get("state_transition", "constant")),
                drift_rate=float(ext.get("drift_rate", 0.0)),
                initial_error_covariance=P0,
                sensor_id=sensor_id,
            )
        else:  # simple
            kf = SimpleKalmanFilter(
                process_noise=Q,
                measurement_noise=R,
                initial_error_covariance=P0,
                sensor_id=sensor_id,
            )

        diag = collect_diagnostics if collect_diagnostics is not None else self.enable_diagnostics
        if diag:
            kf.enable_diagnostics()

        return kf


# ====================================================================
# 流式增量卡尔曼管理器：与 SlidingWindowManager 配合
# ====================================================================

class StreamingKalmanManager:
    """
    流式增量卡尔曼管理器

    与 SlidingWindowManager 配合使用：
    - 每个 sensor/bolt 维护独立的滤波器状态
    - 每条新增数据仅做一次 update（不从头 filter）
    - 状态可序列化，支持 Redis 持久化
    - 窗口滑动时自动裁剪诊断序列
    """

    def __init__(
        self,
        factory: Optional[KalmanFilterFactory] = None,
        max_diagnostics_history: int = 1000,
    ):
        self.factory = factory or KalmanFilterFactory()
        self._filters: Dict[str, BaseKalmanFilter] = {}
        self.max_diagnostics_history = max_diagnostics_history

    def _make_key(self, sensor_id: str, tenant_id: str = "default") -> str:
        return f"{tenant_id}:{sensor_id}"

    def _get_or_create_filter(
        self,
        sensor_id: str,
        tenant_id: str = "default",
    ) -> BaseKalmanFilter:
        key = self._make_key(sensor_id, tenant_id)
        if key not in self._filters:
            self._filters[key] = self.factory.create_filter(sensor_id=sensor_id)
        return self._filters[key]

    def update(
        self,
        sensor_id: str,
        value: float,
        tenant_id: str = "default",
    ) -> Tuple[float, Optional[KalmanDiagnostics]]:
        """
        增量处理单个数据点

        Returns:
            (smoothed_value, diagnostics_snapshot)
        """
        kf = self._get_or_create_filter(sensor_id, tenant_id)
        state = kf.update(float(value))
        diag = kf.get_diagnostics()
        return state.estimate, diag

    def update_batch(
        self,
        sensor_id: str,
        values: List[float],
        tenant_id: str = "default",
    ) -> Tuple[np.ndarray, Optional[KalmanDiagnostics]]:
        """增量处理一批数据点"""
        kf = self._get_or_create_filter(sensor_id, tenant_id)
        results = []
        for v in values:
            s = kf.update(float(v))
            results.append(s.estimate)
        return np.array(results), kf.get_diagnostics()

    def save_state(self, sensor_id: str, tenant_id: str = "default") -> Optional[KalmanStreamingState]:
        """导出指定传感器的流式状态（持久化用）"""
        key = self._make_key(sensor_id, tenant_id)
        if key not in self._filters:
            return None
        return self._filters[key].save_state()

    def load_state(
        self,
        sensor_id: str,
        state: KalmanStreamingState,
        tenant_id: str = "default",
    ) -> None:
        """从持久化状态恢复指定传感器的滤波器"""
        kf = self._get_or_create_filter(sensor_id, tenant_id)
        kf.load_state(state)

    def reset(self, sensor_id: str, tenant_id: str = "default") -> None:
        key = self._make_key(sensor_id, tenant_id)
        if key in self._filters:
            self._filters[key].reset()

    def reset_all(self, tenant_id: Optional[str] = None) -> None:
        if tenant_id is None:
            self._filters.clear()
        else:
            prefix = f"{tenant_id}:"
            self._filters = {k: v for k, v in self._filters.items() if not k.startswith(prefix)}

    def has_filter(self, sensor_id: str, tenant_id: str = "default") -> bool:
        return self._make_key(sensor_id, tenant_id) in self._filters


# ====================================================================
# 顶层服务类：对外简单接口（兼容旧代码）
# ====================================================================

class KalmanFilterService:
    """
    卡尔曼滤波服务（兼容旧 API + 新高级特性）
    """

    def __init__(self):
        self.factory = KalmanFilterFactory()
        self.streaming_manager = StreamingKalmanManager(self.factory)
        self.standard_filter = self.factory.create_filter(mode="simple", collect_diagnostics=False)
        self.adaptive_filter = self.factory.create_filter(mode="adaptive", collect_diagnostics=False)
        self.rts_smoother = RauchTungStriebelSmoother(
            process_noise=self.factory.default_Q,
            measurement_noise=self.factory.default_R,
        )
        logger.info("卡尔曼滤波服务初始化完成")

    # ---------- 兼容旧 API ----------

    def smooth(self, data: np.ndarray, method: str = "standard") -> np.ndarray:
        if len(data) == 0:
            return data

        method_map = {
            "standard": "simple",
            "adaptive": "adaptive",
        }
        mode = method_map.get(method, "simple")

        if method == "rts":
            return self.rts_smoother.smooth(data)

        kf = self.factory.create_filter(mode=mode, collect_diagnostics=False)
        return kf.filter(data).smoothed_data

    def smooth_with_details(
        self,
        data: np.ndarray,
        method: str = "standard",
    ) -> KalmanFilterResult:
        method_map = {"standard": "simple", "adaptive": "adaptive"}
        mode = method_map.get(method, "simple")
        kf = self.factory.create_filter(mode=mode, collect_diagnostics=True)
        return kf.filter_with_diagnostics(data)

    # ---------- 新高级 API ----------

    def smooth_sensor(
        self,
        data: np.ndarray,
        sensor_id: Optional[str] = None,
        mode: Optional[str] = None,
        collect_diagnostics: Optional[bool] = None,
    ) -> KalmanFilterResult:
        """按传感器ID（应用覆盖配置）进行滤波"""
        kf = self.factory.create_filter(
            sensor_id=sensor_id, mode=mode, collect_diagnostics=collect_diagnostics
        )
        return kf.filter(data, collect_diagnostics=kf.get_diagnostics() is not None)

    # ---------- 流式增量 API（转发给 StreamingKalmanManager） ----------

    def streaming_update(
        self,
        sensor_id: str,
        value: float,
        tenant_id: str = "default",
    ) -> Tuple[float, Optional[KalmanDiagnostics]]:
        return self.streaming_manager.update(sensor_id, value, tenant_id)

    def streaming_update_batch(
        self,
        sensor_id: str,
        values: List[float],
        tenant_id: str = "default",
    ) -> Tuple[np.ndarray, Optional[KalmanDiagnostics]]:
        return self.streaming_manager.update_batch(sensor_id, values, tenant_id)

    def save_streaming_state(
        self,
        sensor_id: str,
        tenant_id: str = "default",
    ) -> Optional[KalmanStreamingState]:
        return self.streaming_manager.save_state(sensor_id, tenant_id)

    def load_streaming_state(
        self,
        sensor_id: str,
        state: KalmanStreamingState,
        tenant_id: str = "default",
    ) -> None:
        self.streaming_manager.load_state(sensor_id, state, tenant_id)
