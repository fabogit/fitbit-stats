"""Logging of the server: one logger tree, uvicorn's format, no private paths.

Everything the server says goes through the "fitstats" logger (children are
made with `get_logger`). Its handler writes to stderr in the format of
uvicorn's own log lines (`INFO:     text`), which is what the desktop shell
reads to give each line its level. The handler's filter replaces the folders
of the current run and the user's home with placeholders, in the message and
in tracebacks, so the log can be shared without exposing where the data is.
"""
import logging
import ntpath
import os
import posixpath
import re
import sys
import threading
from pathlib import Path

ROOT = "fitstats"
HOME_PLACEHOLDER = "~"
DATA_PLACEHOLDER = "<data>"
OUTPUT_PLACEHOLDER = "<output>"
# A folder shorter than this ("/", ".", "C:\") would hide far too much of the text.
MIN_PATH_LENGTH = 4


def _is_absolute(path: str) -> bool:
    """Absolute in either spelling, so a Windows path is recognised on any system."""
    return posixpath.isabs(path) or ntpath.isabs(path)


def _spellings(path) -> set[str]:
    """The ways `path` may appear in a message: as given, absolute, with either slash."""
    text = os.fspath(path)
    found = set()
    for candidate in (text, text if _is_absolute(text) else os.path.abspath(text)):
        candidate = candidate.rstrip("/\\")
        if _is_absolute(candidate) and len(candidate) >= MIN_PATH_LENGTH:
            found.update({candidate, candidate.replace("\\", "/"), candidate.replace("/", "\\")})
    return found


class PathScrubber(logging.Filter):
    """Replaces known private folders in a record by placeholders.

    The home folder is always known; the folders of a run are added with `hide`
    when it starts. The longest path is replaced first, since a folder is a
    prefix of everything inside it.
    """

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._hidden: dict[str, str] = {}   # spelling -> placeholder
        self._compiled: tuple[re.Pattern, dict[str, str]] | None = None

    def hide(self, path, placeholder: str) -> None:
        with self._lock:
            for spelling in _spellings(path):
                self._hidden[self._key(spelling)] = placeholder
            self._compiled = None

    @staticmethod
    def _key(spelling: str) -> str:
        # Windows paths differ only in case when they are the same path.
        return spelling.lower() if os.name == "nt" else spelling

    def _rules(self) -> tuple[re.Pattern, dict[str, str]] | None:
        with self._lock:
            if self._compiled is None:
                rules = dict(self._hidden)
                if _home_known():
                    for spelling in _spellings(Path.home()):
                        rules.setdefault(self._key(spelling), HOME_PLACEHOLDER)
                if not rules:
                    return None
                pattern = re.compile("|".join(re.escape(p) for p in sorted(rules, key=len, reverse=True)),
                                     re.IGNORECASE if os.name == "nt" else 0)
                self._compiled = (pattern, rules)
            return self._compiled

    def scrub(self, text: str) -> str:
        rules = self._rules()
        if rules is None:
            return text
        pattern, placeholders = rules
        return pattern.sub(lambda m: placeholders[self._key(m.group(0))], text)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        record.msg, record.args = self.scrub(message), ()
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = self.scrub(record.exc_text)
        return True


def _home_known() -> bool:
    try:
        Path.home()
    except (RuntimeError, KeyError):
        return False
    return True


scrubber = PathScrubber()


def hide_folders(data_dir, output_dir) -> None:
    """Keeps the folders of a run out of the log from now on."""
    scrubber.hide(data_dir, DATA_PLACEHOLDER)
    scrubber.hide(output_dir, OUTPUT_PLACEHOLDER)


def get_logger(name: str) -> logging.Logger:
    """The logger of a module: a child of "fitstats"."""
    return logging.getLogger(f"{ROOT}.{name}")


def make_handler(stream, plain: bool = False) -> logging.Handler:
    """A handler that writes the filtered records to `stream`.

    `plain` writes the bare message (the command line); otherwise the line starts
    with the level, as uvicorn's do.
    """
    handler = logging.StreamHandler(stream)
    if plain:
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        from uvicorn.logging import DefaultFormatter
        handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=False))
    handler.addFilter(scrubber)
    return handler


def configure_logging(plain: bool = False) -> logging.Logger:
    """Sends the "fitstats" logger to stderr; does nothing if that is done already."""
    logger = logging.getLogger(ROOT)
    if any(getattr(h, "_fitstats", False) for h in logger.handlers):
        return logger
    handler = make_handler(sys.stderr, plain)
    handler._fitstats = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def scrub_uvicorn_logs() -> None:
    """Puts the scrubber on uvicorn's own handlers, once uvicorn has set them up.

    Its error log can carry a traceback with the user's folders in it.
    """
    for name in ("uvicorn", "uvicorn.error"):
        for handler in logging.getLogger(name).handlers:
            if scrubber not in handler.filters:
                handler.addFilter(scrubber)
