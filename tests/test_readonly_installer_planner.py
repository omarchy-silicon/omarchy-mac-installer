import hashlib
import json
import sys
import unittest
from copy import copy, deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from credential_states import (  # noqa: E402
    AuthorizationKind,
    AuthorizationReceipt,
    ConsumptionAuthority,
    CredentialState,
    DataVolumeLockState,
    FileVaultState,
    LinuxEncryptionState,
    MacOSAdministratorState,
    MachineOwnerState,
    OneTRState,
    PairedRecoveryOSState,
    ReceiptLedger,
    REQUIRED_STATE_ORDER,
    ReadinessDecision,
)
from installer_transaction import Artifact  # noqa: E402
from readonly_installer_planner import (  # noqa: E402
    APFSContainerObservation,
    BoardObservation,
    BusyState,
    CandidateAdmission,
    CandidateAdmissionError,
    CandidateEvidence,
    CandidateRequest,
    ConsentConsumedError,
    ConsentAuthority,
    DiskObservation,
    EncryptionState,
    Geometry,
    InputSchemaError,
    InputBoundsError,
    InventoryObservation,
    MachineObservation,
    MediaKind,
    MountState,
    ObservationError,
    QualificationState,
    PlanningAuthority,
    PlannerAuthorityError,
    TargetError,
    VolumeObservation,
    generate_installer_plan,
    parse_inventory_json,
)


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def make_inventory(**changes):
    machine = MachineObservation("machine-1", 1000, QualificationState.QUALIFIED)
    board = BoardObservation("board-1", "machine-1", QualificationState.QUALIFIED)
    disk = DiskObservation("disk-1", "machine-1", Geometry(0, 1000), MediaKind.INTERNAL, MountState.UNMOUNTED, BusyState.IDLE, EncryptionState.CLEAR, QualificationState.QUALIFIED)
    container = APFSContainerObservation("container-1", "machine-1", "disk-1", Geometry(100, 800), MountState.UNMOUNTED, BusyState.IDLE, EncryptionState.CLEAR, QualificationState.QUALIFIED)
    volume = VolumeObservation("volume-1", "machine-1", "container-1", Geometry(200, 600), MountState.UNMOUNTED, BusyState.IDLE, EncryptionState.CLEAR, QualificationState.QUALIFIED)
    return InventoryObservation(machine, board, (disk,), (container,), (volume,))


def make_admission(now=1100, **request_changes):
    inventory = make_inventory()
    values = {"machine_id": "machine-1", "board_id": "board-1", "disk_id": "disk-1", "container_id": "container-1", "volume_id": "volume-1", "candidate_digest": digest("candidate"), "manifest_digest": digest("manifest"), "schema_digest": digest("schema")}
    values.update(request_changes)
    request = CandidateRequest(**values)
    authority = PlanningAuthority(
        f02_digest=digest("f02"), q00_digest=digest("q00"), q01_digest=digest("q01"), f05_digest=digest("f05"),
        candidate_digest=values["candidate_digest"], manifest_digest=values["manifest_digest"], schema_digest=values["schema_digest"],
        f02_status=QualificationState.QUALIFIED, q00_status=QualificationState.QUALIFIED,
        q01_status=QualificationState.QUALIFIED, f05_status=QualificationState.QUALIFIED,
    )
    return authority, authority.admit(inventory, request, now)


class PlannerTests(unittest.TestCase):
    def test_public_surface_and_import_star(self):
        namespace = {}
        exec("from readonly_installer_planner import *", namespace)
        self.assertIs(namespace["PlanningAuthority"], PlanningAuthority)
        self.assertNotIn("_derive", vars(CandidateEvidence))
        self.assertNotIn("_derive", vars(CandidateAdmission))
        self.assertNotIn("_register", vars(PlanningAuthority))
        self.assertNotIn("_register_plan", vars(PlanningAuthority))
        self.assertNotIn("issue_evidence", vars(PlanningAuthority))

    def test_closed_inventory_and_identity(self):
        _, admission = make_admission()
        self.assertEqual(admission.target.board_id, "board-1")
        with self.assertRaises(FrozenInstanceError):
            admission.target.machine_id = "other"
        with self.assertRaises(CandidateAdmissionError):
            CandidateAdmission("bad")

    def test_json_is_strict_and_bound(self):
        document = make_inventory().to_dict()
        parsed = parse_inventory_json(json.dumps(document))
        self.assertEqual(parsed.digest, make_inventory().digest)
        with self.assertRaises(InputSchemaError):
            parse_inventory_json(json.dumps({**document, "extra": True}))
        with self.assertRaises(InputSchemaError):
            parse_inventory_json(json.dumps(document).replace('1000', '1.0'))
        duplicate = '{"version":"inventory-observation/v1","version":"inventory-observation/v1"}'
        with self.assertRaises(InputSchemaError):
            parse_inventory_json(duplicate)
        with self.assertRaises(InputSchemaError):
            parse_inventory_json("\ud800")
        with self.assertRaises(InputBoundsError):
            parse_inventory_json("[" * 2000 + "0" + "]" * 2000)

    def test_geometry_is_checked_only_within_one_parent(self):
        inventory = make_inventory()
        disk_two = DiskObservation("disk-2", "machine-1", Geometry(0, 1000), MediaKind.INTERNAL, MountState.UNMOUNTED, BusyState.IDLE, EncryptionState.CLEAR, QualificationState.QUALIFIED)
        container_two = APFSContainerObservation("container-2", "machine-1", "disk-2", Geometry(100, 800), MountState.UNMOUNTED, BusyState.IDLE, EncryptionState.CLEAR, QualificationState.QUALIFIED)
        InventoryObservation(inventory.machine, inventory.board, (inventory.disks[0], disk_two), (inventory.containers[0], container_two), inventory.volumes)
        disjoint = APFSContainerObservation("container-2", "machine-1", "disk-1", Geometry(0, 100), MountState.UNMOUNTED, BusyState.IDLE, EncryptionState.CLEAR, QualificationState.QUALIFIED)
        InventoryObservation(inventory.machine, inventory.board, inventory.disks, (inventory.containers[0], disjoint), ())
        overlapping = APFSContainerObservation("container-2", "machine-1", "disk-1", Geometry(500, 500), MountState.UNMOUNTED, BusyState.IDLE, EncryptionState.CLEAR, QualificationState.QUALIFIED)
        with self.assertRaises(ObservationError):
            InventoryObservation(inventory.machine, inventory.board, inventory.disks, (inventory.containers[0], overlapping), ())

    def test_admission_rejects_stale_external_and_unknown(self):
        with self.assertRaises(CandidateAdmissionError):
            make_admission(now=1401)
        authority, _ = make_admission()
        inventory = make_inventory()
        external = DiskObservation("disk-1", "machine-1", Geometry(0, 1000), MediaKind.EXTERNAL, MountState.UNMOUNTED, BusyState.IDLE, EncryptionState.CLEAR, QualificationState.QUALIFIED)
        with self.assertRaises(TargetError):
            authority.admit(InventoryObservation(inventory.machine, inventory.board, (external,), inventory.containers, inventory.volumes), CandidateRequest("machine-1", "board-1", "disk-1", "container-1", "volume-1", digest("candidate"), digest("manifest"), digest("schema")), 1100)

    def test_plan_is_deterministic_and_target_bound(self):
        authority, admission = make_admission()
        artifact = Artifact("image", digest("image"), 100)
        first = generate_installer_plan(authority, admission, artifact, digest("document"))
        second = generate_installer_plan(authority, admission, artifact, digest("document"))
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.plan_digest, first.transaction_plan.digest)
        self.assertEqual(tuple(item.value for item in first.destructive_operations), ("CONFIGURE_BOOT", "PROVISION_VOLUME"))
        with self.assertRaises(FrozenInstanceError):
            first.target = first.target

    def test_authority_rejects_fabrication_copy_tamper_and_cross_authority(self):
        authority, admission = make_admission()
        with self.assertRaises(CandidateAdmissionError):
            CandidateEvidence(digest("f02"), digest("q00"), digest("q01"), digest("f05"), digest("candidate"), digest("manifest"), digest("schema"), QualificationState.QUALIFIED, QualificationState.QUALIFIED, QualificationState.QUALIFIED, QualificationState.QUALIFIED)
        forged_admission = object.__new__(type(admission))
        with self.assertRaises(PlannerAuthorityError):
            authority.verify_admission(forged_admission)
        for name in ("inventory_digest", "evidence", "target", "admitted_at"):
            object.__setattr__(forged_admission, name, getattr(admission, name))
        with self.assertRaises(PlannerAuthorityError):
            authority.verify_admission(forged_admission)
        with self.assertRaises(PlannerAuthorityError):
            authority.verify_admission(copy(admission))
        with self.assertRaises(PlannerAuthorityError):
            authority.verify_admission(deepcopy(admission))
        object.__setattr__(admission, "admitted_at", admission.admitted_at + 1)
        with self.assertRaises(PlannerAuthorityError):
            authority.verify_admission(admission)
        other, other_admission = make_admission()
        with self.assertRaises(PlannerAuthorityError):
            generate_installer_plan(other, admission, Artifact("image", digest("image"), 100), digest("document"))
        plan = generate_installer_plan(other, other_admission, Artifact("image", digest("image"), 100), digest("document"))
        forged_plan = object.__new__(type(plan))
        with self.assertRaises(PlannerAuthorityError):
            other.verify_plan(forged_plan)
        for name in ("transaction_plan", "target", "admission_digest", "candidate_digest", "manifest_digest", "schema_digest", "destructive_operations"):
            object.__setattr__(forged_plan, name, getattr(plan, name))
        with self.assertRaises(PlannerAuthorityError):
            other.verify_plan(forged_plan)
        with self.assertRaises(PlannerAuthorityError):
            other.verify_plan(copy(plan))
        with self.assertRaises(PlannerAuthorityError):
            other.verify_plan(deepcopy(plan))

    def test_consent_is_readiness_bound_and_one_time(self):
        authority, admission = make_admission()
        artifact = Artifact("image", digest("image"), 100)
        plan = generate_installer_plan(authority, admission, artifact, digest("document"))
        now = 1100
        receipts = (
            AuthorizationReceipt.issue(AuthorizationKind.MACOS_ADMINISTRATOR, "machine-1", "board-1", plan.plan_digest, now - 1, now + 100, "admin-receipt"),
            AuthorizationReceipt.issue(AuthorizationKind.MACHINE_OWNER, "machine-1", "board-1", plan.plan_digest, now - 1, now + 100, "owner-receipt"),
        )
        state = CredentialState("machine-1", "board-1", plan.plan_digest, FileVaultState.ENABLED, DataVolumeLockState.UNLOCKED, MacOSAdministratorState.AUTHORIZED, MachineOwnerState.AUTHORIZED, LinuxEncryptionState.VERIFIED, PairedRecoveryOSState.PAIRED, OneTRState.READY, receipts)
        ledger = ReceiptLedger()
        readiness = ReadinessDecision.from_state(state, now, ledger, REQUIRED_STATE_ORDER)
        readiness_authority = ConsumptionAuthority(ledger)
        consent_authority = ConsentAuthority(authority)
        consent = consent_authority.issue(plan, readiness, readiness_authority, now, now + 100)
        with self.assertRaises(PlannerAuthorityError):
            consent_authority.consume(consent, copy(plan), now + 1)
        tx_consent = consent_authority.consume(consent, plan, now + 1)
        self.assertEqual(tx_consent.plan_digest, plan.plan_digest)
        with self.assertRaises(ConsentConsumedError):
            consent_authority.consume(consent, plan, now + 1)


if __name__ == "__main__":
    unittest.main()
