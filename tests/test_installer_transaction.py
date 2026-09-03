import json
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from installer_transaction import (  # noqa: E402
    ActionKind,
    ALLOWED_TRANSITIONS,
    AmbiguousTargetError,
    Artifact,
    Consent,
    ConsentError,
    ContainerIdentity,
    DiskIdentity,
    InstallerPlan,
    InstallerTransaction,
    Journal,
    JournalEntry,
    JournalIntegrityError,
    MutationError,
    Phase,
    PlanStep,
    RecoveryRequiredError,
    RestartDecision,
    SecretLeakError,
    TransitionError,
    VolumeIdentity,
    resolve_single_target,
)


def make_plan(operation_id="op-test-1"):
    disk = DiskIdentity("disk-stable-1", 100_000_000_000)
    container = ContainerIdentity("container-stable-1", disk.stable_id, 80_000_000_000)
    volume = VolumeIdentity("volume-stable-1", container.stable_id, 60_000_000_000)
    artifact = Artifact("omarchy-image", "a" * 64, 1_000_000)
    steps = (
        # Descriptions are labels only; no path or deletion authority exists.
        PlanStep("acquire", ActionKind.ACQUIRE_ARTIFACT, volume.stable_id, "acquire verified image"),
        PlanStep("provision", ActionKind.PROVISION_VOLUME, volume.stable_id, "provision target volume"),
    )
    return InstallerPlan(operation_id, disk, container, volume, artifact, "b" * 64, steps)


class TransactionTests(unittest.TestCase):
    def test_closed_plan_and_journal(self):
        plan = make_plan()
        with self.assertRaises(FrozenInstanceError):
            plan.operation_id = "other"
        tx = InstallerTransaction.start(plan)
        with self.assertRaises(FrozenInstanceError):
            tx.journal = Journal()

    def test_exact_phase_order_and_consent_gate(self):
        plan = make_plan()
        tx = InstallerTransaction.start(plan)
        tx = tx.advance(Phase.ADMISSION).advance(Phase.ACQUISITION).advance(Phase.PLAN_READY).advance(Phase.FINAL_CONSENT)
        with self.assertRaises(ConsentError):
            tx.advance(Phase.MUTATION_STARTED)
        with self.assertRaises(TransitionError):
            tx.advance(Phase.PROVISIONED)
        consent = Consent(tx.plan.operation_id, tx.plan.digest, tx.plan.document_digest, tx.plan.artifact.digest)
        tx = tx.advance(Phase.MUTATION_STARTED, consent)
        self.assertEqual(tx.phase, Phase.MUTATION_STARTED)
        self.assertEqual(tx.status, "in_progress")

    def test_stale_consent_and_no_false_success(self):
        plan = make_plan()
        tx = InstallerTransaction.start(plan)
        for phase in (Phase.ADMISSION, Phase.ACQUISITION, Phase.PLAN_READY, Phase.FINAL_CONSENT):
            tx = tx.advance(phase)
        stale = Consent(plan.operation_id, "c" * 64, plan.document_digest, plan.artifact.digest)
        with self.assertRaises(ConsentError):
            tx.advance(Phase.MUTATION_STARTED, stale)
        consent = Consent(plan.operation_id, plan.digest, plan.document_digest, plan.artifact.digest)
        tx = tx.advance(Phase.MUTATION_STARTED, consent).record_step_started("acquire").record_step_completed("acquire")
        with self.assertRaises(MutationError):
            tx.report_success()
        self.assertNotEqual(tx.status, "success")

    def test_idempotent_steps_and_mid_step_resume(self):
        plan = make_plan()
        tx = InstallerTransaction.start(plan)
        for phase in (Phase.ADMISSION, Phase.ACQUISITION, Phase.PLAN_READY, Phase.FINAL_CONSENT):
            tx = tx.advance(phase)
        consent = Consent(plan.operation_id, plan.digest, plan.document_digest, plan.artifact.digest)
        tx = tx.advance(Phase.MUTATION_STARTED, consent).record_step_started("acquire")
        self.assertIs(tx.record_step_started("acquire"), tx)
        resumed = InstallerTransaction.start(plan).resume(tx.journal)
        self.assertEqual(resumed.restart_decision, RestartDecision.RESUME_SAFE)
        resumed = resumed.record_step_completed("acquire").record_step_started("provision").record_step_completed("provision")
        self.assertEqual(resumed._completed_steps, {"acquire", "provision"})

    def test_hash_chain_detects_deletion_reorder_and_tamper(self):
        plan = make_plan()
        tx = InstallerTransaction.start(plan).advance(Phase.ADMISSION)
        entries = list(tx.journal.entries)
        with self.assertRaises(JournalIntegrityError):
            Journal(tuple(entries[:-1]))
        with self.assertRaises(JournalIntegrityError):
            Journal(tuple(reversed(entries)))
        changed = entries[1]
        entries[1] = JournalEntry(changed.sequence, changed.operation_id, changed.phase, changed.event, changed.payload, changed.previous_hash, "0" * 64)
        with self.assertRaises(JournalIntegrityError):
            Journal(tuple(entries))

    def test_replayed_journal_rejects_skipped_phase(self):
        plan = make_plan()
        journal = InstallerTransaction.start(plan).journal
        journal = journal.append(plan.operation_id, Phase.PLAN_READY, "PHASE", {})
        with self.assertRaises(JournalIntegrityError):
            InstallerTransaction(plan, journal)

    def test_journal_round_trip_and_closed_transition_table(self):
        plan = make_plan()
        journal = InstallerTransaction.start(plan).advance(Phase.ADMISSION).journal
        self.assertEqual(Journal.from_json(journal.to_json()), journal)
        self.assertEqual(ALLOWED_TRANSITIONS[Phase.COMMITTED], frozenset())

    def test_wrong_identity_and_ambiguous_target(self):
        with self.assertRaises(AmbiguousTargetError):
            resolve_single_target([])
        with self.assertRaises(AmbiguousTargetError):
            resolve_single_target([DiskIdentity("a", 1), DiskIdentity("b", 1)])
        disk = DiskIdentity("disk", 100)
        with self.assertRaises(Exception):
            InstallerPlan("op", disk, ContainerIdentity("container", "other-disk", 50), VolumeIdentity("volume", "container", 20), Artifact("a", "a" * 64, 1), "b" * 64, (PlanStep("step", ActionKind.VERIFY_RESULT, "volume", "verify"),))

    def test_rollback_gap_and_recovery(self):
        plan = make_plan()
        tx = InstallerTransaction.start(plan)
        for phase in (Phase.ADMISSION, Phase.ACQUISITION, Phase.PLAN_READY, Phase.FINAL_CONSENT):
            tx = tx.advance(phase)
        consent = Consent(plan.operation_id, plan.digest, plan.document_digest, plan.artifact.digest)
        tx = tx.advance(Phase.MUTATION_STARTED, consent).record_step_started("acquire").record_step_completed("acquire")
        tx = tx.fail_after_mutation("provider_failure")
        self.assertEqual(tx.restart_decision, RestartDecision.ROLLBACK_REQUIRED)
        with self.assertRaises(RecoveryRequiredError):
            tx.mark_rolled_back()
        tx = tx.record_compensation("acquire", ActionKind.VERIFY_RESULT, "restore checkpoint")
        self.assertEqual(tx.mark_rolled_back().phase, Phase.ROLLED_BACK)

    def test_secret_redaction_and_path_free_serialization(self):
        with self.assertRaises(SecretLeakError):
            Journal().append("op", Phase.INVENTORY, "EVENT", {"access_token": "secret"})
        plan = make_plan()
        serialized = json.dumps(plan.to_dict())
        self.assertNotIn("/", serialized)
        self.assertNotIn("delete", serialized.lower())


if __name__ == "__main__":
    unittest.main()
