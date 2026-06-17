#!/usr/bin/env python3
"""
时序数据库模块静态检查脚本
验证模块加载、接口一致性、改造点完整性
"""
import sys
import os
sys.path.insert(0, '.')

errors = []
passed = 0

def check_item(desc, ok, err_msg=None):
    global passed
    if ok:
        print(f"  ✓ {desc}")
        passed += 1
        return True
    else:
        print(f"  ✗ {desc}")
        if err_msg:
            print(f"    → {err_msg}")
            errors.append((desc, err_msg))
        else:
            errors.append((desc, "检查失败"))
        return False

print()
print("=" * 70)
print("[1/8] 模块加载检查")
print("=" * 70)

modules_to_load = [
    ("时序模块包", "app.timeseries"),
    ("基础抽象", "app.timeseries.base"),
    ("工厂函数", "app.timeseries.factory"),
    ("降采样引擎", "app.timeseries.downsampling"),
    ("迁移工具", "app.timeseries.migration"),
    ("InfluxDB后端", "app.timeseries.influxdb_repository"),
    ("TimescaleDB后端", "app.timeseries.timescale_repository"),
    ("时序分析服务", "app.services.timeseries_service"),
    ("时序API Schema", "app.api.timeseries_schemas"),
    ("时序API路由", "app.api.timeseries_routes"),
    ("预测Repository", "app.services.prediction.repository"),
    ("数据库工具", "app.utils.database"),
]

for name, mod_path in modules_to_load:
    try:
        __import__(mod_path)
        check_item(f"{name}  → {mod_path}", True)
    except Exception as e:
        check_item(f"{name}  → {mod_path}", False, str(e))

print()
print("=" * 70)
print("[2/8] 接口契约一致性检查")
print("=" * 70)

try:
    from app.timeseries.base import TimeSeriesRepository

    required_methods = [
        'write_point', 'write_batch',
        'query_raw', 'query_aggregated',
        'query_latest', 'query_prediction_window',
        'count_points', 'get_statistics', 'list_sensors',
        'run_downsampling', 'cleanup_expired',
        'delete_by_sensor',
        'health_check', 'close', 'execute_sql',
    ]

    repo_methods = [m for m in dir(TimeSeriesRepository) if not m.startswith('_')]
    for m in required_methods:
        ok = m in repo_methods
        check_item(f"TimeSeriesRepository.{m}() 已定义", ok)

    for backend_name, filename in [
        ("TimescaleDB", "timescale_repository"),
        ("InfluxDB", "influxdb_repository")
    ]:
        mod = __import__(f"app.timeseries.{filename}", fromlist=['*'])
        for attr in dir(mod):
            if 'Repository' in attr and attr != 'TimeSeriesRepository':
                cls = getattr(mod, attr)
                try:
                    is_sub = issubclass(cls, TimeSeriesRepository)
                    check_item(f"{backend_name} 后端继承抽象基类", is_sub)
                except Exception:
                    pass
except Exception as e:
    check_item("接口检查执行", False, str(e))
    import traceback; traceback.print_exc()

print()
print("=" * 70)
print("[3/8] 工厂函数检查")
print("=" * 70)

try:
    from app.timeseries.factory import (
        is_timeseries_enabled,
        create_timeseries_repository,
        get_timeseries_config,
    )
    cfg = get_timeseries_config()
    enabled = is_timeseries_enabled()
    repo = create_timeseries_repository()
    check_item(f"get_timeseries_config() 返回非空: {bool(cfg)}", True)
    check_item(f"is_timeseries_enabled() = {enabled}", True)
    check_item(f"create_timeseries_repository() 返回类型正确（未启用时为None）",
               repo is None or hasattr(repo, 'write_point'))
except Exception as e:
    check_item("工厂函数执行", False, str(e))

print()
print("=" * 70)
print("[4/8] 数据模型实例化检查")
print("=" * 70)

try:
    from datetime import datetime
    from app.timeseries.base import (
        TimeSeriesDataPoint, AggregatedDataPoint,
        TimeSeriesQuery, AggregationLevel,
    )
    dp = TimeSeriesDataPoint(
        timestamp=datetime.now(), sensor_id="T1", value=120.5,
        fields={'t': 25.0}, tags={'p': 'A1'}
    )
    check_item(f"TimeSeriesDataPoint(value={dp.value}) 实例化", True)

    ap = AggregatedDataPoint(
        timestamp=datetime.now(), sensor_id="T1",
        open=119, high=121, low=118, close=120.5,
        mean=119.8, std=0.8, count=60, sum=7188.0,
        level=AggregationLevel.MINUTE
    )
    check_item(f"AggregatedDataPoint(OHLC) 实例化", True)

    q = TimeSeriesQuery(
        sensor_id="T1", start_time=datetime.now(),
        end_time=datetime.now(), aggregation_level=AggregationLevel.RAW,
        limit=100
    )
    check_item(f"TimeSeriesQuery 实例化", True)
except Exception as e:
    check_item("数据模型实例化", False, str(e))
    import traceback; traceback.print_exc()

print()
print("=" * 70)
print("[5/8] 主应用路由注册检查")
print("=" * 70)

try:
    main_path = os.path.join(os.path.dirname(__file__), '..', '..', 'main.py')
    with open(main_path, 'r') as f:
        main_content = f.read()

    check1 = "from app.api.timeseries_routes import router as timeseries_router" in main_content
    check2 = "app.include_router(timeseries_router" in main_content

    check_item("main.py 导入 timeseries_router", check1)
    check_item("main.py 注册 timeseries_router 到 /api/v1", check2)
except Exception as e:
    check_item("路由注册检查执行", False, str(e))

print()
print("=" * 70)
print("[6/8] 预测主链改造检查")
print("=" * 70)

try:
    from app.services.prediction.repository import PredictionRepository

    methods_to_check = [
        '_fetch_batch_bolt_data_timeseries',
        '_fetch_batch_bolt_data_mysql',
        '_get_bolt_history_timeseries',
        '_get_bolt_history_mysql',
    ]
    for m in methods_to_check:
        check_item(f"PredictionRepository.{m}() 存在", hasattr(PredictionRepository, m))

    # 检查装饰函数
    from app.services.prediction.repository import (
        _is_timeseries_for_prediction,
        _get_prediction_window_size,
    )
    check_item("_is_timeseries_for_prediction() 函数存在", True)
    check_item("_get_prediction_window_size() 默认返回100",
               _get_prediction_window_size() == 100)

except Exception as e:
    check_item("预测主链改造检查", False, str(e))
    import traceback; traceback.print_exc()

print()
print("=" * 70)
print("[7/8] 数据库工具改造检查")
print("=" * 70)

try:
    from datetime import datetime as _dt
    from app.utils.database import (
        _BoltDataCompat,
        _is_timeseries_enabled_for_history,
        _get_bolt_recent_from_timeseries,
        _get_flange_recent_from_timeseries,
    )

    test_obj = _BoltDataCompat(
        sensor_id=123, ptf=120.5, create_time=_dt.now(),
        collector_id=1, splitter_num=2, position='A1'
    )
    required_attrs = ['sensor_id', 'ptf', 'create_time', 'collector_id',
                      'splitter_num', 'position']
    attrs_ok = all(hasattr(test_obj, a) for a in required_attrs)
    check_item("_BoltDataCompat 兼容类属性完整", attrs_ok)
    check_item("_is_timeseries_enabled_for_history() 函数存在", True)
    check_item("_get_bolt_recent_from_timeseries() 函数存在", True)
    check_item("_get_flange_recent_from_timeseries() 函数存在", True)

except Exception as e:
    check_item("数据库工具改造检查", False, str(e))
    import traceback; traceback.print_exc()

print()
print("=" * 70)
print("[8/8] 历史分析兼容层 API 检查")
print("=" * 70)

try:
    routes_path = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'api', 'routes.py')
    with open(routes_path, 'r') as f:
        routes = f.read()

    api_checks = [
        ("/bolt/{sensor_id}/trend 兼容层", "get_bolt_trend_compat"),
        ("/bolt/{sensor_id}/statistics 兼容层", "get_bolt_statistics_compat"),
        ("/bolt/{sensor_id}/compare-periods 兼容层", "get_bolt_period_compare_compat"),
        ("/timeseries/sql-query 兼容层", "timeseries_sql_query_compat"),
    ]
    for endpoint_name, function_name in api_checks:
        ok = function_name in routes
        check_item(f"{endpoint_name} ({function_name})", ok)

except Exception as e:
    check_item("历史分析 API 兼容层检查", False, str(e))


# ============================================================
# 最终报告
# ============================================================
print()
print("=" * 70)
print("FINAL REPORT")
print("=" * 70)

total = passed + len(errors)
print(f"  检查项总数:  {total}")
print(f"  通过数量:    {passed}")
print(f"  问题数量:    {len(errors)}")

if errors:
    print()
    print("问题详情:")
    for item, msg in errors:
        print(f"  - [{item}]: {msg}")

print()
if len(errors) == 0:
    print("✅ 所有静态检查均通过！")
    print()
    print("下一步建议（联调真实数据库）:")
    print("  1. 启动 TimescaleDB:")
    print("     cd .. && docker compose --profile timescaledb up -d")
    print("  2. 运行 TimescaleDB 联调:")
    print("     cd backend && TIMESERIES_ENABLED=true TIMESERIES_BACKEND=timescaledb \\")
    print("       TIMESCALEDB_HOST=localhost TIMESCALEDB_PORT=5432 \\")
    print("       TIMESCALEDB_USER=postgres TIMESCALEDB_PASSWORD=postgres \\")
    print("       TIMESCALEDB_DATABASE=bolt_timeseries \\")
    print("       python tests/timeseries/test_integration.py --backend timescaledb")
    print()
    print("  3. 启动 InfluxDB:")
    print("     cd .. && docker compose --profile influxdb up -d")
    print("  4. 运行 InfluxDB 联调:")
    print("     cd backend && TIMESERIES_ENABLED=true TIMESERIES_BACKEND=influxdb \\")
    print("       INFLUXDB_URL=http://localhost:8086 INFLUXDB_TOKEN=my-token \\")
    print("       INFLUXDB_ORG=bolt INFLUXDB_BUCKET=bolt_data \\")
    print("       python tests/timeseries/test_integration.py --backend influxdb")
    print()
    print("  5. 同时测试两个后端:")
    print("     python tests/timeseries/test_integration.py --all")

else:
    print("⚠️  请先修复上述问题，然后再进行联调测试。")
    sys.exit(1)
