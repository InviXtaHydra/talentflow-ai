"""Central logging. Log records never contain CV text, passwords, tokens or e-mail bodies:
code logs identifiers and outcomes only, and this filter masks anything that looks like a secret."""

import logging
import re
import sys

_SECRET_PATTERNS = [
    (re.compile(r"(?i)(password|token|secret|api[_-]?key|authorization|cookie)(\"?\s*[:=]\s*\"?)([^\s\",]+)"), r"\1\2***"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<email>"),
]


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern, replacement in _SECRET_PATTERNS:
            message = pattern.sub(replacement, message)
        record.msg = message
        record.args = None
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for noisy in ("httpx", "httpcore", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
