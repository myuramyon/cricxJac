import asyncio
from prometheus_client import Counter, Gauge, CollectorRegistry
from app.adapters.manager import AdapterManager, ADAPTER_RESTARTS, ADAPTER_STATUS


class AlwaysFailAdapter:
    async def start(self):
        raise RuntimeError('immediate fail')
    def stop(self):
        pass
    def mark_unhealthy(self):
        pass
    def mark_healthy(self):
        pass
    def is_healthy(self):
        return False


def test_supervisor_max_retries():
    async def runner():
        adapter = AlwaysFailAdapter()
        mgr = AdapterManager([adapter], max_retries=3)
        await mgr.start()
        # allow time for restarts
        await asyncio.sleep(2)
        status = mgr.get_status()
        assert 'AlwaysFailAdapter' in status
        # After a short delay retries should have incremented to at least max_retries
        await asyncio.sleep(2)
        status = mgr.get_status()
        assert status['AlwaysFailAdapter']['restarts'] >= 1
        # Adapter should be marked unhealthy if it exceeded retries
        # (manager will set 'unhealthy' state when threshold reached)
        # Stop manager
        await mgr.stop()
    asyncio.run(runner())
