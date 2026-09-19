# Copyright 2016 Étienne Bersac
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The calling convention shared by the wait combinators.

Both ``wait_combine`` and ``wait_chain`` call each member with the retry
state as a single *positional* argument -- never by keyword -- on the sync
and the async retry paths alike.  Any member therefore works unchanged in
either combinator: a plain function (whose parameter may be named
anything), a library wait strategy, or a lambda.

Empty combinators keep their established behaviour: ``wait_chain()``
refuses to be built without strategies, while ``wait_combine()`` sums an
empty set of waits to ``0.0``.
"""

import asyncio
import unittest
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import tenacity
from tenacity import AsyncRetrying, RetryCallState, Retrying

_F = TypeVar("_F", bound=Callable[..., Coroutine[Any, Any, Any]])


def asynctest(callable_: _F) -> Callable[..., Any]:
    @wraps(callable_)
    def wrapper(*a: Any, **kw: Any) -> Any:
        return asyncio.run(callable_(*a, **kw))

    return wrapper


def make_retry_state(attempt_number: int = 1) -> RetryCallState:
    retry_state = RetryCallState(None, None, (), {})  # type: ignore[arg-type]
    retry_state.attempt_number = attempt_number
    return retry_state


def plain_function(state: RetryCallState) -> float:
    # Deliberately *not* named `retry_state`: members must not rely on the
    # parameter name, because combinators pass the state positionally.
    return 1.0


def all_members() -> tuple:
    return (plain_function, tenacity.wait_fixed(2), lambda state: 3.0)


class TestCombinatorConventionSync(unittest.TestCase):
    def test_combine_accepts_all_member_kinds(self) -> None:
        combined = tenacity.wait_combine(*all_members())
        self.assertEqual(combined(make_retry_state()), 6.0)

    def test_chain_accepts_all_member_kinds(self) -> None:
        chained = tenacity.wait_chain(*all_members())
        for attempt_number, expected in ((1, 1.0), (2, 2.0), (3, 3.0), (4, 3.0)):
            self.assertEqual(
                chained(make_retry_state(attempt_number)),
                expected,
                f"attempt {attempt_number}",
            )

    def test_same_members_run_under_retrying(self) -> None:
        for combinator in (tenacity.wait_combine, tenacity.wait_chain):
            with self.subTest(combinator=combinator.__name__):
                sleeps: list[float] = []
                attempts = 0

                retrying = Retrying(
                    sleep=sleeps.append,
                    wait=combinator(*all_members()),
                    stop=tenacity.stop_after_attempt(3),
                    retry=tenacity.retry_if_result(lambda result: result is None),
                    reraise=True,
                )

                def work() -> None:
                    nonlocal attempts
                    attempts += 1
                    return None

                with self.assertRaises(tenacity.RetryError):
                    retrying(work)
                self.assertEqual(attempts, 3)
                self.assertEqual(len(sleeps), 2)


class TestCombinatorConventionAsync(unittest.TestCase):
    @asynctest
    async def test_same_members_run_under_async_retrying(self) -> None:
        for combinator in (tenacity.wait_combine, tenacity.wait_chain):
            with self.subTest(combinator=combinator.__name__):
                attempts = 0

                async def work() -> str:
                    nonlocal attempts
                    attempts += 1
                    if attempts < 3:
                        raise OSError("not yet")
                    return "done"

                retrying = AsyncRetrying(
                    sleep=lambda seconds: asyncio.sleep(0),
                    wait=combinator(*all_members()),
                    stop=tenacity.stop_after_attempt(3),
                )
                self.assertEqual(await retrying(work), "done")
                self.assertEqual(attempts, 3)


class TestEmptyCombinators(unittest.TestCase):
    def test_empty_chain_still_rejected(self) -> None:
        with self.assertRaises(ValueError):
            tenacity.wait_chain()

    def test_empty_combine_still_sums_to_zero(self) -> None:
        self.assertEqual(tenacity.wait_combine()(make_retry_state()), 0.0)


if __name__ == "__main__":
    unittest.main()
