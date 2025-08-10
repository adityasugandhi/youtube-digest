"""
Exponential backoff retry utility for third-party API calls
"""

import time
import random
import logging
import functools
from typing import Callable, Any, Optional, Tuple, List

# Removed Google API dependencies

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_factor: float = 2.0,
        jitter: bool = True,
        retryable_status_codes: Optional[List[int]] = None,
        retryable_exceptions: Optional[Tuple] = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_factor = exponential_factor
        self.jitter = jitter
        self.retryable_status_codes = retryable_status_codes or [
            429,
            500,
            502,
            503,
            504,
        ]
        self.retryable_exceptions = retryable_exceptions or (
            ConnectionError,
            TimeoutError,
        )


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for exponential backoff with jitter"""
    delay = config.base_delay * (config.exponential_factor**attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add jitter (±25% of the delay)
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0, delay)


def is_retryable_error(exception: Exception, config: RetryConfig) -> bool:
    """Determine if an error is retryable"""
    # Check for retryable exception types
    if isinstance(exception, config.retryable_exceptions):
        return True

    # Check for requests exceptions with status codes
    if hasattr(exception, "response") and hasattr(exception.response, "status_code"):
        return exception.response.status_code in config.retryable_status_codes

    return False


def retry_with_exponential_backoff(config: Optional[RetryConfig] = None):
    """Decorator for adding exponential backoff retry to functions"""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt == config.max_retries:
                        logger.error(
                            f"{func.__name__} failed after {config.max_retries + 1} attempts. "
                            f"Final error: {e}"
                        )
                        break

                    # Check if error is retryable
                    if not is_retryable_error(e, config):
                        logger.error(
                            f"{func.__name__} failed with non-retryable error: {e}"
                        )
                        break

                    # Calculate delay
                    delay = calculate_delay(attempt, config)

                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{config.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )

                    time.sleep(delay)

            # Re-raise the last exception
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


# Pre-configured retry decorators for different API types
def supabase_data_retry(func: Callable) -> Callable:
    """Retry decorator optimized for Supabase data operations"""
    config = RetryConfig(
        max_retries=3,
        base_delay=2.0,
        max_delay=30.0,
        retryable_status_codes=[429, 500, 502, 503, 504, 408],
    )
    return retry_with_exponential_backoff(config)(func)


def supabase_api_retry(func: Callable) -> Callable:
    """Retry decorator optimized for Supabase API"""
    import requests

    config = RetryConfig(
        max_retries=4,
        base_delay=1.5,
        max_delay=45.0,
        retryable_status_codes=[429, 500, 502, 503, 504, 408],
        retryable_exceptions=(
            ConnectionError,
            TimeoutError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ),
    )
    return retry_with_exponential_backoff(config)(func)


def gemini_api_retry(func: Callable) -> Callable:
    """Retry decorator optimized for Gemini API"""
    config = RetryConfig(
        max_retries=3,
        base_delay=3.0,
        max_delay=60.0,
        retryable_status_codes=[429, 500, 502, 503, 504, 503],
    )
    return retry_with_exponential_backoff(config)(func)


# Context manager for manual retry logic
class RetryContext:
    """Context manager for manual retry implementation"""

    def __init__(
        self, config: Optional[RetryConfig] = None, operation_name: str = "operation"
    ):
        self.config = config or RetryConfig()
        self.operation_name = operation_name
        self.attempt = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and self.should_retry(exc_val):
            if self.attempt < self.config.max_retries:
                delay = calculate_delay(self.attempt, self.config)
                logger.warning(
                    f"{self.operation_name} attempt {self.attempt + 1}/{self.config.max_retries + 1} "
                    f"failed: {exc_val}. Retrying in {delay:.2f}s"
                )
                time.sleep(delay)
                self.attempt += 1
                return True  # Suppress exception to continue retry loop
        return False  # Don't suppress - let exception propagate

    def should_retry(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        return is_retryable_error(exception, self.config)
