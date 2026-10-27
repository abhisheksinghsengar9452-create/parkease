from security import SlidingWindowRateLimiter


def test_rate_limiter_blocks_repeated_attempts():
    limiter = SlidingWindowRateLimiter(limit=2, period_seconds=60)
    assert limiter.allowed('127.0.0.1')
    assert limiter.allowed('127.0.0.1')
    assert not limiter.allowed('127.0.0.1')
