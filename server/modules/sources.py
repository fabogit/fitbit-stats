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

    name     output name (a leading "_" marks a helper the ETL drops after combining)
    combine  how a day found in several files is combined
    """
    name: str
    combine: Combine = Agg.LAST


@dataclass(frozen=True)
class Special:
    """A source read by a function of its own: path -> DataFrame | None."""
    parse: Callable


@dataclass(frozen=True)
class Source:
    key: str                     # stable identifier (tests, logs)
    label: str                   # progress message: "Loading <label>"
    folder: str                  # folder inside the export
    pattern: str                 # glob pattern inside the folder
    reader: Special
    columns: tuple[Column, ...]
    parallel: bool = False       # parse the files in a process pool

    @property
    def rules(self) -> dict[str, Combine]:
        """{column: how a day found in several files is combined}."""
        return {c.name: c.combine for c in self.columns}
