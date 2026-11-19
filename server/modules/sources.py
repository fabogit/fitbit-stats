"""Types of the declarative load plan (see load_plan.py).

Only data classes and enums: no pandas work and no import of the other
modules, so parsers.py, load_plan.py and etl.py can all import it.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Agg(Enum):
    """A reduction of several values of the same day.

    A plain Enum on purpose, not a str one: a rule written as the string "sum"
    must be rejected, not silently accepted.
    """
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    FIRST = "first"     # first value in file order
    LAST = "last"       # last value in file order (across files: last file in name order)


@dataclass(frozen=True)
class FromSessions:
    """Across files: recompute from the sessions in the "_sessions" helper column,
    each session counted once by its id. `field` is the name of the session
    field to add up; `mean` averages the non-None values instead (falling back
    to the last file's value when there are none)."""
    field: str
    mean: bool = False


@dataclass(frozen=True)
class Ratio:
    """Across files: sum(numerator) / sum(denominator) over two helper columns."""
    numerator: str
    denominator: str
    decimals: int | None = None


Combine = Agg | FromSessions | Ratio


@dataclass(frozen=True)
class Column:
    """One output column of a source.

    name      output name (a leading "_" marks a helper the ETL drops after combining)
    field     where the value is read: a field name of the file, or None for the
              same name as `name` (or for the output of a special parser)
    required  a file without it gives no data (see parsers.read_json_daily)
    combine   how a day found in several files is combined
    scale, decimals  value * scale, then rounded (unit conversions)
    """
    name: str
    field: str | None = None
    required: bool = True
    combine: Combine = Agg.LAST
    scale: float | None = None
    decimals: int | None = None


@dataclass(frozen=True)
class JsonDaily:
    """A JSON list of records with a date field (for example {"dateTime", "value"})."""
    date_field: str = "dateTime"
    date_format: str = "%m/%d/%y %H:%M:%S"
    per_day: Agg | None = None          # None: one row per record, as written


@dataclass(frozen=True)
class Special:
    """A source too irregular for the generic readers: a function path -> DataFrame | None."""
    parse: Callable


Reader = JsonDaily | Special


@dataclass(frozen=True)
class Source:
    key: str                     # stable identifier (tests, logs)
    label: str                   # progress message: "Loading <label>"
    folder: str                  # folder inside the export
    pattern: str                 # glob pattern inside the folder
    reader: Reader
    columns: tuple[Column, ...]
    parallel: bool = False       # parse the files in a process pool

    @property
    def rules(self) -> dict[str, Combine]:
        """{column: how a day found in several files is combined}."""
        return {c.name: c.combine for c in self.columns}
