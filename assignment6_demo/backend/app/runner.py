import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.domain import AppError


class AsyncBoundedRunner:
    """One CPU task at a time; an expired native call retains its slot."""

    def __init__(self, max_pending=3):
        self.max_pending = max_pending
        self.pending = 0
        self._slot = asyncio.Semaphore(1)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="demo-search")

    async def run(self, fn, timeout=10):
        if self.pending >= self.max_pending:
            raise AppError(429, "SEARCH_BUSY", "Tìm kiếm đang bận, hãy thử lại.", retryable=True)
        self.pending += 1
        acquired = submitted = False
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        try:
            await asyncio.wait_for(self._slot.acquire(), timeout)
            acquired = True
            if loop.time() >= deadline:
                raise asyncio.TimeoutError
            future = self._pool.submit(fn)
            submitted = True

            def finished(_):
                def release():
                    self.pending -= 1
                    self._slot.release()

                if not loop.is_closed():
                    loop.call_soon_threadsafe(release)

            future.add_done_callback(finished)
            wrapped = asyncio.wrap_future(future)
            # Timeout/cancellation ends HTTP waiting, not native execution.
            # Consume late failures so the event-loop logger does not expose them.
            wrapped.add_done_callback(lambda completed: completed.exception() if not completed.cancelled() else None)
            return await asyncio.wait_for(asyncio.shield(wrapped), max(0, deadline - loop.time()))
        except asyncio.TimeoutError as exc:
            raise AppError(504, "SEARCH_TIMEOUT", "Tìm kiếm quá thời gian chờ, hãy thử lại.", retryable=True) from exc
        finally:
            if not submitted:
                self.pending -= 1
                if acquired:
                    self._slot.release()

    def close(self):
        self._pool.shutdown(wait=False, cancel_futures=True)
