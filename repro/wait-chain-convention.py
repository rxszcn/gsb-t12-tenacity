# 复现：同一个普通函数，放进两种组合器，一个按位置传参、一个按关键字传参
from tenacity import RetryCallState
from tenacity import wait_chain, wait_combine, wait_fixed


def naked(state):
    return 1.0


st = RetryCallState(None, lambda: None, (), {})

print("wait_combine 里放同一个函数 ->", wait_combine(naked, wait_fixed(1))(st))
try:
    print("wait_chain  里放同一个函数 ->", wait_chain(naked)(st))
except TypeError as exc:
    print("wait_chain  里放同一个函数 -> TypeError:", str(exc)[:70])
