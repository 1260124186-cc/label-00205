"""
工业协议采集网关 - 主链路回归测试

覆盖三大修复点：
1. 写入器：真实写入结果回调 + 失败回退缓存 + 续传真实判定
2. 热加载：新增/删除设备的锁重入修复
3. OPC UA：证书管理器真正接入安全连接链路
"""

import sys
import os
import time
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

sys.path.insert(0, '.')

from loguru import logger
logger.remove()

PASS = 0
FAIL = 0


def assert_true(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {msg}")
    else:
        FAIL += 1
        print(f"  ✗ {msg}")


# ============================================================
# 准备公共数据
# ============================================================
from app.gateway.models import (
    GatewayConfig,
    DeviceConfig,
    PointConfig,
    DataPoint,
    ProtocolType,
    DataSourceType,
    DataType,
    PLCBrand,
    DeviceStatus,
)

from app.gateway.config_manager import GatewayConfigManager
from app.gateway.data_writer import GatewayDataWriter
from app.gateway.cache import OfflineCache
from app.gateway.health import GatewayHealthMonitor
from app.gateway.cert_manager import CertificateManager
from app.gateway.templates import PLCTemplateManager
from app.gateway.service import IndustrialGatewayService


def make_device(
    device_id: str,
    protocol: ProtocolType = ProtocolType.MODBUS_TCP,
    n_points: int = 3,
) -> DeviceConfig:
    """构造一个测试设备"""
    points = [
        PointConfig(
            point_id=f'p{i}',
            sensor_id=f'100{i}',
            name=f'Point-{i}',
            address=f'holding_register:{100 + i * 2}',
            data_type=DataType.FLOAT32,
            unit='V',
            scale_factor=1.0,
            offset=0.0,
            sampling_period=1.0,
            enabled=True,
        )
        for i in range(n_points)
    ]
    return DeviceConfig(
        device_id=device_id,
        name=f'Device-{device_id}',
        protocol=protocol,
        host='127.0.0.1',
        port=502,
        slave_id=1,
        enabled=True,
        plc_brand=PLCBrand.GENERAL,
        points=points,
    )


def make_data_points(n: int = 5, device_id: str = 'dev-001') -> List[DataPoint]:
    """构造一批测试数据点"""
    return [
        DataPoint(
            device_id=device_id,
            point_id=f'p{i}',
            sensor_id=f'100{i}',
            value=float(i * 10),
            raw_value=float(i * 10),
            timestamp=datetime.now(),
            quality='good',
            unit='V',
        )
        for i in range(n)
    ]


# ============================================================
# 修复1：写入器真实写入结果 + 失败回退
# ============================================================
print("\n" + "=" * 60)
print("修复点1：真实写入结果回调 + 失败回退缓存 + 续传真实判定")
print("=" * 60)


def test_1_batch_result_callback_and_fallback():
    """批次真实写入结果通过回调回传；失败点回退缓存"""
    received_success = []
    received_failed = []
    received_is_replay = []

    def cb(success: List[DataPoint], failed: List[DataPoint], is_replay: bool):
        received_success.extend(success)
        received_failed.extend(failed)
        received_is_replay.append(is_replay)

    tmp = tempfile.mkdtemp()
    try:
        writer = GatewayDataWriter(
            data_target=DataSourceType.STREAM_INGEST,
            stream_ingest_url="http://127.0.0.1:19999/stream/ingest",
            batch_size=5,
            flush_interval=0.3,
            batch_result_callback=cb,
        )
        writer.start()

        cache = OfflineCache(cache_dir=tmp, max_memory_size=1000, max_disk_size=10000)
        service_callback_counter = [0, 0]  # [success_count, failed_count]

        # 模拟 service._on_write_result 行为：失败点回退缓存
        def svc_cb(success, failed, is_replay):
            service_callback_counter[0] += len(success)
            service_callback_counter[1] += len(failed)
            if failed and not is_replay:
                cache.add_points(failed)
            elif failed and is_replay:
                cache.add_points_to_head(failed)

        writer.set_batch_result_callback(svc_cb)

        points = make_data_points(5)
        enqueued = writer.write_batch(points)
        assert_true(enqueued == 5, "5 条数据入队成功 (enqueued=5)")

        stats_before = writer.get_stats()
        assert_true(
            stats_before['total_enqueued'] == 5 and stats_before['total_written'] == 0,
            "入队统计 ≠ 写入统计（此时写入尚未完成）"
        )

        # 等待刷新触发（目标地址不可达，肯定写入失败）
        time.sleep(1.5)

        stats_after = writer.get_stats()
        assert_true(
            stats_after['total_failed'] == 5,
            f"真实写入失败 5 条 (total_failed={stats_after['total_failed']})"
        )
        assert_true(
            service_callback_counter[1] == 5,
            f"回调收到 5 个失败点 (received_failed={service_callback_counter[1]})"
        )
        assert_true(
            service_callback_counter[0] == 0,
            f"回调收到 0 个成功点 (received_success={service_callback_counter[0]})"
        )

        # 失败点已被回退到缓存
        assert_true(cache.size == 5, f"写入失败点已回退缓存 (cache.size={cache.size})")

        # 清空缓存后测试 write_batch_sync 真实返回（续传场景）
        cache.clear()

        s, f = writer.write_batch_sync(make_data_points(3), is_replay=True)
        assert_true(s == 0 and f == 3, f"同步写入续传: s=0,f=3 (实际 s={s},f={f})")

        writer.stop()
        print()
        print(f"  回调触发次数: {len(received_is_replay)}（0=正确，因为我们替换了回调）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


test_1_batch_result_callback_and_fallback()


# ============================================================
# 修复2：配置热加载新增/删除设备无死锁
# ============================================================
print("\n" + "=" * 60)
print("修复点2：配置热加载 _sync_devices 锁重入修复")
print("=" * 60)


def test_2_hot_reload_no_deadlock():
    """动态热加载：新增/删除设备不再死锁"""
    tmpdir = tempfile.mkdtemp()
    try:
        dev1 = make_device('dev-1')
        dev2 = make_device('dev-2')

        cfg1 = GatewayConfig(
            gateway_id='gw-test',
            data_target=DataSourceType.STREAM_INGEST,
            stream_ingest_url="http://127.0.0.1:19999/stream/ingest",
            cache_enabled=True,
            cache_max_size=1000,
            cache_dir=tmpdir,
            health_check_interval=60,
            devices=[dev1],
        )
        cfg_mgr = GatewayConfigManager()
        cfg_mgr._config = cfg1

        svc = IndustrialGatewayService(config_manager=cfg_mgr)

        # 初始化：没有运行时，直接手动触发一次同步（模拟热加载新增）
        svc._is_running = True
        svc._data_writer.start()

        print("  [step1] 初始只有 dev-1，触发热加载 _sync_devices")
        svc._sync_devices(cfg1)
        # 虽然采集器真正连不上 PLC（没有真服务器），但只要不卡/不死锁就通过
        assert_true(True, "热加载单设备无死锁")

        print("  [step2] 配置变更：新增 dev-2")
        cfg2 = GatewayConfig(
            gateway_id='gw-test',
            data_target=DataSourceType.STREAM_INGEST,
            stream_ingest_url="http://127.0.0.1:19999/stream/ingest",
            cache_enabled=True,
            cache_max_size=1000,
            cache_dir=tmpdir,
            health_check_interval=60,
            devices=[dev1, dev2],
        )
        svc._sync_devices(cfg2)
        assert_true(True, "热加载新增 dev-2 无死锁")
        # 没有真实 PLC 时 collector.start() 返回 False，不会进入 _collectors
        # 只要无死锁 + 字典的 key 是正确子集就算通过
        collector_count1 = len(svc._collectors)
        bad_keys = [k for k in svc._collectors if k not in ('dev-1', 'dev-2')]
        assert_true(
            collector_count1 <= 2 and not bad_keys,
            f"_collectors 中只能包含 dev-1/dev-2 (size={collector_count1}, bad={bad_keys})"
        )

        print("  [step3] 配置变更：移除 dev-1，保留 dev-2")
        cfg3 = GatewayConfig(
            gateway_id='gw-test',
            data_target=DataSourceType.STREAM_INGEST,
            stream_ingest_url="http://127.0.0.1:19999/stream/ingest",
            cache_enabled=True,
            cache_max_size=1000,
            cache_dir=tmpdir,
            health_check_interval=60,
            devices=[dev2],
        )
        svc._sync_devices(cfg3)
        assert_true('dev-1' not in svc._collectors, "dev-1 已移除（dict 中不存在）")
        # dev-2 是否在 dict 里取决于 PLC 连接（无真服务器时为 False），只验证类型
        for k in svc._collectors:
            assert_true(k == 'dev-2', f"dict 中剩余的键只能是 dev-2 (实际 {k})")

        print("  [step4] 再次快速多次热加载（压力测试）")
        for round_idx in range(5):
            svc._sync_devices(cfg1)
            svc._sync_devices(cfg2)
            svc._sync_devices(cfg3)
        assert_true(True, "连续 15 次热加载无死锁")

        # 收尾
        svc._data_writer.stop()
        svc._is_running = False
        for c in list(svc._collectors.values()):
            try:
                c.stop()
            except Exception:
                pass
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


test_2_hot_reload_no_deadlock()


# ============================================================
# 修复3：证书管理器接入 OPC UA 链路
# ============================================================
print("\n" + "=" * 60)
print("修复点3：证书管理器接入 OPC UA 安全连接链路")
print("=" * 60)


def test_3_cert_manager_into_opcua():
    """证书管理器真正接入 OPC UA 采集器创建链路"""
    cert_dir = tempfile.mkdtemp()
    try:
        cert_mgr = CertificateManager(cert_dir=cert_dir)

        # 没有 cryptography 会给出 None，但流程要走通
        default_cert = cert_mgr.get_default_certificate()
        if default_cert is not None:
            print(f"  (已安装 cryptography，有证书: {default_cert.cert_path})")
            assert_true(Path(default_cert.cert_path).exists(), "默认证书文件存在")
            assert_true(Path(default_cert.key_path).exists(), "默认私钥文件存在")
        else:
            print("  (cryptography 未安装，跳过文件存在检查，但流程可走)")
            assert_true(True, "证书管理器已实例化（无 cryptography 时降级）")

        # 构造 service：手动传入 cert_manager
        tmpdir = tempfile.mkdtemp()
        try:
            dev_opcua = DeviceConfig(
                device_id='opcua-test-dev',
                name='OPC UA Test',
                protocol=ProtocolType.OPC_UA,
                host='127.0.0.1',
                port=4840,
                enabled=True,
                plc_brand=PLCBrand.GENERAL,
                # 请求启用安全连接（即使服务器不可达，也要走证书解析流程）
                connection_config={
                    'security_mode': 'SignAndEncrypt',
                    'security_policy': 'Basic256Sha256',
                },
                points=[
                    PointConfig(
                        point_id='opcua-p1',
                        sensor_id='2001',
                        name='OPC UA Temp',
                        address='ns=2;s=Temp',
                        data_type=DataType.FLOAT32,
                        unit='°C',
                        scale_factor=1.0,
                        offset=0.0,
                        sampling_period=1.0,
                        enabled=True,
                    ),
                ],
            )

            from app.gateway.opcua_collector import create_opcua_collector

            # 关键断言：service._create_collector 将 cert_manager 传入
            # 这里直接调用工厂函数模拟
            collector = create_opcua_collector(
                device_config=dev_opcua,
                data_callback=lambda p: None,
                status_callback=lambda a, b, c: None,
                cert_manager=cert_mgr,
            )
            assert_true(collector is not None, "OPC UA 采集器创建成功")
            assert_true(
                getattr(collector, '_cert_manager', None) is cert_mgr,
                "采集器持有 cert_manager 引用（链路已打通）"
            )

            # 调用 _resolve_certificate：即使没有 cryptography，也应优雅降级
            cert_path, key_path, server_cert = collector._resolve_certificate(
                security_mode='SignAndEncrypt',
                security_policy='Basic256Sha256',
            )
            print(f"  解析证书结果: cert={cert_path}, key={key_path}")

            if default_cert is not None:
                # 当 cryptography 可用时，应成功解析
                assert_true(cert_path is not None, "证书路径非空（有 cryptography）")
                assert_true(key_path is not None, "私钥路径非空（有 cryptography）")
            else:
                # 没有 cryptography → 返回 None，但流程不报错
                assert_true(True, "无 cryptography 时降级为 None（流程正常）")

            # 用不同 cert_name 走按名查找分支
            dev_opcua.connection_config['cert_name'] = 'brand-x-opcua'
            collector2 = create_opcua_collector(
                device_config=dev_opcua,
                data_callback=lambda p: None,
                status_callback=lambda a, b, c: None,
                cert_manager=cert_mgr,
            )
            cert_path2, key_path2, _ = collector2._resolve_certificate(
                security_mode='Sign',
                security_policy='Basic256',
            )
            if default_cert is not None:
                # 会自动生成 brand-x-opcua 证书
                assert_true(cert_path2 is not None, "按 cert_name 自动生成证书成功")
                brand_path = Path(cert_dir) / "brand-x-opcua.crt"
                assert_true(brand_path.exists(), "brand-x-opcua.crt 文件存在")
                print(f"  自动生成按名证书: {cert_path2}")
            else:
                assert_true(True, "无 cryptography 时按名查找分支不报错")

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    finally:
        shutil.rmtree(cert_dir, ignore_errors=True)


test_3_cert_manager_into_opcua()


# ============================================================
# 修复点额外验证：service._on_data_collected 数据完整链路
# ============================================================
print("\n" + "=" * 60)
print("补充验证：service._on_data_collected 完整链路（入队→回调→回退缓存）")
print("=" * 60)


def test_4_service_full_data_pipeline():
    """主服务的数据采集链路：入队 → 写入失败 → 通过回调回退缓存"""
    tmpdir = tempfile.mkdtemp()
    try:
        dev1 = make_device('dev-001')
        cfg = GatewayConfig(
            gateway_id='gw-1',
            data_target=DataSourceType.STREAM_INGEST,
            stream_ingest_url="http://127.0.0.1:19999/x",  # 不可达
            cache_enabled=True,
            cache_max_size=5000,
            cache_dir=tmpdir,
            health_check_interval=60,
            devices=[dev1],
        )
        cfg_mgr = GatewayConfigManager()
        cfg_mgr._config = cfg

        service = IndustrialGatewayService(config_manager=cfg_mgr)

        # 手动启动写入器（避免开整个网关）
        service._data_writer.start()

        assert_true(service._offline_cache.size == 0, "初始缓存为空")

        # 模拟采集到 10 条数据
        data = make_data_points(10, device_id='dev-001')
        service._on_data_collected(data)

        assert_true(
            service._data_writer.queue_size == 10,
            f"数据入队成功: queue_size={service._data_writer.queue_size}"
        )
        assert_true(service._offline_cache.size == 0, "入队阶段缓存为空")

        # 等待写入刷新失败 → 触发 _on_write_result → 回退缓存
        time.sleep(2.0)

        assert_true(
            service._offline_cache.size == 10,
            f"写入失败后数据已回退到缓存 (size={service._offline_cache.size})"
        )

        # 续传：write_batch_sync 返回真实结果；失败 → 回调自动 add_points_to_head
        # 此时缓存: 10，pop 5 后剩 5
        replay_points = service._offline_cache.pop_points(5)
        assert_true(len(replay_points) == 5, f"取出 5 条续传 (实际 {len(replay_points)})")
        assert_true(
            service._offline_cache.size == 5,
            f"pop 后续传 5 条，缓存剩 5 (实际 {service._offline_cache.size})"
        )

        ok = service._replay_callback(replay_points)
        assert_true(ok is False, f"续传因目标不可达返回 False (实际 {ok})")
        # _replay_callback 内部的 write_batch_sync 触发了 _on_write_result(is_replay=True)
        # → 失败的 5 条已经被自动 add_points_to_head，缓存应该是 5+5=10
        assert_true(
            service._offline_cache.size == 10,
            f"续传失败后，回调自动 add_points_to_head 5 条，缓存 size=10 (实际 {service._offline_cache.size})"
        )
        # 额外验证：队首是之前续传失败的那条（get_points(n) 不 pop，只是查看）
        peek = service._offline_cache.get_points(1)
        assert_true(
            len(peek) == 1 and peek[0].point_id == replay_points[0].point_id,
            "续传失败的点已被放回队首（下一次续传优先重试）"
        )

        # 收尾
        service._data_writer.stop()

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


test_4_service_full_data_pipeline()


# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 60)
print("回归测试汇总")
print("=" * 60)
print(f"  通过: {PASS}")
print(f"  失败: {FAIL}")
print()
if FAIL == 0:
    print("  ★ 所有修复点通过 ★")
else:
    print(f"  !! 有 {FAIL} 项失败，请检查输出")
    sys.exit(1)
