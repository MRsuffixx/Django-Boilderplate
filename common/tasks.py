from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _synchronous_task[TaskFunction: Callable[..., Any]](
    function: TaskFunction,
) -> TaskFunction:
    """Expose a small Celery-compatible surface while running work inline."""

    @wraps(function)
    def delay(*args, **kwargs):
        return function(*args, **kwargs)

    def apply_async(args=None, kwargs=None, **_options):
        return function(*(args or ()), **(kwargs or {}))

    function.delay = delay  # type: ignore[attr-defined]
    function.apply_async = apply_async  # type: ignore[attr-defined]
    return function


def shared_task(*decorator_args, **decorator_kwargs):
    """Use Celery only when enabled; otherwise execute task dispatch synchronously."""

    if settings.CELERY_ENABLED:
        try:
            from celery import shared_task as celery_shared_task
        except ImportError as exc:
            raise ImproperlyConfigured(
                'CELERY_ENABLED=true requires the optional ".[celery]" dependency.'
            ) from exc
        return celery_shared_task(*decorator_args, **decorator_kwargs)

    if len(decorator_args) == 1 and callable(decorator_args[0]) and not decorator_kwargs:
        return _synchronous_task(cast(Callable[..., Any], decorator_args[0]))

    def decorator[TaskFunction: Callable[..., Any]](function: TaskFunction) -> TaskFunction:
        return _synchronous_task(function)

    return decorator
