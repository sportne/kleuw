"""Staleness detection helpers for Kleuw.

These utilities re-compute region hashes for link targets and compare them
against the stored digests to determine whether the referenced text has drifted.
The implementation mirrors the behavior described in
``spec/kleuw_staleness.md``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .hashing import DEFAULT_HASH_ALGORITHM, compute_region_hash
from .model import LineSpan, Link, RegionHash, Target

__all__ = [
    "TargetStalenessResult",
    "LinkStalenessResult",
    "check_target_staleness",
    "check_link_staleness",
    "check_links_staleness",
]

_FILE_MISSING = "file missing"
_INVALID_RANGE = "invalid line range"
_DECODE_ERROR = "decode error"


@dataclass(frozen=True, slots=True)
class TargetStalenessResult:
    """Result of recomputing the hash for a single target."""

    stale: bool
    reason: str | None
    computed_hash: RegionHash | None


@dataclass(frozen=True, slots=True)
class LinkStalenessResult:
    """Aggregated staleness state for an entire link."""

    link_id: str
    stale: bool
    reasons: tuple[str, ...]
    src: TargetStalenessResult
    dst: TargetStalenessResult


def check_links_staleness(
    links: Iterable[Link],
    *,
    file_lookup: Mapping[str, object] | None = None,
) -> list[LinkStalenessResult]:
    """Evaluate the staleness state for each link in ``links``.

    Args:
        links: Iterable of link objects to evaluate.
        file_lookup: Optional mapping used to resolve file identifiers to
            filesystem paths. Values may be strings, :class:`pathlib.Path`
            instances, objects with a ``path`` attribute, or mappings containing
            a ``"path"`` entry.

    Returns:
        list[LinkStalenessResult]: Result entries mirroring the input order.
    """

    return [check_link_staleness(link, file_lookup=file_lookup) for link in links]


def check_link_staleness(
    link: Link,
    *,
    file_lookup: Mapping[str, object] | None = None,
) -> LinkStalenessResult:
    """Determine whether ``link`` is stale.

    Args:
        link: Link to evaluate.
        file_lookup: Optional mapping used to resolve file identifiers to
            filesystem paths.

    Returns:
        LinkStalenessResult: Aggregated staleness information for ``link``.
    """

    src_result = check_target_staleness(link.src, file_lookup=file_lookup, label="src")
    dst_result = check_target_staleness(link.dst, file_lookup=file_lookup, label="dst")
    reasons = tuple(
        reason
        for reason in (src_result.reason, dst_result.reason)
        if reason is not None
    )
    return LinkStalenessResult(
        link_id=link.id,
        stale=src_result.stale or dst_result.stale,
        reasons=reasons,
        src=src_result,
        dst=dst_result,
    )


def check_target_staleness(
    target: Target,
    *,
    file_lookup: Mapping[str, object] | None = None,
    label: str | None = None,
) -> TargetStalenessResult:
    """Recompute the hash for ``target`` and determine whether it is stale.

    Args:
        target: Target description containing the stored hash and line span.
        file_lookup: Optional mapping used to resolve ``file_id`` targets.
        label: Optional label describing the target (e.g. ``"src"`` or
            ``"dst"``) used when formatting mismatch reasons.

    Returns:
        TargetStalenessResult: Evaluation result for ``target``.
    """

    path = _resolve_target_path(target, file_lookup=file_lookup)
    if path is None:
        return TargetStalenessResult(True, _FILE_MISSING, None)

    stored_hash = target.region_hash
    if stored_hash is None:
        return TargetStalenessResult(
            True,
            _format_reason("region hash missing", label=label),
            None,
        )

    start_line, end_line = _extract_line_span(target.lines)
    try:
        computed = compute_region_hash(
            path,
            start_line=start_line,
            end_line=end_line,
            algo=stored_hash.algo or DEFAULT_HASH_ALGORITHM,
        )
    except FileNotFoundError:
        return TargetStalenessResult(True, _FILE_MISSING, None)
    except UnicodeDecodeError:
        return TargetStalenessResult(True, _DECODE_ERROR, None)
    except ValueError:
        return TargetStalenessResult(True, _INVALID_RANGE, None)

    if computed == stored_hash:
        return TargetStalenessResult(False, None, computed)
    return TargetStalenessResult(
        True,
        _format_reason("region changed", label=label),
        computed,
    )


def _extract_line_span(span: LineSpan | None) -> tuple[int | None, int | None]:
    if span is None:
        return None, None
    return span.start, span.end


def _resolve_target_path(
    target: Target,
    *,
    file_lookup: Mapping[str, object] | None,
) -> Path | None:
    if target.path is not None:
        return Path(target.path)

    if target.file_id is None or file_lookup is None:
        return None

    candidate = file_lookup.get(target.file_id)
    if candidate is None:
        return None

    resolved = _candidate_to_path(candidate)
    return resolved


def _candidate_to_path(candidate: object) -> Path | None:
    if isinstance(candidate, (str, PathLike)):
        return Path(candidate)

    try:
        path_value = candidate.path  # type: ignore[attr-defined]
    except AttributeError:
        path_value = None
    if isinstance(path_value, (str, PathLike)):
        return Path(path_value)

    if isinstance(candidate, Mapping):
        path_value = candidate.get("path")
        if isinstance(path_value, (str, PathLike)):
            return Path(path_value)

    return None


def _format_reason(message: str, *, label: str | None) -> str:
    return f"{label} {message}" if label else message
