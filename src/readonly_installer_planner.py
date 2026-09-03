"""Pure, fail-closed read-only installer inventory and planning boundary.

The module deliberately performs no discovery.  Callers provide a bounded JSON
observation, and this module only validates, binds, and plans against it.  No
path, device node, credential, subprocess, filesystem, or disk mutation is
represented here.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from credential_states import (
    ConsumptionAuthority,
    CredentialBindingError,
    CredentialReadinessError,
    ReadinessDecision,
    require_readiness_for_i01,
)
from installer_transaction import (
    ActionKind,
    Artifact,
    Consent,
    ContainerIdentity,
    DiskIdentity,
    InstallerPlan,
    PlanStep,
    VolumeIdentity,
)


MAX_INPUT_BYTES = 64 * 1024
MAX_STRING_LENGTH = 256
MAX_COLLECTION_ITEMS = 128
MAX_OBSERVATION_AGE = 300
MAX_CONSENT_LIFETIME = 900
MAX_GEOMETRY = 2**63 - 1
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class PlannerError(Exception):
    """Base class for deterministic planner failures."""


class InputBoundsError(PlannerError):
    pass


class InputSchemaError(PlannerError):
    pass


class ObservationError(PlannerError):
    pass


class TargetError(PlannerError):
    pass


class CandidateAdmissionError(PlannerError):
    pass


class PlannerAuthorityError(PlannerError):
    pass


class ConsentError(PlannerError):
    pass


class ConsentExpiredError(ConsentError):
    pass


class ConsentConsumedError(ConsentError):
    pass


class QualificationState(StrEnum):
    QUALIFIED = "QUALIFIED"
    UNKNOWN = "UNKNOWN"
    NOT_QUALIFIED = "NOT_QUALIFIED"


class MediaKind(StrEnum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class MountState(StrEnum):
    UNMOUNTED = "UNMOUNTED"
    MOUNTED = "MOUNTED"
    UNKNOWN = "UNKNOWN"


class BusyState(StrEnum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    UNKNOWN = "UNKNOWN"


class EncryptionState(StrEnum):
    CLEAR = "CLEAR"
    ENCRYPTED = "ENCRYPTED"
    UNKNOWN = "UNKNOWN"


class DestructiveOperation(StrEnum):
    PROVISION_VOLUME = "PROVISION_VOLUME"
    CONFIGURE_BOOT = "CONFIGURE_BOOT"


def _strict_id(value: Any, label: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise InputSchemaError(f"invalid {label}")
    return value


def _strict_digest(value: Any, label: str) -> str:
    if type(value) is not str or not _DIGEST.fullmatch(value) or len(set(value)) == 1:
        raise InputSchemaError(f"invalid or sentinel {label} digest")
    return value


def _strict_time(value: Any, label: str) -> int:
    if type(value) is not int or value < 0 or value >= 2**63:
        raise InputSchemaError(f"invalid {label} timestamp")
    return value


def _strict_size(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0 or value > MAX_GEOMETRY:
        raise InputSchemaError(f"invalid {label} size")
    return value


def _enum(value: Any, expected: type[StrEnum], label: str) -> StrEnum:
    if not isinstance(value, expected):
        raise InputSchemaError(f"invalid {label}")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise InputSchemaError("value is not canonical JSON") from exc


def _digest_for(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + _canonical(value)).hexdigest()


def _check_no_float(value: Any, location: str = "$") -> None:
    if isinstance(value, float):
        raise InputSchemaError(f"floating-point value at {location}")
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if type(key) is not str:
                raise InputSchemaError(f"non-string key at {location}")
            _check_no_float(nested, f"{location}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _check_no_float(nested, f"{location}[{index}]")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputSchemaError(f"duplicate JSON field {key}")
        result[key] = value
    return result


def _check_tree(value: Any, depth: int = 0) -> None:
    if depth > 10:
        raise InputBoundsError("JSON nesting exceeds bound")
    if isinstance(value, Mapping):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise InputBoundsError("JSON object exceeds bound")
        for key, nested in value.items():
            if type(key) is not str or len(key) > MAX_STRING_LENGTH:
                raise InputBoundsError("JSON field exceeds bound")
            _check_tree(nested, depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_COLLECTION_ITEMS:
            raise InputBoundsError("JSON list exceeds bound")
        for nested in value:
            _check_tree(nested, depth + 1)
    elif type(value) is str:
        if len(value) > MAX_STRING_LENGTH:
            raise InputBoundsError("JSON string exceeds bound")
    elif value is None or type(value) in {bool, int}:
        return
    else:
        raise InputSchemaError("unsupported JSON value")


def _require_keys(document: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    if set(document) != expected:
        raise InputSchemaError(f"invalid {label} fields")


@dataclass(frozen=True, slots=True)
class Geometry:
    start_bytes: int
    size_bytes: int

    def __post_init__(self) -> None:
        if type(self.start_bytes) is not int or self.start_bytes < 0:
            raise InputSchemaError("invalid geometry start")
        _strict_size(self.size_bytes, "geometry")
        if self.start_bytes + self.size_bytes > MAX_GEOMETRY:
            raise InputSchemaError("geometry exceeds address bound")

    @property
    def end_bytes(self) -> int:
        return self.start_bytes + self.size_bytes

    def to_dict(self) -> dict[str, int]:
        return {"start_bytes": self.start_bytes, "size_bytes": self.size_bytes}


@dataclass(frozen=True, slots=True)
class MachineObservation:
    machine_id: str
    observed_at: int
    qualification: QualificationState

    def __post_init__(self) -> None:
        _strict_id(self.machine_id, "machine identity")
        _strict_time(self.observed_at, "observation")
        _enum(self.qualification, QualificationState, "machine qualification")

    def to_dict(self) -> dict[str, Any]:
        return {"machine_id": self.machine_id, "observed_at": self.observed_at, "qualification": self.qualification.value}


@dataclass(frozen=True, slots=True)
class BoardObservation:
    board_id: str
    machine_id: str
    qualification: QualificationState

    def __post_init__(self) -> None:
        _strict_id(self.board_id, "board identity")
        _strict_id(self.machine_id, "machine identity")
        _enum(self.qualification, QualificationState, "board qualification")

    def to_dict(self) -> dict[str, Any]:
        return {"board_id": self.board_id, "machine_id": self.machine_id, "qualification": self.qualification.value}


@dataclass(frozen=True, slots=True)
class DiskObservation:
    disk_id: str
    machine_id: str
    geometry: Geometry
    media: MediaKind
    mount: MountState
    busy: BusyState
    encryption: EncryptionState
    qualification: QualificationState

    def __post_init__(self) -> None:
        _strict_id(self.disk_id, "disk identity")
        _strict_id(self.machine_id, "machine identity")
        if not isinstance(self.geometry, Geometry):
            raise InputSchemaError("disk geometry is required")
        _enum(self.media, MediaKind, "disk media")
        _enum(self.mount, MountState, "disk mount")
        _enum(self.busy, BusyState, "disk busy state")
        _enum(self.encryption, EncryptionState, "disk encryption")
        _enum(self.qualification, QualificationState, "disk qualification")

    def to_dict(self) -> dict[str, Any]:
        return {"disk_id": self.disk_id, "machine_id": self.machine_id, "geometry": self.geometry.to_dict(), "media": self.media.value, "mount": self.mount.value, "busy": self.busy.value, "encryption": self.encryption.value, "qualification": self.qualification.value}


@dataclass(frozen=True, slots=True)
class APFSContainerObservation:
    container_id: str
    machine_id: str
    disk_id: str
    geometry: Geometry
    mount: MountState
    busy: BusyState
    encryption: EncryptionState
    qualification: QualificationState

    def __post_init__(self) -> None:
        for value, label in ((self.container_id, "container identity"), (self.machine_id, "machine identity"), (self.disk_id, "disk identity")):
            _strict_id(value, label)
        if not isinstance(self.geometry, Geometry):
            raise InputSchemaError("container geometry is required")
        _enum(self.mount, MountState, "container mount")
        _enum(self.busy, BusyState, "container busy state")
        _enum(self.encryption, EncryptionState, "container encryption")
        _enum(self.qualification, QualificationState, "container qualification")

    def to_dict(self) -> dict[str, Any]:
        return {"container_id": self.container_id, "machine_id": self.machine_id, "disk_id": self.disk_id, "geometry": self.geometry.to_dict(), "mount": self.mount.value, "busy": self.busy.value, "encryption": self.encryption.value, "qualification": self.qualification.value}


@dataclass(frozen=True, slots=True)
class VolumeObservation:
    volume_id: str
    machine_id: str
    container_id: str
    geometry: Geometry
    mount: MountState
    busy: BusyState
    encryption: EncryptionState
    qualification: QualificationState

    def __post_init__(self) -> None:
        for value, label in ((self.volume_id, "volume identity"), (self.machine_id, "machine identity"), (self.container_id, "container identity")):
            _strict_id(value, label)
        if not isinstance(self.geometry, Geometry):
            raise InputSchemaError("volume geometry is required")
        _enum(self.mount, MountState, "volume mount")
        _enum(self.busy, BusyState, "volume busy state")
        _enum(self.encryption, EncryptionState, "volume encryption")
        _enum(self.qualification, QualificationState, "volume qualification")

    def to_dict(self) -> dict[str, Any]:
        return {"volume_id": self.volume_id, "machine_id": self.machine_id, "container_id": self.container_id, "geometry": self.geometry.to_dict(), "mount": self.mount.value, "busy": self.busy.value, "encryption": self.encryption.value, "qualification": self.qualification.value}


def _ordered_unique(items: tuple[Any, ...], label: str, identity: str) -> None:
    values = [getattr(item, identity) for item in items]
    if values != sorted(values):
        raise ObservationError(f"{label} identities are reordered")
    if len(values) != len(set(values)):
        raise ObservationError(f"duplicate {label} identity")


def _no_overlap(items: tuple[Any, ...], label: str) -> None:
    ranges = sorted((item.geometry.start_bytes, item.geometry.end_bytes) for item in items)
    if any(next_start < previous_end for (_, previous_end), (next_start, _) in zip(ranges, ranges[1:])):
        raise ObservationError(f"overlapping {label} geometry")


@dataclass(frozen=True, slots=True)
class InventoryObservation:
    machine: MachineObservation
    board: BoardObservation
    disks: tuple[DiskObservation, ...]
    containers: tuple[APFSContainerObservation, ...]
    volumes: tuple[VolumeObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.machine, MachineObservation) or not isinstance(self.board, BoardObservation):
            raise InputSchemaError("machine and board observations are required")
        if self.board.machine_id != self.machine.machine_id:
            raise ObservationError("board is bound to another machine")
        for collection, typ, label in ((self.disks, DiskObservation, "disk"), (self.containers, APFSContainerObservation, "container"), (self.volumes, VolumeObservation, "volume")):
            if not isinstance(collection, tuple) or len(collection) > MAX_COLLECTION_ITEMS or any(not isinstance(item, typ) for item in collection):
                raise InputSchemaError(f"invalid {label} observations")
            _ordered_unique(collection, label, {"disk": "disk_id", "container": "container_id", "volume": "volume_id"}[label])
        for disk in self.disks:
            if disk.machine_id != self.machine.machine_id:
                raise ObservationError("disk machine binding mismatch")
        disk_by_id = {disk.disk_id: disk for disk in self.disks}
        for container in self.containers:
            disk = disk_by_id.get(container.disk_id)
            if container.machine_id != self.machine.machine_id or disk is None:
                raise ObservationError("container parent binding mismatch")
            if container.geometry.start_bytes < disk.geometry.start_bytes or container.geometry.end_bytes > disk.geometry.end_bytes:
                raise ObservationError("container geometry is outside disk")
        for disk_id in {container.disk_id for container in self.containers}:
            _no_overlap(tuple(container for container in self.containers if container.disk_id == disk_id), "container")
        container_by_id = {container.container_id: container for container in self.containers}
        for volume in self.volumes:
            container = container_by_id.get(volume.container_id)
            if volume.machine_id != self.machine.machine_id or container is None:
                raise ObservationError("volume parent binding mismatch")
            if volume.geometry.start_bytes < container.geometry.start_bytes or volume.geometry.end_bytes > container.geometry.end_bytes:
                raise ObservationError("volume geometry is outside container")
        for container in self.containers:
            _no_overlap(tuple(volume for volume in self.volumes if volume.container_id == container.container_id), "volume")

    @property
    def observed_at(self) -> int:
        return self.machine.observed_at

    @property
    def digest(self) -> str:
        return _digest_for("omarchy-inventory-observation/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"version": "inventory-observation/v1", "machine": self.machine.to_dict(), "board": self.board.to_dict(), "disks": [item.to_dict() for item in self.disks], "containers": [item.to_dict() for item in self.containers], "volumes": [item.to_dict() for item in self.volumes]}


def _parse_geometry(value: Any) -> Geometry:
    if not isinstance(value, Mapping):
        raise InputSchemaError("geometry must be an object")
    _require_keys(value, frozenset({"start_bytes", "size_bytes"}), "geometry")
    return Geometry(value["start_bytes"], value["size_bytes"])


def _parse_state(value: Any, expected: type[StrEnum], label: str) -> StrEnum:
    if type(value) is not str:
        raise InputSchemaError(f"invalid {label}")
    try:
        return expected(value)
    except ValueError as exc:
        raise InputSchemaError(f"invalid {label}") from exc


def parse_inventory_json(value: str | bytes) -> InventoryObservation:
    """Parse exactly one bounded inventory document; never touches the host."""
    if not isinstance(value, (str, bytes)):
        raise InputSchemaError("inventory input must be text or bytes")
    try:
        raw = value.encode("utf-8") if isinstance(value, str) else value
        if len(raw) > MAX_INPUT_BYTES:
            raise InputBoundsError("inventory input exceeds bound")
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs, parse_constant=lambda _: (_ for _ in ()).throw(InputSchemaError("non-finite JSON number")))
    except UnicodeEncodeError as exc:
        raise InputSchemaError("inventory input is not valid UTF-8") from exc
    except UnicodeDecodeError as exc:
        raise InputSchemaError("invalid inventory JSON") from exc
    except RecursionError as exc:
        raise InputBoundsError("JSON nesting exceeds bound") from exc
    except json.JSONDecodeError as exc:
        raise InputSchemaError("invalid inventory JSON") from exc
    _check_tree(document)
    if not isinstance(document, Mapping):
        raise InputSchemaError("inventory document must be an object")
    _require_keys(document, frozenset({"version", "machine", "board", "disks", "containers", "volumes"}), "inventory")
    if document["version"] != "inventory-observation/v1":
        raise InputSchemaError("unsupported inventory version")
    machine_data = document["machine"]
    board_data = document["board"]
    if not isinstance(machine_data, Mapping) or not isinstance(board_data, Mapping):
        raise InputSchemaError("machine and board must be objects")
    _require_keys(machine_data, frozenset({"machine_id", "observed_at", "qualification"}), "machine")
    _require_keys(board_data, frozenset({"board_id", "machine_id", "qualification"}), "board")
    machine = MachineObservation(machine_data["machine_id"], machine_data["observed_at"], _parse_state(machine_data["qualification"], QualificationState, "machine qualification"))
    board = BoardObservation(board_data["board_id"], board_data["machine_id"], _parse_state(board_data["qualification"], QualificationState, "board qualification"))

    def parse_items(items: Any, label: str, parser: Any) -> tuple[Any, ...]:
        if not isinstance(items, list):
            raise InputSchemaError(f"{label} must be a list")
        return tuple(parser(item) for item in items)

    def disk_parser(item: Any) -> DiskObservation:
        if not isinstance(item, Mapping):
            raise InputSchemaError("disk must be an object")
        _require_keys(item, frozenset({"disk_id", "machine_id", "geometry", "media", "mount", "busy", "encryption", "qualification"}), "disk")
        return DiskObservation(item["disk_id"], item["machine_id"], _parse_geometry(item["geometry"]), _parse_state(item["media"], MediaKind, "disk media"), _parse_state(item["mount"], MountState, "disk mount"), _parse_state(item["busy"], BusyState, "disk busy"), _parse_state(item["encryption"], EncryptionState, "disk encryption"), _parse_state(item["qualification"], QualificationState, "disk qualification"))

    def container_parser(item: Any) -> APFSContainerObservation:
        if not isinstance(item, Mapping):
            raise InputSchemaError("container must be an object")
        _require_keys(item, frozenset({"container_id", "machine_id", "disk_id", "geometry", "mount", "busy", "encryption", "qualification"}), "container")
        return APFSContainerObservation(item["container_id"], item["machine_id"], item["disk_id"], _parse_geometry(item["geometry"]), _parse_state(item["mount"], MountState, "container mount"), _parse_state(item["busy"], BusyState, "container busy"), _parse_state(item["encryption"], EncryptionState, "container encryption"), _parse_state(item["qualification"], QualificationState, "container qualification"))

    def volume_parser(item: Any) -> VolumeObservation:
        if not isinstance(item, Mapping):
            raise InputSchemaError("volume must be an object")
        _require_keys(item, frozenset({"volume_id", "machine_id", "container_id", "geometry", "mount", "busy", "encryption", "qualification"}), "volume")
        return VolumeObservation(item["volume_id"], item["machine_id"], item["container_id"], _parse_geometry(item["geometry"]), _parse_state(item["mount"], MountState, "volume mount"), _parse_state(item["busy"], BusyState, "volume busy"), _parse_state(item["encryption"], EncryptionState, "volume encryption"), _parse_state(item["qualification"], QualificationState, "volume qualification"))

    return InventoryObservation(machine, board, parse_items(document["disks"], "disks", disk_parser), parse_items(document["containers"], "containers", container_parser), parse_items(document["volumes"], "volumes", volume_parser))


@dataclass(frozen=True, slots=True)
class TargetIdentity:
    machine_id: str
    board_id: str
    disk_id: str
    disk_geometry: Geometry
    container_id: str
    container_geometry: Geometry
    volume_id: str
    volume_geometry: Geometry

    def __post_init__(self) -> None:
        for value, label in ((self.machine_id, "machine identity"), (self.board_id, "board identity"), (self.disk_id, "disk identity"), (self.container_id, "container identity"), (self.volume_id, "volume identity")):
            _strict_id(value, label)
        for value in (self.disk_geometry, self.container_geometry, self.volume_geometry):
            if not isinstance(value, Geometry):
                raise TargetError("target geometry is required")

    @property
    def digest(self) -> str:
        return _digest_for("omarchy-target-identity/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"machine_id": self.machine_id, "board_id": self.board_id, "disk_id": self.disk_id, "disk_geometry": self.disk_geometry.to_dict(), "container_id": self.container_id, "container_geometry": self.container_geometry.to_dict(), "volume_id": self.volume_id, "volume_geometry": self.volume_geometry.to_dict()}


@dataclass(frozen=True, slots=True, init=False)
class CandidateEvidence:
    f02_digest: str
    q00_digest: str
    q01_digest: str
    f05_digest: str
    candidate_digest: str
    manifest_digest: str
    schema_digest: str
    f02_status: QualificationState
    q00_status: QualificationState
    q01_status: QualificationState
    f05_status: QualificationState

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise CandidateAdmissionError("candidate evidence must be issued by planning authority")

    def __post_init__(self) -> None:
        for value, label in ((self.f02_digest, "F-02"), (self.q00_digest, "Q-00"), (self.q01_digest, "Q-01"), (self.f05_digest, "F-05"), (self.candidate_digest, "candidate"), (self.manifest_digest, "manifest"), (self.schema_digest, "schema")):
            _strict_digest(value, label)
        for value, label in ((self.f02_status, "F-02"), (self.q00_status, "Q-00"), (self.q01_status, "Q-01"), (self.f05_status, "F-05")):
            _enum(value, QualificationState, label)

    @property
    def digest(self) -> str:
        return _digest_for("omarchy-candidate-evidence/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"f02_digest": self.f02_digest, "q00_digest": self.q00_digest, "q01_digest": self.q01_digest, "f05_digest": self.f05_digest, "candidate_digest": self.candidate_digest, "manifest_digest": self.manifest_digest, "schema_digest": self.schema_digest, "f02_status": self.f02_status.value, "q00_status": self.q00_status.value, "q01_status": self.q01_status.value, "f05_status": self.f05_status.value}


@dataclass(frozen=True, slots=True)
class CandidateRequest:
    machine_id: str
    board_id: str
    disk_id: str
    container_id: str
    volume_id: str
    candidate_digest: str
    manifest_digest: str
    schema_digest: str

    def __post_init__(self) -> None:
        for value, label in ((self.machine_id, "machine identity"), (self.board_id, "board identity"), (self.disk_id, "disk identity"), (self.container_id, "container identity"), (self.volume_id, "volume identity")):
            _strict_id(value, label)
        for value, label in ((self.candidate_digest, "candidate"), (self.manifest_digest, "manifest"), (self.schema_digest, "schema")):
            _strict_digest(value, label)


@dataclass(frozen=True, slots=True, init=False)
class CandidateAdmission:
    inventory_digest: str
    evidence: CandidateEvidence
    target: TargetIdentity
    admitted_at: int

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise CandidateAdmissionError("candidate admission must be derived")

    @property
    def digest(self) -> str:
        return _digest_for("omarchy-candidate-admission/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"version": "candidate-admission/v1", "inventory_digest": self.inventory_digest, "evidence": self.evidence.to_dict(), "target": self.target.to_dict(), "admitted_at": self.admitted_at}


class PlanningAuthority:
    """Trusted in-process composition-root capability for I-03.

    The configured pins and statuses are a caller-selected trust root for this
    process only.  A separately created authority is not interchangeable, and
    this class makes no cryptographic, durable, or cross-process trust claim.
    """

    def __init__(
        self,
        *,
        f02_digest: str,
        q00_digest: str,
        q01_digest: str,
        f05_digest: str,
        candidate_digest: str,
        manifest_digest: str,
        schema_digest: str,
        f02_status: QualificationState,
        q00_status: QualificationState,
        q01_status: QualificationState,
        f05_status: QualificationState,
    ) -> None:
        self.__digests = tuple((value, label) for value, label in ((f02_digest, "F-02"), (q00_digest, "Q-00"), (q01_digest, "Q-01"), (f05_digest, "F-05"), (candidate_digest, "candidate"), (manifest_digest, "manifest"), (schema_digest, "schema")))
        for value, label in self.__digests:
            _strict_digest(value, label)
        self.__statuses = (f02_status, q00_status, q01_status, f05_status)
        for status, label in zip(self.__statuses, ("F-02", "Q-00", "Q-01", "F-05")):
            _enum(status, QualificationState, label)
        self.__lock = threading.Lock()
        self.__evidence: dict[int, tuple[CandidateEvidence, str]] = {}
        self.__admissions: dict[int, tuple[CandidateAdmission, str]] = {}
        self.__plans: dict[int, tuple[ReadOnlyInstallerPlan, str]] = {}

    def admit(self, inventory: InventoryObservation, request: CandidateRequest, now: int) -> CandidateAdmission:
        if not isinstance(inventory, InventoryObservation) or not isinstance(request, CandidateRequest):
            raise CandidateAdmissionError("inventory and request are required")
        _strict_time(now, "admission")
        evidence = object.__new__(CandidateEvidence)
        for name, value in (
            ("f02_digest", self.__digests[0][0]), ("q00_digest", self.__digests[1][0]),
            ("q01_digest", self.__digests[2][0]), ("f05_digest", self.__digests[3][0]),
            ("candidate_digest", self.__digests[4][0]), ("manifest_digest", self.__digests[5][0]),
            ("schema_digest", self.__digests[6][0]), ("f02_status", self.__statuses[0]),
            ("q00_status", self.__statuses[1]), ("q01_status", self.__statuses[2]),
            ("f05_status", self.__statuses[3]),
        ):
            object.__setattr__(evidence, name, value)
        evidence.__post_init__()
        if now < inventory.observed_at or now - inventory.observed_at > MAX_OBSERVATION_AGE:
            raise CandidateAdmissionError("inventory observation is stale")
        if inventory.machine.qualification is not QualificationState.QUALIFIED or inventory.board.qualification is not QualificationState.QUALIFIED:
            raise CandidateAdmissionError("machine or board is not qualified")
        if (request.machine_id, request.board_id) != (inventory.machine.machine_id, inventory.board.board_id):
            raise CandidateAdmissionError("request machine binding mismatch")
        if (request.candidate_digest, request.manifest_digest, request.schema_digest) != (evidence.candidate_digest, evidence.manifest_digest, evidence.schema_digest):
            raise CandidateAdmissionError("candidate input digest binding mismatch")
        if any(status is not QualificationState.QUALIFIED for status in (evidence.f02_status, evidence.q00_status, evidence.q01_status, evidence.f05_status)):
            raise CandidateAdmissionError("candidate evidence is unknown or not qualified")
        disks = tuple(disk for disk in inventory.disks if disk.disk_id == request.disk_id)
        containers = tuple(container for container in inventory.containers if container.container_id == request.container_id and container.disk_id == request.disk_id)
        volumes = tuple(volume for volume in inventory.volumes if volume.volume_id == request.volume_id and volume.container_id == request.container_id)
        if len(disks) != 1 or len(containers) != 1 or len(volumes) != 1:
            raise TargetError("target is missing or ambiguous")
        disk, container, volume = disks[0], containers[0], volumes[0]
        if disk.media is not MediaKind.INTERNAL:
            raise TargetError("external target is not admissible")
        resources = (disk, container, volume)
        if any(item.mount is not MountState.UNMOUNTED or item.busy is not BusyState.IDLE or item.encryption is not EncryptionState.CLEAR or item.qualification is not QualificationState.QUALIFIED for item in resources):
            raise TargetError("target is mounted, busy, encrypted, unknown, or not qualified")
        target = TargetIdentity(inventory.machine.machine_id, inventory.board.board_id, disk.disk_id, disk.geometry, container.container_id, container.geometry, volume.volume_id, volume.geometry)
        admission = object.__new__(CandidateAdmission)
        object.__setattr__(admission, "inventory_digest", inventory.digest)
        object.__setattr__(admission, "evidence", evidence)
        object.__setattr__(admission, "target", target)
        object.__setattr__(admission, "admitted_at", now)
        with self.__lock:
            self.__evidence[id(evidence)] = (evidence, evidence.digest)
            self.__admissions[id(admission)] = (admission, admission.digest)
        return admission

    def _verify_admission_locked(self, admission: CandidateAdmission) -> None:
        record = self.__admissions.get(id(admission))
        if record is None or record[0] is not admission:
            raise PlannerAuthorityError("candidate admission is unregistered or changed")
        try:
            admission_digest = admission.digest
            evidence = admission.evidence
        except Exception as exc:
            raise PlannerAuthorityError("candidate admission is malformed") from exc
        if admission_digest != record[1]:
            raise PlannerAuthorityError("candidate admission is unregistered or changed")
        evidence_record = self.__evidence.get(id(evidence))
        try:
            evidence_digest = evidence.digest
        except Exception as exc:
            raise PlannerAuthorityError("candidate evidence is malformed") from exc
        if evidence_record is None or evidence_record[0] is not evidence or evidence_digest != evidence_record[1]:
            raise PlannerAuthorityError("candidate evidence is unregistered or changed")

    def verify_admission(self, admission: CandidateAdmission) -> None:
        if not isinstance(admission, CandidateAdmission):
            raise PlannerAuthorityError("candidate admission is required")
        with self.__lock:
            self._verify_admission_locked(admission)

    def generate_plan(self, admission: CandidateAdmission, artifact: Artifact, document_digest: str) -> ReadOnlyInstallerPlan:
        if not isinstance(admission, CandidateAdmission) or not isinstance(artifact, Artifact):
            raise PlannerAuthorityError("admission and artifact are required")
        _strict_digest(document_digest, "document")
        with self.__lock:
            self._verify_admission_locked(admission)
            admission_digest = admission.digest
            target_digest = admission.target.digest
            target = admission.target
            evidence = admission.evidence
            operation_id = "op-" + _digest_for("omarchy-operation/v1", {"admission": admission_digest, "artifact": artifact.digest, "document": document_digest})[:32]
            tx_plan = InstallerPlan(operation_id, DiskIdentity(target.disk_id, target.disk_geometry.size_bytes), ContainerIdentity(target.container_id, target.disk_id, target.container_geometry.size_bytes), VolumeIdentity(target.volume_id, target.container_id, target.volume_geometry.size_bytes), artifact, document_digest, (PlanStep("acquire", ActionKind.ACQUIRE_ARTIFACT, target.volume_id, "acquire verified artifact"), PlanStep("provision", ActionKind.PROVISION_VOLUME, target.volume_id, "provision target volume"), PlanStep("boot", ActionKind.CONFIGURE_BOOT, target.volume_id, "configure verified boot"), PlanStep("verify", ActionKind.VERIFY_RESULT, target.volume_id, "verify planned result")))
            plan = object.__new__(ReadOnlyInstallerPlan)
            object.__setattr__(plan, "transaction_plan", tx_plan)
            object.__setattr__(plan, "target", target)
            object.__setattr__(plan, "admission_digest", admission_digest)
            object.__setattr__(plan, "candidate_digest", evidence.candidate_digest)
            object.__setattr__(plan, "manifest_digest", evidence.manifest_digest)
            object.__setattr__(plan, "schema_digest", evidence.schema_digest)
            object.__setattr__(plan, "destructive_operations", tuple(sorted((DestructiveOperation.CONFIGURE_BOOT, DestructiveOperation.PROVISION_VOLUME), key=lambda item: item.value)))
            plan.__post_init__()
            if admission.digest != admission_digest or admission.target.digest != target_digest:
                raise PlannerAuthorityError("admission changed during plan generation")
            self.__plans[id(plan)] = (plan, plan.digest)
            return plan

    def verify_plan(self, plan: ReadOnlyInstallerPlan) -> None:
        if not isinstance(plan, ReadOnlyInstallerPlan):
            raise PlannerAuthorityError("installer plan is required")
        with self.__lock:
            record = self.__plans.get(id(plan))
            if record is None or record[0] is not plan:
                raise PlannerAuthorityError("installer plan is unregistered or changed")
            try:
                digest = plan.digest
            except Exception as exc:
                raise PlannerAuthorityError("installer plan is malformed") from exc
            if digest != record[1]:
                raise PlannerAuthorityError("installer plan is unregistered or changed")


@dataclass(frozen=True, slots=True, init=False)
class ReadOnlyInstallerPlan:
    transaction_plan: InstallerPlan
    target: TargetIdentity
    admission_digest: str
    candidate_digest: str
    manifest_digest: str
    schema_digest: str
    destructive_operations: tuple[DestructiveOperation, ...]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise PlannerAuthorityError("installer plans must be generated from admitted candidates")

    def __post_init__(self) -> None:
        if not isinstance(self.transaction_plan, InstallerPlan) or not isinstance(self.target, TargetIdentity):
            raise PlannerAuthorityError("plan must contain transaction plan and target")
        _strict_digest(self.admission_digest, "admission")
        for value, label in ((self.candidate_digest, "candidate"), (self.manifest_digest, "manifest"), (self.schema_digest, "schema")):
            _strict_digest(value, label)
        if not isinstance(self.destructive_operations, tuple) or self.destructive_operations != tuple(sorted(self.destructive_operations, key=lambda item: item.value)) or not self.destructive_operations or len(set(self.destructive_operations)) != len(self.destructive_operations) or any(not isinstance(item, DestructiveOperation) for item in self.destructive_operations):
            raise PlannerAuthorityError("destructive operation set is not closed")
        if self.transaction_plan.disk.stable_id != self.target.disk_id or self.transaction_plan.container.stable_id != self.target.container_id or self.transaction_plan.volume.stable_id != self.target.volume_id:
            raise PlannerAuthorityError("plan target binding mismatch")

    @property
    def plan_digest(self) -> str:
        return self.transaction_plan.digest

    @property
    def digest(self) -> str:
        return _digest_for("omarchy-readonly-installer-plan/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"version": "readonly-installer-plan/v1", "transaction_plan": self.transaction_plan.to_dict(), "target": self.target.to_dict(), "admission_digest": self.admission_digest, "candidate_digest": self.candidate_digest, "manifest_digest": self.manifest_digest, "schema_digest": self.schema_digest, "destructive_operations": [item.value for item in self.destructive_operations]}


def generate_installer_plan(authority: PlanningAuthority, admission: CandidateAdmission, artifact: Artifact, document_digest: str) -> ReadOnlyInstallerPlan:
    """Thin public delegator; assembly and registration stay in the authority."""
    if not isinstance(authority, PlanningAuthority):
        raise PlannerAuthorityError("planning authority is required")
    return authority.generate_plan(admission, artifact, document_digest)


@dataclass(frozen=True, slots=True, init=False)
class FinalConsent:
    plan_digest: str
    plan_envelope_digest: str
    target_digest: str
    destructive_operations: tuple[DestructiveOperation, ...]
    candidate_digest: str
    manifest_digest: str
    schema_digest: str
    readiness_attestation_digest: str
    issued_at: int
    expires_at: int
    consent_id: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ConsentError("final consent must be issued by its authority")

    def __post_init__(self) -> None:
        _strict_digest(self.plan_digest, "plan")
        _strict_digest(self.plan_envelope_digest, "plan envelope")
        _strict_digest(self.target_digest, "target")
        _strict_digest(self.candidate_digest, "candidate")
        _strict_digest(self.manifest_digest, "manifest")
        _strict_digest(self.schema_digest, "schema")
        _strict_digest(self.readiness_attestation_digest, "readiness attestation")
        _strict_time(self.issued_at, "consent issue")
        _strict_time(self.expires_at, "consent expiry")
        if self.expires_at <= self.issued_at or self.expires_at - self.issued_at > MAX_CONSENT_LIFETIME:
            raise ConsentError("invalid consent lifetime")
        _strict_id(self.consent_id, "consent identity")

    @property
    def digest(self) -> str:
        return _digest_for("omarchy-final-consent/v1", self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"version": "final-consent/v1", "plan_digest": self.plan_digest, "plan_envelope_digest": self.plan_envelope_digest, "target_digest": self.target_digest, "destructive_operations": [item.value for item in self.destructive_operations], "candidate_digest": self.candidate_digest, "manifest_digest": self.manifest_digest, "schema_digest": self.schema_digest, "readiness_attestation_digest": self.readiness_attestation_digest, "issued_at": self.issued_at, "expires_at": self.expires_at, "consent_id": self.consent_id}


class ConsentAuthority:
    """In-process one-time final-consent authority; no durable claims."""

    def __init__(self, planning_authority: PlanningAuthority) -> None:
        if not isinstance(planning_authority, PlanningAuthority):
            raise PlannerAuthorityError("consent authority requires planning authority")
        self.__planning_authority = planning_authority
        self.__lock = threading.Lock()
        self.__issued: dict[str, FinalConsent] = {}
        self.__consumed: set[str] = set()

    def issue(self, plan: ReadOnlyInstallerPlan, decision: ReadinessDecision, readiness_authority: ConsumptionAuthority, now: int, expires_at: int) -> FinalConsent:
        if not isinstance(plan, ReadOnlyInstallerPlan) or not isinstance(decision, ReadinessDecision) or not isinstance(readiness_authority, ConsumptionAuthority):
            raise PlannerAuthorityError("plan, readiness decision, and readiness authority are required")
        self.__planning_authority.verify_plan(plan)
        _strict_time(now, "consent issue")
        _strict_time(expires_at, "consent expiry")
        if expires_at <= now or expires_at - now > MAX_CONSENT_LIFETIME:
            raise ConsentError("invalid consent lifetime")
        if (decision.machine_id, decision.board_id) != (plan.target.machine_id, plan.target.board_id) or decision.plan_digest != plan.plan_digest or not decision.ready:
            raise PlannerAuthorityError("readiness is not bound to exact plan")
        try:
            attestation = require_readiness_for_i01(decision, plan.target.machine_id, decision.board_id, plan.plan_digest, now, readiness_authority)
        except (CredentialBindingError, CredentialReadinessError) as exc:
            raise PlannerAuthorityError("readiness authority denied exact plan") from exc
        consent_id = "consent-" + _digest_for("omarchy-consent-id/v1", {"plan": plan.digest, "attestation": attestation.digest, "issued_at": now})[:32]
        consent = object.__new__(FinalConsent)
        object.__setattr__(consent, "plan_digest", plan.plan_digest)
        object.__setattr__(consent, "plan_envelope_digest", plan.digest)
        object.__setattr__(consent, "target_digest", plan.target.digest)
        object.__setattr__(consent, "destructive_operations", plan.destructive_operations)
        object.__setattr__(consent, "candidate_digest", plan.candidate_digest)
        object.__setattr__(consent, "manifest_digest", plan.manifest_digest)
        object.__setattr__(consent, "schema_digest", plan.schema_digest)
        object.__setattr__(consent, "readiness_attestation_digest", attestation.digest)
        object.__setattr__(consent, "issued_at", now)
        object.__setattr__(consent, "expires_at", expires_at)
        object.__setattr__(consent, "consent_id", consent_id)
        consent.__post_init__()
        with self.__lock:
            self.__issued[consent.digest] = consent
        return consent

    def consume(self, consent: FinalConsent, plan: ReadOnlyInstallerPlan, now: int) -> Consent:
        if not isinstance(consent, FinalConsent) or not isinstance(plan, ReadOnlyInstallerPlan):
            raise ConsentError("consent and exact plan are required")
        _strict_time(now, "consent use")
        if now < consent.issued_at or now >= consent.expires_at:
            raise ConsentExpiredError("final consent is expired")
        if consent.plan_digest != plan.plan_digest or consent.plan_envelope_digest != plan.digest or consent.target_digest != plan.target.digest or consent.destructive_operations != plan.destructive_operations or (consent.candidate_digest, consent.manifest_digest, consent.schema_digest) != (plan.candidate_digest, plan.manifest_digest, plan.schema_digest):
            raise ConsentError("consent substitution or replay binding mismatch")
        with self.__lock:
            if self.__issued.get(consent.digest) is not consent:
                raise ConsentError("consent is not issued by this authority")
            if consent.digest in self.__consumed:
                raise ConsentConsumedError("final consent was already consumed")
            self.__consumed.add(consent.digest)
        return Consent(plan.transaction_plan.operation_id, plan.plan_digest, plan.transaction_plan.document_digest, plan.transaction_plan.artifact.digest, consent.consent_id)


def issue_final_consent(consent_authority: ConsentAuthority, plan: ReadOnlyInstallerPlan, decision: ReadinessDecision, readiness_authority: ConsumptionAuthority, now: int, expires_at: int) -> FinalConsent:
    if not isinstance(consent_authority, ConsentAuthority):
        raise PlannerAuthorityError("consent authority is required")
    return consent_authority.issue(plan, decision, readiness_authority, now, expires_at)


# Compatibility names for callers using the vocabulary from the I-03 design.
APFSContainer = APFSContainerObservation
MachineIdentityObservation = MachineObservation
BoardIdentityObservation = BoardObservation
DiskIdentityObservation = DiskObservation
VolumeIdentityObservation = VolumeObservation
Candidate = CandidateRequest
Admission = CandidateAdmission
PlannerPlan = ReadOnlyInstallerPlan
FinalConsentAuthority = ConsentAuthority
parse_inventory = parse_inventory_json
build_installer_plan = generate_installer_plan


__all__ = [
    "APFSContainer", "APFSContainerObservation", "Admission", "BoardIdentityObservation", "BoardObservation", "BusyState", "Candidate", "CandidateAdmission", "CandidateAdmissionError", "CandidateEvidence", "CandidateRequest", "ConsentAuthority", "ConsentConsumedError", "ConsentError", "ConsentExpiredError", "DestructiveOperation", "DiskIdentityObservation", "DiskObservation", "EncryptionState", "FinalConsent", "FinalConsentAuthority", "Geometry", "InputBoundsError", "InputSchemaError", "InventoryObservation", "MachineIdentityObservation", "MachineObservation", "MediaKind", "MountState", "ObservationError", "PlanningAuthority", "PlannerError", "PlannerAuthorityError", "PlannerPlan", "QualificationState", "ReadOnlyInstallerPlan", "TargetError", "TargetIdentity", "VolumeIdentityObservation", "VolumeObservation", "build_installer_plan", "generate_installer_plan", "issue_final_consent", "parse_inventory", "parse_inventory_json",
]
