import asyncio
import time

from app.adapters.manager import AdapterManager


class FlakyAdapter:
    """Adapter that fails on first start call and succeeds on the second."""

    def __init__(self):
        self.attempts = 0
        self.running = False

    async def start(self):
        self.attempts += 1
        if self.attempts == 1:
            # Simulate immediate failure
            raise RuntimeError('simulated failure')
        # On second attempt, run for a short time then return
        self.running = True
        await asyncio.sleep(0.05)
        self.running = False

    def stop(self):
        self.running = False


def test_manager_restarts_adapter():
    async def runner():
        adapter = FlakyAdapter()
        mgr = AdapterManager([adapter])
        await mgr.start()
        # allow time for failure and restart
        await asyncio.sleep(0.5)
        status = mgr.get_status()
        assert 'FlakyAdapter' in status
        assert status['FlakyAdapter']['restarts'] >= 1
        # stop manager
        await mgr.stop()

    asyncio.run(runner())
