"""Drain current HTTP readers for a short in-process catalog activation (one worker)."""
import asyncio
from contextlib import asynccontextmanager


class CatalogGate:
    def __init__(self):
        self.condition = asyncio.Condition()
        self.readers = 0
        self.writing = False
        self.publisher = asyncio.Lock()

    @asynccontextmanager
    async def read(self):
        async with self.condition:
            await self.condition.wait_for(lambda: not self.writing)
            self.readers += 1
        try:
            yield
        finally:
            async with self.condition:
                self.readers -= 1
                self.condition.notify_all()

    @asynccontextmanager
    async def write(self):
        async with self.publisher:
            async with self.condition:
                self.writing = True
                try:
                    await self.condition.wait_for(lambda: self.readers == 0)
                except BaseException:
                    self.writing = False
                    self.condition.notify_all()
                    raise
            try:
                yield
            finally:
                async with self.condition:
                    self.writing = False
                    self.condition.notify_all()
