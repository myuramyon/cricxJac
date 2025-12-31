import asyncio
from typing import List, Dict, Any

class AdapterManager:
    """Supervises adapters: starts them, restarts on unhandled exceptions and tracks status.

    Behavior:
    - Calls adapter.start() in its own task.
    - If adapter.start() raises, the manager records a restart and retries with exponential backoff.
    - stop() cancels running tasks and invokes adapter.stop().
    """

    def __init__(self, adapters: List[Any], loop: asyncio.AbstractEventLoop = None):
        self.adapters = adapters
        self.loop = loop or asyncio.get_event_loop()
        self.tasks: Dict[str, asyncio.Task] = {}
        self.status: Dict[str, str] = {}
        self.restarts: Dict[str, int] = {}
        self._stop = False

    async def start(self):
        self._stop = False
        for adapter in self.adapters:
            name = adapter.__class__.__name__
            self.status[name] = 'starting'
            task = self.loop.create_task(self._run_adapter(adapter))
            self.tasks[name] = task

    async def _run_adapter(self, adapter):
        name = adapter.__class__.__name__
        backoff = 1.0
        while not self._stop:
            try:
                self.status[name] = 'running'
                await adapter.start()
                # adapter.start returned normally: mark stopped and exit loop
                self.status[name] = 'stopped'
                break
            except asyncio.CancelledError:
                self.status[name] = 'cancelled'
                break
            except Exception as exc:  # pylint: disable=broad-except
                # mark failed and schedule restart with backoff
                self.status[name] = 'failed'
                self.restarts[name] = self.restarts.get(name, 0) + 1
                print(f"Adapter {name} failed with error: {exc}; restarting in {backoff}s")
                try:
                    await asyncio.sleep(min(backoff, 60.0))
                except asyncio.CancelledError:
                    self.status[name] = 'cancelled'
                    break
                backoff = min(backoff * 2, 60.0)
                continue

    async def stop(self):
        self._stop = True
        # cancel tasks
        for name, task in list(self.tasks.items()):
            try:
                task.cancel()
            except Exception:
                pass
        # call adapter.stop()
        for adapter in self.adapters:
            try:
                adapter.stop()
            except Exception as e:
                print('Error stopping adapter', adapter, e)
        # wait for tasks to finish
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for adapter in self.adapters:
            name = adapter.__class__.__name__
            out[name] = {
                'state': self.status.get(name, 'unknown'),
                'restarts': self.restarts.get(name, 0)
            }
        return out
