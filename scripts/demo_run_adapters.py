"""Demo script to run configured adapters locally and print incoming normalized events.

Usage:
  python scripts/demo_run_adapters.py

Ensure environment variables are set (or use defaults in `.env.example`).
"""
import asyncio
import os
from app.adapters.loader import load_adapters

async def main():
    events = []
    def cb(e):
        print('EVENT:', e)
        events.append(e)
    adapters = load_adapters(cb)
    tasks = [asyncio.create_task(a.start()) for a in adapters]

    try:
        # Run for a short demo duration
        await asyncio.sleep(10)
    finally:
        for a in adapters:
            try:
                a.stop()
            except Exception:
                pass
        for t in tasks:
            t.cancel()

if __name__ == '__main__':
    asyncio.run(main())
