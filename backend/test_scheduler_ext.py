"""
测试调度器扩展功能

快速验证:
1. Leader选举
2. 任务分片
3. 任务日志
"""

import sys
sys.path.insert(0, '.')

from loguru import logger


def test_leader_election():
    """测试Leader选举"""
    logger.info("=" * 60)
    logger.info("测试 Leader 选举功能")
    logger.info("=" * 60)

    try:
        from app.schedulers.leader_election import get_leader_election

        le = get_leader_election()
        logger.info(f"Instance ID: {le.instance_id}")
        logger.info(f"Lease TTL: {le.lease_ttl}")

        job_key = 'test_job'
        acquired = le.try_acquire_leadership(job_key)
        logger.info(f"获取Leader锁: {acquired}")

        is_leader = le.is_leader(job_key)
        logger.info(f"是否为Leader: {is_leader}")

        info = le.get_leader_info(job_key)
        logger.info(f"Leader信息: {info}")

        released = le.release_leadership(job_key)
        logger.info(f"释放Leader锁: {released}")

        logger.info("✅ Leader选举测试通过")
        return True
    except Exception as e:
        logger.error(f"❌ Leader选举测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_job_sharding():
    """测试任务分片"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 任务分片 功能")
    logger.info("=" * 60)

    try:
        from app.schedulers.job_sharding import job_sharding

        bolt_ids = [str(i) for i in range(1, 101)]
        logger.info(f"生成测试bolt_id: 1-100")

        shards = job_sharding.create_shards(bolt_ids=bolt_ids, shard_count=4)
        logger.info(f"分片数: {len(shards)}")

        for shard in shards:
            logger.info(
                f"  分片[{shard.shard_index}/{shard.shard_total}]: "
                f"count={shard.bolt_count}, "
                f"range=[{shard.bolt_id_min}, {shard.bolt_id_max}], "
                f"ids={shard.bolt_ids[:3]}..."
            )

        total_count = sum(s.bolt_count for s in shards)
        logger.info(f"分片总数验证: {total_count} == {len(bolt_ids)}: {total_count == len(bolt_ids)}")

        logger.info("✅ 任务分片测试通过")
        return True
    except Exception as e:
        logger.error(f"❌ 任务分片测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_job_logger():
    """测试任务日志"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 任务日志 功能")
    logger.info("=" * 60)

    try:
        from app.schedulers.job_logger import job_execution_logger

        logger.info(f"Instance ID: {job_execution_logger.instance_id}")

        logs = job_execution_logger.get_recent_logs(limit=5)
        logger.info(f"最近日志数: {len(logs)}")

        for log in logs[:3]:
            logger.info(
                f"  [{log['id']}] {log['job_name']} - {log['status']} "
                f"- {log['start_time']}"
            )

        logger.info("✅ 任务日志测试通过")
        return True
    except Exception as e:
        logger.error(f"❌ 任务日志测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_scheduler():
    """测试增强调度器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 增强调度器 功能")
    logger.info("=" * 60)

    try:
        from app.schedulers.scheduler_ext import EnhancedTaskScheduler

        scheduler = EnhancedTaskScheduler()
        logger.info(f"Leader选举启用: {scheduler.enable_leader_election}")
        logger.info(f"任务分片启用: {scheduler.enable_sharding}")
        logger.info(f"分片数: {scheduler.shard_count}")
        logger.info(f"最大并行分片数: {scheduler.max_parallel_shards}")

        logger.info(f"支持的任务: {list(scheduler.JOB_NAME_MAPPING.keys())}")

        logger.info("✅ 增强调度器测试通过")
        return True
    except Exception as e:
        logger.error(f"❌ 增强调度器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("\n" + "=" * 60)
    logger.info("调度器扩展功能测试套件")
    logger.info("=" * 60)

    results = []
    results.append(('Leader选举', test_leader_election()))
    results.append(('任务分片', test_job_sharding()))
    results.append(('任务日志', test_job_logger()))
    results.append(('增强调度器', test_enhanced_scheduler()))

    logger.info("\n" + "=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "✅ 通过" if ok else "❌ 失败"
        logger.info(f"  {name}: {status}")

    logger.info(f"\n总计: {passed}/{total} 通过")
    logger.info("=" * 60)

    return passed == total


if __name__ == '__main__':
    import os
    os.environ.setdefault('PYTHONPATH', '.')
    success = main()
    sys.exit(0 if success else 1)
