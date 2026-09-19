# 复现：同一个裸函数放进两种组合器，一个按位置传参、一个按关键字传参
import sys
sys.path.insert(0, ".")
from tenacity import RetryCallState, wait_chain, wait_fixed


def naked(retry_state):
    return 1.0


state = RetryCallState(None, lambda: None, (), {})
print("wait_fixed 这种直接组合器  ->", wait_fixed(1)(state))
try:
    print("wait_chain 里放同一个裸函数 ->", wait_chain(naked)(state))
except TypeError as exc:
    print("wait_chain 里放同一个裸函数 -> TypeError:", str(exc)[:70])
