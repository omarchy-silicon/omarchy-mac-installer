"""Pure, non-secret credential facts for the installer planning boundary.

This module intentionally has no platform, process, network, filesystem, or
privilege integration.  Apple-owned authorization surfaces may return an
opaque receipt identifier; the installer can bind and consume that receipt,
but never receives a password, key, token, or credential value.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
import threading
import uuid
from typing import Any, Mapping, Self


MAX_IDENTIFIER_LENGTH = 128
MAX_RECEIPTS = 16
MAX_BLOCKERS = 32
MAX_SERIALIZED_BYTES = 16 * 1024
MAX_TIME = 2**63 - 1

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+=-]{0,127}$")
_SECRET_FIELD = re.compile(
    r"(?:pass(?:word)?|secret|token|credential|private.?key|recovery.?key|"
    r"authorization|cookie|api.?key|secure.?enclave|environment)",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(?:\bbearer\s+|\bsk-[A-Za-z0-9]|-----BEGIN .* PRIVATE KEY-----|"
    r"(?:password|passphrase|recovery[_ -]?key|token|secret)\s*[:=]|"
    r"\bcredential\s*[:=])",
    re.IGNORECASE,
)


class CredentialStateError(Exception):
    """Base class for deterministic, fail-closed credential errors."""


class CredentialBoundsError(CredentialStateError):
    pass


class CredentialTypeError(CredentialStateError):
    pass


class CredentialBindingError(CredentialStateError):
    pass


class CredentialDependencyError(CredentialStateError):
    pass


class CredentialReceiptError(CredentialStateError):
    pass


class CredentialSecretError(CredentialStateError):
    pass


class CredentialSerializationError(CredentialStateError):
    pass


class CredentialReadinessError(CredentialStateError):
    pass


class ReadinessExpiredError(CredentialReadinessError):
    pass


class ReadinessAlreadyConsumedError(CredentialReadinessError):
    pass


class ReadinessAuthorityStateError(CredentialReadinessError):
    pass


class FileVaultState(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class DataVolumeLockState(StrEnum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class MacOSAdministratorState(StrEnum):
    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not_authorized"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class MachineOwnerState(StrEnum):
    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not_authorized"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class LinuxEncryptionState(StrEnum):
    NOT_SELECTED = "not_selected"
    CONFIGURED = "configured"
    VERIFIED = "verified"
    CLEARED = "cleared"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"

    def advance_to(self, target: "LinuxEncryptionState") -> "LinuxEncryptionState":
        if not isinstance(target, LinuxEncryptionState):
            raise CredentialTypeError("invalid Linux encryption transition target")
        allowed = {
            LinuxEncryptionState.NOT_SELECTED: frozenset({LinuxEncryptionState.CONFIGURED}),
            LinuxEncryptionState.CONFIGURED: frozenset({LinuxEncryptionState.VERIFIED}),
            LinuxEncryptionState.VERIFIED: frozenset({LinuxEncryptionState.CLEARED}),
            LinuxEncryptionState.CLEARED: frozenset(),
            LinuxEncryptionState.UNKNOWN: frozenset(),
            LinuxEncryptionState.UNAVAILABLE: frozenset(),
        }
        if target not in allowed[self]:
            raise CredentialDependencyError(
                f"invalid Linux encryption transition {self.value}->{target.value}"
            )
        return target


class PairedRecoveryOSState(StrEnum):
    PAIRED = "paired"
    NOT_PAIRED = "not_paired"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class OneTRState(StrEnum):
    READY = "ready"
    NOT_READY = "not_ready"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"


class AuthorizationKind(StrEnum):
    FILEVAULT = "filevault"
    DATA_VOLUME = "data_volume"
    MACOS_ADMINISTRATOR = "macos_administrator"
    MACHINE_OWNER = "machine_owner"
    LINUX_ENCRYPTION = "linux_encryption"
    PAIRED_RECOVERY_OS = "paired_recovery_os"
    ONE_TRUE_RECOVERY = "one_true_recovery"

    # Short names are aliases, not new credential kinds.
    MACOS_ADMIN = "macos_administrator"
    RECOVERY_OS = "paired_recovery_os"
    ONE_TR = "one_true_recovery"


class ReadinessBlocker(StrEnum):
    FILEVAULT_UNKNOWN = "filevault_unknown"
    DATA_VOLUME_NOT_UNLOCKED = "data_volume_not_unlocked"
    ADMINISTRATOR_NOT_AUTHORIZED = "administrator_not_authorized"
    MACHINE_OWNER_NOT_AUTHORIZED = "machine_owner_not_authorized"
    LINUX_ENCRYPTION_NOT_VERIFIED = "linux_encryption_not_verified"
    RECOVERY_OS_NOT_PAIRED = "recovery_os_not_paired"
    ONE_TR_NOT_READY = "one_tr_not_ready"
    DEPENDENCY_ORDER_INVALID = "dependency_order_invalid"
    RECEIPT_MISSING = "authorization_receipt_missing"
    RECEIPT_INVALID = "authorization_receipt_invalid"
    RECEIPT_REUSED = "authorization_receipt_reused"


CROSS_PROCESS_PERSISTENCE_RESIDUAL = "durable_cross_process_cas_not_implemented"


REQUIRED_STATE_ORDER: tuple[str, ...] = (
    "filevault",
    "data_volume",
    "macos_administrator",
    "machine_owner",
    "linux_encryption",
    "paired_recovery_os",
    "one_true_recovery",
)


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise CredentialTypeError(f"invalid {label}")
    return value


def _digest(value: Any, label: str) -> str:
    if type(value) is not str or not _DIGEST.fullmatch(value):
        raise CredentialTypeError(f"invalid {label} digest")
    return value


def _opaque(value: Any, label: str) -> str:
    if type(value) is not str or not _OPAQUE_ID.fullmatch(value):
        raise CredentialTypeError(f"invalid opaque {label}")
    if _SECRET_VALUE.search(value):
        raise CredentialSecretError(f"secret-like opaque {label}")
    return value


def _strict_time(value: Any, label: str) -> int:
    if type(value) is not int or value < 0 or value > MAX_TIME:
        raise CredentialTypeError(f"invalid {label} timestamp")
    return value


def _enum(value: Any, expected: type[StrEnum], label: str) -> StrEnum:
    if not isinstance(value, expected):
        raise CredentialTypeError(f"invalid {label} state")
    return value


def _safe(value: Any, location: str = "$") -> None:
    """Reject secret-looking mappings and unsupported JSON values."""
    if isinstance(value, Mapping):
        if len(value) > MAX_RECEIPTS:
            raise CredentialBoundsError(f"mapping exceeds bound at {location}")
        for key, nested in value.items():
            if type(key) is not str:
                raise CredentialSerializationError(f"non-string field at {location}")
            if _SECRET_FIELD.search(key):
                raise CredentialSecretError(f"secret-like field at {location}.{key}")
            if len(key) > MAX_IDENTIFIER_LENGTH:
                raise CredentialBoundsError(f"field exceeds bound at {location}")
            _safe(nested, f"{location}.{key}")
    elif isinstance(value, (list, tuple)):
        if len(value) > MAX_RECEIPTS:
            raise CredentialBoundsError(f"list exceeds bound at {location}")
        for index, nested in enumerate(value):
            _safe(nested, f"{location}[{index}]")
    elif type(value) is str:
        if len(value) > MAX_IDENTIFIER_LENGTH:
            raise CredentialBoundsError(f"string exceeds bound at {location}")
        if _SECRET_VALUE.search(value):
            raise CredentialSecretError(f"secret-like value at {location}")
    elif value is None or type(value) is bool or type(value) is int:
        return
    else:
        raise CredentialSerializationError(f"unsupported value at {location}")


def canonical_bytes(value: Any) -> bytes:
    """Return bounded canonical JSON bytes, with no secret-bearing input."""
    _safe(value)
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CredentialSerializationError("value is not canonical JSON") from exc
    if len(encoded) > MAX_SERIALIZED_BYTES:
        raise CredentialBoundsError("canonical representation exceeds bound")
    return encoded


def canonical_json(value: Any) -> str:
    return canonical_bytes(value).decode("ascii")


def _domain_digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class AuthorizationReceipt:
    """An opaque, one-use result from an Apple-owned authorization surface."""

    kind: AuthorizationKind
    machine_id: str
    board_id: str
    plan_digest: str
    issued_at: int
    expires_at: int
    receipt_id: str

    def __post_init__(self) -> None:
        _enum(self.kind, AuthorizationKind, "authorization kind")
        _identifier(self.machine_id, "machine identity")
        _identifier(self.board_id, "board identity")
        _digest(self.plan_digest, "plan")
        _strict_time(self.issued_at, "issued")
        _strict_time(self.expires_at, "expiry")
        if self.expires_at <= self.issued_at:
            raise CredentialBoundsError("authorization receipt expiry must follow issue time")
        if self.expires_at - self.issued_at > 3600:
            raise CredentialBoundsError("authorization receipt lifetime exceeds bound")
        _opaque(self.receipt_id, "receipt id")

    @classmethod
    def issue(
        cls,
        kind: AuthorizationKind,
        machine_id: str,
        board_id: str,
        plan_digest: str,
        issued_at: int,
        expires_at: int,
        receipt_id: str,
    ) -> Self:
        return cls(kind, machine_id, board_id, plan_digest, issued_at, expires_at, receipt_id)

    def validate(
        self,
        kind: AuthorizationKind,
        machine_id: str,
        board_id: str,
        plan_digest: str,
        now: int,
    ) -> None:
        if not isinstance(kind, AuthorizationKind):
            raise CredentialTypeError("invalid expected authorization kind")
        if kind is not self.kind:
            raise CredentialBindingError("authorization receipt kind mismatch")
        if (machine_id, board_id, plan_digest) != (self.machine_id, self.board_id, self.plan_digest):
            raise CredentialBindingError("authorization receipt binding mismatch")
        _strict_time(now, "current")
        if now < self.issued_at or now >= self.expires_at:
            raise CredentialReceiptError("authorization receipt is expired or not yet valid")

    def to_dict(self) -> dict[str, Any]:
        """Serialize only the non-secret receipt envelope; never its opaque handle."""
        return {
            "kind": self.kind.value,
            "machine_id": self.machine_id,
            "board_id": self.board_id,
            "plan_digest": self.plan_digest,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "receipt_digest": _domain_digest("omarchy-credential-receipt/v1", {
                "kind": self.kind.value,
                "machine_id": self.machine_id,
                "board_id": self.board_id,
                "plan_digest": self.plan_digest,
                "issued_at": self.issued_at,
                "expires_at": self.expires_at,
                "receipt_id": self.receipt_id,
            }),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    def __repr__(self) -> str:
        return (
            f"AuthorizationReceipt(kind={self.kind.value!r}, machine_id={self.machine_id!r}, "
            f"board_id={self.board_id!r}, plan_digest={self.plan_digest!r}, "
            f"issued_at={self.issued_at}, expires_at={self.expires_at}, receipt_id=<opaque>)"
        )


@dataclass(frozen=True, slots=True)
class ReceiptLedger:
    """Immutable one-use receipt ledger; a consumer stores only receipt IDs."""

    consumed_receipt_ids: frozenset[str] = frozenset()
    checkpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        if not isinstance(self.consumed_receipt_ids, frozenset):
            raise CredentialTypeError("receipt ledger must be a frozenset")
        if len(self.consumed_receipt_ids) > MAX_RECEIPTS:
            raise CredentialBoundsError("receipt ledger exceeds bound")
        _opaque(self.checkpoint_id, "ledger checkpoint id")
        for receipt_id in self.consumed_receipt_ids:
            _opaque(receipt_id, "receipt id")

    def consume(
        self,
        receipt: AuthorizationReceipt,
        kind: AuthorizationKind,
        machine_id: str,
        board_id: str,
        plan_digest: str,
        now: int,
    ) -> Self:
        if not isinstance(receipt, AuthorizationReceipt):
            raise CredentialTypeError("authorization receipt is required")
        receipt.validate(kind, machine_id, board_id, plan_digest, now)
        if receipt.receipt_id in self.consumed_receipt_ids:
            raise CredentialReceiptError("authorization receipt was already consumed")
        return type(self)(self.consumed_receipt_ids | {receipt.receipt_id}, self.checkpoint_id)


@dataclass(frozen=True, slots=True)
class CredentialState:
    """All seven independent, closed credential facts for one exact plan."""

    machine_id: str
    board_id: str
    plan_digest: str
    filevault: FileVaultState
    data_volume: DataVolumeLockState
    macos_administrator: MacOSAdministratorState
    machine_owner: MachineOwnerState
    linux_encryption: LinuxEncryptionState
    paired_recovery_os: PairedRecoveryOSState
    one_true_recovery: OneTRState
    authorization_receipts: tuple[AuthorizationReceipt, ...] = ()

    def __post_init__(self) -> None:
        _identifier(self.machine_id, "machine identity")
        _identifier(self.board_id, "board identity")
        _digest(self.plan_digest, "plan")
        _enum(self.filevault, FileVaultState, "FileVault")
        _enum(self.data_volume, DataVolumeLockState, "Data-volume lock")
        _enum(self.macos_administrator, MacOSAdministratorState, "macOS administrator")
        _enum(self.machine_owner, MachineOwnerState, "machine owner")
        _enum(self.linux_encryption, LinuxEncryptionState, "Linux encryption")
        _enum(self.paired_recovery_os, PairedRecoveryOSState, "paired RecoveryOS")
        _enum(self.one_true_recovery, OneTRState, "1TR")
        if not isinstance(self.authorization_receipts, tuple):
            raise CredentialTypeError("authorization receipts must be a tuple")
        if len(self.authorization_receipts) > MAX_RECEIPTS:
            raise CredentialBoundsError("authorization receipt count exceeds bound")
        seen: set[AuthorizationKind] = set()
        for receipt in self.authorization_receipts:
            if not isinstance(receipt, AuthorizationReceipt):
                raise CredentialTypeError("invalid authorization receipt")
            if receipt.kind in seen:
                raise CredentialBindingError("duplicate receipt kind")
            if (receipt.machine_id, receipt.board_id, receipt.plan_digest) != (self.machine_id, self.board_id, self.plan_digest):
                raise CredentialBindingError("receipt is not bound to credential state")
            seen.add(receipt.kind)

    @property
    def digest(self) -> str:
        return _domain_digest("omarchy-credential-state/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "credential-state/v1",
            "machine_id": self.machine_id,
            "board_id": self.board_id,
            "plan_digest": self.plan_digest,
            "filevault": self.filevault.value,
            "data_volume": self.data_volume.value,
            "macos_administrator": self.macos_administrator.value,
            "machine_owner": self.machine_owner.value,
            "linux_encryption": self.linux_encryption.value,
            "paired_recovery_os": self.paired_recovery_os.value,
            "one_true_recovery": self.one_true_recovery.value,
            # Only public receipt envelopes are serialized; opaque receipt IDs
            # and all Apple-owned credential material stay out of the digest.
            "receipt_envelopes": [receipt.to_dict() for receipt in self.authorization_receipts],
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    def ordered_facts(self) -> tuple[tuple[str, StrEnum], ...]:
        return tuple((name, getattr(self, name)) for name in REQUIRED_STATE_ORDER)

    @staticmethod
    def validate_dependency_order(observed_order: tuple[str, ...]) -> None:
        if not isinstance(observed_order, tuple) or observed_order != REQUIRED_STATE_ORDER:
            raise CredentialDependencyError("credential facts are not in dependency order")

    def evaluate(
        self,
        now: int,
        ledger: ReceiptLedger | None = None,
        observed_order: tuple[str, ...] | None = None,
    ) -> "ReadinessDecision":
        return ReadinessDecision.from_state(self, now, ReceiptLedger() if ledger is None else ledger, observed_order)


@dataclass(frozen=True, slots=True, init=False)
class ReadinessDecision:
    """Derived decision consumed by I-01; callers cannot launder ``ready=True``."""

    machine_id: str
    board_id: str
    plan_digest: str
    state_digest: str
    ready: bool
    blockers: tuple[ReadinessBlocker, ...]
    evaluated_at: int
    _ledger_checkpoint_id: str = field(repr=False, compare=False)
    _ledger_consumed_ids: frozenset[str] = field(repr=False, compare=False)
    _receipts: tuple[AuthorizationReceipt, ...] = field(repr=False, compare=False)

    def __init__(
        self,
        machine_id: str,
        board_id: str,
        plan_digest: str,
        state_digest: str,
        ready: bool,
        blockers: tuple[ReadinessBlocker, ...],
        evaluated_at: int,
    ) -> None:
        """Private-shape initializer; use :meth:`from_state` for a decision."""
        raise CredentialReadinessError("readiness decisions must be derived from credential state")

    @classmethod
    def from_state(
        cls,
        state: CredentialState,
        now: int,
        ledger: ReceiptLedger,
        observed_order: tuple[str, ...] | None = None,
    ) -> Self:
        if not isinstance(state, CredentialState) or not isinstance(ledger, ReceiptLedger):
            raise CredentialTypeError("credential state and receipt ledger are required")
        _strict_time(now, "evaluation")
        blockers: list[ReadinessBlocker] = []
        if not isinstance(observed_order, tuple) or observed_order != REQUIRED_STATE_ORDER:
            blockers.append(ReadinessBlocker.DEPENDENCY_ORDER_INVALID)
        if state.filevault not in {FileVaultState.ENABLED, FileVaultState.DISABLED}:
            blockers.append(ReadinessBlocker.FILEVAULT_UNKNOWN)
        if state.data_volume is not DataVolumeLockState.UNLOCKED:
            blockers.append(ReadinessBlocker.DATA_VOLUME_NOT_UNLOCKED)
        if state.macos_administrator is not MacOSAdministratorState.AUTHORIZED:
            blockers.append(ReadinessBlocker.ADMINISTRATOR_NOT_AUTHORIZED)
        if state.machine_owner is not MachineOwnerState.AUTHORIZED:
            blockers.append(ReadinessBlocker.MACHINE_OWNER_NOT_AUTHORIZED)
        if state.linux_encryption is not LinuxEncryptionState.VERIFIED:
            blockers.append(ReadinessBlocker.LINUX_ENCRYPTION_NOT_VERIFIED)
        if state.paired_recovery_os is not PairedRecoveryOSState.PAIRED:
            blockers.append(ReadinessBlocker.RECOVERY_OS_NOT_PAIRED)
        if state.one_true_recovery is not OneTRState.READY:
            blockers.append(ReadinessBlocker.ONE_TR_NOT_READY)
        required_receipts = {
            AuthorizationKind.MACOS_ADMINISTRATOR,
            AuthorizationKind.MACHINE_OWNER,
        }
        receipt_by_kind = {receipt.kind: receipt for receipt in state.authorization_receipts}
        for kind, blocker in (
            (AuthorizationKind.MACOS_ADMINISTRATOR, ReadinessBlocker.RECEIPT_MISSING),
            (AuthorizationKind.MACHINE_OWNER, ReadinessBlocker.RECEIPT_MISSING),
        ):
            receipt = receipt_by_kind.get(kind)
            if kind in required_receipts and receipt is None:
                blockers.append(blocker)
            elif receipt is not None:
                try:
                    receipt.validate(kind, state.machine_id, state.board_id, state.plan_digest, now)
                except CredentialReceiptError:
                    blockers.append(ReadinessBlocker.RECEIPT_INVALID)
                except CredentialBindingError:
                    blockers.append(ReadinessBlocker.RECEIPT_INVALID)
                if receipt.receipt_id in ledger.consumed_receipt_ids:
                    blockers.append(ReadinessBlocker.RECEIPT_REUSED)
        if len(blockers) > MAX_BLOCKERS:
            raise CredentialBoundsError("readiness blocker count exceeds bound")
        return object.__new__(cls)._init_derived(state, now, tuple(dict.fromkeys(blockers)), ledger)

    def _init_derived(
        self,
        state: CredentialState,
        now: int,
        blockers: tuple[ReadinessBlocker, ...],
        ledger: ReceiptLedger,
    ) -> Self:
        object.__setattr__(self, "machine_id", state.machine_id)
        object.__setattr__(self, "board_id", state.board_id)
        object.__setattr__(self, "plan_digest", state.plan_digest)
        object.__setattr__(self, "state_digest", state.digest)
        object.__setattr__(self, "ready", not blockers)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "evaluated_at", now)
        object.__setattr__(self, "_ledger_checkpoint_id", ledger.checkpoint_id)
        object.__setattr__(self, "_ledger_consumed_ids", ledger.consumed_receipt_ids)
        object.__setattr__(self, "_receipts", state.authorization_receipts)
        return self

    @property
    def digest(self) -> str:
        return _domain_digest("omarchy-readiness-decision/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "readiness-decision/v1",
            "machine_id": self.machine_id,
            "board_id": self.board_id,
            "plan_digest": self.plan_digest,
            "state_digest": self.state_digest,
            "ready": self.ready,
            "blockers": [blocker.value for blocker in self.blockers],
            "evaluated_at": self.evaluated_at,
        }

    def consume(
        self,
        machine_id: str,
        board_id: str,
        plan_digest: str,
        now: int,
        authority: "ConsumptionAuthority",
    ) -> "ReadinessAttestation":
        if not isinstance(authority, ConsumptionAuthority):
            raise CredentialTypeError("consumption authority is required")
        return authority.consume(self, machine_id, board_id, plan_digest, now)


@dataclass(frozen=True, slots=True)
class ConsumptionCheckpoint:
    """Canonical in-process CAS checkpoint; durable CAS remains residual."""

    decision_digest: str
    machine_id: str
    board_id: str
    plan_digest: str
    receipt_digests: tuple[str, ...]
    ledger_checkpoint_id: str
    consumed_at: int
    authority_id: str = "unbound"
    authority_revision: int = 0

    def __post_init__(self) -> None:
        _digest(self.decision_digest, "decision")
        _identifier(self.machine_id, "machine identity")
        _identifier(self.board_id, "board identity")
        _digest(self.plan_digest, "plan")
        if not isinstance(self.receipt_digests, tuple) or len(self.receipt_digests) > MAX_RECEIPTS:
            raise CredentialTypeError("invalid receipt digest set")
        for digest in self.receipt_digests:
            _digest(digest, "receipt")
        _opaque(self.ledger_checkpoint_id, "ledger checkpoint id")
        _strict_time(self.consumed_at, "consumption")
        _opaque(self.authority_id, "authority id")
        if type(self.authority_revision) is not int or self.authority_revision <= 0:
            raise CredentialTypeError("invalid authority revision")

    @property
    def digest(self) -> str:
        return _domain_digest("omarchy-credential-consumption/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "credential-consumption-checkpoint/v1",
            "decision_digest": self.decision_digest,
            "machine_id": self.machine_id,
            "board_id": self.board_id,
            "plan_digest": self.plan_digest,
            "receipt_digests": list(self.receipt_digests),
            "ledger_checkpoint_id": self.ledger_checkpoint_id,
            "consumed_at": self.consumed_at,
            "authority_id": self.authority_id,
            "authority_revision": self.authority_revision,
            "durability": "in_process_only",
            "cross_process_persistence": CROSS_PROCESS_PERSISTENCE_RESIDUAL,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())


class ConsumptionAuthority:
    """Lock-protected compare-and-consume authority for one process."""

    def __init__(self, ledger: ReceiptLedger) -> None:
        if not isinstance(ledger, ReceiptLedger):
            raise CredentialTypeError("consumption authority requires a receipt ledger")
        self._lock = threading.Lock()
        self._ledger = ledger
        self._authority_id = uuid.uuid4().hex
        self._revision = 0
        self._consumed: dict[tuple[str, tuple[str, ...], str, str, str], ConsumptionCheckpoint] = {}
        self._issued: dict[str, ReadinessAttestation] = {}

    @property
    def ledger(self) -> ReceiptLedger:
        return self._ledger

    def checkpoint_for(self, decision: ReadinessDecision) -> ConsumptionCheckpoint | None:
        if not isinstance(decision, ReadinessDecision):
            raise CredentialTypeError("readiness decision is required")
        with self._lock:
            return self._consumed.get(self._key(decision))

    @staticmethod
    def _key(decision: ReadinessDecision) -> tuple[str, tuple[str, ...], str, str, str]:
        return (
            decision.digest,
            tuple(receipt.receipt_id for receipt in decision._receipts),
            decision.machine_id,
            decision.board_id,
            decision.plan_digest,
        )

    def consume(
        self,
        decision: ReadinessDecision,
        machine_id: str,
        board_id: str,
        plan_digest: str,
        now: int,
    ) -> "ReadinessAttestation":
        if not isinstance(decision, ReadinessDecision):
            raise CredentialTypeError("readiness decision is required")
        if not decision.ready:
            raise CredentialReadinessError("cannot consume a non-ready decision")
        _strict_time(now, "consumption")
        if (machine_id, board_id, plan_digest) != (decision.machine_id, decision.board_id, decision.plan_digest):
            raise CredentialBindingError("readiness decision binding mismatch")
        key = self._key(decision)
        with self._lock:
            if key in self._consumed:
                raise ReadinessAlreadyConsumedError("ALREADY_CONSUMED")
            if (
                self._ledger.checkpoint_id != decision._ledger_checkpoint_id
                or self._ledger.consumed_receipt_ids != decision._ledger_consumed_ids
            ):
                raise ReadinessAuthorityStateError("AUTHORITY_STATE_MISMATCH")
            for receipt in decision._receipts:
                try:
                    receipt.validate(receipt.kind, decision.machine_id, decision.board_id, decision.plan_digest, now)
                except CredentialReceiptError as exc:
                    raise ReadinessExpiredError("READINESS_EXPIRED") from exc
                if receipt.receipt_id in self._ledger.consumed_receipt_ids:
                    raise ReadinessAuthorityStateError("AUTHORITY_STATE_MISMATCH")
            checkpoint = ConsumptionCheckpoint(
                decision.digest,
                decision.machine_id,
                decision.board_id,
                decision.plan_digest,
                tuple(sorted(_domain_digest("omarchy-receipt-envelope/v1", receipt.to_dict()) for receipt in decision._receipts)),
                self._ledger.checkpoint_id,
                now,
                self._authority_id,
                self._revision + 1,
            )
            self._revision += 1
            self._ledger = ReceiptLedger(
                self._ledger.consumed_receipt_ids | {receipt.receipt_id for receipt in decision._receipts},
                self._ledger.checkpoint_id,
            )
            self._consumed[key] = checkpoint
            attestation = object.__new__(ReadinessAttestation)
            object.__setattr__(attestation, "machine_id", decision.machine_id)
            object.__setattr__(attestation, "board_id", decision.board_id)
            object.__setattr__(attestation, "plan_digest", decision.plan_digest)
            object.__setattr__(attestation, "decision_digest", decision.digest)
            object.__setattr__(attestation, "consumption_checkpoint_digest", checkpoint.digest)
            object.__setattr__(attestation, "authority_id", self._authority_id)
            object.__setattr__(attestation, "authority_revision", self._revision)
            object.__setattr__(attestation, "consumed_at", now)
            object.__setattr__(attestation, "receipt_digests", checkpoint.receipt_digests)
            object.__setattr__(attestation, "ledger_checkpoint_id", checkpoint.ledger_checkpoint_id)
            object.__setattr__(attestation, "_receipt_ids", tuple(sorted(receipt.receipt_id for receipt in decision._receipts)))
            self._issued[attestation.digest] = attestation
            return attestation

    def verify_attestation(
        self,
        attestation: "ReadinessAttestation",
        decision: ReadinessDecision,
        machine_id: str,
        board_id: str,
        plan_digest: str,
        now: int,
    ) -> None:
        """Verify an in-process attestation is the exact registered issuance."""
        if not isinstance(attestation, ReadinessAttestation):
            raise CredentialTypeError("readiness attestation is required")
        if not isinstance(decision, ReadinessDecision):
            raise CredentialTypeError("readiness decision is required")
        _strict_time(now, "verification")
        if (machine_id, board_id, plan_digest) != (decision.machine_id, decision.board_id, decision.plan_digest):
            raise CredentialBindingError("readiness attestation binding mismatch")
        with self._lock:
            registered = self._issued.get(attestation.digest)
            if registered is not attestation:
                raise CredentialReadinessError("ATTESTATION_NOT_REGISTERED")
            checkpoint = self._consumed.get(self._key(decision))
            if checkpoint is None:
                raise CredentialReadinessError("ATTESTATION_NOT_REGISTERED")
            expected_ids = tuple(sorted(receipt.receipt_id for receipt in decision._receipts))
            if (
                attestation.decision_digest != decision.digest
                or attestation.machine_id != machine_id
                or attestation.board_id != board_id
                or attestation.plan_digest != plan_digest
                or attestation.authority_id != self._authority_id
                or attestation.authority_revision != checkpoint.authority_revision
                or attestation.consumed_at != checkpoint.consumed_at
                or attestation.ledger_checkpoint_id != checkpoint.ledger_checkpoint_id
                or attestation.consumption_checkpoint_digest != checkpoint.digest
                or attestation.receipt_digests != checkpoint.receipt_digests
                or attestation._receipt_ids != expected_ids
            ):
                raise CredentialReadinessError("ATTESTATION_BINDING_MISMATCH")


@dataclass(frozen=True, slots=True, init=False)
class ReadinessAttestation:
    """Exact-plan proof handed to I-01 immediately before final consent."""

    machine_id: str
    board_id: str
    plan_digest: str
    decision_digest: str
    consumption_checkpoint_digest: str
    authority_id: str
    authority_revision: int
    consumed_at: int
    receipt_digests: tuple[str, ...]
    ledger_checkpoint_id: str
    _receipt_ids: tuple[str, ...] = field(repr=False, compare=False)

    def __init__(self, machine_id: str, board_id: str, plan_digest: str, decision_digest: str) -> None:
        raise CredentialReadinessError("readiness attestations must come from a derived decision")

    def __post_init__(self) -> None:
        _identifier(self.machine_id, "machine identity")
        _identifier(self.board_id, "board identity")
        _digest(self.plan_digest, "plan")
        _digest(self.decision_digest, "decision")

    @property
    def digest(self) -> str:
        return _domain_digest("omarchy-readiness-attestation/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "readiness-attestation/v1",
            "machine_id": self.machine_id,
            "board_id": self.board_id,
            "plan_digest": self.plan_digest,
            "decision_digest": self.decision_digest,
            "consumption_checkpoint_digest": self.consumption_checkpoint_digest,
            "authority_id": self.authority_id,
            "authority_revision": self.authority_revision,
            "consumed_at": self.consumed_at,
            "receipt_digests": list(self.receipt_digests),
            "ledger_checkpoint_id": self.ledger_checkpoint_id,
        }


def require_readiness_for_i01(
    decision: ReadinessDecision,
    machine_id: str,
    board_id: str,
    plan_digest: str,
    now: int,
    authority: ConsumptionAuthority,
) -> ReadinessAttestation:
    """The explicit I-01 handoff; mutation code should require this result."""
    if not isinstance(decision, ReadinessDecision):
        raise CredentialTypeError("readiness decision is required before final consent")
    if not isinstance(authority, ConsumptionAuthority):
        raise CredentialTypeError("consumption authority is required before final consent")
    attestation = decision.consume(machine_id, board_id, plan_digest, now, authority)
    authority.verify_attestation(attestation, decision, machine_id, board_id, plan_digest, now)
    return attestation


# Compatibility names make the distinct vocabulary explicit at call sites.
FileVaultStatus = FileVaultState
DataVolumeStatus = DataVolumeLockState
MacOSAdminState = MacOSAdministratorState
MacOSAdministratorStatus = MacOSAdministratorState
MachineOwnerStatus = MachineOwnerState
LinuxEncryptionSetupState = LinuxEncryptionState
PairedRecoveryOSStatus = PairedRecoveryOSState
PairedRecoveryOSAvailability = PairedRecoveryOSState
OneTrueRecoveryState = OneTRState
OneTRReadiness = OneTRState


__all__ = [
    "AuthorizationKind", "AuthorizationReceipt", "ConsumptionAuthority", "ConsumptionCheckpoint",
    "CredentialBindingError", "CredentialBoundsError", "CredentialDependencyError",
    "CredentialReadinessError", "CredentialSecretError",
    "CredentialSerializationError", "CredentialState", "CredentialStateError", "CredentialTypeError",
    "DataVolumeLockState", "DataVolumeStatus", "FileVaultState", "FileVaultStatus",
    "LinuxEncryptionSetupState", "LinuxEncryptionState", "MacOSAdminState", "MacOSAdministratorState",
    "MacOSAdministratorStatus", "MachineOwnerState", "MachineOwnerStatus", "OneTRReadiness", "OneTRState",
    "OneTrueRecoveryState", "PairedRecoveryOSAvailability", "PairedRecoveryOSState", "PairedRecoveryOSStatus",
    "ReadinessAlreadyConsumedError", "ReadinessAttestation", "ReadinessAuthorityStateError",
    "ReadinessBlocker", "ReadinessDecision", "ReadinessExpiredError",
    "ReceiptLedger", "REQUIRED_STATE_ORDER", "canonical_bytes", "canonical_json", "require_readiness_for_i01",
]
