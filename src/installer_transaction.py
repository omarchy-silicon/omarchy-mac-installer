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


class _Event(StrEnum):
    PHASE = "PHASE"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    COMPENSATION_RECORDED = "COMPENSATION_RECORDED"
    FAILURE = "FAILURE"


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


def _check_safe(value: Any, location: str = "payload") -> None:
    """Reject values that could put credentials or host paths in the journal."""
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str) or _SECRET_KEY_RE.search(key):
                raise SecretLeakError(f"secret-like field in {location}")
            _check_safe(nested, f"{location}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _check_safe(nested, f"{location}[{index}]")
    elif isinstance(value, str) and _SECRET_VALUE_RE.search(value):
        raise SecretLeakError(f"secret-like value in {location}")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise SecretLeakError(f"non-serializable value in {location}")


def _canonical(value: Any) -> bytes:
    _check_safe(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
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
        if self.container.disk_id != self.disk.stable_id:
            raise InvalidPlanError("container is not on target disk")
        if self.volume.container_id != self.container.stable_id:
            raise InvalidPlanError("volume is not in target container")
        _digest(self.document_digest, "document")
        if not isinstance(self.steps, tuple) or not self.steps or len(self.steps) > MAX_ACTIONS:
            raise BoundsError("invalid action count")
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
    if len(candidates) != 1:
        raise AmbiguousTargetError("target disk is not unique")
    return candidates[0]


@dataclass(frozen=True, slots=True)
class JournalEntry:
    sequence: int
    operation_id: str
    phase: Phase
    event: str
    payload: Mapping[str, Any]
    previous_hash: str
    entry_hash: str

    @staticmethod
    def create(sequence: int, operation_id: str, phase: Phase, event: str, payload: Mapping[str, Any], previous_hash: str) -> "JournalEntry":
        if sequence < 0:
            raise JournalIntegrityError("negative journal sequence")
        _bounded_id(operation_id, "operation id")
        if not isinstance(phase, Phase) or not isinstance(event, str) or not _ID_RE.fullmatch(event):
            raise JournalIntegrityError("invalid journal event")
        safe_payload = dict(payload)
        encoded_payload = _canonical(safe_payload)
        if len(encoded_payload) > MAX_PAYLOAD_BYTES:
            raise BoundsError("journal payload exceeds bound")
        if sequence == 0 and previous_hash != "":
            raise JournalIntegrityError("invalid journal genesis")
        if sequence > 0 and not _DIGEST_RE.fullmatch(previous_hash):
            raise JournalIntegrityError("invalid previous journal hash")
        body = {"sequence": sequence, "operation_id": operation_id, "phase": phase.value, "event": event, "payload": safe_payload, "previous_hash": previous_hash}
        entry_hash = hashlib.sha256(_canonical(body)).hexdigest()
        return JournalEntry(sequence, operation_id, phase, event, MappingProxyType(safe_payload), previous_hash, entry_hash)

    def verify(self) -> None:
        expected = JournalEntry.create(self.sequence, self.operation_id, self.phase, self.event, self.payload, self.previous_hash)
        if expected.entry_hash != self.entry_hash:
            raise JournalIntegrityError(f"journal entry {self.sequence} hash mismatch")


@dataclass(frozen=True, slots=True)
class Journal:
    entries: tuple[JournalEntry, ...] = ()
    # The tail hash is an append-only checkpoint.  A persisted journal must
    # retain it; this makes truncation detectable in addition to chain checks.
    anchor_hash: str = ""

    def __post_init__(self) -> None:
        if len(self.entries) > MAX_JOURNAL_ENTRIES:
            raise BoundsError("journal entry bound exceeded")
        if self.entries and (not _DIGEST_RE.fullmatch(self.anchor_hash) or self.anchor_hash != self.entries[-1].entry_hash):
            raise JournalIntegrityError("journal tail anchor mismatch")
        if not self.entries and self.anchor_hash:
            raise JournalIntegrityError("empty journal has a tail anchor")
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

    def append(self, operation_id: str, phase: Phase, event: str, payload: Mapping[str, Any] | None = None) -> "Journal":
        if self.entries and operation_id != self.last.operation_id:
            raise JournalIntegrityError("journal operation id changed")
        entry = JournalEntry.create(len(self.entries), operation_id, phase, event, payload or {}, self.entries[-1].entry_hash if self.entries else "")
        return Journal(self.entries + (entry,), entry.entry_hash)

    def verify(self) -> None:
        Journal(self.entries, self.anchor_hash)

    def to_json(self) -> str:
        return json.dumps({"anchor_hash": self.anchor_hash, "entries": [{"sequence": e.sequence, "operation_id": e.operation_id, "phase": e.phase.value, "event": e.event, "payload": dict(e.payload), "previous_hash": e.previous_hash, "entry_hash": e.entry_hash} for e in self.entries]}, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> "Journal":
        try:
            document = json.loads(value)
            entries = tuple(JournalEntry(int(item["sequence"]), item["operation_id"], Phase(item["phase"],), item["event"], MappingProxyType(dict(item["payload"])), item["previous_hash"], item["entry_hash"]) for item in document["entries"])
            return cls(entries, document["anchor_hash"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise JournalIntegrityError("invalid journal document") from exc


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

    @classmethod
    def start(cls, plan: InstallerPlan) -> Self:
        journal = Journal().append(plan.operation_id, Phase.INVENTORY, _Event.PHASE.value, {"plan_digest": plan.digest, "document_digest": plan.document_digest, "artifact_digest": plan.artifact.digest})
        return cls(plan, journal)

    def __post_init__(self) -> None:
        self.journal.verify()
        if self.journal.last.operation_id != self.plan.operation_id:
            raise JournalIntegrityError("journal does not belong to plan")
        first = self.journal.entries[0]
        if first.phase != Phase.INVENTORY or first.payload.get("plan_digest") != self.plan.digest:
            raise JournalIntegrityError("journal inventory does not match plan")
        current = Phase.INVENTORY
        for entry in self.journal.entries[1:]:
            if entry.phase != current:
                if entry.phase not in _ALLOWED[current]:
                    raise JournalIntegrityError(f"journal skipped phase {current.value}->{entry.phase.value}")
                if entry.event not in {_Event.PHASE.value, _Event.FAILURE.value}:
                    raise JournalIntegrityError("phase change is missing a phase event")
                current = entry.phase
            elif entry.event == _Event.PHASE.value:
                raise JournalIntegrityError("duplicate phase event")
            if entry.phase == Phase.MUTATION_STARTED and entry.event == _Event.PHASE.value:
                expected = {
                    "plan_digest": self.plan.digest,
                    "document_digest": self.plan.document_digest,
                    "artifact_digest": self.plan.artifact.digest,
                }
                if any(entry.payload.get(key) != value for key, value in expected.items()) or not entry.payload.get("consent_id"):
                    raise JournalIntegrityError("mutation authorization is not bound to exact plan")

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
        journal = self.journal.append(self.plan.operation_id, phase, _Event.PHASE.value, payload or {})
        return type(self)(self.plan, journal)

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
        return tuple(e for e in self.journal.entries if e.event in {_Event.STEP_STARTED.value, _Event.STEP_COMPLETED.value})

    @property
    def _started_steps(self) -> frozenset[str]:
        return frozenset(str(e.payload["step_id"]) for e in self._step_events if e.event == _Event.STEP_STARTED.value)

    @property
    def _completed_steps(self) -> frozenset[str]:
        return frozenset(str(e.payload["step_id"]) for e in self._step_events if e.event == _Event.STEP_COMPLETED.value)

    @property
    def _all_steps_completed(self) -> bool:
        return self._completed_steps == frozenset(step.step_id for step in self.plan.steps)

    def record_step_started(self, step_id: str) -> Self:
        self._require_mutation_phase()
        self._require_step(step_id)
        if step_id in self._started_steps:
            return self
        journal = self.journal.append(self.plan.operation_id, self.phase, _Event.STEP_STARTED.value, {"step_id": step_id})
        return type(self)(self.plan, journal)

    def record_step_completed(self, step_id: str) -> Self:
        self._require_mutation_phase()
        self._require_step(step_id)
        if step_id not in self._started_steps:
            raise MutationError("cannot complete a step that was not started")
        if step_id in self._completed_steps:
            return self
        journal = self.journal.append(self.plan.operation_id, self.phase, _Event.STEP_COMPLETED.value, {"step_id": step_id})
        return type(self)(self.plan, journal)

    def record_compensation(self, step_id: str, action: ActionKind, reason: str) -> Self:
        if self.phase != Phase.ROLLBACK_REQUIRED:
            raise TransitionError("compensation requires rollback")
        self._require_step(step_id)
        if not isinstance(action, ActionKind) or not isinstance(reason, str) or not reason or len(reason) > MAX_DESCRIPTION_LENGTH:
            raise BoundsError("invalid compensation record")
        _check_safe({"reason": reason})
        if step_id in self._compensated_steps:
            return self
        journal = self.journal.append(self.plan.operation_id, self.phase, _Event.COMPENSATION_RECORDED.value, {"step_id": step_id, "action": action.value, "reason": reason})
        return type(self)(self.plan, journal)

    @property
    def _compensated_steps(self) -> frozenset[str]:
        return frozenset(str(e.payload["step_id"]) for e in self.journal.entries if e.event == _Event.COMPENSATION_RECORDED.value)

    def fail_after_mutation(self, code: str) -> Self:
        self._require_mutation_phase()
        if not isinstance(code, str) or not _ID_RE.fullmatch(code):
            raise BoundsError("invalid failure code")
        journal = self.journal.append(self.plan.operation_id, Phase.ROLLBACK_REQUIRED, _Event.FAILURE.value, {"code": code})
        return type(self)(self.plan, journal)

    def mark_rolled_back(self) -> Self:
        if self.phase != Phase.ROLLBACK_REQUIRED:
            raise TransitionError("rollback is not required")
        if not self._completed_steps.issubset(self._compensated_steps):
            raise RecoveryRequiredError("rollback compensation gap")
        return self._transition(Phase.ROLLED_BACK)

    def require_recovery(self, code: str) -> Self:
        if self.phase != Phase.ROLLBACK_REQUIRED:
            raise TransitionError("recovery requires rollback state")
        if not isinstance(code, str) or not _ID_RE.fullmatch(code):
            raise BoundsError("invalid recovery code")
        return self._transition(Phase.RECOVERY_REQUIRED, {"code": code})

    def resume(self, journal: Journal) -> Self:
        """Re-open a persisted journal only when it is for this exact plan."""
        resumed = type(self)(self.plan, journal)
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
    "ALLOWED_TRANSITIONS", "ActionKind", "AmbiguousTargetError", "Artifact", "BoundsError", "Consent", "ConsentError", "ContainerIdentity", "DiskIdentity", "IdentityError", "InstallerPlan", "InstallerTransaction", "Journal", "JournalEntry", "JournalIntegrityError", "MutationError", "Phase", "Plan", "PlanStep", "RecoveryRequiredError", "RestartDecision", "SecretLeakError", "StableContainerIdentity", "StableDiskIdentity", "StableVolumeIdentity", "Transaction", "TransactionError", "TransitionError", "VolumeIdentity", "allowed_transitions", "resolve_single_target",
]
