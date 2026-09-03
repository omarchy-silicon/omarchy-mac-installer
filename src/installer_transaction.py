"""Pure transaction primitives for a future installer integration.

This module deliberately has no operating-system, disk, boot, network, or
privilege dependencies.  It models the safety boundary that an eventual
executor must use; it is not an installer executor.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Self


MAX_ID_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 256
MAX_ACTIONS = 128
MAX_JOURNAL_ENTRIES = 4096
MAX_PAYLOAD_BYTES = 16 * 1024
MAX_ARTIFACT_BYTES = 2 * 1024**4
MAX_PAYLOAD_DEPTH = 8
MAX_STRING_LENGTH = 512
MAX_LIST_ITEMS = 1024

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_SECRET_KEY_RE = re.compile(
    r"(?:pass(?:word)?|secret|token|credential|private.?key|authorization|cookie|api.?key)",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(
    r"(?:\bbearer\s+|\bsk-[A-Za-z0-9]|-----BEGIN .* PRIVATE KEY-----)", re.IGNORECASE
)


class TransactionError(Exception):
    """Base class for deterministic, caller-actionable transaction errors."""


class BoundsError(TransactionError):
    pass


class IdentityError(TransactionError):
    pass


class AmbiguousTargetError(IdentityError):
    pass


class InvalidPlanError(TransactionError):
    pass


class TransitionError(TransactionError):
    pass


class ConsentError(TransactionError):
    pass


class SecretLeakError(TransactionError):
    pass


class JournalIntegrityError(TransactionError):
    pass


class MutationError(TransactionError):
    pass


class RecoveryRequiredError(TransactionError):
    pass


class Phase(StrEnum):
    INVENTORY = "INVENTORY"
    ADMISSION = "ADMISSION"
    ACQUISITION = "ACQUISITION"
    PLAN_READY = "PLAN_READY"
    FINAL_CONSENT = "FINAL_CONSENT"
    MUTATION_STARTED = "MUTATION_STARTED"
    PROVISIONED = "PROVISIONED"
    BOOT_CONFIGURED = "BOOT_CONFIGURED"
    COMMITTED = "COMMITTED"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"
    ROLLED_BACK = "ROLLED_BACK"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class RestartDecision(StrEnum):
    RESUME_SAFE = "RESUME_SAFE"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    ALREADY_COMMITTED = "ALREADY_COMMITTED"
    RESTART_DENIED = "RESTART_DENIED"


class ActionKind(StrEnum):
    ACQUIRE_ARTIFACT = "ACQUIRE_ARTIFACT"
    PROVISION_VOLUME = "PROVISION_VOLUME"
    CONFIGURE_BOOT = "CONFIGURE_BOOT"
    VERIFY_RESULT = "VERIFY_RESULT"


class EventKind(StrEnum):
    PHASE = "PHASE"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    COMPENSATION_RECORDED = "COMPENSATION_RECORDED"
    FAILURE = "FAILURE"


class CompensationOutcome(StrEnum):
    REVERTED = "REVERTED"
    VERIFIED = "VERIFIED"


def _bounded_id(value: str, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise IdentityError(f"invalid {label}")
    return value


def _digest(value: str, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise InvalidPlanError(f"invalid {label} digest")
    return value


def _positive_size(value: int, label: str, maximum: int = MAX_ARTIFACT_BYTES) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0 or value > maximum:
        raise BoundsError(f"invalid {label} size")
    return value


def _check_safe(value: Any, location: str = "payload", depth: int = 0) -> None:
    """Reject values that could put credentials or host paths in the journal."""
    if depth > MAX_PAYLOAD_DEPTH:
        raise BoundsError(f"payload nesting exceeds bound at {location}")
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str) or _SECRET_KEY_RE.search(key):
                raise SecretLeakError(f"secret-like field in {location}")
            if len(key) > MAX_STRING_LENGTH:
                raise BoundsError(f"string exceeds bound at {location}.{key}")
            _check_safe(nested, f"{location}.{key}", depth + 1)
    elif isinstance(value, (list, tuple)):
        if len(value) > MAX_LIST_ITEMS:
            raise BoundsError(f"list exceeds bound at {location}")
        for index, nested in enumerate(value):
            _check_safe(nested, f"{location}[{index}]", depth + 1)
    elif isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise BoundsError(f"string exceeds bound at {location}")
        if _SECRET_VALUE_RE.search(value):
            raise SecretLeakError(f"secret-like value in {location}")
    elif value is not None and not isinstance(value, (int, bool)):
        raise JournalIntegrityError(f"non-canonical scalar at {location}")


def _canonical(value: Any) -> bytes:
    _check_safe(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise JournalIntegrityError("payload is not canonical JSON") from exc


@dataclass(frozen=True, slots=True)
class DiskIdentity:
    """Stable disk identity; paths and display names are intentionally absent."""

    stable_id: str
    size_bytes: int
    media_kind: str = "internal"

    def __post_init__(self) -> None:
        _bounded_id(self.stable_id, "disk identity")
        _positive_size(self.size_bytes, "disk")
        _bounded_id(self.media_kind, "media kind")


@dataclass(frozen=True, slots=True)
class ContainerIdentity:
    stable_id: str
    disk_id: str
    size_bytes: int

    def __post_init__(self) -> None:
        _bounded_id(self.stable_id, "container identity")
        _bounded_id(self.disk_id, "disk identity")
        _positive_size(self.size_bytes, "container")


@dataclass(frozen=True, slots=True)
class VolumeIdentity:
    stable_id: str
    container_id: str
    size_bytes: int

    def __post_init__(self) -> None:
        _bounded_id(self.stable_id, "volume identity")
        _bounded_id(self.container_id, "container identity")
        _positive_size(self.size_bytes, "volume")


@dataclass(frozen=True, slots=True)
class Artifact:
    artifact_id: str
    digest: str
    size_bytes: int

    def __post_init__(self) -> None:
        _bounded_id(self.artifact_id, "artifact id")
        _digest(self.digest, "artifact")
        _positive_size(self.size_bytes, "artifact")


@dataclass(frozen=True, slots=True)
class PlanStep:
    step_id: str
    action: ActionKind
    target_volume_id: str
    description: str = ""

    def __post_init__(self) -> None:
        _bounded_id(self.step_id, "step id")
        if not isinstance(self.action, ActionKind):
            raise InvalidPlanError("invalid action kind")
        _bounded_id(self.target_volume_id, "target volume identity")
        if not isinstance(self.description, str) or not self.description or len(self.description) > MAX_DESCRIPTION_LENGTH:
            raise BoundsError("invalid step description")
        _check_safe({"description": self.description})


@dataclass(frozen=True, slots=True)
class InstallerPlan:
    operation_id: str
    disk: DiskIdentity
    container: ContainerIdentity
    volume: VolumeIdentity
    artifact: Artifact
    document_digest: str
    steps: tuple[PlanStep, ...]

    def __post_init__(self) -> None:
        _bounded_id(self.operation_id, "operation id")
        if not isinstance(self.disk, DiskIdentity) or not isinstance(self.container, ContainerIdentity) or not isinstance(self.volume, VolumeIdentity) or not isinstance(self.artifact, Artifact):
            raise InvalidPlanError("plan identities have invalid types")
        if self.container.disk_id != self.disk.stable_id:
            raise InvalidPlanError("container is not on target disk")
        if self.volume.container_id != self.container.stable_id:
            raise InvalidPlanError("volume is not in target container")
        _digest(self.document_digest, "document")
        if not isinstance(self.steps, tuple) or not self.steps or len(self.steps) > MAX_ACTIONS:
            raise BoundsError("invalid action count")
        if any(not isinstance(step, PlanStep) for step in self.steps):
            raise InvalidPlanError("plan contains an invalid step")
        ids = [step.step_id for step in self.steps]
        if len(set(ids)) != len(ids):
            raise InvalidPlanError("duplicate step id")
        if any(step.target_volume_id != self.volume.stable_id for step in self.steps):
            raise InvalidPlanError("step target does not match plan volume")

    @property
    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "disk": {"stable_id": self.disk.stable_id, "size_bytes": self.disk.size_bytes, "media_kind": self.disk.media_kind},
            "container": {"stable_id": self.container.stable_id, "disk_id": self.container.disk_id, "size_bytes": self.container.size_bytes},
            "volume": {"stable_id": self.volume.stable_id, "container_id": self.volume.container_id, "size_bytes": self.volume.size_bytes},
            "artifact": {"artifact_id": self.artifact.artifact_id, "digest": self.artifact.digest, "size_bytes": self.artifact.size_bytes},
            "document_digest": self.document_digest,
            "steps": [{"step_id": s.step_id, "action": s.action.value, "target_volume_id": s.target_volume_id, "description": s.description} for s in self.steps],
        }


@dataclass(frozen=True, slots=True)
class Consent:
    operation_id: str
    plan_digest: str
    document_digest: str
    artifact_digest: str
    consent_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        _bounded_id(self.operation_id, "operation id")
        _bounded_id(self.consent_id, "consent id")
        _digest(self.plan_digest, "plan")
        _digest(self.document_digest, "document")
        _digest(self.artifact_digest, "artifact")


def resolve_single_target(candidates: tuple[DiskIdentity, ...] | list[DiskIdentity]) -> DiskIdentity:
    """Require exactly one inventory-selected disk; never select by name/path."""
    if not isinstance(candidates, (tuple, list)) or any(not isinstance(candidate, DiskIdentity) for candidate in candidates):
        raise IdentityError("invalid target inventory")
    if len(candidates) != 1:
        raise AmbiguousTargetError("target disk is not unique")
    return candidates[0]


def _validate_event_payload(event: EventKind, phase: Phase, payload: Mapping[str, Any]) -> None:
    required: dict[EventKind, frozenset[str]] = {
        EventKind.PHASE: frozenset(),
        EventKind.STEP_STARTED: frozenset({"step_id"}),
        EventKind.STEP_COMPLETED: frozenset({"step_id"}),
        EventKind.COMPENSATION_RECORDED: frozenset({"step_id", "action", "reason", "outcome"}),
        EventKind.FAILURE: frozenset({"code"}),
    }
    keys = frozenset(payload)
    if not keys.issuperset(required[event]) or not keys.issubset(required[event] | {"plan_digest", "document_digest", "artifact_digest", "consent_id", "code"}):
        raise JournalIntegrityError(f"invalid {event.value} payload keys")
    if event == EventKind.PHASE:
        phase_keys = {
            Phase.INVENTORY: frozenset({"plan_digest", "document_digest", "artifact_digest"}),
            Phase.MUTATION_STARTED: frozenset({"consent_id", "plan_digest", "document_digest", "artifact_digest"}),
            Phase.RECOVERY_REQUIRED: frozenset({"code"}),
        }.get(phase, frozenset())
        if keys != phase_keys:
            raise JournalIntegrityError("invalid phase payload keys")
    elif event in {EventKind.STEP_STARTED, EventKind.STEP_COMPLETED}:
        if keys != {"step_id"} or not isinstance(payload["step_id"], str):
            raise JournalIntegrityError("invalid step event payload")
    elif event == EventKind.COMPENSATION_RECORDED:
        if keys != {"step_id", "action", "reason", "outcome"}:
            raise JournalIntegrityError("invalid compensation payload")
        if not isinstance(payload["step_id"], str) or not isinstance(payload["action"], str) or not isinstance(payload["reason"], str) or not isinstance(payload["outcome"], str):
            raise JournalIntegrityError("invalid compensation payload types")
        try:
            ActionKind(payload["action"])
            CompensationOutcome(payload["outcome"])
        except ValueError as exc:
            raise JournalIntegrityError("invalid compensation vocabulary") from exc
        if not payload["reason"] or len(payload["reason"]) > MAX_DESCRIPTION_LENGTH:
            raise BoundsError("invalid compensation reason")
    elif event == EventKind.FAILURE:
        if keys != {"code"} or not isinstance(payload["code"], str):
            raise JournalIntegrityError("invalid failure payload")


@dataclass(frozen=True, slots=True)
class JournalEntry:
    sequence: int
    operation_id: str
    phase: Phase
    event: EventKind
    payload: Mapping[str, Any]
    previous_hash: str
    entry_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 0 or self.sequence >= MAX_JOURNAL_ENTRIES:
            raise JournalIntegrityError("invalid journal sequence")
        _bounded_id(self.operation_id, "operation id")
        if not isinstance(self.phase, Phase) or not isinstance(self.event, EventKind):
            raise JournalIntegrityError("invalid journal event")
        if not isinstance(self.payload, Mapping):
            raise JournalIntegrityError("event payload must be a mapping")
        safe_payload = dict(self.payload)
        _check_safe(safe_payload)
        _validate_event_payload(self.event, self.phase, safe_payload)
        object.__setattr__(self, "payload", MappingProxyType(safe_payload))
        if self.sequence == 0 and self.previous_hash != "":
            raise JournalIntegrityError("invalid journal genesis")
        if self.sequence > 0 and not _DIGEST_RE.fullmatch(self.previous_hash):
            raise JournalIntegrityError("invalid previous journal hash")
        if not _DIGEST_RE.fullmatch(self.entry_hash):
            raise JournalIntegrityError("invalid journal hash")

    @staticmethod
    def create(sequence: int, operation_id: str, phase: Phase, event: EventKind, payload: Mapping[str, Any], previous_hash: str) -> "JournalEntry":
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0 or sequence >= MAX_JOURNAL_ENTRIES:
            raise JournalIntegrityError("negative journal sequence")
        _bounded_id(operation_id, "operation id")
        if not isinstance(phase, Phase) or not isinstance(event, EventKind):
            raise JournalIntegrityError("invalid journal event")
        if not isinstance(payload, Mapping):
            raise JournalIntegrityError("event payload must be a mapping")
        safe_payload = dict(payload)
        _check_safe(safe_payload)
        _validate_event_payload(event, phase, safe_payload)
        encoded_payload = _canonical(safe_payload)
        if len(encoded_payload) > MAX_PAYLOAD_BYTES:
            raise BoundsError("journal payload exceeds bound")
        if sequence == 0 and previous_hash != "":
            raise JournalIntegrityError("invalid journal genesis")
        if sequence > 0 and not _DIGEST_RE.fullmatch(previous_hash):
            raise JournalIntegrityError("invalid previous journal hash")
        body = {"sequence": sequence, "operation_id": operation_id, "phase": phase.value, "event": event.value, "payload": safe_payload, "previous_hash": previous_hash}
        entry_hash = hashlib.sha256(_canonical(body)).hexdigest()
        return JournalEntry(sequence, operation_id, phase, event, MappingProxyType(safe_payload), previous_hash, entry_hash)

    def verify(self) -> None:
        expected = JournalEntry.create(self.sequence, self.operation_id, self.phase, self.event, self.payload, self.previous_hash)
        if expected.entry_hash != self.entry_hash:
            raise JournalIntegrityError(f"journal entry {self.sequence} hash mismatch")


@dataclass(frozen=True, slots=True)
class Journal:
    entries: tuple[JournalEntry, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple) or any(not isinstance(entry, JournalEntry) for entry in self.entries):
            raise JournalIntegrityError("journal entries have invalid types")
        if len(self.entries) > MAX_JOURNAL_ENTRIES:
            raise BoundsError("journal entry bound exceeded")
        previous = ""
        for expected_sequence, entry in enumerate(self.entries):
            if entry.sequence != expected_sequence or entry.previous_hash != previous:
                raise JournalIntegrityError("journal sequence or chain gap")
            entry.verify()
            previous = entry.entry_hash
        if self.entries:
            operation = self.entries[0].operation_id
            if any(entry.operation_id != operation for entry in self.entries):
                raise JournalIntegrityError("journal operation id changed")

    @property
    def last(self) -> JournalEntry:
        if not self.entries:
            raise JournalIntegrityError("empty journal")
        return self.entries[-1]

    def append(self, operation_id: str, phase: Phase, event: EventKind, payload: Mapping[str, Any] | None = None) -> "Journal":
        if self.entries and operation_id != self.last.operation_id:
            raise JournalIntegrityError("journal operation id changed")
        entry = JournalEntry.create(len(self.entries), operation_id, phase, event, {} if payload is None else payload, self.entries[-1].entry_hash if self.entries else "")
        return Journal(self.entries + (entry,))

    def verify(self) -> None:
        Journal(self.entries)

    def to_json(self) -> str:
        return json.dumps({"entries": [{"sequence": e.sequence, "operation_id": e.operation_id, "phase": e.phase.value, "event": e.event.value, "payload": dict(e.payload), "previous_hash": e.previous_hash, "entry_hash": e.entry_hash} for e in self.entries]}, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> "Journal":
        try:
            document = json.loads(value)
            if not isinstance(document, Mapping) or set(document) != {"entries"} or not isinstance(document["entries"], list):
                raise JournalIntegrityError("invalid journal document")
            entries = tuple(JournalEntry(item["sequence"], item["operation_id"], Phase(item["phase"]), EventKind(item["event"]), MappingProxyType(dict(item["payload"])), item["previous_hash"], item["entry_hash"]) for item in document["entries"])
            return cls(entries)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise JournalIntegrityError("invalid journal document") from exc


@dataclass(frozen=True, slots=True)
class JournalCheckpoint:
    """Trusted out-of-band journal anchor; it is never serialized in Journal."""

    operation_id: str
    plan_digest: str
    sequence: int
    head_hash: str

    def __post_init__(self) -> None:
        _bounded_id(self.operation_id, "operation id")
        _digest(self.plan_digest, "plan")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 0 or self.sequence >= MAX_JOURNAL_ENTRIES:
            raise JournalIntegrityError("invalid checkpoint sequence")
        if not _DIGEST_RE.fullmatch(self.head_hash):
            raise JournalIntegrityError("invalid checkpoint hash")

    @classmethod
    def for_journal(cls, operation_id: str, plan_digest: str, journal: Journal) -> "JournalCheckpoint":
        if not journal.entries:
            raise JournalIntegrityError("genesis checkpoint requires journal entry")
        if journal.last.operation_id != operation_id:
            raise JournalIntegrityError("checkpoint operation does not match journal")
        return cls(operation_id, plan_digest, journal.last.sequence, journal.last.entry_hash)


_ALLOWED: dict[Phase, frozenset[Phase]] = {
    Phase.INVENTORY: frozenset({Phase.ADMISSION}),
    Phase.ADMISSION: frozenset({Phase.ACQUISITION}),
    Phase.ACQUISITION: frozenset({Phase.PLAN_READY}),
    Phase.PLAN_READY: frozenset({Phase.FINAL_CONSENT}),
    Phase.FINAL_CONSENT: frozenset({Phase.MUTATION_STARTED}),
    Phase.MUTATION_STARTED: frozenset({Phase.PROVISIONED, Phase.ROLLBACK_REQUIRED}),
    Phase.PROVISIONED: frozenset({Phase.BOOT_CONFIGURED, Phase.ROLLBACK_REQUIRED}),
    Phase.BOOT_CONFIGURED: frozenset({Phase.COMMITTED, Phase.ROLLBACK_REQUIRED}),
    Phase.COMMITTED: frozenset(),
    Phase.ROLLBACK_REQUIRED: frozenset({Phase.ROLLED_BACK, Phase.RECOVERY_REQUIRED}),
    Phase.ROLLED_BACK: frozenset(),
    Phase.RECOVERY_REQUIRED: frozenset(),
}
ALLOWED_TRANSITIONS: Mapping[Phase, frozenset[Phase]] = MappingProxyType(_ALLOWED)


def allowed_transitions(phase: Phase) -> frozenset[Phase]:
    """Return the closed transition set for a phase."""
    if not isinstance(phase, Phase):
        raise TransitionError("invalid phase")
    return ALLOWED_TRANSITIONS[phase]


@dataclass(frozen=True, slots=True)
class InstallerTransaction:
    plan: InstallerPlan
    journal: Journal
    checkpoint: JournalCheckpoint

    @classmethod
    def start(cls, plan: InstallerPlan) -> Self:
        if not isinstance(plan, InstallerPlan):
            raise InvalidPlanError("transaction requires an installer plan")
        journal = Journal().append(plan.operation_id, Phase.INVENTORY, EventKind.PHASE, {"plan_digest": plan.digest, "document_digest": plan.document_digest, "artifact_digest": plan.artifact.digest})
        checkpoint = JournalCheckpoint.for_journal(plan.operation_id, plan.digest, journal)
        return cls(plan, journal, checkpoint)

    def __post_init__(self) -> None:
        self.journal.verify()
        if not isinstance(self.checkpoint, JournalCheckpoint):
            raise JournalIntegrityError("trusted checkpoint is required")
        if self.journal.last.operation_id != self.plan.operation_id:
            raise JournalIntegrityError("journal does not belong to plan")
        if self.checkpoint.operation_id != self.plan.operation_id or self.checkpoint.plan_digest != self.plan.digest:
            raise JournalIntegrityError("checkpoint does not belong to plan")
        if self.checkpoint.sequence != self.journal.last.sequence or self.checkpoint.head_hash != self.journal.last.entry_hash:
            raise JournalIntegrityError("journal does not match trusted checkpoint")
        first = self.journal.entries[0]
        if first.phase != Phase.INVENTORY or first.event != EventKind.PHASE or first.payload != {"plan_digest": self.plan.digest, "document_digest": self.plan.document_digest, "artifact_digest": self.plan.artifact.digest}:
            raise JournalIntegrityError("journal inventory does not match plan")
        current = Phase.INVENTORY
        step_ids = {step.step_id for step in self.plan.steps}
        started: set[str] = set()
        completed: set[str] = set()
        compensated: set[str] = set()
        for entry in self.journal.entries[1:]:
            if entry.event == EventKind.PHASE:
                if entry.phase not in _ALLOWED[current]:
                    raise JournalIntegrityError(f"journal skipped phase {current.value}->{entry.phase.value}")
                self._validate_phase_payload(entry)
                current = entry.phase
            else:
                if entry.phase != current:
                    raise JournalIntegrityError("event phase does not match derived state")
                if current not in {Phase.MUTATION_STARTED, Phase.PROVISIONED, Phase.BOOT_CONFIGURED, Phase.ROLLBACK_REQUIRED} and entry.event in {EventKind.STEP_STARTED, EventKind.STEP_COMPLETED, EventKind.COMPENSATION_RECORDED, EventKind.FAILURE}:
                    raise JournalIntegrityError("mutation event occurred before mutation phase")
                if entry.event in {EventKind.STEP_STARTED, EventKind.STEP_COMPLETED}:
                    if current not in {Phase.MUTATION_STARTED, Phase.PROVISIONED, Phase.BOOT_CONFIGURED} or entry.payload["step_id"] not in step_ids:
                        raise JournalIntegrityError("step event is outside the authorized plan")
                    step_id = entry.payload["step_id"]
                    if entry.event == EventKind.STEP_STARTED:
                        started.add(step_id)
                    elif step_id not in started:
                        raise JournalIntegrityError("step completed before start")
                    else:
                        completed.add(step_id)
                elif entry.event == EventKind.COMPENSATION_RECORDED:
                    step_id = entry.payload["step_id"]
                    if current != Phase.ROLLBACK_REQUIRED or step_id not in started or step_id in compensated:
                        raise JournalIntegrityError("invalid compensation coverage")
                    compensated.add(step_id)
                elif entry.event == EventKind.FAILURE and current not in {Phase.MUTATION_STARTED, Phase.PROVISIONED, Phase.BOOT_CONFIGURED}:
                    raise JournalIntegrityError("failure is not a mutation event")
        if current != self.journal.last.phase:
            raise JournalIntegrityError("journal state derivation mismatch")
        all_steps = step_ids
        if current in {Phase.PROVISIONED, Phase.BOOT_CONFIGURED, Phase.COMMITTED} and completed != all_steps:
            raise JournalIntegrityError("journal reports success before all steps completed")
        if current == Phase.ROLLED_BACK and not started.issubset(compensated):
            raise JournalIntegrityError("journal reports rollback with compensation gap")

    def _validate_phase_payload(self, entry: JournalEntry) -> None:
        expected: dict[str, Any] = {}
        if entry.phase == Phase.MUTATION_STARTED:
            expected = {"consent_id": entry.payload.get("consent_id"), "plan_digest": self.plan.digest, "document_digest": self.plan.document_digest, "artifact_digest": self.plan.artifact.digest}
            if not expected["consent_id"] or entry.payload != expected:
                raise JournalIntegrityError("mutation authorization is not bound to exact plan")
        elif entry.phase == Phase.RECOVERY_REQUIRED:
            if set(entry.payload) != {"code"} or not isinstance(entry.payload["code"], str):
                raise JournalIntegrityError("recovery phase requires a code")
        elif entry.payload:
            raise JournalIntegrityError("phase has forbidden payload keys")

    @property
    def phase(self) -> Phase:
        return self.journal.last.phase

    @property
    def status(self) -> str:
        return "success" if self.phase == Phase.COMMITTED else "in_progress" if self.phase not in {Phase.ROLLED_BACK, Phase.RECOVERY_REQUIRED} else "failed"

    @property
    def restart_decision(self) -> RestartDecision:
        if self.phase == Phase.COMMITTED:
            return RestartDecision.ALREADY_COMMITTED
        if self.phase == Phase.ROLLBACK_REQUIRED:
            return RestartDecision.ROLLBACK_REQUIRED
        if self.phase == Phase.RECOVERY_REQUIRED:
            return RestartDecision.RECOVERY_REQUIRED
        if self.phase == Phase.ROLLED_BACK:
            return RestartDecision.RESTART_DENIED
        return RestartDecision.RESUME_SAFE

    def _transition(self, phase: Phase, payload: Mapping[str, Any] | None = None) -> Self:
        if phase not in _ALLOWED[self.phase]:
            raise TransitionError(f"invalid transition {self.phase.value}->{phase.value}")
        journal = self.journal.append(self.plan.operation_id, phase, EventKind.PHASE, payload or {})
        return type(self)(self.plan, journal, JournalCheckpoint.for_journal(self.plan.operation_id, self.plan.digest, journal))

    def advance(self, phase: Phase, consent: Consent | None = None) -> Self:
        if phase == Phase.MUTATION_STARTED:
            if self.phase != Phase.FINAL_CONSENT:
                raise TransitionError(f"invalid transition {self.phase.value}->{phase.value}")
            self._validate_consent(consent)
            return self._transition(phase, {"consent_id": consent.consent_id, "plan_digest": self.plan.digest, "document_digest": self.plan.document_digest, "artifact_digest": self.plan.artifact.digest})
        # Validate the phase edge first, so skipped phases always have the
        # same deterministic transition error even when other guards fail.
        if phase not in _ALLOWED[self.phase]:
            raise TransitionError(f"invalid transition {self.phase.value}->{phase.value}")
        if phase == Phase.PROVISIONED and not self._all_steps_completed:
            raise MutationError("cannot provision before all mutation steps complete")
        if phase == Phase.COMMITTED and not self._all_steps_completed:
            raise MutationError("cannot commit before all mutation steps complete")
        return self._transition(phase)

    def _validate_consent(self, consent: Consent | None) -> None:
        if consent is None:
            raise ConsentError("final consent is required before mutation")
        if (consent.operation_id, consent.plan_digest, consent.document_digest, consent.artifact_digest) != (self.plan.operation_id, self.plan.digest, self.plan.document_digest, self.plan.artifact.digest):
            raise ConsentError("consent does not match exact plan")

    @property
    def _step_events(self) -> tuple[JournalEntry, ...]:
        return tuple(e for e in self.journal.entries if e.event in {EventKind.STEP_STARTED, EventKind.STEP_COMPLETED})

    @property
    def _started_steps(self) -> frozenset[str]:
        return frozenset(str(e.payload["step_id"]) for e in self._step_events if e.event == EventKind.STEP_STARTED)

    @property
    def _completed_steps(self) -> frozenset[str]:
        return frozenset(str(e.payload["step_id"]) for e in self._step_events if e.event == EventKind.STEP_COMPLETED)

    @property
    def _all_steps_completed(self) -> bool:
        return self._completed_steps == frozenset(step.step_id for step in self.plan.steps)

    def record_step_started(self, step_id: str) -> Self:
        self._require_mutation_phase()
        self._require_step(step_id)
        if step_id in self._started_steps:
            return self
        journal = self.journal.append(self.plan.operation_id, self.phase, EventKind.STEP_STARTED, {"step_id": step_id})
        return type(self)(self.plan, journal, JournalCheckpoint.for_journal(self.plan.operation_id, self.plan.digest, journal))

    def record_step_completed(self, step_id: str) -> Self:
        self._require_mutation_phase()
        self._require_step(step_id)
        if step_id not in self._started_steps:
            raise MutationError("cannot complete a step that was not started")
        if step_id in self._completed_steps:
            return self
        journal = self.journal.append(self.plan.operation_id, self.phase, EventKind.STEP_COMPLETED, {"step_id": step_id})
        return type(self)(self.plan, journal, JournalCheckpoint.for_journal(self.plan.operation_id, self.plan.digest, journal))

    def record_compensation(self, step_id: str, action: ActionKind, reason: str) -> Self:
        if self.phase != Phase.ROLLBACK_REQUIRED:
            raise TransitionError("compensation requires rollback")
        self._require_step(step_id)
        if not isinstance(action, ActionKind) or not isinstance(reason, str) or not reason or len(reason) > MAX_DESCRIPTION_LENGTH:
            raise BoundsError("invalid compensation record")
        _check_safe({"reason": reason})
        if step_id not in self._started_steps:
            raise MutationError("compensation requires a started mutation step")
        if step_id in self._compensated_steps:
            raise MutationError("duplicate compensation record")
        journal = self.journal.append(self.plan.operation_id, self.phase, EventKind.COMPENSATION_RECORDED, {"step_id": step_id, "action": action.value, "reason": reason, "outcome": CompensationOutcome.REVERTED.value})
        return type(self)(self.plan, journal, JournalCheckpoint.for_journal(self.plan.operation_id, self.plan.digest, journal))

    @property
    def _compensated_steps(self) -> frozenset[str]:
        return frozenset(str(e.payload["step_id"]) for e in self.journal.entries if e.event == EventKind.COMPENSATION_RECORDED)

    def fail_after_mutation(self, code: str) -> Self:
        self._require_mutation_phase()
        if not isinstance(code, str) or not _ID_RE.fullmatch(code):
            raise BoundsError("invalid failure code")
        journal = self.journal.append(self.plan.operation_id, self.phase, EventKind.FAILURE, {"code": code})
        journal = journal.append(self.plan.operation_id, Phase.ROLLBACK_REQUIRED, EventKind.PHASE, {})
        return type(self)(self.plan, journal, JournalCheckpoint.for_journal(self.plan.operation_id, self.plan.digest, journal))

    def mark_rolled_back(self) -> Self:
        if self.phase != Phase.ROLLBACK_REQUIRED:
            raise TransitionError("rollback is not required")
        if not self._started_steps.issubset(self._compensated_steps):
            raise RecoveryRequiredError("rollback compensation gap")
        return self._transition(Phase.ROLLED_BACK)

    def require_recovery(self, code: str) -> Self:
        if self.phase != Phase.ROLLBACK_REQUIRED:
            raise TransitionError("recovery requires rollback state")
        if not isinstance(code, str) or not _ID_RE.fullmatch(code):
            raise BoundsError("invalid recovery code")
        return self._transition(Phase.RECOVERY_REQUIRED, {"code": code})

    def resume(self, journal: Journal, checkpoint: JournalCheckpoint) -> Self:
        """Re-open a persisted journal only when it is for this exact plan."""
        resumed = type(self)(self.plan, journal, checkpoint)
        if resumed.phase == Phase.COMMITTED:
            return resumed
        if resumed.restart_decision == RestartDecision.ROLLBACK_REQUIRED:
            raise RecoveryRequiredError("resume requires rollback")
        if resumed.restart_decision == RestartDecision.RECOVERY_REQUIRED:
            raise RecoveryRequiredError("resume requires operator recovery")
        return resumed

    def _require_mutation_phase(self) -> None:
        if self.phase not in {Phase.MUTATION_STARTED, Phase.PROVISIONED, Phase.BOOT_CONFIGURED}:
            raise MutationError("mutation is not authorized in this phase")

    def _require_step(self, step_id: str) -> None:
        if step_id not in {step.step_id for step in self.plan.steps}:
            raise MutationError("unknown plan step")

    def report_success(self) -> Mapping[str, str]:
        if self.phase != Phase.COMMITTED:
            raise MutationError("transaction has not committed")
        return MappingProxyType({"operation_id": self.plan.operation_id, "status": "success", "plan_digest": self.plan.digest})


# Friendly aliases for consumers that use the shorter terminology.
Plan = InstallerPlan
Transaction = InstallerTransaction
StableDiskIdentity = DiskIdentity
StableContainerIdentity = ContainerIdentity
StableVolumeIdentity = VolumeIdentity

__all__ = [
    "ALLOWED_TRANSITIONS", "ActionKind", "AmbiguousTargetError", "Artifact", "BoundsError", "CompensationOutcome", "Consent", "ConsentError", "ContainerIdentity", "DiskIdentity", "EventKind", "IdentityError", "InstallerPlan", "InstallerTransaction", "Journal", "JournalCheckpoint", "JournalEntry", "JournalIntegrityError", "MutationError", "Phase", "Plan", "PlanStep", "RecoveryRequiredError", "RestartDecision", "SecretLeakError", "StableContainerIdentity", "StableDiskIdentity", "StableVolumeIdentity", "Transaction", "TransactionError", "TransitionError", "VolumeIdentity", "allowed_transitions", "resolve_single_target",
]
