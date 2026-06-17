import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, '.')

from app.services.prediction.orchestrator import PredictionOrchestrator

orch = PredictionOrchestrator()
np.random.seed(42)
n = 200

# 生成带时间戳的数据
start_date = datetime(2025, 1, 1)
timestamps = [(start_date + timedelta(hours=i)).isoformat() for i in range(n)]

print("=" * 60)
print(" Prophet 互补功能全链路验证")
print("=" * 60)

# 测试1: 螺栓预测 - 带时间戳
print("\n--- 测试1: 螺栓预测（带时间戳）---")
steady_data = np.random.normal(loc=500, scale=10, size=(n, 1))
result = orch.predict_bolt('prophet_test_bolt', steady_data, timestamps=timestamps)
wc = result.get('working_condition', {})

print(f"  工况: {wc.get('condition')}")
print(f"  状态码: {result.get('status_code')}")
print(f"  prophet_forecast 存在: {wc.get('prophet_forecast') is not None}")
print(f"  seasonal_decomposition 存在: {wc.get('seasonal_decomposition') is not None}")

if wc.get('prophet_forecast'):
    pf = wc['prophet_forecast']
    print(f"  Prophet预测类型: {type(pf).__name__}")
    if isinstance(pf, dict):
        print(f"  Prophet预测keys: {list(pf.keys())[:10]}")

if wc.get('seasonal_decomposition'):
    sd = wc['seasonal_decomposition']
    print(f"  季节性分解类型: {type(sd).__name__}")
    if isinstance(sd, dict):
        print(f"  季节性分解keys: {list(sd.keys())}")

# 测试2: 螺栓预测 - 不带时间戳
print("\n--- 测试2: 螺栓预测（不带时间戳）---")
result2 = orch.predict_bolt('prophet_test_bolt2', steady_data)
wc2 = result2.get('working_condition', {})
print(f"  工况: {wc2.get('condition')}")
print(f"  prophet_forecast 存在: {wc2.get('prophet_forecast') is not None}")
print(f"  seasonal_decomposition 存在: {wc2.get('seasonal_decomposition') is not None}")

# 测试3: 法兰面预测 - 带时间戳
print("\n--- 测试3: 法兰面预测（带时间戳）---")
flange_data = [
    np.random.normal(loc=500 + i * 5, scale=8 + i, size=(n, 1))
    for i in range(4)
]
flange_ids = [f'flange_bolt_{i}' for i in range(4)]
flange_result = orch.predict_flange(
    flange_id='prophet_test_flange',
    multi_bolt_data=flange_data,
    timestamps=timestamps,
    bolt_ids=flange_ids,
    bolt_data_dict=None,
    enable_correlation_analysis=False,
    version=None,
    save_to_db=False,
)
fwc = flange_result.get('working_condition', {})
print(f"  工况: {fwc.get('condition')}")
print(f"  状态码: {flange_result.get('status_code')}")
print(f"  prophet_forecast 存在: {fwc.get('prophet_forecast') is not None}")
print(f"  seasonal_decomposition 存在: {fwc.get('seasonal_decomposition') is not None}")

# 测试4: 工况振幅系数验证
print("\n--- 测试4: 不同工况下的季节性振幅 ---")
from app.models.working_condition_classifier import WorkingCondition

predictor = orch.condition_adaptive_predictor
conditions = [
    WorkingCondition.STEADY_STATE,
    WorkingCondition.LOAD_INCREASE,
    WorkingCondition.LOAD_DECREASE,
    WorkingCondition.SHUTDOWN_COOLING,
    WorkingCondition.POST_MAINTENANCE_RECOVERY,
]

for cond in conditions:
    amp = predictor._get_condition_amplitude(cond)
    print(f"  {cond.value}: {amp}")

print("\n" + "=" * 60)
print(" 验证完成")
print("=" * 60)
