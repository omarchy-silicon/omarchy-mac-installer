# Omarchy Silicon native installer transaction design

Status: DESIGN ONLY — CORRECTED DESIGN, NOT IMPLEMENTED, QUALIFIED, SUPPORTED, PROMOTED, OR DONE.

This document is the sole design artifact for the native installer transaction lane. It corrects the rejected reviewed tip `1042ef04d65a7a59c46c7ea8b4d2a7c0db61869e`; it does not implement I-01 through I-09, the Apple adapter, a boot chain, a package system, a validator, a test suite, a qualification record, or a release. No statement in this document is evidence that an installation is safe or that any board is supported.

Design lane: `factory/design-installer-transaction`

Program authority input: read-only `omarchy-apple-platform/PROGRAM.md` at authority commit `58302d148f0e8b855578f9aa518ff1c5eb48c515`. This ledger is an external authority input; it does not make implementation, qualification, support, promotion, or DONE evidence.

Cross-contract F-02 input: provisional rejected snapshot `c315c7e79928d0041deb582bed79a61074361b21`, `docs/design/platform-schema.md`. This lane consumes its exact vocabulary only as an unresolved dependency. It is not canonical, approved, implemented, or release authority. If the authoritative F-02 artifact differs, this lane is `BLOCKED_F02_AUTHORITY_UNRESOLVED` until the owner resolves the conflict; no installer-local schema, identity, trust, or boot authority may substitute for it.

The `m1n1-omarchy` boundary is opaque and human-produced. This document does not inspect, traverse, clone, fetch, characterize, edit, test, or make source-level claims about that repository or its contents. The only permitted future input is a human-produced signed artifact envelope and the observable external handoff described below. No agent or installer operation may turn that envelope into a claim about the source repository.

## 1. Scope, ownership, and design honesty

The installer repository owns the macOS entry point, read-only inventory, typed plan, owner handoff, Apple-supported provisioning adapter, transaction journal, live-image handoff, Linux target setup, update and rollback UX, exact-ownership uninstall, recovery guidance, accessibility, localization, privacy consent, and support export. Those are ownership boundaries, not completed deliverables.

The platform repository owns the canonical schemas, signing policy, trust context, board registry, platform manifest, component locks, candidate assembly, qualification contracts, release compliance, and promotion. The installer consumes verified trusted values and does not choose a component tuple, board capability, signing role, or release independently.

The installer never declares a board FULL, promotes a release, certifies hardware, approves an artifact, or replaces a physical qualification record. Boot health is an installer transaction result. It is not a qualification record and it is not a support-ledger decision.

Apple APFS, RecoveryOS, LocalPolicy, machine-owner authorization, and DFU remain Apple-supported and human-authorized boundaries. The installer does not implement an independent APFS writer, manufacture machine-owner authority, or automate a DFU sequence whose owner and Apple baseline are unresolved.

The design uses the following terms precisely:

| Term | Meaning | Authority consequence |
|---|---|---|
| Observation | A read-only, locally collected fact with source and observation identity | It can inform planning, never authorize a mutation by itself. |
| Candidate input closure | One complete set of verified immutable inputs selected by the signed plan before consent | No mutation may consume an input outside the closure. |
| Trusted<T> | A value constructed only by the common authenticated-envelope verifier for a closed type | Consumers accept only this value, never a raw parsed object. |
| Owner approval | A separate authenticated `owner-approval/v1` receipt | A journal, prompt, account name, or prior transaction cannot reconstruct it. |
| Fresh snapshot | A new observation of the approved machine and target topology at the required boundary | Any mismatch invalidates approval and requires read-only replanning. |
| Design evidence | A contract, table, fixture definition, or proposed gate in this document | It is not implementation, a passing test, or qualification evidence. |

## 2. Correction coverage

The rejected findings are corrected by the sections shown here. The mapping is a document cross-reference, not a claim that any mapped implementation exists.

| Finding | Corrected sections |
|---|---|
| 1. State and event closure | Sections 8 and 9 |
| 2. Destructive authority | Sections 3, 7, 8, and 10 |
| 3. Complete offline input closure | Section 4 |
| 4. Stable identity and uninstall | Section 5 and Section 10 |
| 5. Credentials and secrets | Section 6 |
| 6. Canonical trust seam | Section 3 |
| 7. Apple platform adapter | Section 7 |
| 8. Crash, journal, and boot safety | Sections 9 and 11 |
| 9. Product UX | Section 12 |
| 10. Executable future gates | Section 13 |
| 11. Dependency handoffs | Section 14 |
| 12. Residual ownership and honesty | Sections 15 and 16 |

## 3. Canonical authenticated trust seam

### 3.1 One envelope and one verification constructor

The installer consumes the exact eight-payload vocabulary and signing rows from the supplied provisional F-02 snapshot, but the snapshot remains rejected and unresolved. Until an authoritative F-02 artifact is admitted, every consumer gate below remains blocked and no local field list or alternate authority is valid. The wire envelope is the closed `omarchy-signed/v1` object with exactly `format`, `payload_type`, `payload_version`, `domain`, `context`, `schema_set_digest`, `payload`, and `signatures`. The payload is canonical UTF-8 JSON under RFC 8785 JCS and carries the exact common fields `schema`, `schema_set_digest`, `document_id`, `issuer`, `issued_at`, and `expires_at` followed by its closed type-specific fields. `document_id` is stable authority-selected identity, not a content digest; `payload_digest = sha256(JCS(P))` is computed independently.

The only authenticated construction seam is:

```text
strict_parse(bytes) -> Parsed<T> | ParseError
canonicalize(Parsed<T>) -> Canonical<T> | CanonicalizationError
verify(Canonical<T>, Trusted<TrustContext>, VerifiedClock, ExpectedContext) -> Trusted<T> | TrustError
admit(Trusted<T>, Admitted<Policy>) -> Admitted<T> | AdmissionError
```

`verify` performs bounded parsing and canonical-byte equality, exact payload type and version, exact schema-set pin, domain/context equality, payload digest recomputation, anti-transplant preimage equality, signature and threshold verification, role-binding and scope verification, verified-clock issuance/expiry checks, replay reservation, and field validation in that order. `admit` is a separate seam: it accepts only the nominal `Trusted<T>` and a nominal `Admitted<Policy>`, checks the policy digest and required gate set against the verified value, and returns `Admitted<T>` or one stable rejection. A raw parsed object, unsealed policy map, boolean override, or caller-selected schema can never cross either seam. A failed step emits exactly one stable code and JSON path, no partial authority-bearing value, and no warning-success. These constructors are not implemented by this design.

`Trusted<TrustContext>` is supplied by F-03 and is the only source of the closed `AuthorityRoleBinding` used to resolve repository, slice, operation, policy, signer, threshold, custody, revocation, and expiry authority. `Admitted<Policy>` is produced only by the F-03 policy seam from a trusted policy source. A consumer may not extend, replace, unwrap, or reconstruct either nominal value from an account name, journal field, UI role, local map, or unverified key. No consumer-local authority document or shadow role table grants authority.

These are the only authenticated payload types in the transaction contract:

| Exact payload type | Required contract in this lane |
|---|---|
| `board-registry/v1` | Exact board and SoC selectors, device-tree compatibility identity, firmware schema, physical capability profile, lifecycle state, and qualification requirements. |
| `platform-manifest/v1` | Exact component records at `components.linux_kernel`, `components.dtb_set`, `components.firmware_bundle`, `components.mesa_stack`, and `components.boot_stack`; source, configuration, patch, toolchain, report, and artifact locks; typed relations; required health policy; rollback compatibility; and selected installer inputs. |
| `installer-plan/v1` | Read-only inventory digest, stable identities, protected-object set, target and ownership manifests, ordered operations, complete candidate input closure, selected board and platform records, policy decisions, and approval binding requirements. |
| `qualification-record/v1` | Physical board/profile identity, baseline, manifest identity and digest, test procedures, raw evidence references, results, failures, residuals, operator identity, and timestamps. It is evidence owned by the qualification process, not installer authority. |
| `boot-health/v1` | The signed health core: selected slot, generation, lineage, attempt counter, manifest binding, required-check results, failure reason, and fallback set. It contains no success marker. |
| `owner-approval/v1` | A separate destructive-consent receipt with the complete binding in Section 3.3. |
| `boot-success-mark/v1` | A separate authenticated success statement bound to a verified boot-health core, board, manifest, slot, generation, lineage, attempt counter, source generation, required-check policy, and rollback set. |
| `dtb-mutation-envelope/v1` | Board and source identity, manifest identity, pre- and post-DTB digests, exact policy/tool/artifact locks, ordered authorized DTB mutations, firmware schema and bundle identity, signer, expiry, and replay identity. |

The eight domain/context/role rows are closed and exact: `board-registry/v1` uses `omarchy-board-registry` / `board-registry-publication` / `board-admission`; `platform-manifest/v1` uses `omarchy-platform-manifest` / `manifest-publication` / `manifest-release`; `installer-plan/v1` uses `omarchy-installer-plan` / `installer-plan-proposal` / `installer-planner`; `qualification-record/v1` uses `omarchy-qualification-record` / `qualification-result` / `qualification-lab`; `boot-health/v1` uses `omarchy-boot-runtime` / `boot-health-core` / `boot-runtime`; `owner-approval/v1` uses `omarchy-owner-authorization` / `installer-plan-execution` / `owner-authorization`; `boot-success-mark/v1` uses `omarchy-boot-runtime` / `boot-success-marker` / `boot-runtime`; and `dtb-mutation-envelope/v1` uses `omarchy-dtb-authority` / `dtb-mutation-authorization` / `dtb-authority`. The two `boot-runtime` rows remain distinct because their contexts and complete scope differ. A type, domain, context, role, version, scope, or signer transplant is `ERR_TRUST_CONTEXT_MISMATCH` at the first differing path.

Journal records, observations, cache receipts, Apple adapter results, support-bundle manifests, and UI state are internal records. They are not additional authenticated payload types and they never acquire authority merely by being signed by the transaction process.

### 3.2 Exact consumer behavior

Every consumer takes the specific `Trusted<T>` or `Admitted<T>` nominal type required by its operation. A raw JSON object, decoded plist, local cache entry, package-manager result, source URL, stable document ID, payload digest alone, journal record, account identity, UI confirmation, or caller-created `BootContext` is rejected at the consumer boundary with `ERR_TRUSTED_VALUE_REQUIRED` at the consumer JSON path. The installer does not parse a second copy of a canonical field list.

`ExpectedContext` is the typed anti-transplant input to `verify`. It contains exactly `context_schema = "expected-context/v1"`, `payload_type`, `payload_version`, `domain`, `context`, `project_id`, `repository_id`, `slice_id`, `operation`, `board_id`, `manifest_id`, `manifest_digest`, `schema_set_digest`, `target_account_id`, `target_account_binding`, `target_identity_digests`, and `policy_digest`. Null is permitted only where the applicable F-02 row marks a field not applicable. Its constructor derives scope from the verified document and rejects any caller value that cannot be byte-for-byte compared.

For payload `P` and signature entry `S`, the domain-separated anti-transplant preimage is exact:

```text
A = {
  envelope_format: "omarchy-signed/v1",
  signature_format: "raw-ed25519/v1",
  key_id: S.key_id,
  signer_role: S.signer_role,
  algorithm: "ed25519",
  domain: envelope.domain,
  context: envelope.context,
  payload_type: envelope.payload_type,
  payload_version: envelope.payload_version,
  schema_set_digest: envelope.schema_set_digest,
  payload_digest: sha256(JCS(P)),
  anti_transplant: {document_id: P.document_id, schema: P.schema,
                    payload_type: envelope.payload_type,
                    payload_version: envelope.payload_version,
                    schema_set_digest: envelope.schema_set_digest,
                    domain: envelope.domain, context: envelope.context},
  payload: P
}
auth_preimage = ASCII("omarchy-auth-preimage/v1") || 0x00 || JCS(A)
```

The schema-set digest is pinned in every payload and envelope, the owner approval, the plan-to-manifest bindings, the lock records, and every consumer capability record. Negotiation is the exact ordered set `board-registry/v1`, `platform-manifest/v1`, `installer-plan/v1`, `qualification-record/v1`, `boot-health/v1`, `owner-approval/v1`, `boot-success-mark/v1`, `dtb-mutation-envelope/v1`; it must select one exact pinned schema-set digest and rejects omission, duplication, reordering, downgrade, mixed digest, or compatibility alias with `ERR_TRUST_SCHEMA_SET_MISMATCH`. No negotiated result is evidence until F-02 provides the authoritative schema-set artifact and generated bindings.

The accepted sequence is:

1. Obtain `Trusted<TrustContext>` from F-03 and `Admitted<Policy>` from the policy seam.
2. Build the closed `ExpectedContext` for the exact operation, board, manifest, target, and policy.
3. Parse and canonicalize, then call `verify(..., Trusted<TrustContext>, VerifiedClock, ExpectedContext)` for the exact payload type.
4. Call `admit(Trusted<T>, Admitted<Policy>)`; then check cross-payload relations and the pinned schema-set digest.
5. Copy only the resulting `Admitted<T>` into an immutable transaction context; quarantine raw bytes and never pass them to a mutator.

The rejected sequence is any path that accepts a parsed object before verification, calls a consumer with `Trusted<T>` but no `admit`, passes an unsealed policy map, supplies a caller-created `ExpectedContext`, omits the anti-transplant preimage, fills fields from local defaults, derives authority from an owner map, compares only a stable document ID or digest, accepts a stale/replayed value, or substitutes a manifest alias for one of the five canonical component paths.

### 3.3 Separate owner approval contract

The final destructive boundary requires a fresh `Trusted<OwnerApproval>` whose payload type is `owner-approval/v1`, followed by `admit(Trusted<OwnerApproval>, Admitted<Policy>)`. Its domain is `omarchy-owner-authorization`, its context is `installer-plan-execution`, and its signer role is `owner-authorization`. The closed payload has the common fields plus exactly `plan_digest`, `scope_digest`, `project_id`, `repository_id`, `slice_id`, `board_id`, `board_registry_digest`, `manifest_id`, `manifest_digest`, `schema_set_digest`, `policy_id`, `policy_digest`, `actor_id`, `account_id`, `actor_role`, `approved_at`, `topology_digest`, `target_ids`, `target_identities`, `operations`, `authorization_method`, `authorization_result`, `external_proof_digest`, `authorization_evidence_digest`, `service_policy_id`, `service_policy_digest`, `replay_id`, `proof_receipt_id`, `target_account_record_id`, and `target_account_binding`. `actor_role` is exactly `owner` and `authorization_result` is exactly `success`; `authorization_method` is exactly `webauthn/v1`, `oidc-step-up/v1`, or `hardware-token/v1`.

The binding is total: actor is `actor_id = "actor:" || LowerAsciiToken`; account is `account_id = "acct:" || LowerAsciiToken`; time is common `issued_at`/`expires_at` plus `approved_at` checked against `VerifiedClock`; method and result are the closed values above; proof is both `proof_receipt_id` and `external_proof_digest` projected from a separately trusted `OwnerProofReceipt`; policy is `policy_id`, `policy_digest`, `service_policy_id`, and `service_policy_digest`; replay is `replay_id` plus nonce/replay state; and target is the complete byte-equal `target_ids`, `target_identities`, `topology_digest`, operation set, and `target_account_binding`. The target-account binding preimage is `ASCII("omarchy-owner-target-account/v1") || 0x00 || JCS({project_id, repository_id, slice_id, operation, account_id, plan_digest, scope_digest, policy_digest, manifest_digest, topology_digest, target_identity_digests})` hashed with SHA-256.

`OwnerProofReceipt` and `TargetAccount` are closed supporting records, not additional authenticated payload types. Their only constructors return `Trusted<OwnerProofReceipt>` and `Trusted<TargetAccount>` after source, evidence bytes, account ownership, allowed operation, target set, validity, nonce, replay, and digest recomputation pass. The approval is admitted only when those trusted records, `Trusted<TrustContext>`, `Admitted<Policy>`, the verified plan, and the fresh snapshot agree byte-for-byte. A journal, prompt, actor/account string, role string, proof digest without its receipt, or prior transaction cannot create, widen, refresh, or substitute approval.

The approval is not a prose checkbox. It is issued only after the complete binding is displayed and the owner-authorized result succeeds. Any changed actor, account, role, time window, method, result, proof, policy, replay identity, target identity, topology, project, repository, slice, board, manifest, schema set, operation, or argument returns `PLAN_SCOPE_OR_APPROVAL_FAILURE` at the first differing path and returns to read-only planning. Expiry is `ERR_APPROVAL_EXPIRED`; replay is `ERR_APPROVAL_REPLAYED`; a journal preserves evidence only.

## 4. Complete pre-consent offline input closure

### 4.1 Closure contents

The plan contains exactly one signed candidate input closure. It is a field of `installer-plan/v1`, and its digest is included in `owner-approval/v1`. It is complete only when every direct and transitive installer input has a verified cache object before owner consent.

Each closure entry has these required fields:

| Field | Rule |
|---|---|
| `input_id` | Closed per-kind ID derived from the declared input kind and content digest. |
| `source_selector` | Immutable source reference: a content-addressed object, exact commit, exact Apple source policy, or exact human-produced signed artifact reference. A branch, tag, latest pointer, mutable index, or resolver result is not immutable. |
| `content_digest` | SHA-256 of the complete bytes consumed by the installer. |
| `length` | Exact byte length checked before and after acquisition. |
| `media_type` | Allowlisted media type checked against the consumer. |
| `artifact_identity` | Producer, artifact name, version, source identity, build identity, and artifact digest from the verified producer envelope. |
| `manifest_identity` | Stable platform-manifest document ID and payload digest selecting the input, plus the exact component path when applicable. |
| `verification.result` | `PASS` only after signature, digest, length, media, producer, board, firmware-schema, and internal-format checks pass. |
| `verification.evidence_digest` | Digest of the bounded verification evidence and tool identity. |
| `cache_receipt` | Immutable cache object ID, path-independent receipt digest, complete-byte status, and fsync/read-back result. |
| `completeness_proof` | Closure root, dependency list, transitive count, expected byte total, and proof that every consumer-required input is present. |

The closure enumerates every selected firmware blob and bundle, RecoveryOS and stub input, live image, package and package index, repository metadata, image, boot input, DTB input, installer executable or library, schema binding, trust metadata, and every transitive input. The opaque human-produced boot artifact is represented only by its signed envelope, declared digest, schema/interface, provenance, license and redistribution decision, and observable handoff result. The installer never opens or analyzes its producing repository.

The five canonical component paths are the only manifest component selectors:

```text
components.linux_kernel
components.dtb_set
components.firmware_bundle
components.mesa_stack
components.boot_stack
```

Typed relations connect these records by exact document IDs and payload digests. No unlisted component selector, convenience field, family selector, or display label may authorize selection; consumers accept only the five paths above.

### 4.2 Acquisition and mutation boundary

Acquisition is a pre-consent phase. It may write only a path-independent content-addressed cache entry and its receipt. It must verify each entry before the final plan is rendered. The GUI and CLI display source policy, length, digest, provenance, verification evidence, cache state, and completeness. A cached partial, expired, unverified, or substituted object is not closure-complete.

After final consent, the mutation executor starts with network access denied, DNS and resolver fallback denied, package-index refresh denied, mirror selection denied, mutable-reference resolution denied, and cache insertion denied for required inputs. It may read only closure objects whose receipts and digests match the approved closure. A missing or changed closure entry rejects the operation with `ERR_INPUT_CLOSURE_NOT_READY` or `ERR_INPUT_CLOSURE_CHANGED`; it cannot retry from a network, package manager, resolver, or fallback mirror.

Apple IPSW, OTA, RecoveryOS, and firmware bytes remain subject to Apple source policy and owner legal ruling. Direct fetch from Apple is the design default. A cache or redistribution path is not treated as approved until its owner decision, exact artifact class, source evidence, notice, and retention rule are immutable inputs. The platform signature proves Omarchy selection; Apple verification proves Apple provenance; neither substitutes for the other.

### 4.3 Hostile closure fixtures

Closure cases are part of the single canonical fixture index in Section 13.1. They are not a second fixture table: each `CLOSURE-*` row there has one mutation, prior state, attempted input/transition, exact result state, stable rejection code, JSON path, phase, durable evidence, and restart observation. The index is future test input only; no fixture or validator exists in this design.

## 5. Stable identity and exact-ownership uninstall

### 5.1 Closed identity grammars

Stable IDs are consumed only through the four provisional F-02 hashed identity kinds. A display name, `/dev/diskN`, `/dev/rdiskN`, path, glob, label, size, first-disk rule, package-manager object, or installer-local token is never an identity. The exact grammar is:

```text
whole_disk stable_id = ^disk:v1:sha256:[0-9a-f]{64}$
gpt_partition stable_id = ^partition:v1:sha256:[0-9a-f]{64}$
apfs_container stable_id = ^container:v1:sha256:[0-9a-f]{64}$
apfs_volume stable_id = ^volume:v1:sha256:[0-9a-f]{64}$
ObjectKind = "whole_disk" | "gpt_partition" | "apfs_container" | "apfs_volume"
StableId = DiskStableId | PartitionStableId | ContainerStableId | VolumeStableId
```

For kind `K` and its closed F-02 identity preimage `I_K`, `stable_id(K, I_K) = kind_prefix(K) || hex_lower(sha256(ASCII("omarchy-storage-identity/v2") || 0x00 || JCS({source: I_K.source, identity: I_K})))`; the corresponding `identity_anchor_digest` uses `ASCII("omarchy-storage-identity-anchor/v1")`. The source tuple, parent stable ID, typed identity fields, source observation digest, source generation, normalization version, and physical parent closure are required to reproduce the value. The 64-hex suffix is kind-specific identity bytes, not a second `sha256:` label and not an artifact or payload digest.

This lane has no fifth identity kind and no alternate grammar. Until the supplied F-02 vocabulary is authoritative and admitted, identity selection and uninstall are `BLOCKED_F02_IDENTITY_AUTHORITY_UNRESOLVED`; after admission, an unknown prefix, old local prefix, uppercase/short hash, path, `diskN` token, missing source tuple, missing parent, collision, clone, or changed normalized tuple is rejected. No local truth may override F-02.

### 5.2 Re-observation and ambiguity rules

At each approval and mutation boundary, the adapter re-observes the entire target and protected topology. It resolves by the typed identity tuple on the same physical parent and compares type, offset, length, capacity, role, UUID, GPT/APFS digest, mount state, and allowed generation. A path-only match, changed device path, device-path reuse, duplicate ID, clone, collision, ambiguous role map, missing parent, changed capacity, or stale observation rejects with an exact identity error. No stale ID is adopted because a new object happens to occupy the old path.

Identity errors are ordered by safety: `ERR_IDENTITY_SCHEMA`, `ERR_IDENTITY_PARENT_MISSING`, `ERR_IDENTITY_DUPLICATE`, `ERR_IDENTITY_COLLISION`, `ERR_IDENTITY_CLONE`, `ERR_IDENTITY_PATH_REUSE`, `ERR_IDENTITY_AMBIGUOUS`, `ERR_IDENTITY_STALE`, then `ERR_IDENTITY_PROPERTY_CHANGED`. The first applicable error is durable; later checks do not conceal it.

### 5.3 Authenticated exact-ownership manifest

The `installer-plan/v1` payload contains an exact-ownership manifest for install-created objects. Each entry records the typed ID, creation lineage, creation generation, parent closure, creation operation, expected type and range, creation evidence digest, and whether the object is shared or exclusively owned. The manifest is authenticated with the plan and bound into `owner-approval/v1`.

Uninstall accepts only a verified plan ownership manifest, a fresh matching snapshot, and a new `Trusted<OwnerApproval>` whose ordered operations contain the exact deletion IDs. It first verifies an Apple-supported macOS or paired RecoveryOS boot, a surviving macOS fallback, target boot-policy state, and target ownership. It then sets and verifies macOS as the fallback before deleting any exact owned object. It re-observes after every deletion and stops at the first uncertainty.

Pattern, name, size, filesystem type, first internal disk, partition order, directory name, or boot-picker position is unrepresentable as an uninstall selector. Existing objects without a cryptographic ownership entry are displayed as `UNKNOWN_OWNERSHIP` and cannot be deleted automatically. Space reclamation is a separately listed and separately approved Apple-supported operation after exact object deletion. It enters `SPACE_RECLAIM_REQUESTED`, durably commits that request in both journal replicas, and can reach `UNINSTALLED` only through a separately classified `SPACE_RECLAIM_COMMITTED` result; it is never implicit cleanup.

## 6. Credential and secret boundaries

### 6.1 Distinct states and Apple-owned results

The transaction records credential state as typed non-secret results. It never treats all prompts as an administrator password and never copies an Apple secret into installer state.

| State | Values | Owner of secret and result returned to installer |
|---|---|---|
| FileVault | `ON`, `OFF`, `UNKNOWN` | Apple volume/security surface; installer receives state and evidence digest only. |
| Data-lock | `LOCKED`, `UNLOCKED`, `UNKNOWN` | Apple Data-volume surface; installer receives state and target identity only. |
| macOS administrator | `ELIGIBLE`, `NOT_ELIGIBLE`, `UNKNOWN` | Apple account authorization surface; installer receives account/result, never password. |
| Machine owner | `ELIGIBLE`, `NOT_ELIGIBLE`, `UNKNOWN` | Apple machine-owner authorization surface; installer receives typed result, never owner secret. |
| SecureToken/APFS crypto-user | `ELIGIBLE`, `NOT_ELIGIBLE`, `UNKNOWN` | Apple security surface; installer receives capability result and target binding only. |
| RecoveryOS/1TR | `NOT_REQUIRED`, `REQUIRED`, `PENDING`, `ACCEPTED`, `CANCELLED`, `FAILED`, `UNKNOWN` | Apple RecoveryOS/1TR surface; installer receives handoff result and evidence. |
| Linux encryption | `NOT_SELECTED`, `SELECTED_UNVERIFIED`, `VERIFIED`, `CLEARED`, `FAILED` | Omarchy live UI owns the Linux passphrase; it is never an Apple credential and never enters the journal. |

FileVault state does not prove Data-lock state. Administrator eligibility does not prove machine-owner authority. SecureToken or APFS crypto-user eligibility does not prove owner approval. Recovery authorization does not prove LocalPolicy success. A Linux passphrase does not unlock Apple storage. An unknown state blocks the operation that needs it.

### 6.2 Sole Linux secret route

The only permitted Linux passphrase route is one dedicated anonymous close-on-exec pipe created for the single intended consumer. A native helper allocates a bounded, NUL-free UTF-8 buffer of at most 256 bytes in locked memory, disables echo before reading, rejects empty or over-limit input, applies `mlock` and a no-core-dump memory policy, creates the pipe with both descriptors close-on-exec, launches the exact locked consumer command with no inherited standard input, writes once, closes the writer, and zeroizes the buffer. The reader is the sole consumer and does not forward the bytes to another process.

The pipe lifetime is at most 10 seconds and ends on successful read, cancellation, error, process exit, or timeout. The helper closes all unrelated descriptors before exec, verifies the intended child identity, clears the buffer and pipe storage on every exit path, and reports only `VERIFIED`, `CLEARED`, or a typed failure. It does not use general stdin. It does not use argv, environment, a temporary file, a cache, a filesystem path, a journal, a log, a structured event, telemetry, a support bundle, a crash artifact, swap, or a command output channel. Swap must be disabled or cryptographically proven absent for the helper lifetime; a crash, cancellation, timeout, recovery screen, redaction failure, log, telemetry event, or support export must expose zero secret bytes. The implementation must prove locked-memory, swap, crash-dump, cancellation, recovery, and redaction behavior on each supported Linux baseline; “best effort” is not a release result.

Apple passwords, FileVault secrets, machine-owner secrets, SecureToken/APFS crypto-user material, RecoveryOS/1TR authorization, LocalPolicy material, and recovery keys stay in Apple-owned or user-held surfaces. They never enter the Linux pipe. A recovery key is shown once for user storage only when the exact layout policy requires it; it is not uploaded or written to the ESP, cache, journal, log, swap, crash artifact, telemetry, recovery screen, or support export. Cancellation and recovery preserve only a typed state and redacted evidence, never the secret or a recoverable copy.

### 6.3 Secret-leak fixtures

Secret cases are part of the single canonical fixture index in Section 13.1. It includes the original argv, environment, stdin, descriptor, cache, filesystem, locked-memory, echo, length, zeroization, crash-dump, event, journal, support-export, and Apple-secret crossing cases plus explicit swap, crash-artifact, log, telemetry, redaction, cancellation, and recovery-exposure cases. Every `SECRET-*` row has the same ten required fields; no secret fixture or leak scanner exists yet.

## 7. Closed Apple platform adapter

### 7.1 Adapter boundary and immutable locks

The Apple adapter is a closed set of typed operations. It accepts only typed IDs, approved field references, `Trusted<OwnerApproval>` where required, and exact command/API entries from named immutable locks. It never accepts a raw path, shell fragment, environment-selected command, or unbounded argument list.

The required immutable inputs are owner-approved immutable external artifacts `APPLE_BASELINE_LOCK`, `APPLE_COMMAND_LOCK`, and `APPLE_AUTHORIZATION_POLICY_LOCK`. Each is admitted only as a complete signed record with an artifact identity, exact bytes digest, issuing owner and approval proof, scope, issuance/expiry, supported macOS and RecoveryOS/1TR build values, API availability, tool versions, tool paths, full argument arrays, output schemas, timeout, read-back classifier, and policy digest. A lock ID without its complete bytes, digest, owner approval, or exact scope is absent. A version guessed from the host, a manual command copied into a ticket, a current-host observation, or a latest tool is not a lock.

The exact admission is `admit_apple_baseline(owner_approved_immutable_artifact, Trusted<TrustContext>, VerifiedClock) -> Admitted<AppleBaselineLock> | typed rejection`; it recomputes the artifact digest, verifies the owner proof and role binding, checks freshness/expiry, checks the requested host/API tuple against the lock, and requires byte-equal command/output entries. Missing, unsigned, stale, expired, wrong-owner, wrong-scope, digest-mismatched, unsupported-version, incomplete, or guessed input returns `BLOCKED_APPLE_BASELINE_UNRESOLVED` at the first failing field before inventory approval or any external call. No value is supplied or approved in this design.

The design has no owner-approved lock bytes or Apple version ruling at this time. Therefore every operation whose row requires one of these locks is currently `BLOCKED_APPLE_BASELINE_UNRESOLVED`; this is an explicit fail-closed state, not an assumed supported baseline.

The exact-array rule is normative for the future implementation: every command array is a JSON array stored under an immutable lock key, contains no three-dot token, shell expansion, pipeline, command substitution, or unresolved free-form argument, and is compared byte-for-byte with the array recorded in the plan. Typed substitutions such as `{target.apfs_container_id}` are resolved only from the approved typed object and are rejected if any substitution is absent, duplicated, or outside the lock's declared position. No executable command array is claimed to exist in this design.

The lock must at minimum contain full arrays for these read-only operations:

```json
{
  "inventory.ioreg": ["/usr/sbin/ioreg", "-a", "-l"],
  "inventory.sysctl": ["/usr/sbin/sysctl", "-a"],
  "inventory.disk_list": ["/usr/sbin/diskutil", "list", "-plist"],
  "inventory.disk_info": ["/usr/sbin/diskutil", "info", "-plist", "{whole_disk.stable_id}"],
  "inventory.apfs_list": ["/usr/sbin/diskutil", "apfs", "list", "-plist"],
  "inventory.volume_groups": ["/usr/sbin/diskutil", "apfs", "listVolumeGroups", "-plist"],
  "inventory.policy": ["/usr/bin/bputil", "-d"]
}
```

These arrays are design-time required lock entries, not values or evidence that the corresponding tools or flags are available on any current Apple baseline. They cannot be admitted until the lock owner binds them to exact immutable bytes and an owner-approved version ruling. Mutation arrays for APFS resize, partition creation, role creation, Preboot/RecoveryOS staging, LocalPolicy, boot selection, and space reclaim are likewise absent until the lock owner supplies the complete external artifact. The absent artifact keeps the adapter blocked.

### 7.2 Owner-authority matrix

| Adapter operation | Apple or human surface | Required lock and owner authority | Precondition | Structured postcondition and classifier | Unknown behavior |
|---|---|---|---|---|---|
| `inventory_board` | Read-only IORegistry/sysctl | `APPLE_BASELINE_LOCK`; no owner credential | macOS session and bounded output | Exact board identity fields and source digest; partial output is `ERR_APPLE_OUTPUT_PARTIAL` | Reject `ERR_APPLE_BASELINE_UNRESOLVED`. |
| `inventory_storage` | Read-only diskutil/APFS | `APPLE_BASELINE_LOCK`; no owner credential | No mutation in progress | Complete GPT/APFS topology with stable IDs; duplicate or partial plist is `ERR_APPLE_TOPOLOGY_UNREADABLE` | Hold before planning. |
| `inventory_policy` | Read-only bputil or Apple API | `APPLE_BASELINE_LOCK`; no owner credential | Target and macOS policy identities known | Target and macOS policy snapshots with build IDs; incomplete output is `ERR_APPLE_POLICY_READBACK_INCOMPLETE` | Hold before approval. |
| `authorize_owner` | Apple-owned authorization UI | `APPLE_AUTHORIZATION_POLICY_LOCK`; human machine owner | Apple reports exact target and account | Typed eligibility and authorization result; exit status alone is insufficient | `ERR_OWNER_AUTH_UNKNOWN`. |
| `resize_macos_container` | Apple-supported diskutil/API | `APPLE_COMMAND_LOCK`; owner-approved exact target | Fresh container/store IDs, free range, protected set, and approval | Same container roles and exact requested boundary; partial output is `ERR_APFS_RESIZE_UNCLASSIFIED` | `RECOVERY_REQUIRED`, never speculative inverse. |
| `create_stub_partition` | Apple-supported GPT/APFS API | `APPLE_COMMAND_LOCK`; owner approval | Approved free range and parent disk | New UUID, type, range, and parent match | Preserve and classify; no label search. |
| `create_stub_roles` | Apple-supported APFS role API | `APPLE_COMMAND_LOCK`; owner approval | New partition exact ID | Complete role map and UUIDs read back | Stop with `ERR_APPLE_ROLE_MAP_UNKNOWN`. |
| `stage_recovery_handoff` | Apple-supported RecoveryOS/Preboot path | `APPLE_COMMAND_LOCK`; human Recovery authorization if requested | Verified Apple input closure and target VGID | Pairing/build identity and control descriptor match | Remain `OWNER_HANDOFF_PENDING`. |
| `authorize_target_policy` | Apple-owned LocalPolicy surface | `APPLE_AUTHORIZATION_POLICY_LOCK`; machine owner | Exact target VGID, Apple authorization, and approval | Target policy changed as expected and macOS policy unchanged | `ERR_LOCALPOLICY_TARGET_UNKNOWN`; no inverse guess. |
| `set_boot_target` | Apple-supported bless/boot-selection API | `APPLE_COMMAND_LOCK`; owner approval | Target boot ID and macOS fallback proof | Target/default selection read back with exact IDs | Safe macOS return or recovery. |
| `handoff_live_image` | Apple boot picker and human selection | `APPLE_COMMAND_LOCK`; human physical action | Signed image closure and handoff descriptor | Live identity and plan digest read back | Persist checkpoint; no timeout deletion. |
| `dfu_escalation` | Apple-supported second-host process | Human owner and qualified runbook | Incident evidence and human confirmation | External Apple recovery result plus post-recovery inventory | Never automated; `ERR_DFU_RUNBOOK_UNRESOLVED`. |
| `return_macOS_space` | Apple-supported resize API | `APPLE_COMMAND_LOCK`; separate space-reclaim approval | Exact owned objects absent and macOS fallback healthy | Space result and protected set read back | Leave space free and hold. |

Any Apple operation or version not settled by the immutable locks becomes a named owner ruling and blocking gate. It is not filled with a guessed command, a current-host result, or a compatibility assumption. The adapter has no independent APFS implementation.

### 7.3 DTB mutation boundary

Any DTB mutation requires `Trusted<DtbMutationEnvelope>` from `dtb-mutation-envelope/v1`, an `Admitted<Policy>`, and a sealed `Trusted<BootContext>` where the operation requires boot lineage. The exact signed tuple includes project/repository/slice, board identity and board-registry digest, source identity with source generation and observation/source-byte digests, platform-manifest document ID and payload digest, pre- and post-mutation DTB digests, policy ID/digest, tool ID/version/digest, DTB artifact ID/version/digest, firmware bundle ID/version/digest/schema, DT schema ID/version/digest, ordered authorized mutation sentinels, `dtb-authority` signer binding, expiry, nonce, and replay identity. `ExpectedContext` binds `domain = "omarchy-dtb-authority"`, `context = "dtb-mutation-authorization"`, the exact closed mutation operation, board, manifest, policy, tool, artifact, firmware, DT schema, source generation, and ordered mutation set. A raw DTB, DTB path, post-build hash, caller-created context, forged `VerifiedDtbInputs`, or successful boot does not authorize mutation. A mismatch before or after mutation is `ERR_DTB_ENVELOPE_MISMATCH` and enters recovery; missing, stale, replayed, or unsealed DTB inputs yield no trusted value.

## 8. Transaction state and event closure

### 8.1 Closed states

The transaction state set is closed. No spelling, alias, numeric code, warning state, or future state is accepted beyond this table:

```text
NEW
INVENTORY_READY
PLAN_READY
APPROVED
JOURNALED
RESIZING
STUB_CREATING
APPLE_STUB_READY
OWNER_HANDOFF_PENDING
IN_1TR
LOCALPOLICY_READY
LIVE_HANDOFF_PENDING
LIVE_RUNNING
LAYOUT_READY
IMAGE_STAGED
PENDING_BOOT
FIRST_BOOT_PENDING
HEALTH_CHECKING
SUCCESS
UPDATE_PENDING
UNINSTALL_PENDING
SPACE_RECLAIM_REQUESTED
ROLLBACK_REQUIRED
ROLLED_BACK
ABORTED
UNINSTALLED
RECOVERY_REQUIRED
```

The event set is also closed:

```text
INVENTORY_ACCEPTED
PLAN_BUILT
OWNER_APPROVED
JOURNAL_DURABLE
RESIZE_STARTED
RESIZE_COMMITTED
STUB_STARTED
STUB_COMMITTED
HANDOFF_REQUESTED
IN_1TR_VERIFIED
LOCALPOLICY_COMMITTED
LIVE_HANDOFF_COMMITTED
LIVE_STARTED
LAYOUT_COMMITTED
IMAGE_COMMITTED
PENDING_SLOT_COMMITTED
BOOT_ATTEMPTED
HEALTH_STARTED
BOOT_SUCCEEDED
BOOT_FAILED
UPDATE_REQUESTED
UNINSTALL_REQUESTED
UNINSTALL_DEFAULT_COMMITTED
UNINSTALL_OBJECTS_COMMITTED
SPACE_RECLAIM_REQUESTED
SPACE_RECLAIM_COMMITTED
ROLLBACK_REQUESTED
ROLLBACK_COMMITTED
ABORT_REQUESTED
ABORT_COMMITTED
RECOVERY_REQUESTED
RECOVERY_REPAIRED
RETRY_APPROVED
HOLD_REQUESTED
```

`RESUME` is an operation that replays the state-machine evaluator from durable evidence; it is not an event and cannot advance state. `REOBSERVE` and `RETRY` are internal actions only when the named event guard permits them. A refusal must be classified as one of the closed rejection codes; an unclassified refusal is `ERR_REFUSAL_UNCLASSIFIED`.

### 8.2 Generation, lineage, and replay identity

Every installation family has an immutable `lineage_id`. Its first transaction has `generation = 1`; each approved install, update, uninstall, abort-and-restart, or human recovery repair creates the next strictly larger generation in that lineage. Generation zero, decrement, wrap, reuse, and cross-lineage adoption are rejected. The maximum is 2^63-1; reaching it is `ERR_GENERATION_EXHAUSTED`, not wraparound.

Every durable transition carries `lineage_id`, `generation`, `parent_generation`, `state_before`, `event`, `state_after`, `operation_sequence`, `plan_digest`, `topology_digest`, and a unique `replay_identity` composed of lineage, generation, operation sequence, event, phase, and transaction nonce. `operation_sequence` is strictly increasing from 1. A duplicate replay identity is accepted only as an exact byte-identical durable replay whose before and after evidence already match. Any differing duplicate is `ERR_EVENT_REPLAYED`; an event with a lower sequence is `ERR_EVENT_OUT_OF_ORDER`; a future sequence is `ERR_EVENT_SEQUENCE_GAP`; a wrong generation or lineage is `ERR_EVENT_LINEAGE_MISMATCH`.

Transition rejection precedence is fixed: decode and validate `state`; decode and validate `event`; validate lineage and generation; validate sequence and replay identity; validate the closed state/event pair; validate the operation guard and fresh approval; validate the precondition and protected-set proof; then invoke the adapter and classify its postcondition. The first failure in that order is the only durable rejection. An unknown state never becomes an unknown event, an unknown event never becomes an operation refusal, and an operation refusal never becomes a warning or skipped step.

### 8.3 Exhaustive transition table

The following table is the complete normal transition graph. Cross-cutting fault and hold transitions are specified immediately below it. Every row requires the state entry invariant, event guard, and state exit invariant in Section 8.4.

Stable transition IDs T01-T44 are preserved from the prior design; T30 now terminates deletion at `SPACE_RECLAIM_REQUESTED`, and T45/T46 append the durable request and classified commit boundary without renumbering earlier coverage.

| Transition | From | Event | To | Guard |
|---|---|---|---|---|
| T01 | `NEW` | `INVENTORY_ACCEPTED` | `INVENTORY_READY` | Fresh read-only inventory is complete and all Apple reads are classified. |
| T02 | `INVENTORY_READY` | `PLAN_BUILT` | `PLAN_READY` | Verified board/platform values and pure deterministic plan exist. |
| T03 | `PLAN_READY` | `OWNER_APPROVED` | `APPROVED` | Fresh `Trusted<OwnerApproval>` binds every Section 3.3 field. |
| T04 | `APPROVED` | `JOURNAL_DURABLE` | `JOURNALED` | Approval and signed plan header are durable in both replicas. |
| T05 | `JOURNALED` | `RESIZE_STARTED` | `RESIZING` | The fixed operation graph requires resize and prepare evidence is durable. |
| T06 | `RESIZING` | `RESIZE_COMMITTED` | `STUB_CREATING` | Apple resize postcondition and protected-set equality pass. |
| T07 | `JOURNALED` | `STUB_STARTED` | `STUB_CREATING` | No resize is required and the first stub prepare is durable. |
| T08 | `STUB_CREATING` | `STUB_COMMITTED` | `APPLE_STUB_READY` | Partition, APFS roles, files, pairing, and read-backs all pass. |
| T09 | `APPLE_STUB_READY` | `HANDOFF_REQUESTED` | `OWNER_HANDOFF_PENDING` | Target descriptor, visible instructions, and Apple boot selection are durable. |
| T10 | `OWNER_HANDOFF_PENDING` | `IN_1TR_VERIFIED` | `IN_1TR` | The exact target enters paired RecoveryOS/1TR and identity is re-observed. |
| T11 | `IN_1TR` | `LOCALPOLICY_COMMITTED` | `LOCALPOLICY_READY` | Target-only LocalPolicy postcondition passes and macOS policy is unchanged. |
| T12 | `LOCALPOLICY_READY` | `LIVE_HANDOFF_COMMITTED` | `LIVE_HANDOFF_PENDING` | Signed live-image descriptor and closure are verified in the target handoff. |
| T13 | `LIVE_HANDOFF_PENDING` | `LIVE_STARTED` | `LIVE_RUNNING` | Live agent verifies board, plan, target, and artifact closure. |
| T14 | `LIVE_RUNNING` | `LAYOUT_COMMITTED` | `LAYOUT_READY` | Exact new layout and ownership manifest pass read-back. |
| T15 | `LAYOUT_READY` | `IMAGE_COMMITTED` | `IMAGE_STAGED` | Inactive image and boot bundle pass digest, length, fsync, and read-back. |
| T16 | `IMAGE_STAGED` | `PENDING_SLOT_COMMITTED` | `PENDING_BOOT` | Pending tuple, attempt policy, and last-known-good slot pass. |
| T17 | `PENDING_BOOT` | `BOOT_ATTEMPTED` | `FIRST_BOOT_PENDING` | One boot selection is durable and the fallback remains available. |
| T18 | `FIRST_BOOT_PENDING` | `HEALTH_STARTED` | `HEALTH_CHECKING` | The selected slot starts the bounded health procedure. |
| T19 | `HEALTH_CHECKING` | `BOOT_SUCCEEDED` | `SUCCESS` | `Trusted<BootHealthCore>` passes through the sealed boot context and separate `Trusted<BootSuccessMark>` is durable. |
| T20 | `SUCCESS` | `UPDATE_REQUESTED` | `UPDATE_PENDING` | New update plan is rendered and approval is pending for the inactive-slot generation. |
| T21 | `SUCCESS` | `UNINSTALL_REQUESTED` | `UNINSTALL_PENDING` | Exact ownership manifest, fresh topology, and uninstall approval pass. |
| T22 | `HEALTH_CHECKING` | `BOOT_FAILED` | `ROLLBACK_REQUIRED` | A required check or attempt policy fails with a typed result. |
| T23 | `PENDING_BOOT` | `BOOT_FAILED` | `ROLLBACK_REQUIRED` | Boot boundary reports a typed failed attempt before health. |
| T24 | `ROLLBACK_REQUIRED` | `ROLLBACK_REQUESTED` | `ROLLBACK_REQUIRED` | Last-known-good selection is prepared and no unknown mutation is hidden. |
| T25 | `ROLLBACK_REQUIRED` | `ROLLBACK_COMMITTED` | `ROLLED_BACK` | Prior slot and fallback boot read back exactly. |
| T26 | `ROLLED_BACK` | `RETRY_APPROVED` | `UPDATE_PENDING` | New generation, fresh plan, and separate approval are issued. |
| T27 | `UNINSTALL_PENDING` | `UNINSTALL_DEFAULT_COMMITTED` | `UNINSTALL_PENDING` | macOS fallback selection is read back before deletion. |
| T28 | `UNINSTALL_PENDING` | `ABORT_REQUESTED` | `UNINSTALL_PENDING` | Abort is requested; no delete begins until safe abort evidence is durable. |
| T29 | `UNINSTALL_PENDING` | `ABORT_COMMITTED` | `ABORTED` | Any permitted non-destructive abort evidence is durable. |
| T30 | `UNINSTALL_PENDING` | `UNINSTALL_OBJECTS_COMMITTED` | `SPACE_RECLAIM_REQUESTED` | All approved owned objects are absent, macOS fallback is verified, and the post-delete reclaim scope is prepared; no space mutation is inferred. |
| T31 | `ABORTED` | `RECOVERY_REPAIRED` | `NEW` | Human recovery evidence is complete and a new generation is created. |
| T32 | `ROLLED_BACK` | `RECOVERY_REPAIRED` | `NEW` | Recovery evidence is complete and no old approval is reused. |
| T33 | `RECOVERY_REQUIRED` | `RECOVERY_REPAIRED` | `NEW` | Named human recovery, fresh inventory, and new generation pass. |
| T34 | `RECOVERY_REQUIRED` | `ABORT_COMMITTED` | `ABORTED` | Abort is safe and durable without claiming external state was repaired. |
| T35 | `NEW` | `ABORT_COMMITTED` | `ABORTED` | No mutation has begun and no approval is needed to abandon planning. |
| T36 | `INVENTORY_READY` | `ABORT_COMMITTED` | `ABORTED` | No mutation has begun and all user-owned inputs remain unchanged. |
| T37 | `PLAN_READY` | `ABORT_COMMITTED` | `ABORTED` | No mutation has begun and plan data remains available as evidence. |
| T38 | `APPROVED` | `ABORT_COMMITTED` | `ABORTED` | Approval is revoked and no durable mutation has begun. |
| T39 | `JOURNALED` | `ABORT_COMMITTED` | `ABORTED` | Only transaction metadata exists and its ownership is clear. |
| T40 | `OWNER_HANDOFF_PENDING` | `ABORT_COMMITTED` | `ABORTED` | Apple target selection is safely returned or remains visibly pending; no guessed cleanup. |
| T41 | `LIVE_HANDOFF_PENDING` | `ABORT_COMMITTED` | `ABORTED` | No Linux target mutation has begun and Apple fallback is preserved. |
| T42 | `SUCCESS` | `ABORT_COMMITTED` | `SUCCESS` | Abort is not a deletion; success history is immutable. |
| T43 | `UNINSTALLED` | `INVENTORY_ACCEPTED` | `INVENTORY_READY` | A new installation family generation starts from a fresh observation. |
| T44 | `UPDATE_PENDING` | `OWNER_APPROVED` | `APPROVED` | Fresh approval binds the new update generation and its inactive-slot plan. |
| T45 | `SPACE_RECLAIM_REQUESTED` | `SPACE_RECLAIM_REQUESTED` | `SPACE_RECLAIM_REQUESTED` | The post-delete reclaim request, exact deleted-object set, fresh snapshot, separate approval, and lock identity are durable in both replicas before the Apple call. |
| T46 | `SPACE_RECLAIM_REQUESTED` | `SPACE_RECLAIM_COMMITTED` | `UNINSTALLED` | The Apple space result is complete, classified, read back exactly, and leaves the protected set unchanged; the commit record is durable in both replicas. |

The explicit states `UPDATE_PENDING`, `ROLLBACK_REQUIRED`, `ROLLED_BACK`, and `ABORTED` are not aliases for another state. They have their own durable records, user-visible text, restart behavior, and promotion consequences.

### 8.3.1 Global hold and fault transitions

`RECOVERY_REQUESTED` and `HOLD_REQUESTED` are valid from every state that can have an in-flight operation. They never advance over a missing postcondition. The explicit rows below make the global rule enumerable; `RECOVERY_REQUIRED` is the only destination for a hold or an uncertain external effect.

| Transition | From | Event | To | Guard |
|---|---|---|---|---|
| G01 | `NEW` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | A hold is recorded without any external mutation. |
| G02 | `INVENTORY_READY` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | The read-only observation is retained and no mutation is allowed. |
| G03 | `PLAN_READY` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | The plan remains evidence and cannot be executed while held. |
| G04 | `APPROVED` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Approval is not consumed by a hold and cannot be reused after repair. |
| G05 | `JOURNALED` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Journal metadata is held without an external call. |
| G06 | `RESIZING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Resize state is re-observed before any retry. |
| G07 | `STUB_CREATING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Partial new objects are classified before any further operation. |
| G08 | `APPLE_STUB_READY` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Stub evidence is held and no boot switch is inferred. |
| G09 | `OWNER_HANDOFF_PENDING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Physical handoff remains pending and cannot time out into mutation. |
| G10 | `IN_1TR` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | RecoveryOS and policy state are re-read before continuation. |
| G11 | `LOCALPOLICY_READY` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Target and macOS policy are re-read before continuation. |
| G12 | `LIVE_HANDOFF_PENDING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Offline closure remains fixed and no network refresh is permitted. |
| G13 | `LIVE_RUNNING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Linux targets are observed before any formatting operation. |
| G14 | `LAYOUT_READY` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Encryption and filesystem state are classified before retry. |
| G15 | `IMAGE_STAGED` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Active and last-good slots remain untouched. |
| G16 | `PENDING_BOOT` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Pending marker and fallback are read back before continuation. |
| G17 | `FIRST_BOOT_PENDING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | The attempt record is preserved and no success is inferred. |
| G18 | `HEALTH_CHECKING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Partial health is held and cannot be promoted. |
| G19 | `UPDATE_PENDING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | The update generation is held without package refresh. |
| G20 | `UNINSTALL_PENDING` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | No next deletion is permitted until exact ownership is re-observed. |
| G21 | `ROLLBACK_REQUIRED` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | Fallback is held until its exact identity is verified. |
| G22 | `ROLLED_BACK` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | The failed generation remains quarantined. |
| G23 | `RECOVERY_REQUIRED` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | A repeated hold is an exact idempotent status event only. |
| G24 | `NEW` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | The request is durable even though no external effect exists. |
| G25 | `INVENTORY_READY` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Fresh observation is required before any future plan. |
| G26 | `PLAN_READY` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | The plan is held without owner approval. |
| G27 | `APPROVED` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Approval is invalidated and cannot be replayed. |
| G28 | `JOURNALED` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Replica and topology evidence are rechecked. |
| G29 | `RESIZING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Resize outcome is classified before retry or abort. |
| G30 | `STUB_CREATING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | New objects are not removed without exact ownership proof. |
| G31 | `APPLE_STUB_READY` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Stub and pairing state are held for human review. |
| G32 | `OWNER_HANDOFF_PENDING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | No timeout or unseen physical action advances state. |
| G33 | `IN_1TR` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Policy mutation is not repeated. |
| G34 | `LOCALPOLICY_READY` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Both Apple policy states are observed again. |
| G35 | `LIVE_HANDOFF_PENDING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | The exact closure and descriptor are preserved. |
| G36 | `LIVE_RUNNING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Linux identity and target state are observed again. |
| G37 | `LAYOUT_READY` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Partial encryption state is not reinitialized. |
| G38 | `IMAGE_STAGED` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Inactive-slot evidence is retained without overwrite. |
| G39 | `PENDING_BOOT` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Pending state is held without an extra boot attempt. |
| G40 | `FIRST_BOOT_PENDING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | The attempt budget is not advanced by recovery request. |
| G41 | `HEALTH_CHECKING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | No partial check can produce success. |
| G42 | `UPDATE_PENDING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | The update cannot refresh or substitute inputs. |
| G43 | `UNINSTALL_PENDING` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Deletion is stopped before the next exact target. |
| G44 | `ROLLBACK_REQUIRED` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Fallback selection remains bounded by the manifest. |
| G45 | `ROLLED_BACK` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | Retry requires a fresh generation after repair. |
| G46 | `RECOVERY_REQUIRED` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | A repeated request is exact and idempotent. |
| G47 | `SPACE_RECLAIM_REQUESTED` | `HOLD_REQUESTED` | `RECOVERY_REQUIRED` | A reclaim request is held until its exact request record, approval, lock, and target state are re-observed. |
| G48 | `SPACE_RECLAIM_REQUESTED` | `RECOVERY_REQUESTED` | `RECOVERY_REQUIRED` | No reclaim call is repeated; deleted objects remain absent and space is not guessed to be reclaimed. |

`SUCCESS`, `ABORTED`, and `UNINSTALLED` accept no hold or fault event that changes their state. A request presented there is `ERR_EVENT_ORDER`; status inspection is read-only. `ABORT_REQUESTED` is safe only in the explicitly listed pre-mutation or handoff states; after any uncertain mutation it is converted to `RECOVERY_REQUESTED`, never directly to `ABORTED`. Thus hold, abort, rollback, and recovery are bounded at every boundary.

### 8.4 Entry, exit, restart, hold, abort, and rollback invariants

Every state has bounded behavior. Entry is committed only after the event's before-state record and event evidence are durable on both replicas. Exit is committed only after fresh observations prove the next state's invariant. A crash before the entry commit leaves the previous state; a crash after entry commit reopens the entered state and runs its restart rule. A crash with an uncertain external effect enters `RECOVERY_REQUIRED`; it never guesses based on process position.

| State | Durable entry invariant | Allowed exit | Restart, hold, abort, and rollback rule |
|---|---|---|---|
| `NEW` | No transaction mutation and no accepted plan | `INVENTORY_READY` or `ABORTED` | Restart performs read-only inventory; hold is harmless; abort creates no target. |
| `INVENTORY_READY` | Complete fresh inventory and no mutation | `PLAN_READY` or `ABORTED` | Restart re-runs inventory; any change invalidates the observation; rollback is not applicable. |
| `PLAN_READY` | Canonical plan, protected set, closure, and preview | `APPROVED` or `ABORTED` | Restart rerenders; approval must be reissued if any byte changes; abort leaves storage unchanged. |
| `APPROVED` | Fresh separate approval and no mutation | `JOURNALED` or `ABORTED` | Approval expiry, replay, or snapshot change returns to `PLAN_READY`; no resume from a prompt. |
| `JOURNALED` | Signed plan header and two matching replicas | `RESIZING`, `STUB_CREATING`, `RECOVERY_REQUIRED`, or `ABORTED` | Restart reads fresh topology; hold is allowed only before first mutation; abort removes metadata only. |
| `RESIZING` | Resize prepare, exact target, and approval evidence | `STUB_CREATING` or `RECOVERY_REQUIRED` | Reclassify old/exact-new/unknown; unknown holds in recovery; no automatic inverse. |
| `STUB_CREATING` | New-object prepare with exact parent and range | `APPLE_STUB_READY` or `RECOVERY_REQUIRED` | Adopt only exact postcondition; partial or duplicate objects require recovery. |
| `APPLE_STUB_READY` | Stub roles, files, pairing, and descriptor verified | `OWNER_HANDOFF_PENDING` or `RECOVERY_REQUIRED` | Restart verifies exact IDs and digest; abort may clean only proven new files before handoff. |
| `OWNER_HANDOFF_PENDING` | Apple target selection and physical instructions durable | `IN_1TR`, `ABORTED`, or `RECOVERY_REQUIRED` | Retry handoff without mutation; hold is visible; abort restores Apple fallback only with proof. |
| `IN_1TR` | Paired RecoveryOS/1TR and target identity verified | `LOCALPOLICY_READY` or `RECOVERY_REQUIRED` | Wrong mode returns to handoff; no policy mutation is repeated blindly. |
| `LOCALPOLICY_READY` | Target-only policy change and unchanged macOS policy | `LIVE_HANDOFF_PENDING` or `RECOVERY_REQUIRED` | Restart reads both policy states; unknown policy is recovery. |
| `LIVE_HANDOFF_PENDING` | Live descriptor and offline closure available | `LIVE_RUNNING` or `ABORTED` | Retry exact handoff; no network refresh; abort leaves Apple fallback. |
| `LIVE_RUNNING` | Linux agent verified plan, board, target, and closure | `LAYOUT_READY` or `RECOVERY_REQUIRED` | Restart revalidates all identities; any change is recovery. |
| `LAYOUT_READY` | Exact ESP, encryption, filesystem, and ownership layout | `IMAGE_STAGED` or `RECOVERY_REQUIRED` | Resume only exact new IDs; uncertain encryption key state never reinitializes. |
| `IMAGE_STAGED` | Inactive slot read-back matches approved digest | `PENDING_BOOT` or `RECOVERY_REQUIRED` | Active and last-good slots are immutable; retry uses same digest only. |
| `PENDING_BOOT` | Pending tuple, attempt policy, and fallback are durable | `FIRST_BOOT_PENDING` or `ROLLBACK_REQUIRED` | Restart preserves pending state; failed selection requests rollback. |
| `FIRST_BOOT_PENDING` | One attempt and fallback record are durable | `HEALTH_CHECKING` or `ROLLBACK_REQUIRED` | Boot agent increments bounded attempts; exhaustion requests rollback. |
| `HEALTH_CHECKING` | Required health procedure is running for exact slot | `SUCCESS` or `ROLLBACK_REQUIRED` | Partial health never succeeds; crash resumes checks or rolls back on typed failure. |
| `SUCCESS` | Health core and separate success mark are durable | `UPDATE_PENDING`, `UNINSTALL_PENDING`, or same-state status | Restart is read-only status; updates and uninstall require new generation and approval. |
| `UPDATE_PENDING` | New inactive update plan is bound and approval is pending | `APPROVED` or `RECOVERY_REQUIRED` | Restart revalidates update generation; no package refresh or alternate artifact. |
| `UNINSTALL_PENDING` | Exact ownership preview, fallback proof, and approval are durable | `SPACE_RECLAIM_REQUESTED`, `ABORTED`, or `RECOVERY_REQUIRED` | Revalidate before each delete; crash preserves remaining objects and stops. |
| `SPACE_RECLAIM_REQUESTED` | Exact deleted-object set, reclaim scope, request event, approval, and lock are durable in both replicas | `UNINSTALLED` or `RECOVERY_REQUIRED` | Restart re-observes the Apple target and request record; no reclaim call is made until the request is durable and exact. |
| `ROLLBACK_REQUIRED` | Typed failure and last-good candidate are durable | `ROLLED_BACK` or `RECOVERY_REQUIRED` | Select only verified last-good; unknown boot policy requires recovery. |
| `ROLLED_BACK` | Prior slot and fallback read back; failed slot quarantined | `UPDATE_PENDING`, `NEW`, or `RECOVERY_REQUIRED` | Restart shows failed generation; retry needs new approval; no silent repair. |
| `ABORTED` | Abort result and untouched/known residuals are durable | `NEW` only through `RECOVERY_REPAIRED` | Same generation cannot resume; residual uncertainty is recovery. |
| `UNINSTALLED` | Exact owned objects absent, macOS fallback verified, and space-reclaim commit read back | `NEW` through fresh inventory | Restart is status only; new install cannot reuse old approval or IDs. |
| `RECOVERY_REQUIRED` | Ambiguity, unsupported state, or crash uncertainty is durable | `ABORTED` or `NEW` through human `RECOVERY_REPAIRED` | Hold indefinitely without mutation; rollback is only verified fallback; no warning-success. |

Any event presented to a state outside the table is rejected with `ERR_EVENT_ORDER` before state or disk mutation. Unknown state, event, generation, sequence, replay identity, refusal, or transition is fatal: `ERR_UNKNOWN_STATE`, `ERR_UNKNOWN_EVENT`, `ERR_EVENT_LINEAGE_MISMATCH`, `ERR_EVENT_SEQUENCE_GAP`, `ERR_EVENT_REPLAYED`, `ERR_REFUSAL_UNCLASSIFIED`, or `ERR_EVENT_ORDER` is recorded and the transaction enters `RECOVERY_REQUIRED` when a transaction exists. The engine never warns, skips, or chooses the nearest state.

### 8.5 Exhaustive operation-to-event guards

Every mutating operation is in this closed list. A mutation cannot be called unless the exact row guard and event are satisfied.

For every operation in the table that can change storage, boot policy, or slot state, the proof includes a fresh matching snapshot and a separate non-replayed `Trusted<OwnerApproval>` bound to the exact operation. A row lacking either term is invalid even when its other proof terms pass.

| Operation ID | Required current state | Required event | Required proof | Success state |
|---|---|---|---|---|
| `O01 reserve_transaction` | `APPROVED` | `JOURNAL_DURABLE` | Approval, plan, closure digest, two replicas, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `JOURNALED` |
| `O02 resize_macos_container` | `JOURNALED` | `RESIZE_STARTED` | Fresh APFS IDs, free-range proof, protected disjointness, Apple lock, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `RESIZING` |
| `O03 create_stub_partition` | `RESIZING` or `STUB_CREATING` | `STUB_STARTED` | Exact parent, range, type, ownership, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `STUB_CREATING` |
| `O04 create_stub_apfs_roles` | `STUB_CREATING` | `STUB_STARTED` | New partition ID, Apple role recipe, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `STUB_CREATING` |
| `O05 stage_apple_stub_and_recovery` | `STUB_CREATING` | `STUB_COMMITTED` | Closure Apple inputs, exact target VGID, pairing recipe, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `APPLE_STUB_READY` |
| `O06 authorize_localpolicy` | `IN_1TR` | `LOCALPOLICY_COMMITTED` | Apple owner result, target VGID, unchanged macOS policy, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `LOCALPOLICY_READY` |
| `O07 set_boot_target` | `APPLE_STUB_READY` or `UNINSTALL_PENDING` | `HANDOFF_REQUESTED` or `UNINSTALL_DEFAULT_COMMITTED` | Apple lock, exact target/fallback, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | Recorded handoff or `UNINSTALL_PENDING` |
| `O08 handoff_live_image` | `LOCALPOLICY_READY` | `LIVE_HANDOFF_COMMITTED` | Closure-complete image, descriptor, target policy, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `LIVE_HANDOFF_PENDING` |
| `O09 create_esp_and_linux_partitions` | `LIVE_RUNNING` | `LAYOUT_COMMITTED` | Exact layout digest, new ranges, protected disjointness, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `LAYOUT_READY` |
| `O10 format_luks_and_btrfs` | `LIVE_RUNNING` | `LAYOUT_COMMITTED` | New target IDs, selected encryption state, secure-pipe proof, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `LAYOUT_READY` |
| `O11 write_inactive_slot` | `LAYOUT_READY` | `IMAGE_COMMITTED` | Inactive slot, same closure digest, exact length, image and bundle verification, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `IMAGE_STAGED` |
| `O12 set_pending_slot` | `IMAGE_STAGED` | `PENDING_SLOT_COMMITTED` | Slot manifest, last-good slot, manifest policy, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `PENDING_BOOT` |
| `O13 mark_boot_success` | `HEALTH_CHECKING` | `BOOT_SUCCEEDED` | Trusted boot-health, separate boot-success mark, fresh matching snapshot, and separate `Trusted<OwnerApproval>` for the approved transition | `SUCCESS` |
| `O14 select_last_known_good` | `ROLLBACK_REQUIRED` | `ROLLBACK_REQUESTED` | Verified rollback set from platform manifest, exact slot generation, fresh matching snapshot, and separate `Trusted<OwnerApproval>` for the rollback operation | `ROLLBACK_REQUIRED` |
| `O15 commit_rollback` | `ROLLBACK_REQUIRED` | `ROLLBACK_COMMITTED` | Fallback read-back, failed-slot quarantine, fresh matching snapshot, and separate `Trusted<OwnerApproval>` for the rollback operation | `ROLLED_BACK` |
| `O16 uninstall_set_macos_default` | `UNINSTALL_PENDING` | `UNINSTALL_DEFAULT_COMMITTED` | Exact Apple fallback proof, fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `UNINSTALL_PENDING` |
| `O17 uninstall_owned_objects` | `UNINSTALL_PENDING` | `UNINSTALL_OBJECTS_COMMITTED` | Exact ownership, fresh matching snapshot, per-object approval, prior fallback proof, and separate `Trusted<OwnerApproval>` | `SPACE_RECLAIM_REQUESTED` or recovery |
| `O18 reclaim_space` | `SPACE_RECLAIM_REQUESTED` | `SPACE_RECLAIM_COMMITTED` | Durable `SPACE_RECLAIM_REQUESTED` record, separate reclaim approval, Apple lock, exact fresh matching snapshot, and separate `Trusted<OwnerApproval>` | `UNINSTALLED` or recovery |

An operation that has no row, has the wrong event, or has an event in the wrong order rejects with `ERR_OPERATION_GUARD` before its external call. Operation success is never inferred from a process exit code without the row's postcondition classifier.

## 9. Journal, crash safety, and durable boundaries

### 9.1 Bounded authenticated replicas

The journal is a bounded canonical JSON Lines evidence log. It contains a signed plan header reference, lineage, generation, sequence, state/event, operation ID, phase, plan and topology digests, typed target IDs, precondition and expected-postcondition digests, observed result digest, replay identity, and record digest. It contains no password, passphrase, recovery key, token, raw NVRAM, serial, unredacted device path, or command output.

Two replicas are required after the transaction header exists: an application-support replica and an Omarchy-owned control-area replica. Each replica has a bounded maximum record size and total byte budget from immutable policy. Each record is written to a temporary file, flushed, file-synced, atomically renamed, directory-synced where supported, and read back by digest. A commit is valid only when both replicas contain the same record bytes and chain prefix. A single durable replica is evidence of a fault, not sufficient authority.

The journal is authenticated as evidence by the signed plan header, hash chain, record digest, replica agreement, and transaction signer. It is not an authenticated payload and it never grants a target or recreates `owner-approval/v1`.

### 9.2 Flush and mutation ordering

For every external mutation, the executor performs this exact sequence. Uninstall has one additional mandatory boundary: O17 deletion commits first, then T30 enters `SPACE_RECLAIM_REQUESTED`, T45 durably commits the `SPACE_RECLAIM_REQUESTED` request in both replicas, and only then may O18 call the Apple reclaim surface and emit `SPACE_RECLAIM_COMMITTED` through T46.

1. Freshly observe the complete allowlisted target and protected snapshots.
2. Validate the plan, closure, approval, generation, event guard, lock, and operation precondition.
3. Write and verify a `PREPARE` record to both replicas using the flush ordering above.
4. Invoke exactly one Apple or Linux adapter operation with typed arguments and network denied.
5. Capture bounded structured output and classify complete, partial, timeout, error, or unknown result.
6. Freshly re-observe targets, protected objects, boot policy, and relevant artifacts.
7. Verify the exact operation postcondition and unchanged protected properties.
8. Write and verify the matching `COMMIT` record to both replicas.
9. Only then emit the state-transition event and advance the durable state.

A crash before `PREPARE` means no operation may have run; the executor re-observes and either proves no mutation or enters recovery. A crash after `PREPARE` and before the call replays only an idempotent operation with the same fresh proof. A crash during or after the call before `COMMIT` always runs the classifier; old, exact-new, and unknown states have separate outcomes. Unknown is recovery. A crash after `COMMIT` but before state display reopens the committed next state and does not repeat the operation.

### 9.3 Replica and disk-full rules

The following cases are closed:

| Condition | Result |
|---|---|
| Identical complete replicas | Use their common verified prefix and fresh hardware state. |
| One truncated tail but identical complete prefix | Retain the tail as diagnostic evidence; if no prepare is missing, continue from the prefix; if a prepare is missing or the truncation boundary is uncertain, enter recovery. |
| Divergent records before the common prefix | `ERR_JOURNAL_DIVERGENT`; enter `RECOVERY_REQUIRED`; never choose the longer replica. |
| Replayed record with same identity and different bytes | `ERR_JOURNAL_REPLAYED`; enter recovery. |
| Duplicate identical record after commit | Accept only as exact byte-identical replay; no state advance. |
| Invalid hash or invalid canonical JSON | `ERR_JOURNAL_RECORD_INVALID`; ignore no safety-relevant suffix; enter recovery unless both replicas prove a safe pre-mutation prefix. |
| Missing replica | `ERR_JOURNAL_REPLICA_MISSING`; no mutation; recovery or safe abort only. |
| Disk full before prepare | `ERR_JOURNAL_FULL`; no external call and no state advance. |
| Disk full after an external call | `ERR_JOURNAL_DURABILITY_UNKNOWN`; classify hardware, preserve data, and enter recovery. |
| Record or output exceeds bound | `ERR_JOURNAL_RECORD_TOO_LARGE`; truncate only the diagnostic copy, never the authority record, and fail closed. |
| Replica read-back digest differs | `ERR_JOURNAL_READBACK_MISMATCH`; enter recovery. |

No journal timestamp determines order. Sequence, hash chain, generation, lineage, and replay identity determine order. A journal can show what was attempted; it cannot prove consent, widen scope, or supply a raw target.

### 9.4 Per-operation crash matrix

The future fault-injection suite must plant a crash immediately before and immediately after every durable mutation and every external call in O01 through O18. The expected classifier is fixed here:

| Boundary | Before-call result | After-call or uncertain result |
|---|---|---|
| O01 transaction reservation | No mutation; rerun fresh approval check | Replica mismatch is recovery; no external target exists. |
| O02 APFS resize | Original boundary; retry only after fresh exact proof | Old, exact new, or unknown; unknown is recovery, never inverse cleanup. |
| O03 partition creation | No new partition; rerun exact range proof | Adopt only exact UUID/type/range/parent; otherwise preserve and recover. |
| O04 APFS role creation | New partition remains unformatted or is classified | Complete only declared new roles; ambiguous role map is recovery. |
| O05 stub and RecoveryOS staging | No boot switch; remove only proven staged files | Hash and pairing classify; no label search or guessed cleanup. |
| O06 LocalPolicy | No policy call; rerun Apple authorization | Read target and macOS policy; any unknown result is recovery. |
| O07 boot selection | Apple fallback remains selected | Read back exact target and fallback; uncertainty is recovery. |
| O08 live handoff | Apple fallback and closure remain intact | Restart live agent only after identity and closure revalidation. |
| O09 layout creation | No new format; rerun exact range proof | Quarantine partial new objects; never touch protected objects. |
| O10 encryption/filesystem setup | No key state assumed | Probe exact metadata; partial key state is recovery, never reinitialize. |
| O11 inactive image write | Active slot unchanged | Verify same digest; invalidate pending partial and rewrite inactive only. |
| O12 pending marker | No boot switch | Read marker and attempts; uncertain marker is recovery. |
| O13 health/success commit | No success claim | Boot-health core and separate success mark must both verify; otherwise fallback. |
| O14/O15 rollback | Last-good remains available | Verify exact fallback and quarantine failed generation; uncertainty is recovery. |
| O16 default boot for uninstall | No deletion | Read back macOS fallback before any delete. |
| O17 object deletion | No deletion | Reobserve ownership and delete only exact remaining IDs, or stop. |
| O18 space reclaim | Before O18, deleted owned objects remain absent and the durable reclaim request, approval, lock, and fallback are present | After O18, read back the exact Apple space result and unchanged protected set; uncertainty leaves space free, keeps `SPACE_RECLAIM_REQUESTED`, and enters recovery rather than claiming `UNINSTALLED`. |

## 10. Destructive operation proofs and ownership

Before every operation classified as destructive, the engine computes:

```text
protected_before = JCS(all protected typed IDs and structural properties)
target_before = JCS(all target typed IDs and structural properties)
intent = JCS(plan_digest, scope_digest, generation, operation_id, typed arguments, expected result)
```

It then requires a fresh snapshot digest equal to the approved topology digest or an explicitly allowed state transition in the same operation row, target set a subset of the exact ownership manifest, target set disjoint from the protected set, physical byte ranges non-overlapping, parent closure exact, operation order exact, closure digest unchanged, Apple baseline lock present, and a fresh non-replayed `Trusted<OwnerApproval>`. The adapter receives a typed object. It never receives a raw path.

After the call, the engine requires complete structured output, a successful operation-specific classifier, exact postcondition, fresh target identity, unchanged protected snapshot for every non-allowed field, matching journal evidence, and the same generation and replay identity. A short output, warning, exit code, progress message, or successful tool invocation cannot satisfy the postcondition.

The destructive transition proof is therefore:

```text
Trusted<OwnerApproval>
  + fresh matching topology and identity snapshot
  + exact ownership and protected-set proof
  + closure-complete verified inputs
  + closed operation/event guard
  + immutable Apple/tool/policy locks
  + durable prepare
  -> one typed adapter call
  -> fresh classified postcondition
  -> durable commit
```

Any missing term returns a typed rejection before the external call. If a mutation may already have occurred, the result is `RECOVERY_REQUIRED` until exact observation proves a safe state. Journal evidence never supplies a missing term.

## 11. Slot generation, boot health, and rollback

### 11.1 Manifest-bound slot policy

Slot policy is derived only from `Trusted<PlatformManifest>` and its `components.boot_stack` relation. The policy defines slot names, generation width and monotonicity, lineage rules, attempt budget, fallback set, pending format, success-mark binding, update compatibility, and retention count. A local default attempt count or bootloader preference is not authority.

Each slot record contains exact ESP ID, slot name, root/LUKS/Btrfs IDs, platform-manifest document ID and payload digest, all five canonical component identities and artifact digests, board-registry identity, firmware schema, DTB pre/post identity where applicable, `source_generation`, generation, lineage, attempt counter, state, and record digest. Slot states are internal fields and cannot replace the transaction states or the separate success mark.

The active and last-known-good slots are never written while staging an inactive slot. The pending tuple is written only after the inactive slot read-back succeeds. The attempt counter is monotonic within the slot generation and bounded by the manifest policy. An attempt beyond the bound produces `ERR_BOOT_ATTEMPT_EXHAUSTED` and requests rollback; it does not wrap or mark success.

### 11.2 Boot-health and separate success

The boot-health agent emits a verified `boot-health/v1` core only from the sealed boot handoff. Its canonical payload is the common F-02 payload plus exactly `board_id`, `manifest_id`, `manifest_digest`, `profile_id`, `profile_digest`, `lineage_id`, `source_generation`, `slot`, `attempt`, `checks`, `checks_digest`, `success`, and `fallback`. `slot` contains exactly `slot_id`, `slot_generation`, and `boot_artifact_digest`; `attempt` contains exactly `counter`, `started_at`, `finished_at`, `previous_slot`, and `boot_context_generation`; `checks` is the sorted complete required set and `fallback` contains exactly `decision`, `target_slot`, `rollback_set_digest`, and `failure_code`. `source_generation` and `attempt.counter` are signed core fields, not diagnostics. The core contains no marker field, marker digest, or self-digest.

The core preimage is domain-separated and acyclic: `D_core = sha256(ASCII("omarchy-boot-health-core/v1") || 0x00 || JCS(C))`, where `C` is the complete canonical boot-health core payload. The separate `boot-success-mark/v1` carries `core_digest = D_core`, never its own digest or a core self-reference, and is accepted only after the core is durable and independently verified. A changed core field, `source_generation`, lineage, slot, attempt, check set, or fallback set changes `D_core` and invalidates the marker.

The boot handoff admits only an opaque external signed artifact envelope with identity, digest, interface/schema, provenance, license/redistribution decision, and observable handoff metadata. The producer source is not inspected or characterized here. The installer obtains one complete authenticated `Trusted<AtomicBootRecord>` at the boundary and calls `verify_boot_context(Trusted<AtomicBootRecord>, Trusted<TrustContext>, VerifiedClock) -> Trusted<BootContext> | typed rejection`. The sealed `BootContext` contains exactly `context_schema = "boot-context/v1"`, `board_id`, `manifest_id`, `manifest_digest`, `lineage_id`, `slot_id`, `slot_generation`, `attempt_counter`, `source_generation`, `atomic_record_digest`, `lineage_source_digest`, and source provenance. It is private to the contract library; no raw record, parsed core, local default, screenshot, process result, or caller-created context can reach a consumer.

`source_generation` is zero only before the first committed topology, becomes one with that first atomic commit, then increments exactly once for each different committed canonical topology and never resets, reuses, decrements, or wraps. The atomic boot record binds board, manifest, slot, lineage, slot generation, attempt counter, source generation, commit state, source bytes digest, and replay identity. A partial/torn record, generation reset, context transplant, stale record, or recomputation mismatch returns `BOOT_COUNTER_FAILURE`, `BOOT_CONTEXT_MISMATCH`, or `TRUST_BOUNDARY_FAILURE` with no `Trusted<BootContext>`.

Only after the core is durable and all required checks pass may a separate `boot-success-mark/v1` be constructed and verified. It binds `D_core` plus the exact board, manifest, selected slot, slot generation, lineage, attempt counter, `source_generation`, marker generation, check set, and rollback set. The success mark is accepted only when both redundant records are complete and the previous good slot remains readable. A desktop screenshot, process start, systemd success, bootloader handoff, or journal result cannot substitute for `Trusted<BootHealthCore>`, `Trusted<BootSuccessMark>`, or sealed `Trusted<BootContext>`.

The atomic protocol is:

1. Write and verify the health core as a pending or failed result.
2. Re-read the exact running board, slot, manifest, component digests, and previous-good slot.
3. Construct and verify the separate success mark only for a passing core.
4. Atomically replace the boot-status record set with the core and success mark together, or leave the prior committed set intact.
5. Emit `BOOT_SUCCEEDED` only after redundant read-back matches both trusted digests.

If any write, read-back, or power boundary is uncertain, the boot boundary preserves the prior good slot and returns `ROLLBACK_REQUIRED` or `RECOVERY_REQUIRED`. No half-written success can be interpreted as success.

### 11.3 Failure, fallback, and update behavior

Required-check failure, wrong board, digest mismatch, fatal boot error, or attempt exhaustion produces a typed failed health core and selects the exact last-known-good slot from the manifest-bound fallback set. If that slot is missing, mismatched, or cannot be read back, the result is `RECOVERY_REQUIRED`, not a warning-success.

An update begins at `UPDATE_PENDING` with a new generation and fresh approval. It stages only the inactive slot, preserves the prior good slot, switches once, and requires the same separate success mark. A failed update reaches `ROLLBACK_REQUIRED` and then `ROLLED_BACK` only after exact fallback read-back. A failure after switching but before classification remains recovery until observed. Package-by-package repair is not claimed as rollback.

## 12. Product UX, accessibility, localization, privacy, and support

### 12.1 Native GUI and CLI parity

The release UX is a signed, notarized native macOS GUI with a semantically equivalent CLI using the same transaction core, validators, state/event graph, plan bytes, approval contract, failure codes, and recovery instructions. A terminal-only script, second-stage shell, raw one-letter prompt, or divergent CLI is not the release UX.

The GUI and CLI expose the same user-visible state names, exact target and protected identifiers in redacted display form, byte changes, closure status, Apple handoff, progress, failure code, recovery action, rollback result, uninstall preview, and support-export preview. The CLI offers structured non-interactive read-only output and does not use cursor rewriting as a required interaction.

### 12.2 Accessibility and dynamic text

Every flow and every persisted recovery screen must pass VoiceOver, keyboard-only navigation, Switch Control, Dynamic Type, high contrast, reduced motion, and color-independent meaning. Focus order, labels, roles, state announcements, destructive confirmation, error recovery, and physical instructions are programmatically inspectable. Color is never the only signal. Motion never conveys the only progress or failure state.

All dynamic text is measured and laid out without truncation of board names, byte counts, paths shown for recovery, digests, error codes, Apple labels, or next actions. Overflow becomes wrapping, scrolling, or an explicit expandable region. No hidden abbreviation is used to conceal a security or destructive value. All strings, errors, units, dates, recovery instructions, boot-picker labels, 1TR guidance, uninstall text, and support content are localized. Apple-owned labels are quoted exactly as displayed so a localized user can identify them.

Reboot, boot-picker, 1TR, RecoveryOS, machine-owner, and DFU guidance is persisted in both visual and text form with numbered steps, target identity, plan digest, cancel/retry route, and safe return path. A timeout cannot delete data. A manual physical action is never recorded as complete without an observable handoff or an explicit human checkpoint.

### 12.3 Privacy and telemetry

Telemetry is off by default. Artifact downloads disclose their source policy and unavoidable server metadata but do not imply analytics consent. Optional metrics require a separate previewable consent containing the exact payload, retention, endpoint, and deletion path. Failure to report never changes installation, rollback, uninstall, or recovery.

The default report excludes passwords, passphrases, owner tokens, LocalPolicy material, recovery keys, serials, raw APFS identifiers, hostnames, usernames, home paths, MAC/IP addresses, SSIDs/BSSIDs, full partition maps, raw command output, and arbitrary paths. Any board identity detail or disk detail requires a separate explicit support choice and redaction policy.

A support bundle is local-first, redacted, and user-selected. Before save or upload, the UI shows a manifest with every included file, content digest, redaction status, authorization requirement, destination, access scope, retention period, and deletion action. Upload is a separate consent from save. Support staff access requires the owner-approved support case and role binding; retention expires under the owner policy; transaction outcome never depends on support export.

## 13. Executable future gates and hostile test contract

### 13.1 Versioned hostile fixtures

The fixture corpus is one deterministic, versioned index. The prior family lists are intentionally not duplicate fixture tables: this index is the sole row authority and contains 122 rows in the order closure, secret, trust, approval, identity, Apple, journal, boot, uninstall, and UX. Every row mechanically includes exactly one mutation, the exact prior state, attempted input/transition, exact result state, stable rejection code, JSON path, phase, durable evidence, and restart observation. A row with an omitted field, a warning-success result, a non-durable rejection, a duplicate ID, or a duplicate code/path/phase triple is invalid. These are future test inputs only; no fixture, validator, state-machine runner, fault harness, or report artifact exists.

| Fixture ID | Single mutation | Prior state | Attempted input or transition | Exact result state | Stable rejection code | JSON path | Phase | Durable evidence | Restart observation |
|---|---|---|---|---|---|---|---|---|---|
| CLOSURE-001 | Remove the first cache receipt | PLAN_READY | PLAN_READY: hostile pre_consent_closure input at $.candidate_input_closure.entries[0].cache_receipt | PLAN_READY | `ERR_CLOSURE_CACHE_RECEIPT_MISSING` | `$.candidate_input_closure.entries[0].cache_receipt` | `pre_consent_closure` | rejection_record/CLOSURE-001; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-002 | Flip one byte of a cached firmware object | PLAN_READY | PLAN_READY: hostile pre_consent_verify input at $.candidate_input_closure.entries[1].content_digest | PLAN_READY | `ERR_CLOSURE_DIGEST_MISMATCH` | `$.candidate_input_closure.entries[1].content_digest` | `pre_consent_verify` | rejection_record/CLOSURE-002; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-003 | Return hostile-valid-HTTP bytes with a hostile source selector | PLAN_READY | PLAN_READY: hostile pre_consent_acquire input at $.candidate_input_closure.entries[2].source_selector | PLAN_READY | `ERR_CLOSURE_SOURCE_POLICY_MISMATCH` | `$.candidate_input_closure.entries[2].source_selector` | `pre_consent_acquire` | rejection_record/CLOSURE-003; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-004 | Replace an exact commit selector with a mutable-ref branch name | PLAN_READY | PLAN_READY: hostile pre_consent_validate input at $.candidate_input_closure.entries[3].source_selector | PLAN_READY | `ERR_CLOSURE_MUTABLE_SELECTOR` | `$.candidate_input_closure.entries[3].source_selector` | `pre_consent_validate` | rejection_record/CLOSURE-004; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-005 | Serve the right digest through an unapproved mirror-substitution | PLAN_READY | PLAN_READY: hostile pre_consent_acquire input at $.candidate_input_closure.entries[4].source_selector.mirror | PLAN_READY | `ERR_CLOSURE_MIRROR_NOT_ALLOWED` | `$.candidate_input_closure.entries[4].source_selector.mirror` | `pre_consent_acquire` | rejection_record/CLOSURE-005; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-006 | Advance an input beyond its expiry | PLAN_READY | PLAN_READY: hostile pre_consent_verify input at $.candidate_input_closure.entries[5].verification.expires_at | PLAN_READY | `ERR_CLOSURE_INPUT_EXPIRED` | `$.candidate_input_closure.entries[5].verification.expires_at` | `pre_consent_verify` | rejection_record/CLOSURE-006; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-007 | Change the declared byte length by one | PLAN_READY | PLAN_READY: hostile pre_consent_verify input at $.candidate_input_closure.entries[6].length | PLAN_READY | `ERR_CLOSURE_LENGTH_MISMATCH` | `$.candidate_input_closure.entries[6].length` | `pre_consent_verify` | rejection_record/CLOSURE-007; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-008 | Change a package media type to an accepted-looking type | PLAN_READY | PLAN_READY: hostile pre_consent_verify input at $.candidate_input_closure.entries[7].media_type | PLAN_READY | `ERR_CLOSURE_MEDIA_TYPE_MISMATCH` | `$.candidate_input_closure.entries[7].media_type` | `pre_consent_verify` | rejection_record/CLOSURE-008; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-009 | Remove one transitive package index | PLAN_READY | PLAN_READY: hostile pre_consent_complete input at $.candidate_input_closure.completeness_proof.dependencies[8] | PLAN_READY | `ERR_CLOSURE_TRANSITIVE_INPUT_MISSING` | `$.candidate_input_closure.completeness_proof.dependencies[8]` | `pre_consent_complete` | rejection_record/CLOSURE-009; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-010 | Replace the selected artifact identity while retaining its digest field | PLAN_READY | PLAN_READY: hostile pre_consent_cross_check input at $.candidate_input_closure.entries[9].artifact_identity | PLAN_READY | `ERR_CLOSURE_ARTIFACT_IDENTITY_MISMATCH` | `$.candidate_input_closure.entries[9].artifact_identity` | `pre_consent_cross_check` | rejection_record/CLOSURE-010; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-011 | Substitute an accepted mirror after consent | JOURNALED | JOURNALED: hostile post_consent_read input at $.candidate_input_closure.entries[10].cache_receipt.object_id | JOURNALED | `ERR_POST_CONSENT_MIRROR_SUBSTITUTION` | `$.candidate_input_closure.entries[10].cache_receipt.object_id` | `post_consent_read` | rejection_record/CLOSURE-011; replicas=2; state_before_digest=JOURNALED; state_after_digest=JOURNALED; external_effect=none | restart: JOURNALED; reobserve; no replay |
| CLOSURE-012 | Perform a post-consent refresh of a mutable package index | JOURNALED | JOURNALED: hostile post_consent_mutation input at $.candidate_input_closure.entries[11].source_selector | JOURNALED | `ERR_POST_CONSENT_REFRESH_DENIED` | `$.candidate_input_closure.entries[11].source_selector` | `post_consent_mutation` | rejection_record/CLOSURE-012; replicas=2; state_before_digest=JOURNALED; state_after_digest=JOURNALED; external_effect=none | restart: JOURNALED; reobserve; no replay |
| CLOSURE-013 | Delete a required RecoveryOS input after consent | JOURNALED | JOURNALED: hostile post_consent_mutation input at $.candidate_input_closure.entries[12].cache_receipt | JOURNALED | `ERR_POST_CONSENT_INPUT_MISSING` | `$.candidate_input_closure.entries[12].cache_receipt` | `post_consent_mutation` | rejection_record/CLOSURE-013; replicas=2; state_before_digest=JOURNALED; state_after_digest=JOURNALED; external_effect=none | restart: JOURNALED; reobserve; no replay |
| CLOSURE-014 | Change a platform-manifest payload digest after consent | JOURNALED | JOURNALED: hostile post_consent_revalidate input at $.candidate_input_closure.entries[13].manifest_identity.payload_digest | PLAN_READY | `ERR_POST_CONSENT_MANIFEST_CHANGED` | `$.candidate_input_closure.entries[13].manifest_identity.payload_digest` | `post_consent_revalidate` | rejection_record/CLOSURE-014; replicas=2; state_before_digest=JOURNALED; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| CLOSURE-015 | Return a valid opaque artifact envelope for the wrong interface | PLAN_READY | PLAN_READY: hostile pre_consent_cross_check input at $.candidate_input_closure.entries[14].artifact_identity.interface | PLAN_READY | `ERR_OPAQUE_INTERFACE_MISMATCH` | `$.candidate_input_closure.entries[14].artifact_identity.interface` | `pre_consent_cross_check` | rejection_record/CLOSURE-015; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| SECRET-001 | Place a passphrase in a child argv slot | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_preflight input at $.secure_control.argv[0] | LAYOUT_READY | `ERR_SECRET_ARGV_REJECTED` | `$.secure_control.argv[0]` | `linux_secret_preflight` | rejection_record/SECRET-001; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-002 | Place a passphrase in an environment value | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_preflight input at $.secure_control.environment.SECRET | LAYOUT_READY | `ERR_SECRET_ENV_REJECTED` | `$.secure_control.environment.SECRET` | `linux_secret_preflight` | rejection_record/SECRET-002; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-003 | Write a passphrase to ordinary stdin | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_preflight input at $.secure_control.stdin_route | LAYOUT_READY | `ERR_SECRET_GENERAL_STDIN_REJECTED` | `$.secure_control.stdin_route` | `linux_secret_preflight` | rejection_record/SECRET-003; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-004 | Leave an unrelated descriptor inherited | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_exec input at $.secure_control.inherited_fds[3] | LAYOUT_READY | `ERR_SECRET_UNINTENDED_FD_REJECTED` | `$.secure_control.inherited_fds[3]` | `linux_secret_exec` | rejection_record/SECRET-004; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-005 | Spill a passphrase into a cache file | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_write input at $.secure_control.cache_path | LAYOUT_READY | `ERR_SECRET_CACHE_WRITE_REJECTED` | `$.secure_control.cache_path` | `linux_secret_write` | rejection_record/SECRET-005; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-006 | Spill a passphrase into a filesystem file | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_write input at $.secure_control.filesystem_path | LAYOUT_READY | `ERR_SECRET_FILESYSTEM_WRITE_REJECTED` | `$.secure_control.filesystem_path` | `linux_secret_write` | rejection_record/SECRET-006; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-007 | Permit a writable buffer outside locked memory | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_preflight input at $.secure_control.memory.locked | LAYOUT_READY | `ERR_SECRET_UNLOCKED_MEMORY_REJECTED` | `$.secure_control.memory.locked` | `linux_secret_preflight` | rejection_record/SECRET-007; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-008 | Enable echo during input | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_read input at $.secure_control.terminal.echo | LAYOUT_READY | `ERR_SECRET_ECHO_REJECTED` | `$.secure_control.terminal.echo` | `linux_secret_read` | rejection_record/SECRET-008; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-009 | Exceed the byte bound by one | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_read input at $.secure_control.passphrase_length | LAYOUT_READY | `ERR_SECRET_LENGTH_REJECTED` | `$.secure_control.passphrase_length` | `linux_secret_read` | rejection_record/SECRET-009; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-010 | Preserve bytes after cancellation | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_cleanup input at $.secure_control.cleanup.cancelled | LAYOUT_READY | `ERR_SECRET_ZEROIZATION_REJECTED` | `$.secure_control.cleanup.cancelled` | `linux_secret_cleanup` | rejection_record/SECRET-010; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-011 | Permit a core dump containing the buffer | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_preflight input at $.secure_control.memory.core_dump | LAYOUT_READY | `ERR_SECRET_COREDUMP_REJECTED` | `$.secure_control.memory.core_dump` | `linux_secret_preflight` | rejection_record/SECRET-011; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-012 | Emit the secret in a structured event | LAYOUT_READY | LAYOUT_READY: hostile secret_output_scan input at $.events[0].fields.passphrase | LAYOUT_READY | `ERR_SECRET_EVENT_REJECTED` | `$.events[0].fields.passphrase` | `secret_output_scan` | rejection_record/SECRET-012; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-013 | Emit the secret in a journal result | LAYOUT_READY | LAYOUT_READY: hostile secret_output_scan input at $.journal.records[0].result | LAYOUT_READY | `ERR_SECRET_JOURNAL_REJECTED` | `$.journal.records[0].result` | `secret_output_scan` | rejection_record/SECRET-013; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-014 | Include the secret in support export | LAYOUT_READY | LAYOUT_READY: hostile support_export_scan input at $.support_bundle.files[0].content | LAYOUT_READY | `ERR_SECRET_SUPPORT_EXPORT_REJECTED` | `$.support_bundle.files[0].content` | `support_export_scan` | rejection_record/SECRET-014; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-015 | Route an Apple authorization secret into the Linux pipe | LAYOUT_READY | LAYOUT_READY: hostile credential_boundary input at $.secure_control.source_credential_class | LAYOUT_READY | `ERR_APPLE_SECRET_CROSSING_REJECTED` | `$.secure_control.source_credential_class` | `credential_boundary` | rejection_record/SECRET-015; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-016 | Swap the passphrase into an unlocked secondary buffer | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_swap_check input at $.secure_control.swap | LAYOUT_READY | `ERR_SECRET_SWAP_REJECTED` | `$.secure_control.swap` | `linux_secret_swap_check` | rejection_record/SECRET-016; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-017 | Write the passphrase into a crash artifact | LAYOUT_READY | LAYOUT_READY: hostile secret_output_scan input at $.secure_control.crash_artifact | RECOVERY_REQUIRED | `ERR_SECRET_CRASH_ARTIFACT_REJECTED` | `$.secure_control.crash_artifact` | `secret_output_scan` | rejection_record/SECRET-017; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| SECRET-018 | Emit the passphrase in a log line | LAYOUT_READY | LAYOUT_READY: hostile secret_output_scan input at $.logs[0].message | LAYOUT_READY | `ERR_SECRET_LOG_REJECTED` | `$.logs[0].message` | `secret_output_scan` | rejection_record/SECRET-018; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-019 | Emit the passphrase in telemetry | LAYOUT_READY | LAYOUT_READY: hostile secret_output_scan input at $.telemetry.events[0].fields | LAYOUT_READY | `ERR_SECRET_TELEMETRY_REJECTED` | `$.telemetry.events[0].fields` | `secret_output_scan` | rejection_record/SECRET-019; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-020 | Mark an unredacted secret field as redacted | LAYOUT_READY | LAYOUT_READY: hostile support_redaction_scan input at $.support_bundle.files[0].redaction | LAYOUT_READY | `ERR_SECRET_REDACTION_REJECTED` | `$.support_bundle.files[0].redaction` | `support_redaction_scan` | rejection_record/SECRET-020; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=LAYOUT_READY; external_effect=none | restart: LAYOUT_READY; reobserve; no replay |
| SECRET-021 | Retain passphrase bytes after cancellation in recovery data | LAYOUT_READY | LAYOUT_READY: hostile linux_secret_cancel_recovery input at $.secure_control.cleanup.recovery_bytes | RECOVERY_REQUIRED | `ERR_SECRET_CANCELLATION_EXPOSURE_REJECTED` | `$.secure_control.cleanup.recovery_bytes` | `linux_secret_cancel_recovery` | rejection_record/SECRET-021; replicas=2; state_before_digest=LAYOUT_READY; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| SECRET-022 | Expose the passphrase on a recovery screen | RECOVERY_REQUIRED | RECOVERY_REQUIRED: hostile recovery_exposure_scan input at $.recovery_screen.fields | RECOVERY_REQUIRED | `ERR_SECRET_RECOVERY_EXPOSURE_REJECTED` | `$.recovery_screen.fields` | `recovery_exposure_scan` | rejection_record/SECRET-022; replicas=2; state_before_digest=RECOVERY_REQUIRED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| TRUST-001 | Change the payload type to another closed type | PLAN_READY | PLAN_READY: hostile trust_type_check input at `$.envelope.payload_type` | PLAN_READY | `ERR_TRUST_PAYLOAD_TYPE` | `$.envelope.payload_type` | `trust_type_check` | rejection_record/TRUST-001; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-002 | Change one canonical payload byte | PLAN_READY | PLAN_READY: hostile trust_jcs_check input at `$.envelope.payload_bytes` | PLAN_READY | `ERR_TRUST_JCS_BYTES` | `$.envelope.payload_bytes` | `trust_jcs_check` | rejection_record/TRUST-002; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-003 | Change the separately recorded payload digest | PLAN_READY | PLAN_READY: hostile trust_digest_check input at `$.envelope.payload_digest` | PLAN_READY | `ERR_TRUST_PAYLOAD_DIGEST` | `$.envelope.payload_digest` | `trust_digest_check` | rejection_record/TRUST-003; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-004 | Reuse a stable document ID for different content | PLAN_READY | PLAN_READY: hostile trust_identity_check input at `$.envelope.document_id` | PLAN_READY | `ERR_TRUST_DOCUMENT_ID_COLLISION` | `$.envelope.document_id` | `trust_identity_check` | rejection_record/TRUST-004; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-005 | Set the envelope expiry before trusted current time | PLAN_READY | PLAN_READY: hostile trust_time_check input at `$.envelope.expires_at` | PLAN_READY | `ERR_TRUST_ENVELOPE_EXPIRED` | `$.envelope.expires_at` | `trust_time_check` | rejection_record/TRUST-005; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-006 | Reuse an accepted replay identity | PLAN_READY | PLAN_READY: hostile trust_replay_check input at `$.envelope.replay_identity` | PLAN_READY | `ERR_TRUST_REPLAY_IDENTITY` | `$.envelope.replay_identity` | `trust_replay_check` | rejection_record/TRUST-006; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-007 | Remove a required threshold signature | PLAN_READY | PLAN_READY: hostile trust_signature_check input at `$.envelope.signatures[1]` | PLAN_READY | `ERR_TRUST_THRESHOLD_SHORTFALL` | `$.envelope.signatures[1]` | `trust_signature_check` | rejection_record/TRUST-007; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-008 | Bind the signer to an unapproved role | PLAN_READY | PLAN_READY: hostile trust_role_check input at `$.envelope.authority_role_binding` | PLAN_READY | `ERR_TRUST_ROLE_UNBOUND` | `$.envelope.authority_role_binding` | `trust_role_check` | rejection_record/TRUST-008; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-009 | Use a different schema-set digest | PLAN_READY | PLAN_READY: hostile trust_schema_check input at `$.envelope.schema_set_digest` | PLAN_READY | `ERR_TRUST_SCHEMA_SET_MISMATCH` | `$.envelope.schema_set_digest` | `trust_schema_check` | rejection_record/TRUST-009; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-010 | Pass the decoded object around the verifier | PLAN_READY | PLAN_READY: hostile trusted_consumer_check input at `$.consumer.raw_object` | PLAN_READY | `ERR_TRUST_RAW_OBJECT_BYPASS` | `$.consumer.raw_object` | `trusted_consumer_check` | rejection_record/TRUST-010; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-011 | Call `admit` with `Parsed<T>` instead of `Trusted<T>` | PLAN_READY | PLAN_READY: hostile trusted_admission_check input at `$.admit.input` | PLAN_READY | `ERR_TRUST_ADMIT_UNTRUSTED` | `$.admit.input` | `trusted_admission_check` | rejection_record/TRUST-011; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-012 | Pass an unsealed policy map to `admit` | PLAN_READY | PLAN_READY: hostile policy_admission_check input at `$.admit.policy` | PLAN_READY | `ERR_TRUST_POLICY_UNSEALED` | `$.admit.policy` | `policy_admission_check` | rejection_record/TRUST-012; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-013 | Change `ExpectedContext.payload_type` | PLAN_READY | PLAN_READY: hostile trust_context_check input at `$.expected_context.payload_type` | PLAN_READY | `ERR_TRUST_EXPECTED_CONTEXT_MISMATCH` | `$.expected_context.payload_type` | `trust_context_check` | rejection_record/TRUST-013; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-014 | Change `ExpectedContext.target_identity_digests` | PLAN_READY | PLAN_READY: hostile trust_context_check input at `$.expected_context.target_identity_digests[0]` | PLAN_READY | `ERR_TRUST_EXPECTED_CONTEXT_MISMATCH` | `$.expected_context.target_identity_digests[0]` | `trust_context_check` | rejection_record/TRUST-014; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-015 | Alter the domain-separated anti-transplant preimage | PLAN_READY | PLAN_READY: hostile trust_preimage_check input at `$.auth_preimage.anti_transplant` | PLAN_READY | `ERR_TRUST_ANTI_TRANSPLANT_MISMATCH` | `$.auth_preimage.anti_transplant` | `trust_preimage_check` | rejection_record/TRUST-015; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-016 | Negotiate a mixed schema-set digest | PLAN_READY | PLAN_READY: hostile trust_negotiation_check input at `$.negotiation.schema_set_digest` | PLAN_READY | `ERR_TRUST_SCHEMA_SET_MIXED` | `$.negotiation.schema_set_digest` | `trust_negotiation_check` | rejection_record/TRUST-016; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-017 | Duplicate one negotiated payload type | PLAN_READY | PLAN_READY: hostile trust_negotiation_check input at `$.negotiation.payload_types[7]` | PLAN_READY | `ERR_TRUST_NEGOTIATION_DUPLICATE` | `$.negotiation.payload_types[7]` | `trust_negotiation_check` | rejection_record/TRUST-017; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-018 | Reorder two negotiated payload types | PLAN_READY | PLAN_READY: hostile trust_negotiation_check input at `$.negotiation.payload_types[1]` | PLAN_READY | `ERR_TRUST_NEGOTIATION_ORDER` | `$.negotiation.payload_types[1]` | `trust_negotiation_check` | rejection_record/TRUST-018; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-019 | Pass a raw or caller-created `BootContext` | HEALTH_CHECKING | HEALTH_CHECKING: hostile boot_context_seam input at `$.boot_context` | RECOVERY_REQUIRED | `ERR_TRUST_BOOT_CONTEXT_UNSEALED` | `$.boot_context` | `boot_context_seam` | rejection_record/TRUST-019; replicas=2; state_before_digest=HEALTH_CHECKING; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| TRUST-020 | Sign a DTB envelope under the installer-plan context | PLAN_READY | PLAN_READY: hostile dtb_context_check input at `$.dtb.context` | PLAN_READY | `ERR_DTB_CONTEXT_TRANSPLANT` | `$.dtb.context` | `dtb_context_check` | rejection_record/TRUST-020; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-021 | Pass forged `VerifiedDtbInputs` to the DTB producer | PLAN_READY | PLAN_READY: hostile dtb_input_seam input at `$.dtb_inputs` | PLAN_READY | `ERR_DTB_INPUT_UNSEALED` | `$.dtb_inputs` | `dtb_input_seam` | rejection_record/TRUST-021; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| TRUST-022 | Change DTB source generation after observation commit | PLAN_READY | PLAN_READY: hostile dtb_source_generation_check input at `$.dtb.source_identity.source_generation` | PLAN_READY | `ERR_DTB_SOURCE_GENERATION_MISMATCH` | `$.dtb.source_identity.source_generation` | `dtb_source_generation_check` | rejection_record/TRUST-022; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-001 | Change the approved plan digest | PLAN_READY | PLAN_READY: hostile approval_binding_check input at `$.owner_approval.plan_digest` | PLAN_READY | `ERR_APPROVAL_PLAN_CHANGED` | `$.owner_approval.plan_digest` | `approval_binding_check` | rejection_record/APPROVAL-001; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-002 | Change the destructive scope digest | PLAN_READY | PLAN_READY: hostile approval_binding_check input at `$.owner_approval.scope_digest` | PLAN_READY | `ERR_APPROVAL_SCOPE_CHANGED` | `$.owner_approval.scope_digest` | `approval_binding_check` | rejection_record/APPROVAL-002; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-003 | Change the schema-set digest | PLAN_READY | PLAN_READY: hostile approval_binding_check input at `$.owner_approval.schema_set_digest` | PLAN_READY | `ERR_APPROVAL_SCHEMA_SET_CHANGED` | `$.owner_approval.schema_set_digest` | `approval_binding_check` | rejection_record/APPROVAL-003; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-004 | Change the board-registry payload digest | PLAN_READY | PLAN_READY: hostile approval_binding_check input at $.owner_approval.board_registry_digest | PLAN_READY | `ERR_APPROVAL_REGISTRY_CHANGED` | `$.owner_approval.board_registry_digest` | `approval_binding_check` | rejection_record/APPROVAL-004; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-005 | Change the platform-manifest payload digest | PLAN_READY | PLAN_READY: hostile approval_binding_check input at $.owner_approval.manifest_digest | PLAN_READY | `ERR_APPROVAL_MANIFEST_CHANGED` | `$.owner_approval.manifest_digest` | `approval_binding_check` | rejection_record/APPROVAL-005; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-006 | Change the approved topology digest | PLAN_READY | PLAN_READY: hostile approval_fresh_snapshot input at `$.owner_approval.topology_digest` | PLAN_READY | `ERR_APPROVAL_TOPOLOGY_CHANGED` | `$.owner_approval.topology_digest` | `approval_fresh_snapshot` | rejection_record/APPROVAL-006; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-007 | Change one target identity | PLAN_READY | PLAN_READY: hostile approval_fresh_snapshot input at $.owner_approval.target_identities[0] | PLAN_READY | `ERR_APPROVAL_TARGET_CHANGED` | `$.owner_approval.target_identities[0]` | `approval_fresh_snapshot` | rejection_record/APPROVAL-007; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-008 | Reorder two operations | PLAN_READY | PLAN_READY: hostile approval_operation_check input at $.owner_approval.operations[1] | PLAN_READY | `ERR_APPROVAL_OPERATION_ORDER_CHANGED` | `$.owner_approval.operations[1]` | `approval_operation_check` | rejection_record/APPROVAL-008; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-009 | Change the actor account | PLAN_READY | PLAN_READY: hostile approval_actor_check input at $.owner_approval.account_id | PLAN_READY | `ERR_APPROVAL_ACTOR_CHANGED` | `$.owner_approval.account_id` | `approval_actor_check` | rejection_record/APPROVAL-009; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-010 | Change the authority role binding | PLAN_READY | PLAN_READY: hostile approval_role_check input at $.owner_approval.actor_role | PLAN_READY | `ERR_APPROVAL_ROLE_CHANGED` | `$.owner_approval.actor_role` | `approval_role_check` | rejection_record/APPROVAL-010; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-011 | Change the policy digest | PLAN_READY | PLAN_READY: hostile approval_policy_check input at `$.owner_approval.policy_digest` | PLAN_READY | `ERR_APPROVAL_POLICY_CHANGED` | `$.owner_approval.policy_digest` | `approval_policy_check` | rejection_record/APPROVAL-011; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| APPROVAL-012 | Reuse the approval after expiry | PLAN_READY | PLAN_READY: hostile approval_expiry_check input at `$.owner_approval.expires_at` | PLAN_READY | `ERR_APPROVAL_EXPIRED` | `$.owner_approval.expires_at` | `approval_expiry_check` | rejection_record/APPROVAL-012; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| IDENTITY-001 | Duplicate a whole_disk stable ID | INVENTORY_READY | INVENTORY_READY: hostile identity_parse input at `$.observed.disks[1].canonical_value` | INVENTORY_READY | `ERR_IDENTITY_DUPLICATE` | `$.observed.disks[1].canonical_value` | `identity_parse` | rejection_record/IDENTITY-001; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| IDENTITY-002 | Clone an ID onto a different parent | INVENTORY_READY | INVENTORY_READY: hostile identity_parent_check input at `$.observed.partitions[1].physical_parent_ids` | INVENTORY_READY | `ERR_IDENTITY_CLONE` | `$.observed.partitions[1].physical_parent_ids` | `identity_parent_check` | rejection_record/IDENTITY-002; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| IDENTITY-003 | Reuse a device path for another object | INVENTORY_READY | INVENTORY_READY: hostile identity_reobserve input at `$.observed.disks[0].device_path` | INVENTORY_READY | `ERR_IDENTITY_PATH_REUSE` | `$.observed.disks[0].device_path` | `identity_reobserve` | rejection_record/IDENTITY-003; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| IDENTITY-004 | Change capacity after approval | INVENTORY_READY | INVENTORY_READY: hostile identity_reobserve input at `$.observed.disks[0].capacity` | INVENTORY_READY | `ERR_IDENTITY_PROPERTY_CHANGED` | `$.observed.disks[0].capacity` | `identity_reobserve` | rejection_record/IDENTITY-004; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| IDENTITY-005 | Remove the physical parent | INVENTORY_READY | INVENTORY_READY: hostile identity_parent_check input at `$.observed.partitions[0].physical_parent_ids[0]` | INVENTORY_READY | `ERR_IDENTITY_PARENT_MISSING` | `$.observed.partitions[0].physical_parent_ids[0]` | `identity_parent_check` | rejection_record/IDENTITY-005; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| IDENTITY-006 | Add a second volume with the same role | INVENTORY_READY | INVENTORY_READY: hostile identity_role_check input at `$.observed.volume_groups[0].role_map` | INVENTORY_READY | `ERR_IDENTITY_AMBIGUOUS` | `$.observed.volume_groups[0].role_map` | `identity_role_check` | rejection_record/IDENTITY-006; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| IDENTITY-007 | Overflow the numeric byte bound | INVENTORY_READY | INVENTORY_READY: hostile identity_bounds_check input at `$.observed.partitions[0].length` | INVENTORY_READY | `ERR_IDENTITY_NUMERIC_BOUND` | `$.observed.partitions[0].length` | `identity_bounds_check` | rejection_record/IDENTITY-007; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| IDENTITY-008 | Change normalization without changing display text | INVENTORY_READY | INVENTORY_READY: hostile identity_normalization_check input at `$.observed.ids[0].normalization_version` | INVENTORY_READY | `ERR_IDENTITY_NORMALIZATION_COLLISION` | `$.observed.ids[0].normalization_version` | `identity_normalization_check` | rejection_record/IDENTITY-008; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| IDENTITY-009 | Reuse an older observation generation | INVENTORY_READY | INVENTORY_READY: hostile identity_generation_check input at `$.observed.ids[0].observed_generation` | INVENTORY_READY | `ERR_IDENTITY_STALE` | `$.observed.ids[0].observed_generation` | `identity_generation_check` | rejection_record/IDENTITY-009; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| APPLE-001 | Truncate a read-only plist result | INVENTORY_READY | INVENTORY_READY: hostile apple_output_classify input at `$.apple_result.raw_output` | INVENTORY_READY | `ERR_APPLE_OUTPUT_PARTIAL` | `$.apple_result.raw_output` | `apple_output_classify` | rejection_record/APPLE-001; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| APPLE-002 | Report an unlisted Apple tool version | INVENTORY_READY | INVENTORY_READY: hostile apple_baseline_check input at `$.apple_result.tool_version` | INVENTORY_READY | `ERR_APPLE_TOOL_VERSION_UNSUPPORTED` | `$.apple_result.tool_version` | `apple_baseline_check` | rejection_record/APPLE-002; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| APPLE-003 | Call an unavailable Apple API | INVENTORY_READY | INVENTORY_READY: hostile apple_baseline_check input at `$.apple_result.api_name` | INVENTORY_READY | `ERR_APPLE_API_UNSUPPORTED` | `$.apple_result.api_name` | `apple_baseline_check` | rejection_record/APPLE-003; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| APPLE-004 | Return success with a wrong storage postcondition | RESIZING | RESIZING: hostile apple_postcondition_check input at `$.apple_result.postcondition` | RECOVERY_REQUIRED | `ERR_APPLE_POSTCONDITION_MISMATCH` | `$.apple_result.postcondition` | `apple_postcondition_check` | rejection_record/APPLE-004; replicas=2; state_before_digest=RESIZING; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| APPLE-005 | Report a policy change on the wrong target | INVENTORY_READY | INVENTORY_READY: hostile apple_policy_check input at `$.apple_result.target_vgid` | INVENTORY_READY | `ERR_LOCALPOLICY_TARGET_UNKNOWN` | `$.apple_result.target_vgid` | `apple_policy_check` | rejection_record/APPLE-005; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| APPLE-006 | Omit unchanged macOS policy read-back | INVENTORY_READY | INVENTORY_READY: hostile apple_policy_check input at `$.apple_result.macos_policy` | INVENTORY_READY | `ERR_LOCALPOLICY_MACOS_READBACK_MISSING` | `$.apple_result.macos_policy` | `apple_policy_check` | rejection_record/APPLE-006; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| APPLE-007 | Remove the qualified DFU runbook reference | INVENTORY_READY | INVENTORY_READY: hostile apple_recovery_gate input at `$.apple_result.dfu_runbook_digest` | INVENTORY_READY | `ERR_DFU_RUNBOOK_UNRESOLVED` | `$.apple_result.dfu_runbook_digest` | `apple_recovery_gate` | rejection_record/APPLE-007; replicas=2; state_before_digest=INVENTORY_READY; state_after_digest=INVENTORY_READY; external_effect=none | restart: INVENTORY_READY; reobserve; no replay |
| JOURNAL-001 | Cut the final record halfway through | JOURNALED | JOURNALED: hostile journal_parse input at `$.journal.records[7].record_bytes` | RECOVERY_REQUIRED | `ERR_JOURNAL_TORN_RECORD` | `$.journal.records[7].record_bytes` | `journal_parse` | rejection_record/JOURNAL-001; replicas=2; state_before_digest=JOURNALED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| JOURNAL-002 | Change one canonical journal byte | JOURNALED | JOURNALED: hostile journal_hash_check input at `$.journal.records[8].record_digest` | JOURNALED | `ERR_JOURNAL_RECORD_INVALID` | `$.journal.records[8].record_digest` | `journal_hash_check` | rejection_record/JOURNAL-002; replicas=2; state_before_digest=JOURNALED; state_after_digest=JOURNALED; external_effect=none | restart: JOURNALED; reobserve; no replay |
| JOURNAL-003 | Diverge the second replica before the common prefix | JOURNALED | JOURNALED: hostile journal_replica_check input at `$.journal.replicas[1].records[4]` | RECOVERY_REQUIRED | `ERR_JOURNAL_DIVERGENT` | `$.journal.replicas[1].records[4]` | `journal_replica_check` | rejection_record/JOURNAL-003; replicas=2; state_before_digest=JOURNALED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| JOURNAL-004 | Replay an old record with a new result | JOURNALED | JOURNALED: hostile journal_replay_check input at `$.journal.records[3].replay_identity` | RECOVERY_REQUIRED | `ERR_JOURNAL_REPLAYED` | `$.journal.records[3].replay_identity` | `journal_replay_check` | rejection_record/JOURNAL-004; replicas=2; state_before_digest=JOURNALED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| JOURNAL-005 | Remove one sequence number | JOURNALED | JOURNALED: hostile journal_order_check input at `$.journal.records[5].sequence` | RECOVERY_REQUIRED | `ERR_EVENT_SEQUENCE_GAP` | `$.journal.records[5].sequence` | `journal_order_check` | rejection_record/JOURNAL-005; replicas=2; state_before_digest=JOURNALED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| JOURNAL-006 | Lower the generation number | JOURNALED | JOURNALED: hostile journal_generation_check input at `$.journal.records[6].generation` | RECOVERY_REQUIRED | `ERR_GENERATION_ROLLBACK` | `$.journal.records[6].generation` | `journal_generation_check` | rejection_record/JOURNAL-006; replicas=2; state_before_digest=JOURNALED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| JOURNAL-007 | Fill the journal before prepare | JOURNALED | JOURNALED: hostile journal_prepare_gate input at `$.journal.budget.available_bytes` | JOURNALED | `ERR_JOURNAL_FULL` | `$.journal.budget.available_bytes` | `journal_prepare_gate` | rejection_record/JOURNAL-007; replicas=2; state_before_digest=JOURNALED; state_after_digest=JOURNALED; external_effect=none | restart: JOURNALED; reobserve; no replay |
| JOURNAL-008 | Fill the journal after the external call | JOURNALED | JOURNALED: hostile journal_postcall_gate input at `$.journal.commit.available_bytes` | RECOVERY_REQUIRED | `ERR_JOURNAL_DURABILITY_UNKNOWN` | `$.journal.commit.available_bytes` | `journal_postcall_gate` | rejection_record/JOURNAL-008; replicas=2; state_before_digest=JOURNALED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| JOURNAL-009 | Exceed the bounded output size | JOURNALED | JOURNALED: hostile journal_bound_check input at `$.journal.records[9].result` | RECOVERY_REQUIRED | `ERR_JOURNAL_RECORD_TOO_LARGE` | `$.journal.records[9].result` | `journal_bound_check` | rejection_record/JOURNAL-009; replicas=2; state_before_digest=JOURNALED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| BOOT-001 | Change the running board identity | HEALTH_CHECKING | HEALTH_CHECKING: hostile boot_health_preflight input at $.boot_health.board_id | ROLLBACK_REQUIRED | `ERR_BOOT_BOARD_MISMATCH` | `$.boot_health.board_id` | `boot_health_preflight` | rejection_record/BOOT-001; replicas=2; state_before_digest=HEALTH_CHECKING; state_after_digest=ROLLBACK_REQUIRED; external_effect=none | restart: ROLLBACK_REQUIRED; reobserve; no replay |
| BOOT-002 | Select a slot outside the approved tuple | HEALTH_CHECKING | HEALTH_CHECKING: hostile boot_health_preflight input at $.boot_health.slot.slot_id | ROLLBACK_REQUIRED | `ERR_BOOT_SLOT_MISMATCH` | `$.boot_health.slot.slot_id` | `boot_health_preflight` | rejection_record/BOOT-002; replicas=2; state_before_digest=HEALTH_CHECKING; state_after_digest=ROLLBACK_REQUIRED; external_effect=none | restart: ROLLBACK_REQUIRED; reobserve; no replay |
| BOOT-003 | Change one component artifact digest | HEALTH_CHECKING | HEALTH_CHECKING: hostile boot_health_preflight input at $.boot_health.slot.boot_artifact_digest | ROLLBACK_REQUIRED | `ERR_BOOT_COMPONENT_DIGEST` | `$.boot_health.slot.boot_artifact_digest` | `boot_health_preflight` | rejection_record/BOOT-003; replicas=2; state_before_digest=HEALTH_CHECKING; state_after_digest=ROLLBACK_REQUIRED; external_effect=none | restart: ROLLBACK_REQUIRED; reobserve; no replay |
| BOOT-004 | Cut the health-core record before durable completion | HEALTH_CHECKING | HEALTH_CHECKING: hostile boot_health_durable_write input at $.boot_health.core_record | RECOVERY_REQUIRED | `ERR_BOOT_HEALTH_CORE_PARTIAL` | `$.boot_health.core_record` | `boot_health_durable_write` | rejection_record/BOOT-004; replicas=2; state_before_digest=HEALTH_CHECKING; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| BOOT-005 | Omit the separate success mark | HEALTH_CHECKING | HEALTH_CHECKING: hostile boot_success_gate input at $.boot_success_mark | ROLLBACK_REQUIRED | `ERR_BOOT_SUCCESS_MARK_MISSING` | `$.boot_success_mark` | `boot_success_gate` | rejection_record/BOOT-005; replicas=2; state_before_digest=HEALTH_CHECKING; state_after_digest=ROLLBACK_REQUIRED; external_effect=none | restart: ROLLBACK_REQUIRED; reobserve; no replay |
| BOOT-006 | Change the rollback set after health passes | HEALTH_CHECKING | HEALTH_CHECKING: hostile boot_success_binding input at $.boot_success_mark.rollback_set_digest | ROLLBACK_REQUIRED | `ERR_BOOT_ROLLBACK_SET_CHANGED` | `$.boot_success_mark.rollback_set_digest` | `boot_success_binding` | rejection_record/BOOT-006; replicas=2; state_before_digest=HEALTH_CHECKING; state_after_digest=ROLLBACK_REQUIRED; external_effect=none | restart: ROLLBACK_REQUIRED; reobserve; no replay |
| BOOT-007 | Remove the last-known-good slot | ROLLBACK_REQUIRED | ROLLBACK_REQUIRED: hostile boot_fallback_gate input at $.boot_health.fallback.rollback_set_digest | RECOVERY_REQUIRED | `ERR_BOOT_LAST_GOOD_MISSING` | `$.boot_health.fallback.rollback_set_digest` | `boot_fallback_gate` | rejection_record/BOOT-007; replicas=2; state_before_digest=ROLLBACK_REQUIRED; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| BOOT-008 | Increment the attempt counter past its bound | HEALTH_CHECKING | HEALTH_CHECKING: hostile boot_attempt_gate input at $.boot_health.attempt.counter | ROLLBACK_REQUIRED | `ERR_BOOT_ATTEMPT_EXHAUSTED` | `$.boot_health.attempt.counter` | `boot_attempt_gate` | rejection_record/BOOT-008; replicas=2; state_before_digest=HEALTH_CHECKING; state_after_digest=ROLLBACK_REQUIRED; external_effect=none | restart: ROLLBACK_REQUIRED; reobserve; no replay |
| UNINSTALL-001 | Supply a name without an ownership ID | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_selector_check input at `$.uninstall.target.name` | UNINSTALL_PENDING | `ERR_UNINSTALL_NAME_SELECTOR` | `$.uninstall.target.name` | `uninstall_selector_check` | rejection_record/UNINSTALL-001; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=UNINSTALL_PENDING; external_effect=none | restart: UNINSTALL_PENDING; reobserve; no replay |
| UNINSTALL-002 | Supply a size without an ownership ID | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_selector_check input at `$.uninstall.target.size` | UNINSTALL_PENDING | `ERR_UNINSTALL_SIZE_SELECTOR` | `$.uninstall.target.size` | `uninstall_selector_check` | rejection_record/UNINSTALL-002; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=UNINSTALL_PENDING; external_effect=none | restart: UNINSTALL_PENDING; reobserve; no replay |
| UNINSTALL-003 | Change a label while retaining a stale ID | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_identity_check input at `$.uninstall.target.label` | UNINSTALL_PENDING | `ERR_UNINSTALL_LABEL_FALSE_POSITIVE` | `$.uninstall.target.label` | `uninstall_identity_check` | rejection_record/UNINSTALL-003; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=UNINSTALL_PENDING; external_effect=none | restart: UNINSTALL_PENDING; reobserve; no replay |
| UNINSTALL-004 | Add a pre-existing Linux object to the candidate set | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_ownership_check input at `$.uninstall.ownership.entries[1]` | UNINSTALL_PENDING | `ERR_UNINSTALL_OWNERSHIP_MISSING` | `$.uninstall.ownership.entries[1]` | `uninstall_ownership_check` | rejection_record/UNINSTALL-004; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=UNINSTALL_PENDING; external_effect=none | restart: UNINSTALL_PENDING; reobserve; no replay |
| UNINSTALL-005 | Mark a shared ESP as exclusively owned | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_ownership_check input at `$.uninstall.ownership.entries[2].shared` | UNINSTALL_PENDING | `ERR_UNINSTALL_SHARED_ESP` | `$.uninstall.ownership.entries[2].shared` | `uninstall_ownership_check` | rejection_record/UNINSTALL-005; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=UNINSTALL_PENDING; external_effect=none | restart: UNINSTALL_PENDING; reobserve; no replay |
| UNINSTALL-006 | Mark the active target as deletable | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_fallback_check input at `$.uninstall.target.active` | UNINSTALL_PENDING | `ERR_UNINSTALL_ACTIVE_TARGET` | `$.uninstall.target.active` | `uninstall_fallback_check` | rejection_record/UNINSTALL-006; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=UNINSTALL_PENDING; external_effect=none | restart: UNINSTALL_PENDING; reobserve; no replay |
| UNINSTALL-007 | Change the ownership-manifest digest | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_approval_check input at `$.uninstall.ownership.manifest_digest` | UNINSTALL_PENDING | `ERR_UNINSTALL_MANIFEST_CHANGED` | `$.uninstall.ownership.manifest_digest` | `uninstall_approval_check` | rejection_record/UNINSTALL-007; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=UNINSTALL_PENDING; external_effect=none | restart: UNINSTALL_PENDING; reobserve; no replay |
| UNINSTALL-008 | Change the verified macOS fallback | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_fallback_check input at `$.uninstall.macos_fallback` | UNINSTALL_PENDING | `ERR_UNINSTALL_MACOS_FALLBACK_CHANGED` | `$.uninstall.macos_fallback` | `uninstall_fallback_check` | rejection_record/UNINSTALL-008; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=UNINSTALL_PENDING; external_effect=none | restart: UNINSTALL_PENDING; reobserve; no replay |
| UNINSTALL-009 | Remove one deletion postcondition | UNINSTALL_PENDING | UNINSTALL_PENDING: hostile uninstall_postcondition_check input at `$.uninstall.operations[0].postcondition` | RECOVERY_REQUIRED | `ERR_UNINSTALL_DELETE_POSTCONDITION` | `$.uninstall.operations[0].postcondition` | `uninstall_postcondition_check` | rejection_record/UNINSTALL-009; replicas=2; state_before_digest=UNINSTALL_PENDING; state_after_digest=RECOVERY_REQUIRED; external_effect=uncertain | restart: RECOVERY_REQUIRED; reobserve; no replay |
| UX-001 | Remove one localized error string | PLAN_READY | PLAN_READY: hostile ux_localization_check input at `$.localization.errors[0]` | PLAN_READY | `ERR_UX_LOCALIZATION_INCOMPLETE` | `$.localization.errors[0]` | `ux_localization_check` | rejection_record/UX-001; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| UX-002 | Clip a dynamic digest in the destructive summary | PLAN_READY | PLAN_READY: hostile ux_layout_check input at `$.ux.consent.dynamic_text[0]` | PLAN_READY | `ERR_UX_DYNAMIC_TEXT_CLIPPED` | `$.ux.consent.dynamic_text[0]` | `ux_layout_check` | rejection_record/UX-002; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| UX-003 | Remove the VoiceOver label from a destructive control | PLAN_READY | PLAN_READY: hostile ux_voiceover_check input at `$.ux.controls.delete.accessibility_label` | PLAN_READY | `ERR_UX_VOICEOVER_LABEL_MISSING` | `$.ux.controls.delete.accessibility_label` | `ux_voiceover_check` | rejection_record/UX-003; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| UX-004 | Make a destructive control unreachable by keyboard | PLAN_READY | PLAN_READY: hostile ux_keyboard_check input at `$.ux.keyboard.reachable_controls[0]` | PLAN_READY | `ERR_UX_KEYBOARD_PATH_MISSING` | `$.ux.keyboard.reachable_controls[0]` | `ux_keyboard_check` | rejection_record/UX-004; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| UX-005 | Remove Switch Control access to recovery | PLAN_READY | PLAN_READY: hostile ux_switch_control_check input at `$.ux.switch_control.recovery` | PLAN_READY | `ERR_UX_SWITCH_CONTROL_PATH_MISSING` | `$.ux.switch_control.recovery` | `ux_switch_control_check` | rejection_record/UX-005; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| UX-006 | Encode state only by color | PLAN_READY | PLAN_READY: hostile ux_visual_semantics_check input at `$.ux.state_announcements[0].text` | PLAN_READY | `ERR_UX_COLOR_ONLY_STATE` | `$.ux.state_announcements[0].text` | `ux_visual_semantics_check` | rejection_record/UX-006; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| UX-007 | Set telemetry consent to selected | PLAN_READY | PLAN_READY: hostile privacy_consent_check input at `$.privacy.telemetry.default` | PLAN_READY | `ERR_PRIVACY_TELEMETRY_PRESELECTED` | `$.privacy.telemetry.default` | `privacy_consent_check` | rejection_record/UX-007; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| UX-008 | Put a secret in the support manifest | PLAN_READY | PLAN_READY: hostile privacy_export_check input at `$.support_bundle.manifest.files[0].redaction` | PLAN_READY | `ERR_PRIVACY_SUPPORT_SECRET` | `$.support_bundle.manifest.files[0].redaction` | `privacy_export_check` | rejection_record/UX-008; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |
| UX-009 | Upload without showing the payload preview | PLAN_READY | PLAN_READY: hostile privacy_upload_check input at `$.support_bundle.upload.preview` | PLAN_READY | `ERR_PRIVACY_UPLOAD_PREVIEW_MISSING` | `$.support_bundle.upload.preview` | `privacy_upload_check` | rejection_record/UX-009; replicas=2; state_before_digest=PLAN_READY; state_after_digest=PLAN_READY; external_effect=none | restart: PLAN_READY; reobserve; no replay |

### 13.2 Property and state-machine tests

Future implementation must include property tests proving that no generated plan mutates an object outside the ownership set, no protected object changes, no raw path or mutable reference reaches a mutator, every destructive transition has a fresh approval and snapshot, and every postcondition is stronger than an exit code. Model-based tests must generate every closed state/event pair, every unknown event, every replay, every lower and future sequence, every generation mismatch, every refusal class, and every crash boundary. All unknown or out-of-order cases must produce the exact fail-closed code and never advance state.

The restart matrix runs immediately before and after every prepare, every external operation, every commit, every state event, every reboot into macOS, RecoveryOS, 1TR, live image, first boot, fallback, update, and each uninstall deletion. Fault injection covers network loss, DNS failure, hostile valid HTTP, redirect and mirror substitution, expiry, power loss, process death, disk full, partial writes, partial tool output, corrupt archives, wrong board, wrong key, journal divergence, and missing fallback.

Destructive tests run only on disposable Apple-capable hardware with an attached recovery certificate, a rehearsed Apple-supported recovery path, controlled power, and an operator-confirmed target certificate. A VM, mock, compile, image extraction, static assertion, or fake disk can validate lower layers but cannot produce physical qualification evidence.

### 13.3 Exact command and clean-checkout gates

Every future command-array test reads the exact arrays from named immutable `APPLE_COMMAND_LOCK` and `APPLE_BASELINE_LOCK` objects. The test rejects an omitted array, a three-dot token, a shell string, a mutable executable path, an environment-selected argument, an unresolved typed substitution, or a command not named by the lock. No abbreviated or unresolved command array is normative in this design.

Every CI job checks out a clean commit by exact SHA, verifies the schema-set digest, verifies lock digests, runs the relevant validator and property/state-machine tests, runs the full installer suite, scans for secrets and conflict markers, checks generated bindings, and records artifacts by digest. CI must not read the opaque human-produced source boundary. The jobs, validators, fixtures, lock objects, and generated bindings do not yet exist.

### 13.4 Report schema, statuses, artifacts, retention

Each future gate emits a plain internal verification report with `report_id`, `gate_id`, `commit_sha`, `fixture_set_digest`, `lock_digests`, `input_digests`, `status`, `failure_code`, `json_path`, `phase`, `artifact_manifest`, `reviewer_identity`, `started_at`, `finished_at`, and `retention_class`. Status is one of `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`. `PASS` requires every required case to run and pass; `FAIL` requires a reproducible failure record; `BLOCKED` names the missing owner or immutable input; `NOT_RUN` never counts as pass.

Artifacts include immutable logs, redacted traces, state-transition coverage, fixture results, command-array evidence, diff and clean-checkout identities, and physical evidence references where applicable. Retention and access are controlled by the owner-approved policy; raw physical evidence is encrypted and access-controlled, and public exports redact serials, accounts, home paths, network identifiers, filesystem UUIDs, secrets, tokens, and customer data. No report artifact exists yet.

The reviewer is independent of the writer and implementer, works from a clean detached checkout, defaults to reject, plants a single violation from each prerequisite class, and reruns the complete gate battery. The coordinator alone may classify a slice as DONE. This lane has no implementation, QA pass, qualification record, or independent review result.

### 13.5 Slice acceptance gates and current status

These are the future acceptance gates for the installer slices. A design row is not a passing gate. Each row remains `NOT IMPLEMENTED` until its named artifact and independent evidence exist.

| Slice | Required gate and evidence | Current status |
|---|---|---|
| I-01 | Executable closed state/event machine, destructive-boundary model, hostile state vectors, crash matrix, and reviewed threat model | `NOT IMPLEMENTED` |
| I-02 | Signed/notarized native GUI and equivalent CLI, trust verification, immutable locks, complete pre-consent closure, and signed app evidence | `NOT IMPLEMENTED` |
| I-03 | Pure read-only inventory, Q-00 admission, stable-ID resolver, deterministic `installer-plan/v1`, final consent, and no-mutation subprocess proof | `NOT IMPLEMENTED` |
| I-04 | Apple baseline adapter on every locked macOS/RecoveryOS version, owner authorization, journal replicas, crash classifiers, and safe macOS return evidence | `NOT IMPLEMENTED` |
| I-05 | Offline live-image handoff, exact board and target revalidation, manifest-bound layout, secure-pipe implementation, inactive-slot evidence, and artifact proof | `NOT IMPLEMENTED` |
| I-06 | Exact-ownership uninstall, rollback, recovery image, Apple-supported DFU escalation rehearsal, and residual census | `NOT IMPLEMENTED` |
| I-07 | Distinct credential-state implementation, Apple-owned secret handling, sole Linux pipe, zeroization proof, and all SECRET fixtures | `NOT IMPLEMENTED` |
| I-08 | GUI/CLI semantic parity, accessibility matrix, localization completeness, privacy consent, redacted support bundle, and UX evidence | `NOT IMPLEMENTED` |
| I-09 | Full pure-planner, restart, fault, disk-selection, uninstall, privacy, accessibility, localization, clean-path, and disposable-hardware suite | `NOT IMPLEMENTED` |

The dependency handoff graph in Section 14 is acyclic when interpreted as the PROGRAM ledger at the pinned commit. No row adds a reverse dependency or silently substitutes a design document for an implementation, human-only artifact, qualification record, or promotion authority. The only current result for every implementation or qualification prerequisite is `TODO` or `HUMAN-ONLY BLOCKED` in PROGRAM.

### 13.6 Scratch-only planted-violation probes

Before this correction is reported, a throwaway in-memory checker must plant one violation per correction seam and record the exact signal below. The checker may use only a `mktemp` scratch workspace or in-memory text and must never modify a tracked file or cross the opaque boot-artifact boundary. `SCRATCH PASS` means only that the document guard catches the planted text mutation; it is not an implementation, QA, qualification, support, promotion, or DONE result.

| Probe | Scratch mutation | Exact signal required | Meaning of a scratch pass |
|---|---|---|---|
| `RECLAIM` | Remove `T30`, `T45`, or `T46` from the transition corpus | `FAIL_RECLAIM_PATH_INCOMPLETE` | The post-delete request, durable request, and commit path are all required. |
| `OWNER` | Remove one of actor, account, role, time, method, result, proof, policy, replay, or target bindings | `FAIL_OWNER_BINDING_INCOMPLETE` | The exact domain-separated owner envelope cannot be shortened. |
| `TRUST` | Replace `admit(Trusted<T>, Admitted<Policy>)` or remove `ExpectedContext`/`auth_preimage` | `FAIL_TRUST_SEAM_INCOMPLETE` | No raw, unsealed, or transplanted value reaches a consumer. |
| `IDENTITY` | Add a fifth stable-ID kind or restore a local alternate prefix | `FAIL_IDENTITY_AUTHORITY_CONFLICT` | Only the four provisional F-02 hashed kinds are accepted, or the lane blocks. |
| `BOOT` | Remove `source_generation`, `D_core`, or sealed `Trusted<BootContext>` | `FAIL_BOOT_HANDOFF_INCOMPLETE` | Boot lineage and canonical core binding cannot be bypassed. |
| `SECRETS` | Remove any swap, crash-artifact, log, telemetry, redaction, cancellation, or recovery-exposure row | `FAIL_SECRET_EXPOSURE_MATRIX_INCOMPLETE` | Every prohibited route has a distinct hostile case. |
| `FIXTURES` | Drop any required fixture column or alter one row's durable evidence/restart field | `FAIL_FIXTURE_RECORD_SHAPE` | Every row remains a complete ten-field contract with stable identity. |
| `HANDOFFS` | Drop freshness, scope/context, residual owner, due-before gate, or one dependency member | `FAIL_HANDOFF_RECORD_SHAPE` | Every handoff remains exact and matches the PROGRAM set. |
| `BASELINE` | Replace the owner-approved immutable artifact with a guessed/current-host version | `FAIL_APPLE_BASELINE_ADMISSION` | No Apple operation starts without the external owner artifact. |
| `HONESTY` | Change a residual from `NOT IMPLEMENTED`/`BLOCKED` to `DONE` without evidence | `FAIL_DESIGN_ONLY_STATUS` | Paper prose cannot become implementation or release evidence. |

The exact observed output from the scratch checker and its limitation are recorded in the task handoff; no output from this table is a runtime gate result.

Observed scratch-only output from the in-memory checker on 2026-09-02:

```text
RECLAIM: FAIL_RECLAIM_PATH_INCOMPLETE -- SCRATCH PASS
OWNER: FAIL_OWNER_BINDING_INCOMPLETE -- SCRATCH PASS
TRUST: FAIL_TRUST_SEAM_INCOMPLETE -- SCRATCH PASS
IDENTITY: FAIL_IDENTITY_AUTHORITY_CONFLICT -- SCRATCH PASS
BOOT: FAIL_BOOT_HANDOFF_INCOMPLETE -- SCRATCH PASS
SECRETS: FAIL_SECRET_EXPOSURE_MATRIX_INCOMPLETE -- SCRATCH PASS
FIXTURES: FAIL_FIXTURE_RECORD_SHAPE -- SCRATCH PASS
HANDOFFS: FAIL_HANDOFF_RECORD_SHAPE -- SCRATCH PASS
BASELINE: FAIL_APPLE_BASELINE_ADMISSION -- SCRATCH PASS
HONESTY: FAIL_DESIGN_ONLY_STATUS -- SCRATCH PASS
```

The scratch checker used in-memory text mutation only, did not write a file, and did not provide implementation or qualification evidence.

## 14. Authoritative dependency handoffs

The following table compares the requested handoff set with the authority ledger at PROGRAM commit `58302d148f0e8b855578f9aa518ff1c5eb48c515`. Every row includes the exact PROGRAM dependency set, producer, consumer, artifact/type/digest, freshness, scope/context, rejection behavior, residual owner, and due-before gate. An absent, stale, mismatched, or unresolved handoff blocks the consumer; no row is silently deferred. Values about the producer boundary are limited to the immutable metadata and ID set named in PROGRAM; no source boundary is inspected here.

| ID | PROGRAM dependency set | Exact producer | Consumer | Artifact/type/digest | Freshness | Scope/context | Rejection behavior | Residual owner | Due-before gate |
|---|---|---|---|---|---|---|---|---|---|
| F-02 | F-01 | F-01 | F-02 | type=Canonical program decision and schema vocabulary digest; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at F-02 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-01; consumer=F-02; context=F-02 foundation gate; no cross-scope or local-alias reuse | `ERR_F02_PROGRAM_INPUT_MISSING` at `$.schema_set_digest`; block F-02 | F-02 owner | F-02 foundation gate |
| F-03 | F-02 | F-02 | F-03 | type=Canonical schemas, vectors, and schema-set digest; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at F-03 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-02; consumer=F-03; context=F-03 trust-root gate; no cross-scope or local-alias reuse | `ERR_F03_SCHEMA_SET_STALE` at `$.trust.schema_set_digest`; block F-03 | F-03 owner and project owner | F-03 trust-root gate |
| F-04 | F-02 | F-02 | F-04 | type=Canonical schemas and component field paths; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at F-04 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-02; consumer=F-04; context=F-04 builder gate; no cross-scope or local-alias reuse | `ERR_F04_SCHEMA_BINDING_MISSING` at `$.builder.schema_set_digest`; block F-04 | F-04 owner | F-04 builder gate |
| F-05 | F-03, F-04, F-06, Q-00, Q-01 | F-03, F-04, F-06, Q-00, Q-01 | F-05 | type=Trust policy, reproducible artifacts, compliance attestation, intake dataset, qualification schema; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at F-05 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-03, F-04, F-06, Q-00, Q-01; consumer=F-05; context=Candidate assembly gate; no cross-scope or local-alias reuse | `ERR_F05_CANDIDATE_INPUT_MISSING` at `$.candidate.inputs`; block candidate assembly | F-05 owner | Candidate assembly gate |
| F-06 | F-01 | F-01 | F-06 | type=Program license, notice, source-offer, and redistribution decisions; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at F-06 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-01; consumer=F-06; context=Release-compliance gate; no cross-scope or local-alias reuse | `ERR_F06_POLICY_UNRESOLVED` at `$.compliance.policy`; block candidate assembly | F-06 owner and project owner | Release-compliance gate |
| F-07 | F-05, P-03, P-05, I-09, B-04, Q-04, Q-05, Q-06, Q-07, Q-08 | F-05, P-03, P-05, I-09, B-04, Q-04, Q-05, Q-06, Q-07, Q-08 | F-07 | type=Candidate digest, parity census, update UX, installer acceptance, boot implementation, and all physical records; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at F-07 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-05, P-03, P-05, I-09, B-04, Q-04, Q-05, Q-06, Q-07, Q-08; consumer=F-07; context=Sole stable-promotion gate; no cross-scope or local-alias reuse | `ERR_F07_REQUIRED_SLICE_MISSING` at `$.required_closure`; no promotion | coordinator | Sole stable-promotion gate |
| P-04 | F-02 | F-02 | P-04 | type=Generated trusted bindings and redaction policy; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at P-04 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-02; consumer=P-04; context=Diagnostics/support implementation gate; no cross-scope or local-alias reuse | `ERR_P04_BINDING_MISSING` at `$.diagnostics.schema_set_digest`; block P-04 | P-04 owner | Diagnostics/support implementation gate |
| P-06 | P-02 | P-02 | P-06 | type=Typed capability outcomes and clean-path dependency graph; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at P-06 admission and immediately before the gate | project=omarchy-silicon; producer-set=P-02; consumer=P-06; context=Clean-path implementation gate; no cross-scope or local-alias reuse | `ERR_P06_LEGACY_PATH_UNPROVEN` at `$.clean_install.dependency_graph`; block P-06 | P-06 owner | Clean-path implementation gate |
| P-07 | P-05, P-06 | P-05, P-06 | P-07 | type=Atomic update UX and legacy path retirement or separately journaled migration proof; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at P-07 admission and immediately before the gate | project=omarchy-silicon; producer-set=P-05, P-06; consumer=P-07; context=Legacy migration gate; no cross-scope or local-alias reuse | `ERR_P07_MIGRATION_CONTRACT_MISSING` at `$.migration.recovery_root`; block P-07 and F-07 | P-07 owner | Legacy migration gate |
| I-01 | F-01 | F-01 | I-01 | type=Program safety boundary, state/event graph, and owner rules; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-01 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-01; consumer=I-01; context=Transaction design gate; no cross-scope or local-alias reuse | `ERR_I01_DESIGN_CONTRACT_MISSING` at `$.transaction.state_graph`; block I-01 | I-01 owner and coordinator | Transaction design gate |
| I-02 | I-01, F-03, F-06 | I-01, F-03, F-06 | I-02 | type=Closed transaction design, trust root, compliance bundle; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-02 admission and immediately before the gate | project=omarchy-silicon; producer-set=I-01, F-03, F-06; consumer=I-02; context=Signed app and pre-consent acquisition gate; no cross-scope or local-alias reuse | `ERR_I02_RELEASE_INPUT_MISSING` at `$.release.inputs`; block I-02 | I-02 owner | Signed app and pre-consent acquisition gate |
| I-03 | F-02, Q-00, I-01, I-07 | F-02, Q-00, I-01, I-07 | I-03 | type=Schema bindings, cited board intake, transaction contract, credential states; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-03 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-02, Q-00, I-01, I-07; consumer=I-03; context=Pure inventory and plan gate; no cross-scope or local-alias reuse | `ERR_I03_HANDOFF_MISMATCH` at `$.inventory.handoffs`; block I-03 | I-03 owner | Pure inventory and plan gate |
| I-04 | I-02, I-03, I-07 | I-02, I-03, I-07 | I-04 | type=Signed app, pure plan, credential state machine; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-04 admission and immediately before the gate | project=omarchy-silicon; producer-set=I-02, I-03, I-07; consumer=I-04; context=Apple provisioning and journal gate; no cross-scope or local-alias reuse | `ERR_I04_HANDOFF_MISMATCH` at `$.apple_transaction.handoffs`; block I-04 | I-04 owner | Apple provisioning and journal gate |
| I-05 | F-04, F-05, I-04 | F-04, F-05, I-04 | I-05 | type=Reproducible live artifact, assembled manifest, provisioned handoff; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-05 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-04, F-05, I-04; consumer=I-05; context=Linux live/install gate; no cross-scope or local-alias reuse | `ERR_I05_HANDOFF_MISMATCH` at `$.live_install.handoffs`; block I-05 | I-05 owner | Linux live/install gate |
| I-06 | I-04, I-05 | I-04, I-05 | I-06 | type=Journaled Apple state, exact Linux ownership and rollback state; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-06 admission and immediately before the gate | project=omarchy-silicon; producer-set=I-04, I-05; consumer=I-06; context=Uninstall/recovery gate; no cross-scope or local-alias reuse | `ERR_I06_HANDOFF_MISMATCH` at `$.recovery.handoffs`; block I-06 | I-06 owner | Uninstall/recovery gate |
| I-07 | I-01 | I-01 | I-07 | type=Credential-state contract and secret-route policy; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-07 admission and immediately before the gate | project=omarchy-silicon; producer-set=I-01; consumer=I-07; context=Credential implementation gate; no cross-scope or local-alias reuse | `ERR_I07_SECRET_BOUNDARY_MISSING` at `$.credentials.states`; block I-07 | I-07 owner and security reviewer | Credential implementation gate |
| I-08 | I-01, I-07, P-04 | I-01, I-07, P-04 | I-08 | type=State graph, credential UX, diagnostics and redaction contract; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-08 admission and immediately before the gate | project=omarchy-silicon; producer-set=I-01, I-07, P-04; consumer=I-08; context=UX/accessibility/privacy gate; no cross-scope or local-alias reuse | `ERR_I08_UX_HANDOFF_MISSING` at `$.ux.parity`; block I-08 | I-08 and P-04 owners | UX/accessibility/privacy gate |
| I-09 | Q-00, I-02, I-03, I-04, I-05, I-06, I-07, I-08, P-06, P-07 | Q-00, I-02, I-03, I-04, I-05, I-06, I-07, I-08, P-06, P-07 | I-09 | type=All acceptance artifacts, clean-path proof, and disposable hardware evidence; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at I-09 admission and immediately before the gate | project=omarchy-silicon; producer-set=Q-00, I-02, I-03, I-04, I-05, I-06, I-07, I-08, P-06, P-07; consumer=I-09; context=Installer acceptance gate; no cross-scope or local-alias reuse | `ERR_I09_REQUIRED_EVIDENCE_MISSING` at `$.acceptance.required`; block I-09 and F-07 | coordinator and qualification owner | Installer acceptance gate |
| B-04 | B-03 | B-03 | B-04 | type=U-Boot versioned slot, success, and fallback contract; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at B-04 admission and immediately before the gate | project=omarchy-silicon; producer-set=B-03; consumer=B-04; context=Boot implementation gate; no cross-scope or local-alias reuse | `ERR_B04_BOOT_CONTRACT_MISSING` at `$.boot.contract`; block B-04 and dependent Q gates | B-04 owner | Boot implementation gate |
| Q-00 | F-02 | F-02 | Q-00 | type=Canonical board-registry schema and cited intake source bundle; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-00 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-02; consumer=Q-00; context=Board admission gate; no cross-scope or local-alias reuse | `ERR_Q00_INTAKE_DIGEST_MISSING` at `$.intake.source_bundle`; block admission and dependents | Q-00 owner | Board admission gate |
| Q-01 | F-02, Q-00 | F-02, Q-00 | Q-01 | type=Board inventory, capability criteria, and intake dataset; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-01 admission and immediately before the gate | project=omarchy-silicon; producer-set=F-02, Q-00; consumer=Q-01; context=Qualification-schema gate; no cross-scope or local-alias reuse | `ERR_Q01_CRITERIA_MISSING` at `$.qualification.criteria`; block Q-01 | Q-01 owner | Qualification-schema gate |
| Q-02 | Q-01 | Q-01 | Q-02 | type=Qualification schema and redaction rules; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-02 admission and immediately before the gate | project=omarchy-silicon; producer-set=Q-01; consumer=Q-02; context=Evidence-ingestion gate; no cross-scope or local-alias reuse | `ERR_Q02_INGESTION_CONTRACT_MISSING` at `$.evidence.schema_digest`; block Q-02 | Q-02 owner | Evidence-ingestion gate |
| Q-03 | Q-00, Q-01 | Q-00, Q-01 | Q-03 | type=Exact board/profile inventory and qualification criteria; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-03 admission and immediately before the gate | project=omarchy-silicon; producer-set=Q-00, Q-01; consumer=Q-03; context=Hardware acquisition gate; no cross-scope or local-alias reuse | `ERR_Q03_FLEET_INPUT_MISSING` at `$.fleet.profile_set`; block physical acquisition | hardware lab owner | Hardware acquisition gate |
| Q-04 | B-02, B-04, K-02, G-02, I-09, Q-02, Q-03 | B-02, B-04, K-02, G-02, I-09, Q-02, Q-03 | Q-04 | type=M1/M2 opaque boot bundle handoff, boot implementation, kernel/Mesa tuples, installer acceptance, evidence tooling, fleet; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-04 admission and immediately before the gate | project=omarchy-silicon; producer-set=B-02, B-04, K-02, G-02, I-09, Q-02, Q-03; consumer=Q-04; context=M1/M2 physical qualification gate; no cross-scope or local-alias reuse | `ERR_Q04_REFERENCE_INPUT_MISSING` at `$.qualification.m1_m2`; block Q-04 and F-07 | hardware lab owner and coordinator | M1/M2 physical qualification gate |
| Q-05 | B-04, B-05, K-03, G-03, I-09, Q-02, Q-03 | B-04, B-05, K-03, G-03, I-09, Q-02, Q-03 | Q-05 | type=M3 boot bundle, boot implementation, kernel/Mesa tuple, installer evidence, lab evidence, fleet; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-05 admission and immediately before the gate | project=omarchy-silicon; producer-set=B-04, B-05, K-03, G-03, I-09, Q-02, Q-03; consumer=Q-05; context=M3 physical qualification gate; no cross-scope or local-alias reuse | `ERR_Q05_M3_INPUT_MISSING` at `$.qualification.m3`; block Q-05 and F-07 | hardware lab owner and coordinator | M3 physical qualification gate |
| Q-06 | B-04, B-06, K-04, G-04, I-09, Q-02, Q-03 | B-04, B-06, K-04, G-04, I-09, Q-02, Q-03 | Q-06 | type=M4 boot bundle, boot implementation, kernel/Mesa tuple, installer evidence, lab evidence, fleet; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-06 admission and immediately before the gate | project=omarchy-silicon; producer-set=B-04, B-06, K-04, G-04, I-09, Q-02, Q-03; consumer=Q-06; context=M4 physical qualification gate; no cross-scope or local-alias reuse | `ERR_Q06_M4_INPUT_MISSING` at `$.qualification.m4`; block Q-06 and F-07 | hardware lab owner and coordinator | M4 physical qualification gate |
| Q-07 | B-04, B-07, K-05, G-05, I-09, Q-02, Q-03 | B-04, B-07, K-05, G-05, I-09, Q-02, Q-03 | Q-07 | type=A18/M5 boot bundle, boot implementation, kernel/Mesa tuple, installer evidence, lab evidence, fleet; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-07 admission and immediately before the gate | project=omarchy-silicon; producer-set=B-04, B-07, K-05, G-05, I-09, Q-02, Q-03; consumer=Q-07; context=A18/M5 physical qualification gate; no cross-scope or local-alias reuse | `ERR_Q07_A18_M5_INPUT_MISSING` at `$.qualification.a18_m5`; block Q-07 and F-07 | hardware lab owner and coordinator | A18/M5 physical qualification gate |
| Q-08 | B-04, B-08, K-06, G-05, I-09, Q-02, Q-03 | B-04, B-08, K-06, G-05, I-09, Q-02, Q-03 | Q-08 | type=M6 boot bundle, shipping hardware, kernel/Mesa tuple, installer evidence, lab evidence, fleet; digest=required exact immutable producer digest; digest value not supplied in this design | immutable at authority SHA; verify digest, issuance, and expiry at Q-08 admission and immediately before the gate | project=omarchy-silicon; producer-set=B-04, B-08, K-06, G-05, I-09, Q-02, Q-03; consumer=Q-08; context=M6 physical qualification gate; no cross-scope or local-alias reuse | `ERR_Q08_M6_INPUT_MISSING` at `$.qualification.m6`; block Q-08 and F-07 | hardware lab owner and coordinator | M6 physical qualification gate |

This table follows the PROGRAM ledger rather than inventing a shortcut. In particular, I-09 consumes the acceptance dependencies shown above; F-07 consumes I-09, B-04, P-03, P-05, and Q-04 through Q-08; and no installer design document makes any of those slices DONE. The external human-produced boot-bundle handoffs remain opaque, signed, and blocking until received through the platform boundary.

## 15. Residual owner checkpoints and fail-closed defaults

Every material deferral has a named owner, immutable decision or input, fail-closed default, due-before gate, and blocking effect. The following checkpoints are unresolved and deliberately block implementation or promotion.

| Residual | Named owner | Immutable decision or input required | Fail-closed default | Due before | Blocking effect |
|---|---|---|---|---|---|
| Trust roots, roles, thresholds, expiry, revocation, and offline recovery | F-03 owner and project owner | F-03 trust bundle and `Trusted<TrustContext>` with closed `AuthorityRoleBinding` | Reject every envelope and approval | I-02 and F-05 | No trusted input or destructive authority. |
| Canonical schemas and generated bindings | F-02 owner | Authoritative F-02 artifact, executable schema set, vectors, bindings, and drift check; supplied provisional snapshot is not enough | Reject raw or shadow fields and return `BLOCKED_F02_AUTHORITY_UNRESOLVED` | I-02, I-03, and F-05 | No consumer can accept a payload. |
| F-02 stable identity authority | F-02 owner and installer owner | Authoritative ruling for the four hashed identity kinds and their exact preimages; no local alternate | `BLOCKED_F02_IDENTITY_AUTHORITY_UNRESOLVED` | I-03 and I-06 | No target selection, uninstall, or ownership claim. |
| Apple tool, OS, RecoveryOS, API, and command versions | Apple adapter owner and project owner | Owner-approved immutable external `APPLE_BASELINE_LOCK`, `APPLE_COMMAND_LOCK`, and authorization policy lock, with bytes and digests | `BLOCKED_APPLE_BASELINE_UNRESOLVED` | I-02 and I-04 | No Apple operation or claim of baseline support. |
| Apple authorization lifecycle and LocalPolicy semantics | Apple adapter owner and machine-owner authority | Owner-approved API and read-back matrix per locked baseline | Reject unknown owner or target policy | I-04 | No provisioning or boot-policy mutation. |
| APFS/RecoveryOS supported operation details | Apple adapter owner | Exact lock arrays, output schemas, and crash classifiers | No independent APFS writer; recovery on uncertainty | I-04 and I-06 | No storage or RecoveryOS mutation. |
| Opaque human-produced boot artifact contract | Qualified human artifact owner and project owner | Human-signed envelope with identity, digest, interface, provenance, license, redistribution decision, `source_generation` handoff metadata, and observable handoff | Treat input as absent; do not inspect the source boundary; no `Trusted<BootContext>` without verified atomic record | I-05, B-02, B-05 through B-08, Q-04 through Q-08 | No boot tuple, installer completion, or qualification. |
| Board intake and selector evidence | Q-00 owner | Cited immutable dataset, contradictions, source bundle, and digest | Board is UNKNOWN and fails closed | I-03 and Q-01 | No board admission. |
| Apple firmware cache and redistribution policy | Project owner and release-compliance owner | Per-artifact source, signature, notice, retention, and redistribution ruling | Direct fetch only; no redistribution or cache promotion | I-02 and F-06 | No release artifact service or candidate. |
| Stable-ID fields on every Apple baseline | Apple adapter owner and Q-01 owner | Board-specific identity tuple and re-observation fixtures | Reject missing field; no device-number fallback | I-03 and I-06 | No target selection or uninstall. |
| Linux layout and boot-slot policy | Platform, boot, and installer owners | `platform-manifest/v1` layout and `components.boot_stack` policy | No formatting or slot switch | I-05 and B-04 | No Linux mutation. |
| Credential and secure-pipe implementation | I-07 owner and security reviewer | Native helper design, locked-memory/swap/crash proof, sole-pipe proof, redaction policy, and complete exposure fixture matrix | Reject all secret routes except the sole bounded pipe | I-07 and I-09 | No encrypted install. |
| UX, localization, privacy, and support retention | I-08, P-04, and project owner | Native GUI/CLI parity, string catalog, consent text, redaction and retention policy | Telemetry off; no release UX claim | I-08 and I-09 | No user-facing release. |
| Disposable hardware and DFU runbooks | Hardware lab owner and project owner | Two-unit fleet, recovery certificates, calibrated fixtures, and rehearsed Apple runbooks | No destructive physical test; DFU is human escalation | Q-03 through Q-08 and I-09 | No physical qualification or F-07 promotion. |
| Independent review and coordinator acceptance | Coordinator and independent reviewer | Clean detached review, hostile probes, report artifacts, and coordinator ruling | REJECT on any missing or failed prerequisite | I-09 and F-07 | No slice DONE or stable promotion. |

The design intentionally invents none of these owner decisions. A later decision must arrive as an immutable input with an issuing owner, digest, scope, expiry, and due-before gate. Until then, the named fail-closed default remains in force.

## 16. Explicit design fail census

This correction specifies the ten coordinator correction seams as a paper contract, but it does not close any executable gate. The current census separates document coverage from delivery evidence; the provisional F-02 snapshot remains rejected and unresolved.

| Census item | Status | Evidence or blocking reason |
|---|---|---|
| Closed states, events, transitions, generation, lineage, replay, and restart rules | DESIGN-COVERAGE PASS; DELIVERY NOT IMPLEMENTED | Sections 8 and 9 specify 46 normal rows plus hold/fault coverage; no executable state machine exists. |
| Separate owner approval and fresh-snapshot destructive proof | DESIGN-COVERAGE PASS; DELIVERY NOT IMPLEMENTED | Sections 3.3 and 10 specify exact owner fields and the typed seam; no verifier exists. |
| Complete offline input closure and network-denied mutation | DESIGN-COVERAGE PASS; DELIVERY NOT IMPLEMENTED | Section 4 specifies closure and network denial; no closure validator exists. |
| Stable identities and exact-ownership uninstall | DESIGN-COVERAGE PASS or BLOCKED on F-02 authority; DELIVERY NOT IMPLEMENTED | Section 5 specifies the four provisional hashed kinds and blocks on unresolved F-02; no adapter or destructive test exists. |
| Credential separation and sole Linux secret route | DESIGN-COVERAGE PASS; DELIVERY NOT IMPLEMENTED | Section 6 specifies swap, crash, log, telemetry, redaction, cancellation, and recovery exposure cases; no native helper or leak report exists. |
| Eight-payload trust, ExpectedContext, preimage, admission, negotiation, and DTB seams | DESIGN-COVERAGE PASS or BLOCKED on authoritative F-02; DELIVERY NOT IMPLEMENTED | Section 3 consumes the supplied vocabulary without calling it settled; F-02/F-03 artifacts do not exist. |
| Apple adapter and immutable baseline locks | BLOCKED_APPLE_BASELINE_UNRESOLVED | Owner-approved external lock bytes, version rulings, command arrays, output schemas, and physical read-back evidence are absent. |
| Journal, replica, crash, slot, health, fallback, reclaim, and uninstall safety | DESIGN-COVERAGE PASS; DELIVERY NOT IMPLEMENTED | Sections 8 through 11 define the behavior, including T30/T45/T46; no journal, boot implementation, reclaim adapter, or fault harness exists. |
| Native UX, accessibility, localization, privacy, and support export | DESIGN-COVERAGE PASS; DELIVERY NOT IMPLEMENTED | Section 12 defines the release contract; no GUI, CLI parity, string catalog, or support exporter exists. |
| Executable fixtures, property tests, CI, reports, and independent review | FAIL/BLOCKED for delivery | Section 13 defines 122 rows and scratch probes, but all required deliverables and observed runtime results are absent. |
| PROGRAM dependency handoffs | DESIGN-COVERAGE PASS; BLOCKED for delivery | Section 14 maps 28 rows to the exact authority-ledger sets; every implementation and qualification slice remains TODO or HUMAN-ONLY BLOCKED in PROGRAM. |
| Residual ownership and design-only honesty | PASS as document coverage; PROGRAM remains REJECTED | Section 15 names unresolved owners/defaults; no I-01 through I-09 slice is DONE and no support or release claim is made. |

Final verdict: DESIGN CORRECTION SPECIFIED AS A PAPER CONTRACT; IMPLEMENTATION, VERIFICATION, QUALIFICATION, SUPPORT, RELEASE PROMOTION, AND DONE STATUS: FAIL/BLOCKED. The coordinator must not mark I-01 through I-09 or this design DONE from this document. The only honest next state is owner ruling, implementation, QA, independent review, physical qualification, and coordinator-controlled promotion through the PROGRAM gates.
