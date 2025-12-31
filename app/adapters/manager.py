import asyncio
import time
from typing import List, Dict, Any
import logging
from prometheus_client import Counter, Gauge, Histogram

LOG = logging.getLogger(__name__)

# Prometheus metrics
ADAPTER_RESTARTS = Counter('adapter_restarts_total', 'Total adapter restarts', ['name'])
ADAPTER_LATENCY = Histogram('adapter_latency_seconds', 'Adapter run latency seconds', ['name'])
ADAPTER_STATUS = Gauge('adapter_status', 'Adapter status (1=UP,0=DOWN)', ['name'])

class AdapterManager:
    """Supervises adapters: starts them, restarts on unhandled exceptions and tracks status.

    Behavior:
    - Call adapter.start() in a supervised loop.
    - If adapter.start() raises, the manager records a restart and retries with exponential backoff.
    - If restarts exceed max_retries, mark adapter unhealthy and stop restarting.
    """

    def __init__(self, adapters: List[Any], loop: asyncio.AbstractEventLoop = None, max_retries: int = 5):
        self.adapters = adapters
        self.loop = loop or asyncio.get_event_loop()
        self.tasks: Dict[str, asyncio.Task] = {}
        self.status: Dict[str, str] = {}
        self.restarts: Dict[str, int] = {}
        self._stop = False
        self.max_retries = max_retries

    async def start(self):
        self._stop = False
        for adapter in self.adapters:
            name = adapter.__class__.__name__
            self.status[name] = 'starting'
            ADAPTER_STATUS.labels(name=name).set(0)
            task = self.loop.create_task(self._run_adapter(adapter))
            self.tasks[name] = task

    async def _run_adapter(self, adapter):
        name = adapter.__class__.__name__
        backoff = 1.0
        while not self._stop:
            if self.restarts.get(name, 0) >= self.max_retries:
                LOG.error('Adapter %s exceeded max_retries (%s). Marking unhealthy.', name, self.max_retries)
                try:
                    getattr(adapter, 'mark_unhealthy', lambda: None)()
                except Exception:
                    pass
                self.status[name] = 'unhealthy'
                ADAPTER_STATUS.labels(name=name).set(0)
                return
            start = time.monotonic()
            try:
                self.status[name] = 'running'
                try:
                    getattr(adapter, 'mark_healthy', lambda: None)()
                except Exception:
                    pass
                ADAPTER_STATUS.labels(name=name).set(1)
                with ADAPTER_LATENCY.labels(name=name).time():
                    await adapter.start()
                # adapter.start returned normally: mark stopped and exit loop
                self.status[name] = 'stopped'
                ADAPTER_STATUS.labels(name=name).set(0)
                return
            except asyncio.CancelledError:
                self.status[name] = 'cancelled'
                ADAPTER_STATUS.labels(name=name).set(0)
                return
            except Exception as exc:  # pylint: disable=broad-except
                # mark failed and schedule restart with backoff
                self.status[name] = 'failed'
                self.restarts[name] = self.restarts.get(name, 0) + 1
                ADAPTER_RESTARTS.labels(name=name).inc()
                LOG.exception('Adapter %s failed with error: %s; restarting in %ss', name, exc, backoff)
                try:
                    getattr(adapter, 'mark_unhealthy', lambda: None)()
                except Exception:
                    pass
                ADAPTER_STATUS.labels(name=name).set(0)
                try:
                    await asyncio.sleep(min(backoff, 60.0))
                except asyncio.CancelledError:
                    self.status[name] = 'cancelled'
                    ADAPTER_STATUS.labels(name=name).set(0)
                    return
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
                LOG.exception('Error stopping adapter %s: %s', adapter, e)
        # wait for tasks to finish
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        out = {}
        for adapter in self.adapters:
            name = adapter.__class__.__name__
            try:
                healthy = getattr(adapter, 'is_healthy', lambda: False)()
            except Exception:
                healthy = False
            out[name] = {
                'state': self.status.get(name, 'unknown'),
                'restarts': self.restarts.get(name, 0),
                'healthy': healthy
            }
        return out