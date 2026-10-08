"""Concurrency guarantees for the real bounded executor, without model downloads."""

import asyncio
import gc
import threading

import pytest

from app.domain import AppError
from app.runner import AsyncBoundedRunner


async def wait_for_event(event):
    for _ in range(200):
        if event.is_set():
            return
        await asyncio.sleep(0.001)
    assert event.is_set(), "Native worker did not start"


def test_one_active_two_waiting_full_queue_rejected():
    runner = AsyncBoundedRunner(max_pending=3)
    entered, release = threading.Event(), threading.Event()
    completed, thread_ids = [], []

    def work(index):
        thread_ids.append(threading.get_ident())
        if index == 0:
            entered.set()
            release.wait(2)
        completed.append(index)
        return index

    async def exercise():
        active = asyncio.create_task(runner.run(lambda: work(0), timeout=1))
        await wait_for_event(entered)
        queued = [asyncio.create_task(runner.run(lambda index=i: work(index), timeout=1)) for i in (1, 2)]
        await asyncio.sleep(0.01)
        with pytest.raises(AppError) as caught:
            await runner.run(lambda: work(3), timeout=1)
        assert caught.value.code == "SEARCH_BUSY"
        assert caught.value.status == 429
        assert caught.value.retryable
        assert completed == []
        release.set()
        assert await active == 0
        assert await asyncio.gather(*queued) == [1, 2]
        assert completed == [0, 1, 2]
        assert len(set(thread_ids)) == 1

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner.close()


def test_timeout_retains_native_slot_and_does_not_block_event_loop():
    runner = AsyncBoundedRunner(max_pending=3)
    entered, release = threading.Event(), threading.Event()
    called = []

    def slow():
        entered.set()
        release.wait(2)
        return "late"

    async def exercise():
        with pytest.raises(AppError) as timeout:
            await runner.run(slow, timeout=0.02)
        assert entered.is_set()
        assert timeout.value.code == "SEARCH_TIMEOUT"
        assert timeout.value.status == 504
        assert timeout.value.retryable
        queued = [
            asyncio.create_task(runner.run(lambda index=i: called.append(index) or index, timeout=1)) for i in (1, 2)
        ]
        await asyncio.sleep(0.01)
        assert called == []
        with pytest.raises(AppError) as busy:
            await runner.run(lambda: "overflow", timeout=1)
        assert busy.value.code == "SEARCH_BUSY"
        release.set()
        assert await asyncio.gather(*queued) == [1, 2]
        assert await runner.run(lambda: "recovered", timeout=1) == "recovered"

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner.close()


def test_expired_queued_callable_never_runs():
    runner = AsyncBoundedRunner(max_pending=3)
    entered, release = threading.Event(), threading.Event()
    expired_calls = []

    def active():
        entered.set()
        release.wait(2)
        return "active"

    async def exercise():
        task = asyncio.create_task(runner.run(active, timeout=1))
        await wait_for_event(entered)
        with pytest.raises(AppError) as expired:
            await runner.run(lambda: expired_calls.append("should never execute"), timeout=0.02)
        assert expired.value.code == "SEARCH_TIMEOUT"
        release.set()
        assert await task == "active"
        assert await runner.run(lambda: "next", timeout=1) == "next"
        assert expired_calls == []

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner.close()


def test_cancelled_queued_callable_never_runs():
    runner = AsyncBoundedRunner(max_pending=3)
    entered, release = threading.Event(), threading.Event()
    cancelled_calls = []

    def active():
        entered.set()
        release.wait(2)
        return "active"

    async def exercise():
        active_task = asyncio.create_task(runner.run(active, timeout=1))
        await wait_for_event(entered)
        queued = asyncio.create_task(runner.run(lambda: cancelled_calls.append("never"), timeout=1))
        await asyncio.sleep(0.01)
        queued.cancel()
        with pytest.raises(asyncio.CancelledError):
            await queued
        release.set()
        await active_task
        assert await runner.run(lambda: "next", timeout=1) == "next"
        assert cancelled_calls == []

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner.close()


def test_native_failure_preserves_domain_error_and_releases_slot():
    runner = AsyncBoundedRunner(max_pending=3)

    def failing():
        raise AppError(500, "INVALID_VECTOR", "Vector không hợp lệ.")

    async def exercise():
        with pytest.raises(AppError) as caught:
            await runner.run(failing, timeout=1)
        assert caught.value.code == "INVALID_VECTOR"
        assert await runner.run(lambda: 42, timeout=1) == 42

    try:
        asyncio.run(exercise())
    finally:
        runner.close()


def test_late_native_exception_is_consumed_after_http_timeout():
    runner = AsyncBoundedRunner(max_pending=3)
    entered, release = threading.Event(), threading.Event()
    unhandled = []

    def late_failure():
        entered.set()
        release.wait(2)
        raise RuntimeError("Late native error must not reach the event-loop logger")

    async def exercise():
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _loop, context: unhandled.append(context["message"]))
        with pytest.raises(AppError) as timeout:
            await runner.run(late_failure, timeout=0.02)
        assert timeout.value.code == "SEARCH_TIMEOUT"
        del timeout
        release.set()
        assert await runner.run(lambda: "next", timeout=1) == "next"
        gc.collect()
        await asyncio.sleep(0.01)
        assert unhandled == []

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        runner.close()
