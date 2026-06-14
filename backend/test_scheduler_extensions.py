"""
测试脚本 - 验证调度器扩展功能
"""

import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("测试调度器扩展功能")
print("=" * 60)

# Test 1: 测试模块导入
print("\n[测试1] 模块导入测试")
print("-" * 40)
try:
    from app.schedulers.job_execution import (
        JobExecutionService, ErrorSummary, job_execution_context,
        get_instance_id, JobExecutionContext
    )
    print("  ✓ job_execution 模块导入成功")
except Exception as e:
    print(f"  ✗ job_execution 模块导入失败: {e}")

try:
    from app.schedulers.leader_election import (
        LeaderElection, get_leader_election, LeadershipContext
    )
    print("  ✓ leader_election 模块导入成功")
except Exception as e:
    print(f"  ✗ leader_election 模块导入失败: {e}")

try:
    from app.schedulers.task_sharding import (
        BoltIdPartitioner, ShardedTaskExecutor,
        get_bolt_id_partitioner, get_sharded_task_executor,
        ShardInfo, ShardResult
    )
    print("  ✓ task_sharding 模块导入成功")
except Exception as e:
    print(f"  ✗ task_sharding 模块导入失败: {e}")

try:
    from app.schedulers.scheduler import TaskScheduler, scheduler
    print("  ✓ scheduler 模块导入成功")
except Exception as e:
    print(f"  ✗ scheduler 模块导入失败: {e}")

# Test 2: 测试 ErrorSummary
print("\n[测试2] ErrorSummary 测试")
print("-" * 40)
try:
    es = ErrorSummary()
    es.add_error('bolt_001', 'ValueError', 'Invalid value')
    es.add_error('bolt_002', 'ValueError', 'Another invalid value')
    es.add_error('bolt_003', 'RuntimeError', 'Something went wrong')
    es.add_error('bolt_004', 'ValueError', 'Third value error')
    es.add_error('bolt_005', 'TypeError', 'Type mismatch')

    assert es.total_errors == 5, f"期望5个错误，实际{es.total_errors}"
    assert es.error_types.get('ValueError') == 3, "期望3个ValueError"
    assert es.error_types.get('RuntimeError') == 1, "期望1个RuntimeError"
    assert len(es.failed_node_ids) == 5, "期望5个失败节点"

    es_dict = es.to_dict()
    assert es_dict['total_errors'] == 5
    assert 'ValueError' in es_dict['error_types']
    assert not es.is_empty()

    print(f"  ✓ ErrorSummary 功能正常")
    print(f"    - 总错误数: {es.total_errors}")
    print(f"    - 错误类型: {dict(es.error_types)}")
    print(f"    - 失败节点: {es.failed_node_ids[:3]}...")
except Exception as e:
    print(f"  ✗ ErrorSummary 测试失败: {e}")

# Test 3: 测试 BoltIdPartitioner
print("\n[测试3] BoltIdPartitioner 测试")
print("-" * 40)
try:
    partitioner = BoltIdPartitioner(min_shard_size=3, max_shards=10)

    # 生成测试数据
    bolt_ids = [f'bolt_{i:03d}' for i in range(1, 26)]
    shards = partitioner.partition(bolt_ids, num_shards=4)

    assert len(shards) == 4, f"期望4个分片，实际{len(shards)}"
    assert sum(len(s) for s in shards) == 25, "分片总数不正确"

    print(f"  ✓ BoltIdPartitioner 功能正常")
    for i, shard in enumerate(shards):
        print(f"    分片{i+1}: {len(shard)} 个, 范围: {shard.item_min} - {shard.item_max}")

    # 测试按范围分片
    print(f"\n  测试按范围分片...")
    range_shards = partitioner.partition_by_range(
        bolt_ids,
        range_boundaries=['bolt_008', 'bolt_016', 'bolt_024'],
    )
    assert len(range_shards) == 4, f"期望4个范围分片，实际{len(range_shards)}"
    print(f"  ✓ 按范围分片功能正常，共{len(range_shards)}个分片")
except Exception as e:
    print(f"  ✗ BoltIdPartitioner 测试失败: {e}")

# Test 4: 测试 ShardedTaskExecutor
print("\n[测试4] ShardedTaskExecutor 测试")
print("-" * 40)
try:
    executor = ShardedTaskExecutor(max_workers=2)

    def process_item(item):
        if item == 'bolt_010':
            raise ValueError(f"Test error for {item}")
        return item.upper()

    bolt_ids = [f'bolt_{i:03d}' for i in range(1, 21)]

    result = executor.execute_sharded(
        task_name='test_task',
        task_type='test',
        items=bolt_ids,
        process_func=process_item,
        num_shards=4,
        trigger_type='manual',
    )

    assert result.total_count == 20, f"期望20个，实际{result.total_count}"
    assert result.success_count == 19, f"期望19个成功，实际{result.success_count}"
    assert result.failed_count == 1, f"期望1个失败，实际{result.failed_count}"
    assert len(result.results) == 19, f"期望19个结果，实际{len(result.results)}"

    print(f"  ✓ ShardedTaskExecutor 功能正常")
    print(f"    - 总数: {result.total_count}")
    print(f"    - 成功: {result.success_count}")
    print(f"    - 失败: {result.failed_count}")
    print(f"    - 跳过: {result.skipped_count}")
    print(f"    - 错误数: {result.error_summary.total_errors}")
except Exception as e:
    print(f"  ✗ ShardedTaskExecutor 测试失败: {e}")
    import traceback
    traceback.print_exc()

# Test 5: 测试 get_instance_id
print("\n[测试5] get_instance_id 测试")
print("-" * 40)
try:
    inst_id1 = get_instance_id()
    inst_id2 = get_instance_id()

    assert inst_id1 == inst_id2, "实例ID应该一致"
    assert len(inst_id1) > 0, "实例ID不应为空"

    print(f"  ✓ get_instance_id 功能正常")
    print(f"    - 实例ID: {inst_id1}")
except Exception as e:
    print(f"  ✗ get_instance_id 测试失败: {e}")

# Test 6: 测试单例获取
print("\n[测试6] 单例获取测试")
print("-" * 40)
try:
    p1 = get_bolt_id_partitioner()
    p2 = get_bolt_id_partitioner()
    assert p1 is p2, "分片器应该是单例"
    print(f"  ✓ BoltIdPartitioner 单例正常")

    e1 = get_sharded_task_executor()
    e2 = get_sharded_task_executor()
    assert e1 is e2, "执行器应该是单例"
    print(f"  ✓ ShardedTaskExecutor 单例正常")

    l1 = get_leader_election()
    l2 = get_leader_election()
    assert l1 is l2, "Leader选举器应该是单例"
    print(f"  ✓ LeaderElection 单例正常")
except Exception as e:
    print(f"  ✗ 单例测试失败: {e}")

# Test 7: 测试 ShardResult 合并
print("\n[测试7] ShardResult 合并测试")
print("-" * 40)
try:
    r1 = ShardResult(shard_index=0, shard_total=2, total_count=10, success_count=9, failed_count=1)
    r1.item_min = 'bolt_001'
    r1.item_max = 'bolt_010'

    r2 = ShardResult(shard_index=1, shard_total=2, total_count=10, success_count=8, failed_count=2)
    r2.item_min = 'bolt_011'
    r2.item_max = 'bolt_020'

    r1.merge(r2)

    assert r1.total_count == 20, "合并后总数应为20"
    assert r1.success_count == 17, "合并后成功数应为17"
    assert r1.failed_count == 3, "合并后失败数应为3"
    assert r1.item_min == 'bolt_001', "合并后最小值应为bolt_001"
    assert r1.item_max == 'bolt_020', "合并后最大值应为bolt_020"

    print(f"  ✓ ShardResult 合并功能正常")
except Exception as e:
    print(f"  ✗ ShardResult 合并测试失败: {e}")

# Test 8: 测试 JobExecutionContext (without DB)
print("\n[测试8] JobExecutionContext 测试")
print("-" * 40)
try:
    ctx = JobExecutionContext(
        job_name='test_job',
        job_type='test',
        trigger_type='manual',
    )

    ctx.log_id = 0
    ctx.start_time = datetime.now()

    ctx.record_success('bolt_001')
    ctx.record_success('bolt_002')
    ctx.record_failure('bolt_003', 'Test error', 'ValueError')
    ctx.record_failure('bolt_004', 'Another error', 'RuntimeError')
    ctx.record_skipped('bolt_005', 'No data')

    assert ctx.total_nodes == 5, f"期望5个，实际{ctx.total_nodes}"
    assert ctx.success_count == 2, f"期望2个成功，实际{ctx.success_count}"
    assert ctx.failed_count == 2, f"期望2个失败，实际{ctx.failed_count}"
    assert ctx.skipped_count == 1, f"期望1个跳过，实际{ctx.skipped_count}"
    assert ctx.error_summary is not None, "错误摘要不应为空"

    print(f"  ✓ JobExecutionContext 功能正常")
    print(f"    - 总数: {ctx.total_nodes}")
    print(f"    - 成功: {ctx.success_count}")
    print(f"    - 失败: {ctx.failed_count}")
    print(f"    - 跳过: {ctx.skipped_count}")
    print(f"    - 错误数: {ctx.error_summary.total_errors if ctx.error_summary else 0}")
except Exception as e:
    print(f"  ✗ JobExecutionContext 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("所有测试完成!")
print("=" * 60)
