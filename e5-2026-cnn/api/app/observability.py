"""Small, fail-open wrapper around Langfuse observations."""

from collections.abc import Iterator
from contextlib import contextmanager
import logging
import random
from typing import Any

from langfuse import Langfuse

from app import config

logger = logging.getLogger(__name__)


def _create_client() -> Langfuse | None:
    if not config.LANGFUSE_ENABLED:
        logger.info("Langfuse is disabled")
        return None

    missing = [
        name
        for name, value in (
            ("LANGFUSE_PUBLIC_KEY", config.LANGFUSE_PUBLIC_KEY),
            ("LANGFUSE_SECRET_KEY", config.LANGFUSE_SECRET_KEY),
            ("LANGFUSE_BASE_URL", config.LANGFUSE_BASE_URL),
        )
        if not value.strip()
    ]
    if missing:
        logger.error("Langfuse enabled but missing configuration: %s", ", ".join(missing))
        return None

    options: dict[str, Any] = {
        "public_key": config.LANGFUSE_PUBLIC_KEY,
        "secret_key": config.LANGFUSE_SECRET_KEY,
        "base_url": config.LANGFUSE_BASE_URL,
        "environment": config.LANGFUSE_ENV,
    }
    if config.LANGFUSE_RELEASE:
        options["release"] = config.LANGFUSE_RELEASE

    try:
        client = Langfuse(**options)
    except (TypeError, ValueError, RuntimeError, OSError):
        logger.exception("Could not initialize Langfuse")
        return None

    logger.info("Langfuse initialized for environment %s", config.LANGFUSE_ENV)
    return client


client = _create_client()


@contextmanager
def observe(
    name: str,
    input_data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any | None]:
    """Create and close a span; telemetry failures do not fail the API request."""
    sample_rate = min(max(config.LANGFUSE_SAMPLE_RATE, 0.0), 1.0)
    if client is None or random.random() > sample_rate:
        yield None
        return

    try:
        span = client.start_observation(
            name=name,
            as_type="span",
            input=input_data,
            metadata=metadata,
        )
    except Exception:
        logger.exception("Could not start Langfuse observation %s", name)
        yield None
        return

    try:
        yield span
    except Exception as exc:
        update_observation(
            span,
            level="ERROR",
            status_message=str(exc)[:500],
        )
        raise
    finally:
        try:
            span.end()
        except Exception:
            logger.exception("Could not end Langfuse observation %s", name)


def update_observation(observation: Any | None, **fields: Any) -> None:
    if observation is None:
        return
    try:
        observation.update(**fields)
    except Exception:
        logger.exception("Could not update Langfuse observation")


def flush() -> None:
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        logger.exception("Could not flush Langfuse events")
