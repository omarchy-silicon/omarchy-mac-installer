import json
import sys
import threading
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from credential_states import (  # noqa: E402
    AuthorizationKind,
    AuthorizationReceipt,
    ConsumptionAuthority,
    CredentialBindingError,
    CredentialReadinessError,
    CredentialReceiptError,
    CredentialDependencyError,
    ReadinessAlreadyConsumedError,
    ReadinessAuthorityStateError,
    ReadinessExpiredError,
    CredentialSecretError,
    CredentialState,
    CredentialTypeError,
    DataVolumeLockState,
    FileVaultState,
    LinuxEncryptionState,
    MacOSAdministratorState,
    MachineOwnerState,
    OneTRState,
    PairedRecoveryOSState,
    ReadinessBlocker,
    ReadinessAttestation,
    ReadinessDecision,
    ReceiptLedger,
    REQUIRED_STATE_ORDER,
    canonical_bytes,
    require_readiness_for_i01,
)


MACHINE = "machine-1"
BOARD = "board-m2"
PLAN = "a" * 64


def receipt(kind: AuthorizationKind, receipt_id: str = "opaque-handle-1") -> AuthorizationReceipt:
    return AuthorizationReceipt.issue(kind, MACHINE, BOARD, PLAN, 100, 200, receipt_id)


def ready_state(*receipts: AuthorizationReceipt) -> CredentialState:
    return CredentialState(
        MACHINE,
        BOARD,
        PLAN,
        FileVaultState.ENABLED,
        DataVolumeLockState.UNLOCKED,
        MacOSAdministratorState.AUTHORIZED,
        MachineOwnerState.AUTHORIZED,
        LinuxEncryptionState.VERIFIED,
        PairedRecoveryOSState.PAIRED,
        OneTRState.READY,
        tuple(receipts),
    )


def ready_decision(state: CredentialState, ledger: ReceiptLedger | None = None):
    current_ledger = ReceiptLedger() if ledger is None else ledger
    return state.evaluate(150, current_ledger, REQUIRED_STATE_ORDER), current_ledger


class CredentialStateTests(unittest.TestCase):
    def test_seven_facts_are_distinct_and_closed(self):
        state = ready_state(
            receipt(AuthorizationKind.MACOS_ADMINISTRATOR),
            receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"),
        )
        self.assertEqual(tuple(name for name, _ in state.ordered_facts()), REQUIRED_STATE_ORDER)
        with self.assertRaises(FrozenInstanceError):
            state.filevault = FileVaultState.DISABLED
        self.assertNotEqual(FileVaultState.ENABLED, DataVolumeLockState.UNLOCKED)

    def test_canonical_serialization_and_digest_are_stable(self):
        state = ready_state(
            receipt(AuthorizationKind.MACOS_ADMINISTRATOR),
            receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"),
        )
        serialized = canonical_bytes(state.to_dict())
        self.assertEqual(serialized, canonical_bytes(json.loads(serialized)))
        self.assertEqual(state.digest, CredentialState(**{
            "machine_id": MACHINE,
            "board_id": BOARD,
            "plan_digest": PLAN,
            "filevault": FileVaultState.ENABLED,
            "data_volume": DataVolumeLockState.UNLOCKED,
            "macos_administrator": MacOSAdministratorState.AUTHORIZED,
            "machine_owner": MachineOwnerState.AUTHORIZED,
            "linux_encryption": LinuxEncryptionState.VERIFIED,
            "paired_recovery_os": PairedRecoveryOSState.PAIRED,
            "one_true_recovery": OneTRState.READY,
            "authorization_receipts": (
                receipt(AuthorizationKind.MACOS_ADMINISTRATOR),
                receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"),
            ),
        }).digest)
        self.assertNotIn("opaque-handle-1", serialized.decode())
        self.assertNotIn("opaque-owner", serialized.decode())

    def test_ready_decision_is_derived_and_i01_consumes_exact_binding(self):
        state = ready_state(
            receipt(AuthorizationKind.MACOS_ADMINISTRATOR),
            receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"),
        )
        decision, ledger = ready_decision(state)
        self.assertTrue(decision.ready)
        authority = ConsumptionAuthority(ledger)
        attestation = require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 150, authority)
        self.assertEqual(attestation.plan_digest, PLAN)
        with self.assertRaises(CredentialBindingError):
            require_readiness_for_i01(decision, MACHINE, BOARD, "b" * 64, 150, authority)
        with self.assertRaises(CredentialReadinessError):
            ReadinessDecision(MACHINE, BOARD, PLAN, decision.state_digest, True, (), 150)
        with self.assertRaises(CredentialReadinessError):
            ReadinessAttestation(MACHINE, BOARD, PLAN, decision.digest)

    def test_false_ready_laundering_and_missing_dependencies_fail_closed(self):
        state = ready_state(receipt(AuthorizationKind.MACOS_ADMINISTRATOR, "opaque-admin"))
        decision = state.evaluate(150, ReceiptLedger(), REQUIRED_STATE_ORDER)
        self.assertFalse(decision.ready)
        self.assertIn(ReadinessBlocker.RECEIPT_MISSING, decision.blockers)
        self.assertIn(ReadinessBlocker.ONE_TR_NOT_READY, ready_state(
            receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner")
        ).__class__(MACHINE, BOARD, PLAN, FileVaultState.ENABLED, DataVolumeLockState.UNLOCKED,
                    MacOSAdministratorState.AUTHORIZED, MachineOwnerState.AUTHORIZED,
                    LinuxEncryptionState.VERIFIED, PairedRecoveryOSState.PAIRED, OneTRState.UNKNOWN,
                    (receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner")),
        ).evaluate(150).blockers)
        with self.assertRaises(CredentialReadinessError):
            decision.consume(MACHINE, BOARD, PLAN, 150, ConsumptionAuthority(ReceiptLedger()))

    def test_unknown_and_unavailable_are_not_ready(self):
        for enum_type, value, field in (
            (FileVaultState, FileVaultState.UNKNOWN, "filevault"),
            (DataVolumeLockState, DataVolumeLockState.UNKNOWN, "data_volume"),
            (MacOSAdministratorState, MacOSAdministratorState.UNKNOWN, "macos_administrator"),
            (MachineOwnerState, MachineOwnerState.UNAVAILABLE, "machine_owner"),
            (LinuxEncryptionState, LinuxEncryptionState.UNKNOWN, "linux_encryption"),
            (PairedRecoveryOSState, PairedRecoveryOSState.UNKNOWN, "paired_recovery_os"),
            (OneTRState, OneTRState.UNKNOWN, "one_true_recovery"),
        ):
            values = {
                "machine_id": MACHINE, "board_id": BOARD, "plan_digest": PLAN,
                "filevault": FileVaultState.ENABLED, "data_volume": DataVolumeLockState.UNLOCKED,
                "macos_administrator": MacOSAdministratorState.AUTHORIZED, "machine_owner": MachineOwnerState.AUTHORIZED,
                "linux_encryption": LinuxEncryptionState.VERIFIED, "paired_recovery_os": PairedRecoveryOSState.PAIRED,
                "one_true_recovery": OneTRState.READY,
                "authorization_receipts": (receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner")),
            }
            values[field] = value
            self.assertFalse(CredentialState(**values).evaluate(150, ReceiptLedger(), REQUIRED_STATE_ORDER).ready, enum_type)

    def test_receipts_are_exact_kind_bound_expiring_and_single_use(self):
        admin = receipt(AuthorizationKind.MACOS_ADMINISTRATOR)
        with self.assertRaises(CredentialBindingError):
            admin.validate(AuthorizationKind.MACHINE_OWNER, MACHINE, BOARD, PLAN, 150)
        with self.assertRaises(CredentialBindingError):
            admin.validate(AuthorizationKind.MACOS_ADMINISTRATOR, "other-machine", BOARD, PLAN, 150)
        with self.assertRaises(CredentialBindingError):
            admin.validate(AuthorizationKind.MACOS_ADMINISTRATOR, MACHINE, BOARD, "b" * 64, 150)
        ledger = ReceiptLedger().consume(admin, AuthorizationKind.MACOS_ADMINISTRATOR, MACHINE, BOARD, PLAN, 150)
        with self.assertRaises(CredentialReceiptError):
            ledger.consume(admin, AuthorizationKind.MACOS_ADMINISTRATOR, MACHINE, BOARD, PLAN, 150)
        with self.assertRaises(CredentialReceiptError):
            admin.validate(AuthorizationKind.MACOS_ADMINISTRATOR, MACHINE, BOARD, PLAN, 200)

    def test_secret_fields_values_and_handles_never_cross_boundary(self):
        for value in ({"password": "x"}, {"recovery_key": "x"}, {"api_token": "x"}, {"safe": "passphrase: x"}):
            with self.assertRaises(CredentialSecretError):
                canonical_bytes(value)
        with self.assertRaises(CredentialSecretError):
            receipt(AuthorizationKind.MACHINE_OWNER, "password:do-not-store")
        serialized = receipt(AuthorizationKind.MACOS_ADMINISTRATOR).to_dict()
        self.assertNotIn("receipt_id", serialized)

    def test_bool_int_type_confusion_is_rejected(self):
        with self.assertRaises(CredentialTypeError):
            AuthorizationReceipt(AuthorizationKind.MACHINE_OWNER, MACHINE, BOARD, PLAN, True, 200, "h")
        with self.assertRaises(CredentialTypeError):
            AuthorizationReceipt(AuthorizationKind.MACHINE_OWNER, MACHINE, BOARD, PLAN, 100, False, "h")
        with self.assertRaises(CredentialTypeError):
            AuthorizationReceipt("machine_owner", MACHINE, BOARD, PLAN, 100, 200, "h")
        with self.assertRaises(CredentialTypeError):
            CredentialState(MACHINE, BOARD, PLAN, True, DataVolumeLockState.UNLOCKED,
                            MacOSAdministratorState.AUTHORIZED, MachineOwnerState.AUTHORIZED,
                            LinuxEncryptionState.VERIFIED, PairedRecoveryOSState.PAIRED,
                            OneTRState.READY)

    def test_dependency_order_is_explicit(self):
        state = ready_state(receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"))
        decision = state.evaluate(150, observed_order=tuple(reversed(REQUIRED_STATE_ORDER)))
        self.assertFalse(decision.ready)
        self.assertEqual(decision.blockers[0], ReadinessBlocker.DEPENDENCY_ORDER_INVALID)

    def test_missing_dependency_order_and_configured_linux_are_not_ready(self):
        state = ready_state(receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"))
        self.assertFalse(state.evaluate(150, ReceiptLedger()).ready)
        configured = CredentialState(
            MACHINE, BOARD, PLAN, FileVaultState.ENABLED, DataVolumeLockState.UNLOCKED,
            MacOSAdministratorState.AUTHORIZED, MachineOwnerState.AUTHORIZED,
            LinuxEncryptionState.CONFIGURED, PairedRecoveryOSState.PAIRED, OneTRState.READY,
            state.authorization_receipts,
        )
        decision = configured.evaluate(150, ReceiptLedger(), REQUIRED_STATE_ORDER)
        self.assertFalse(decision.ready)
        self.assertIn(ReadinessBlocker.LINUX_ENCRYPTION_NOT_VERIFIED, decision.blockers)
        self.assertEqual(
            LinuxEncryptionState.NOT_SELECTED.advance_to(LinuxEncryptionState.CONFIGURED),
            LinuxEncryptionState.CONFIGURED,
        )
        self.assertEqual(
            LinuxEncryptionState.CONFIGURED.advance_to(LinuxEncryptionState.VERIFIED),
            LinuxEncryptionState.VERIFIED,
        )
        with self.assertRaises(CredentialDependencyError):
            LinuxEncryptionState.NOT_SELECTED.advance_to(LinuxEncryptionState.VERIFIED)

    def test_consumption_requires_authority_and_exact_ledger_checkpoint(self):
        state = ready_state(receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"))
        decision, ledger = ready_decision(state)
        with self.assertRaises(CredentialTypeError):
            require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 150, None)
        with self.assertRaises(ReadinessAuthorityStateError):
            require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 150, ConsumptionAuthority(ReceiptLedger()))
        authority = ConsumptionAuthority(ledger)
        require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 150, authority)
        with self.assertRaises(ReadinessAlreadyConsumedError) as caught:
            require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 150, authority)
        self.assertEqual(str(caught.exception), "ALREADY_CONSUMED")

    def test_consumption_revalidates_receipt_expiry(self):
        state = ready_state(
            AuthorizationReceipt.issue(AuthorizationKind.MACOS_ADMINISTRATOR, MACHINE, BOARD, PLAN, 100, 200, "admin-expiring"),
            AuthorizationReceipt.issue(AuthorizationKind.MACHINE_OWNER, MACHINE, BOARD, PLAN, 100, 200, "owner-expiring"),
        )
        ledger = ReceiptLedger()
        decision = state.evaluate(150, ledger, REQUIRED_STATE_ORDER)
        self.assertTrue(decision.ready)
        with self.assertRaises(ReadinessExpiredError) as caught:
            require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 200, ConsumptionAuthority(ledger))
        self.assertEqual(str(caught.exception), "READINESS_EXPIRED")

    def test_concurrent_duplicate_consumption_has_one_winner(self):
        state = ready_state(receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"))
        decision, ledger = ready_decision(state)
        authority = ConsumptionAuthority(ledger)
        outcomes: list[object] = []
        lock = threading.Lock()

        def consume() -> None:
            try:
                value = require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 150, authority)
            except Exception as error:  # assertions below classify every result
                value = error
            with lock:
                outcomes.append(value)

        threads = [threading.Thread(target=consume) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(isinstance(value, ReadinessAttestation) for value in outcomes), 1)
        errors = [value for value in outcomes if isinstance(value, Exception)]
        self.assertEqual(len(errors), 11)
        self.assertTrue(all(isinstance(error, ReadinessAlreadyConsumedError) and str(error) == "ALREADY_CONSUMED" for error in errors))

    def test_unregistered_fake_checkpoint_and_attestation_are_rejected(self):
        state = ready_state(receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"))
        decision, ledger = ready_decision(state)
        authority = ConsumptionAuthority(ledger)
        attestation = require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 150, authority)
        checkpoint = authority.checkpoint_for(decision)
        self.assertIsNotNone(checkpoint)
        fake_checkpoint = checkpoint.__class__(
            checkpoint.decision_digest, checkpoint.machine_id, checkpoint.board_id,
            checkpoint.plan_digest, checkpoint.receipt_digests, checkpoint.ledger_checkpoint_id,
            checkpoint.consumed_at, "fake-authority", checkpoint.authority_revision,
        )
        fake = object.__new__(ReadinessAttestation)
        for name in ("machine_id", "board_id", "plan_digest", "decision_digest", "authority_id", "authority_revision", "consumed_at", "receipt_digests", "ledger_checkpoint_id", "_receipt_ids"):
            object.__setattr__(fake, name, getattr(attestation, name))
        object.__setattr__(fake, "consumption_checkpoint_digest", fake_checkpoint.digest)
        with self.assertRaises(CredentialReadinessError):
            authority.verify_attestation(fake, decision, MACHINE, BOARD, PLAN, 150)
        with self.assertRaises(CredentialTypeError):
            authority.verify_attestation(object(), decision, MACHINE, BOARD, PLAN, 150)
        with self.assertRaises(Exception):
            replace(attestation, consumed_at=151)

    def test_authority_verification_rejects_tampering_and_copied_fields(self):
        state = ready_state(receipt(AuthorizationKind.MACOS_ADMINISTRATOR), receipt(AuthorizationKind.MACHINE_OWNER, "opaque-owner"))
        decision, ledger = ready_decision(state)
        authority = ConsumptionAuthority(ledger)
        attestation = require_readiness_for_i01(decision, MACHINE, BOARD, PLAN, 150, authority)
        copied = object.__new__(ReadinessAttestation)
        for name in ("machine_id", "board_id", "plan_digest", "decision_digest", "consumption_checkpoint_digest", "authority_id", "authority_revision", "consumed_at", "receipt_digests", "ledger_checkpoint_id", "_receipt_ids"):
            object.__setattr__(copied, name, getattr(attestation, name))
        with self.assertRaises(CredentialReadinessError):
            authority.verify_attestation(copied, decision, MACHINE, BOARD, PLAN, 150)
        object.__setattr__(attestation, "consumed_at", 151)
        with self.assertRaises(CredentialReadinessError):
            authority.verify_attestation(attestation, decision, MACHINE, BOARD, PLAN, 150)


if __name__ == "__main__":
    unittest.main()
