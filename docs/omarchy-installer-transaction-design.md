# Omarchy Silicon native installer transaction design

Status: CORRECTED DESIGN ONLY. The transaction runner, schemas, generated bindings, validator, signed inputs, CI, QA, physical qualification, support claim, release, merge eligibility, and DONE status are all NOT IMPLEMENTED.

This is the sole design artifact for the installer transaction slice. It owns no implementation, schema file, fixture file, workflow, test, CODEOWNERS entry, program edit, or external approval. It defines future contracts and the evidence required before any implementation or promotion can be admitted.

Design branch: `factory/design-installer-transaction`

Program authority: the external `omarchy-apple-platform/PROGRAM.md` ledger at `58302d148f0e8b855578f9aa518ff1c5eb48c515`. The ledger is read-only input and does not make this slice implemented, qualified, supported, promoted, or DONE.

F-02 comparison input: frozen rejected/provisional `platform-schema` design at `c315c7e79928d0041deb582bed79a61074361b21`. It is used only to state the future import seam. It is not canonical, ratified, approved, implemented, or release authority. No installer-local copy, alias, fallback, or shadow authority is permitted. Until an owner-ratified F-02 artifact and its generated locks arrive, every F-02-dependent consumer returns `HANDOFF_INPUT_MISSING` with hold result before mutation.

The human-produced boot-artifact boundary is opaque. This document uses only future signed envelopes and observable handoff records at that boundary and makes no source-level claim about it.

## 1. Ownership and honesty

The installer owns the macOS entry point, read-only observation, plan construction, owner confirmation, Apple-supported adapter boundary, durable transaction journal, live handoff, target setup, update, rollback, exact-ownership uninstall, recovery UX, accessibility, localization, privacy, and support export. These are ownership statements, not completion evidence.

The platform program owns schemas, trust, board registry, manifest, component locks, candidate assembly, qualification, release compliance, and stable promotion. The installer consumes only admitted typed values and cannot select a board, component tuple, signing role, or support level independently.

Apple authorization, storage, Recovery, boot policy, and firmware operations remain external owner-approved boundaries. The installer does not implement an independent storage writer, manufacture owner authority, collect Apple credentials, or infer a successful boot from a process exit code.

The state words in this document are exact protocol values. `DESIGN_MODEL` means a disposable text/model check only. `NOT_IMPLEMENTED` means no corresponding implementation or runtime observation exists. `TOOLING_BLOCK` means a required tool or external artifact is absent and therefore has not passed. Neither status is runtime PASS.

## 2. Closed vocabulary, limits, and precedence

### 2.1 Wire and identifier grammar

All future records use UTF-8 JSON, JSON Schema Draft 2020-12, and RFC 8785 JCS. Duplicate JSON member names are rejected before schema validation. The parser rejects invalid UTF-8, BOM, unpaired surrogates, control characters, NaN, Infinity, negative zero, non-canonical numbers, excessive depth, and over-limit input. It never coerces, truncates, sorts, deduplicates, or repairs input.

| Type | Closed rule |
| --- | --- |
| `DocumentId` | lowercase ASCII `^[a-z0-9][a-z0-9._:-]{0,127}$`; one immutable document lineage only |
| `ProjectId` | `project:` plus one lowercase token, maximum 128 bytes |
| `RepositoryId` | `repo:` plus one lowercase token, maximum 128 bytes |
| `SliceId` | `slice:` plus one lowercase token, maximum 128 bytes |
| `ArtifactId` | `artifact:` plus one lowercase token, maximum 128 bytes |
| `PolicyId` | `policy:` plus one lowercase token, maximum 128 bytes |
| `ActorId` | `actor:` plus one lowercase token, maximum 128 bytes |
| `AccountId` | `acct:` plus one lowercase token, maximum 128 bytes |
| `BoardId` | `apple:` plus lowercase `[a-z0-9][a-z0-9-]{0,63}`; never SoC-only |
| `SocId` | `apple-soc:` plus lowercase `[a-z0-9][a-z0-9-]{0,63}`; diagnostic only |
| `UUID` | lowercase RFC 4122 textual UUID with hyphens |
| `Digest` | `sha256:` plus exactly 64 lowercase hexadecimal characters |
| `Version` | three unsigned decimal components `major.minor.patch`, each 0 through 65,535 |
| `Timestamp` | RFC 3339 UTC ending in `Z`, millisecond precision at most, year 1970 through 9999 |
| `PathToken` | 1 through 256 ASCII bytes; no slash, backslash, `..`, NUL, control, URL delimiter, or environment expansion |
| `JsonPath` | `$` or `$` followed by lower-token members and decimal indexes, maximum 512 ASCII bytes |
| `StableId` | one exact typed prefix plus 64 lowercase hex bytes; not a path, digest alias, or caller token |
| `Nonce` | unpadded base64url decoding to 16 through 32 bytes |
| `SlotId` | exactly `slot-a`, `slot-b`, or `recovery` |
| `Operation` | exactly `inspect/v1`, `write/v1`, `replace/v1`, `remove/v1`, or `rollback/v1` |
| `Result` | exactly `allow`, `reject`, `hold`, `no-op`, `state-unchanged`, `abort-requested`, `recovery-required`, or `terminal` |

Global limits are maximum input 1,048,576 bytes, depth 32, 128 object properties per object, 1,024 array members, 4,096 UTF-8 bytes per string, 262,144 total string bytes, and signed integer magnitude 9,223,372,036,854,775,807 unless a narrower field rule applies. Installer transaction generation, attempt counter, source generation, record sequence, object generation, and boot slot generation use unsigned 64-bit integers from 0 through exactly 18,446,744,073,709,551,615. No counter wraps, resets, or truncates.

The complete boot-success envelope has an inclusive maximum of 4,096 bytes; exactly 4,096 is valid and 4,097 is `RESOURCE_LIMIT`. Boot core and marker payloads are each at most 3,072 bytes. Boot depth is 8, boot object properties are 32, and boot arrays are 32. These are imported constraints, not locally widened values.

### 2.2 Validation phases and total earliest-failure precedence

The validator collects all admissible failures before selecting the result. Input order is never a tie-breaker. It selects the lowest `(phase_rank, condition_rank, canonical_json_path)` tuple from this registry; the selected code, path, phase, and result are therefore deterministic for reordered simultaneous faults.

| Phase | Rank | Closed work | Result family |
| --- | ---: | --- | --- |
| `P0 transport` | 0 | bytes, UTF-8, BOM, duplicate member names, truncation, complete framing | reject |
| `P1 shape` | 1 | required/unknown members, enums, array order, scalar/count/depth bounds | reject |
| `P2 canonical` | 2 | JCS bytes, numeric spelling, digest cycles, recomputation | reject |
| `P3 authority` | 3 | signature context, role, key, freshness, expiry, replay, document identity | reject |
| `P4 local` | 4 | stable identity, provenance, source/transaction/attempt counters, topology | reject or hold per code |
| `P5 relation` | 5 | cross-document, exact scope, manifest, handoff, boot, artifact, policy relation | reject or hold per code |
| `P6 execution` | 6 | trusted nominal type, durable prerequisite, operation guard, rollback, recovery | reject or hold per code |

The closed code registry is normative. Every referenced code appears exactly once here; a future schema generator must reject an unregistered code, a duplicate row, a second phase, a second path family, or a decision not matching this row.

| Code | Phase | Canonical path family | Result | Decision |
| --- | --- | --- | --- | --- |
| `ACCEPT` | P6 | `$` | allow | allow |
| `PARSE_SCHEMA_FAILURE` | P0/P1 | first malformed or missing member | reject | reject |
| `UNKNOWN_FIELD` | P1 | second or unknown member | reject | reject |
| `DUPLICATE_SEMANTIC_KEY` | P0/P1 | second JSON name or collection key | reject | reject |
| `CANONICALIZATION_FAILURE` | P2 | `$` or first non-canonical scalar | reject | reject |
| `SIGNATURE_CONTEXT_MISMATCH` | P3 | envelope type/domain/context/role | reject | reject |
| `TRUST_FAILURE` | P3 | key, role, authority, or proof field | reject | reject |
| `TRUST_BOUNDARY_FAILURE` | P6 | unsealed local source or caller-created nominal value | hold | hold |
| `EXPIRY_OR_REPLAY_FAILURE` | P3 | expiry, nonce, replay, or reservation | reject | reject |
| `FRESHNESS_FAILURE` | P3 | stale clock, lock, record, or source | reject | reject |
| `CROSS_DOCUMENT_MISMATCH` | P5 | first unequal bound field | reject | reject |
| `IDENTITY_INCOMPLETE` | P4 | missing typed identity or capacity field | reject | reject |
| `AMBIGUOUS_IDENTITY` | P4 | second stable ID, tuple, parent, or provenance | reject | reject |
| `PLAN_SCOPE_OR_APPROVAL_FAILURE` | P6 | first plan, actor, account, or scope field | reject | reject |
| `DOCUMENT_ID_REUSE` | P3/P5 | document ID with different payload or lineage | reject | reject |
| `DOCUMENT_ID_FORK` | P5 | document lineage child/current record | reject | reject |
| `PLAN_DIGEST_CYCLE` | P2 | forbidden plan self-reference | reject | reject |
| `MANIFEST_AUTHORITY_CONFLICT` | P5 | first projection differing from component source | reject | reject |
| `BINDING_INTEGRITY_FAILURE` | P1/P5/P6 | schema/generated lock, parser, API, or artifact | reject | reject |
| `UNKNOWN_MUTATION` | P5 | unlisted or unauthorized mutation | reject | reject |
| `DTB_INPUT_VERIFICATION_FAILURE` | P4/P5 | DTB source, policy, artifact, or preimage | reject | reject |
| `BOOT_CONTEXT_MISMATCH` | P5 | core, marker, lineage, slot, or context | hold | hold |
| `BOOT_COUNTER_FAILURE` | P4/P6 | counter, generation, atomic record, or wrap | hold | hold |
| `BOOT_REQUIRED_CHECK_FAILURE` | P5 | required check, measurement, or profile | hold | hold |
| `BOOT_FALLBACK_FAILURE` | P5/P6 | rollback set or fallback target | hold | hold |
| `BOOT_MARKER_AUTH_FAILURE` | P3/P6 | marker signature, reservation, or marker context | hold | hold |
| `RESOURCE_LIMIT` | P0/P1 | first over-limit byte/count/depth/integer | reject | reject |
| `STATE_EVENT_NOT_ALLOWED` | P6 | closed state/event relation | state-unchanged | reject |
| `STATE_TERMINAL` | P6 | terminal state with a non-replay event | terminal | reject |
| `POWER_LOSS_RECOVERY_REQUIRED` | P6 | power-loss event record | recovery-required | hold |
| `PROCESS_DEATH_RECOVERY_REQUIRED` | P6 | process-death event record | recovery-required | hold |
| `CANCEL_AFTER_MUTATION` | P6 | cancellation after a mutation boundary | recovery-required | hold |
| `RETRY_EXHAUSTED_RECOVERY` | P6 | retry counter reaches policy maximum | recovery-required | hold |
| `PARTIAL_DELETE_HOLD` | P6 | deletion result is neither absent nor complete | recovery-required | hold |
| `RECLAIM_INTERRUPTED` | P6 | reclaim request/commit boundary interrupted | recovery-required | hold |
| `JOURNAL_DIVERGENCE` | P6 | replicas or hash chain disagree | recovery-required | hold |
| `DISK_FULL_PREBOUNDARY` | P6 | no room before mutation request commit | state-unchanged | reject |
| `DISK_FULL_POSTBOUNDARY` | P6 | no room after mutation request commit | recovery-required | hold |
| `REPLAY_DUPLICATE_NOOP` | P3/P6 | byte-identical committed replay | no-op | allow |
| `REPLAY_ID_MISMATCH` | P3/P5 | replay identity reused for another tuple | reject | reject |
| `GENERATION_OVERFLOW` | P4 | maximum generation or counter would wrap | recovery-required | hold |
| `HANDOFF_INPUT_MISSING` | P5 | absent or unadmitted handoff artifact | hold | hold |
| `BLOCKED_F02_AUTHORITY_UNRESOLVED` | P5 | missing owner-ratified F-02 schema/binding authority | hold | hold |
| `APPLE_LOCK_MISSING` | P5/P6 | absent, stale, unsigned, or unratified Apple lock | hold | hold |
| `DELIVERY_ARTIFACT_MISSING` | P6 | future acceptance artifact absent | hold | hold |
| `QUALIFICATION_EVIDENCE_MISSING` | P6 | signed QA or physical evidence absent | hold | hold |
| `SECRET_ROUTE_VIOLATION` | P1/P6 | credential in forbidden route or durable field | reject | reject |
| `NETWORK_AFTER_CONSENT` | P6 | network acquisition attempted after consent | recovery-required | hold |

All codes above have one result and one decision. `hold` is never rewritten as success, warning, or compatibility. An unknown phase, path family, result, state, event, code, enum, member, producer, or consumer is a `PARSE_SCHEMA_FAILURE` in a future validator.

## 3. Exact F-02 import seam without shadow authority

### 3.1 Admission rule

The installer may import an F-02 value only through owner-ratified generated bindings selected by both exact schema-input and generated-output locks. The import function accepts the external artifact bytes, the ratified `schema_set_digest`, a ratified `schema-input.lock`, a ratified `generated-output.lock`, the matching compiled consumer lock, `Trusted<TrustContext>`, and `VerifiedClock`. It returns a nominal `Trusted<T>` only after strict parse, JCS, signature, scope, freshness, replay, and cross-document checks. The design never assigns those future digest values.

Absent, locally copied, stale, rejected, unratified, version-mismatched, generated-drifted, aliased, or shadow authority produces `HANDOFF_INPUT_MISSING` or `BINDING_INTEGRITY_FAILURE` and holds before mutation. No installer-local alias may be passed to an `admit` function. A raw parsed map, a payload digest without bytes, a document ID without its payload, a binding with a matching schema-set but mismatched generated output, or a role string without a trusted `AuthorityRoleBinding` is rejected.

### 3.2 Typed external import matrix

The following matrix is a lock on names and seams only. The future values are external fields, not values invented by this design.

| Import | Exact external contract consumed | Required lock/evidence | Consumer seam and fail-closed result |
| --- | --- | --- | --- |
| `OwnerProofReceipt` | `receipt_schema`, `receipt_id`, project/repository/slice, operation, actor, target account, plan/scope, board, manifest, schema-set, policy, topology, target identity digests, authorization method/result, assertion/evidence digests, `SourceEvidence`, validity, nonce, replay, `receipt_digest` | F-02 schema input, generated binding, trusted owner source, signature, fresh clock, replay reservation | `verify_owner_proof(AuthenticatedOwnerProofSource)` -> `Trusted<OwnerProofReceipt>`; missing or transplanted proof -> `TRUST_FAILURE` |
| `TargetAccount` | `account_schema`, record ID, account, project/repository/slice, allowed operation list, complete target identity digest list, board, manifest, schema-set, policy, validity, nonce, replay, account binding, record digest | same exact F-02 locks plus account authority and replay evidence | `verify_target_account(AuthenticatedTargetAccountSource)` -> `Trusted<TargetAccount>`; missing or scope drift -> `PLAN_SCOPE_OR_APPROVAL_FAILURE` |
| `AuthorityRoleBinding` | binding schema, authority ID, closed role, actor/account, sorted key IDs, exact allowed methods, service policy ID/digest, issued/expiry, binding digest | F-03 trust context and F-02 generated type, no local role table | `resolve_authority(Trusted<TrustContext>, ExpectedContext)`; absent or wrong role -> `TRUST_FAILURE` |
| `SchemaInputLock` | exact eleven schema-input IDs, relative source paths, source/reference digests, vocabulary, JCS implementation, all limits, generator/parser/toolchain inputs | future ratified `schemas/schema-input.lock`; input lock has no output-lock field | `verify_schema_input_lock` -> `Trusted<SchemaInputLock>`; missing/extra/order drift -> `BINDING_INTEGRITY_FAILURE` |
| `GeneratedOutputLock` | schema-set digest, language, artifact ID, output path, binding/parser/API/toolchain identities, source schema IDs, output/file-order/memory-report digests, consumer API, output role | future ratified `bindings/generated-output.lock`; exact compiled lock | `load_consumer_capabilities` -> `ConsumerCapabilities`; generated drift -> `BINDING_INTEGRITY_FAILURE` |
| `OwnerApproval` | common signed envelope plus exact owner-approval fields: plan/scope, project/repository/slice, board/registry, manifest, schema-set, policy, actor/account/role, approval time, topology, target IDs/identities, ordered operations, method/result, proof/evidence, service policy, replay, proof receipt, target account record/binding | owner-approval envelope, proof receipt, target account, trust context, fresh clock | `verify_owner_authorization` -> `VerifiedOwnerAuthorizationContext`; any projection mismatch -> `PLAN_SCOPE_OR_APPROVAL_FAILURE` |
| `BootHealthCore` | board, manifest, profile, lineage, `source_generation`, slot/generation, attempt/counter, checks/digest, success, fallback | boot-health binding, exact `uint64`, `Trusted<BootContext>`, atomic boot record | `evaluate_boot_health` consumes only trusted nominal values; missing marker/check -> `BOOT_REQUIRED_CHECK_FAILURE` |
| `BootSuccessMark` | core digest, board/manifest/profile, lineage, source generation, slot/generation, attempt counter, marker generation, marked time, checks/rollback digests, marker replay identity, bounded diagnostic note | separate marker envelope, marker size bound, boot-runtime authority, replay reservation | `evaluate_boot_health` checks marker separately; forged/stale marker -> `BOOT_MARKER_AUTH_FAILURE` |
| `BootContext` | sealed context schema, board, manifest ID/digest, lineage, slot/generation, attempt counter, source generation, atomic record digest, lineage source digest, exact nested provenance | `Trusted<AtomicBootRecord>`, F-02 boot binding, verified clock | `verify_boot_context` is the only constructor; caller-created or partial context -> `TRUST_BOUNDARY_FAILURE` |
| `VerifiedDtbInputs` | manifest/board/policy/tool/artifact/firmware/DT-schema tuple, source generation, source/post bytes digests, source evidence, replay and recomputation digests | exact generated binding and ratified policy/tool/artifact lock | `verify_dtb_inputs` -> trusted inputs; unsealed or stale input -> `DTB_INPUT_VERIFICATION_FAILURE` |

The exact imported supporting grammars are:

```text
AuthorityRoleBinding = {
  binding_schema: "authority-role-binding/v1", authority_id: LowerAsciiToken,
  role: "board-admission" | "manifest-release" | "installer-planner" |
        "owner-authorization" | "ci-conformance" | "qualification-lab" |
        "boot-runtime" | "dtb-authority" | "evidence-reader",
  actor_id: ActorId, account_id: AccountId, key_ids: SortedList<KeyId>,
  allowed_methods: ExactList<AuthorizationMethod>, service_policy_id: PolicyId,
  service_policy_digest: Digest, issued_at: Timestamp, expires_at: Timestamp,
  binding_digest: Digest
}
OwnerProofReceipt = {
  receipt_schema: "owner-proof-receipt/v1", receipt_id: ProofReceiptId,
  project_id: ProjectId, repository_id: RepositoryId, slice_id: SliceId,
  operation: Operation, actor_id: ActorId, target_account_id: AccountId,
  plan_digest: Digest, scope_digest: Digest, board_id: BoardId,
  manifest_id: DocumentId, manifest_digest: Digest, schema_set_digest: Digest,
  policy_id: PolicyId, policy_digest: Digest, topology_digest: Digest,
  target_identity_digests: ExactList<Digest>, authorization_method: AuthorizationMethod,
  authorization_result: "success", assertion_digest: Digest, evidence_digest: Digest,
  source_identity: SourceEvidence, valid_from: Timestamp, expires_at: Timestamp,
  nonce: Nonce, replay_id: UUID, receipt_digest: Digest
}
TargetAccount = {
  account_schema: "target-account/v1", record_id: TargetAccountRecordId,
  account_id: AccountId, project_id: ProjectId, repository_id: RepositoryId,
  slice_id: SliceId, allowed_operations: ExactList<Operation>,
  target_identity_digests: ExactList<Digest>, board_id: BoardId,
  manifest_id: DocumentId, manifest_digest: Digest, schema_set_digest: Digest,
  policy_id: PolicyId, policy_digest: Digest, valid_from: Timestamp,
  expires_at: Timestamp, nonce: Nonce, replay_id: UUID,
  account_binding: Digest, record_digest: Digest
}
SchemaInputLock = {
  lock_schema: "schema-input-lock/v1", schema_set_id: "platform-schema-set/v1",
  schema_entries: ExactList<SchemaInputEntry>, vocabulary: VocabularyLock,
  canonicalization: CanonicalizationLock, limits: LimitLock,
  generator_inputs: ExactList<ToolInput>, parser_inputs: ExactList<ToolInput>,
  toolchain_inputs: ExactList<ToolInput>
}
GeneratedOutputLock = {
  lock_schema: "generated-output-lock/v1", schema_set_digest: Digest,
  generated_entries: SortedList<GeneratedEntry>
}
```

`SchemaInputEntry` contains exactly `schema_id`, `schema_version`, `source_path`, `source_digest`, and sorted `reference_digests`. `GeneratedEntry` contains exactly language, artifact ID, output path, binding identity, generator/parser/toolchain input IDs, source schema IDs, output digest, LF line ending, file-order digest, bounded-memory report digest, consumer API, and output role. `SchemaInputLock` has no output-lock field; `GeneratedOutputLock` points to the schema-set digest and never becomes an input to the schema-set digest. This is the only permitted lock direction.

The lock identities are computed exactly as `schema_set_digest = sha256(ASCII("omarchy-schema-set/v1") || 0x00 || JCS(SchemaInputLock))`, `generated_output_digest = sha256(ASCII("omarchy-generated-output/v1") || 0x00 || LF_normalized_output_bytes)`, and `compiled_lock_digest = sha256(ASCII("omarchy-compiled-binding-lock/v1") || 0x00 || JCS(CompiledLock without lock_digest))`. No lock self-digest, output-to-input back edge, local schema copy, or compatible-looking generated output is accepted.

The exact owner-approval payload is the common signed envelope plus `plan_digest`, `scope_digest`, `project_id`, `repository_id`, `slice_id`, `board_id`, `board_registry_digest`, `manifest_id`, `manifest_digest`, `schema_set_digest`, `policy_id`, `policy_digest`, `actor_id`, `account_id`, `actor_role`, `approved_at`, `topology_digest`, `target_ids`, `target_identities`, `operations`, `authorization_method`, `authorization_result`, `external_proof_digest`, `authorization_evidence_digest`, `service_policy_id`, `service_policy_digest`, `replay_id`, `proof_receipt_id`, `target_account_record_id`, and `target_account_binding`. Its role is exactly `owner`, its result is exactly `success`, and every field is a byte-equal projection of the trusted plan, proof, account, role binding, and verified clock.

### 3.3 Exact document, payload, scope, and replay distinctions

`document_id` is authority-selected identity for one immutable payload lineage. `payload_digest` is `sha256(JCS(payload))`; it is content identity and is never substituted for `document_id`. A document ID cannot be reused for a different payload digest, type, schema, domain, context, scope, generation, or lineage. A correction receives a new document ID, one predecessor, and a higher generation. The same payload digest under two IDs is rejected unless an external ratified lineage record explicitly authorizes the next correction.

The exact anti-transplant preimage is:

```text
A = {envelope_format, signature_format, key_id, signer_role, algorithm, domain, context,
     payload_type, payload_version, schema_set_digest, payload_digest,
     anti_transplant: {document_id, schema, payload_type, payload_version,
                        schema_set_digest, domain, context}, payload}
auth_preimage = ASCII("omarchy-auth-preimage/v1") || 0x00 || JCS(A)
```

The owner target-account binding preimage is:

```text
target_account_binding = sha256(ASCII("omarchy-owner-target-account/v1") || 0x00 ||
  JCS({project_id, repository_id, slice_id, operation, account_id, plan_digest,
       scope_digest, policy_digest, manifest_digest, topology_digest,
       target_identity_digests}))
```

Freshness requires `issued_at <= VerifiedClock.now < expires_at`, a bounded validity window, a matching source generation, a non-replayed nonce/replay ID, and a live external reservation. Scope equality compares the complete canonical project, repository, slice, board, target, operation, candidate, channel, manifest, policy, and schema-set tuple. Role, scope, freshness, and replay are separate checks; none is implied by the others.

## 4. Stable storage identity and boot lineage

### 4.1 Four imported stable-ID preimages

These four kinds and exact preimages are imported only after F-02 ratification. They are not locally renamed or augmented.

```text
I_disk = {identity_schema: "disk-identity/v1", object_kind: "whole_disk", source: SourceTuple,
          gpt_disk_guid: UUID, capacity_bytes: uint64_63,
          transport: "internal-pcie" | "external-usb" | "external-thunderbolt" |
                     "external-sata" | "virtual", model_token: ModelToken | null,
          serial_token: SerialToken | null, physical_location_token: PhysicalLocationToken | null}
I_partition = {identity_schema: "partition-identity/v1", object_kind: "gpt_partition", source: SourceTuple,
               parent_stable_id: DiskStableId, partition_guid: UUID, type_guid: UUID,
               first_lba: uint64_63, last_lba: uint64_63}
I_container = {identity_schema: "container-identity/v1", object_kind: "apfs_container", source: SourceTuple,
              parent_stable_id: DiskStableId | PartitionStableId, container_uuid: UUID,
              capacity_bytes: uint64_63, physical_extents: PhysicalExtentList}
I_volume = {identity_schema: "volume-identity/v1", object_kind: "apfs_volume", source: SourceTuple,
           parent_stable_id: ContainerStableId, volume_uuid: UUID,
           role: "system" | "data" | "preboot" | "recovery" | "vm" | "update" | "other",
           capacity_bytes: uint64_63}
stable_id(kind, I_kind) = kind_prefix(kind) || hex_lower(sha256(
  ASCII("omarchy-storage-identity/v2") || 0x00 || JCS({source: I_kind.source, identity: I_kind})))
identity_anchor_digest = sha256(ASCII("omarchy-storage-identity-anchor/v1") || 0x00 ||
  JCS({source: I_kind.source, identity: I_kind}))
```

`SourceTuple` is exactly `{source_kind, adapter_id, adapter_api_version, observation_digest, source_generation, logical_block_bytes, physical_block_bytes, source_identity_digest}`. `source_kind` is one of `macos-diskutil/v1`, `macos-iokit/v1`, or `linux-sysfs/v1`. `logical_block_bytes` and `physical_block_bytes` are exactly 512 or 4,096. `uint64_63` is 0 through 9,223,372,036,854,775,807. `CapacityPreimage` is `{logical_block_bytes, value_lba, value_bytes}` and `value_bytes` is the exact integral product. No rounding, inferred sector size, path, display name, serial-only match, or device token is an identity authority.

Topology provenance contains exactly source kind, adapter ID/API version, source field names, observation digest, source generation, block geometry, source identity digest, object generation, and identity anchor digest. `source_generation` starts at 0 before a committed snapshot, becomes 1 on the first committed snapshot, increments once per changed canonical topology, and never resets, reuses, or wraps. `object_generation` starts at 1, increments on identity or parent change, and never resumes after disappearance. A changed adapter, API, source field set, block geometry, parent, extent, UUID, role, size, path binding, or evidence digest produces a new preimage or an ambiguity rejection.

### 4.2 Boot attempt, source generation, and separate success

`transaction_generation`, `attempt_counter`, `source_generation`, `slot_generation`, and `marker_generation` are independent unsigned 64-bit fields. Zero has a declared meaning only where written: no committed source snapshot, no started attempt, or no marker. A successful attempt requires counter 1 through maximum. If any next value would exceed the inclusive maximum, the operation returns `GENERATION_OVERFLOW` or `BOOT_COUNTER_FAILURE`, preserves the prior committed record, and never wraps.

The exact durable boot record is `{record_schema, record_id, project_id, repository_id, slice_id, board_id, manifest_id, manifest_digest, lineage_id, slot_id, slot_generation, attempt_counter, source_generation, commit_state, bytes_digest, source, replay_id}` with `commit_state = committed` only after atomic replacement and both replica flushes. `BootContext` is `{context_schema, board_id, manifest_id, manifest_digest, lineage_id, slot_id, slot_generation, attempt_counter, source_generation, atomic_record_digest, lineage_source_digest, provenance}` where nested provenance is `{source_kind: "atomic-boot-journal/v1", source_api_version, storage_generation}`. Only `verify_boot_context(Trusted<AtomicBootRecord>, Trusted<TrustContext>, VerifiedClock)` constructs the sealed value.

The boot-health core contains no marker digest or marker payload. The separate success marker contains `core_digest` and its own document identity but no self-digest field. `D_core = sha256(ASCII("omarchy-boot-health-core/v1") || 0x00 || JCS(core))`. Success requires a verified core, matching sealed context, required checks, separate marker, marker replay reservation, exact rollback set, and the external boot authority. A core, marker, or success process cannot promote support or qualification.

## 5. Apple and external lock contracts

### 5.1 Immutable signed lock envelope

Every Apple or boot external lock is an owner-approved signed artifact with the closed fields `{lock_schema, artifact_id, document_id, record_id, issuer, owner_actor_id, project_id, repository_id, slice_id, board_id, target_id, operation, candidate_id, channel, version, command_argv, source_digest, content_digest, payload_digest, preimage_grammar, issued_at, expires_at, replay_id, supersedes_document_id, correction_reason, signature}`. `command_argv` is a closed ordered array, never a shell string. The actual artifact/document/record IDs and digests are external future inputs; this design assigns none.

The canonical preimage is `sha256(ASCII(lock_schema) || 0x00 || JCS(lock without signature and payload_digest))`, then `payload_digest = sha256(JCS(payload))`, then the external signature covers the complete anti-transplant envelope. `content_digest` covers exact immutable bytes and is distinct from `payload_digest`. `document_id` is distinct from both. A correction supersedes exactly one prior document and cannot silently rewrite it.

### 5.2 Required Apple lock set and admission

The future adapter requires all three records before any privileged call: `APPLE_BASELINE_LOCK` for OS/Recovery/tool/API versions and board scope, `APPLE_COMMAND_LOCK` for exact command arrays, output schemas, and read-back predicates, and `APPLE_AUTHORIZATION_LOCK` for owner-authority method, policy, expiry, replay, and correction rules. Each must be externally signed, ratified, scope-exact, fresh, non-replayed, and digest-consistent. A missing, unsigned, stale, expired, wrong-board, wrong-target, wrong-repository, wrong-slice, wrong-operation, version-mismatched, corrected-but-not-superseded, or locally fabricated lock returns `APPLE_LOCK_MISSING` before mutation.

No current-host observation, command that happens to work, version guess, local plist, environment variable, UI approval, or source path can promote a lock. `source_generation`, transaction generation, attempt counter, `D_core`, core/marker/BootContext provenance, and success-marker separation are imported and compared exactly. Stale clock causes `FRESHNESS_FAILURE`; rollback creates a new lineage and never promotes an old marker; no local record can become owner-approved by copying or signing it with the transaction process.

### 5.3 Destructive boundary ordering

For every destructive operation, the executor performs: fresh trusted observation; exact plan/lock/approval comparison; durable request record in both journal replicas; fsync and read-back; one external call; complete result classification; postcondition observation; durable commit record in both replicas; and final read-back. Network acquisition is forbidden after consent. A missing or changed postcondition never becomes a successful commit.

## 6. Total transaction state machine

### 6.1 Closed states

The exact states, in protocol order, are:

```text
NEW, INVENTORY_READY, PLAN_READY, APPROVAL_REQUESTED, APPROVED,
JOURNAL_REQUESTED, JOURNALED, RESIZE_REQUESTED, RESIZING, RESIZE_COMMITTED,
STUB_REQUESTED, STUB_CREATING, APPLE_STUB_READY, HANDOFF_REQUESTED,
OWNER_HANDOFF_PENDING, IN_1TR, LOCALPOLICY_REQUESTED, LOCALPOLICY_COMMITTED,
LOCALPOLICY_READY, LIVE_HANDOFF_REQUESTED,
LIVE_HANDOFF_PENDING, LIVE_RUNNING, LAYOUT_REQUESTED, LAYOUT_READY,
IMAGE_REQUESTED, IMAGE_STAGED, PENDING_BOOT, FIRST_BOOT_PENDING,
HEALTH_CHECKING, SUCCESS, UPDATE_PENDING, UNINSTALL_PENDING, ABORT_REQUESTED,
ABORTED, ROLLBACK_REQUIRED, ROLLED_BACK, RECOVERY_REQUIRED,
SPACE_RECLAIM_REQUESTED, UNINSTALLED, TERMINAL_REJECTED
```

`SUCCESS`, `ABORTED`, `UNINSTALLED`, and `TERMINAL_REJECTED` are terminal for their transaction generation. A successor update or reinstall receives a new transaction ID and generation; it is not a transition that mutates terminal history. Exact replays of a committed terminal event return `REPLAY_DUPLICATE_NOOP`; every other event returns `STATE_TERMINAL`.

### 6.2 Closed events

The exact event set is:

```text
INVENTORY_ACCEPTED, PLAN_BUILT, APPROVAL_REQUESTED, OWNER_APPROVED,
JOURNAL_REQUESTED, JOURNAL_DURABLE, RESIZE_REQUESTED, RESIZE_COMMITTED,
STUB_REQUESTED, STUB_COMMITTED, HANDOFF_REQUESTED, HANDOFF_COMMITTED,
IN_1TR_VERIFIED, LOCALPOLICY_REQUESTED, LOCALPOLICY_COMMITTED,
LIVE_HANDOFF_REQUESTED, LIVE_HANDOFF_COMMITTED, LAYOUT_REQUESTED,
LAYOUT_COMMITTED, IMAGE_REQUESTED, IMAGE_COMMITTED, PENDING_SLOT_COMMITTED,
BOOT_ATTEMPTED, HEALTH_STARTED, BOOT_SUCCEEDED, UPDATE_REQUESTED,
UNINSTALL_REQUESTED, ABORT_REQUESTED, ABORT_COMMITTED, ROLLBACK_REQUESTED,
ROLLBACK_COMMITTED, SPACE_RECLAIM_REQUESTED, SPACE_RECLAIM_COMMITTED,
RECOVERY_REQUESTED, RECOVERY_REPAIRED, POWER_LOSS, PROCESS_DEATH,
USER_CANCELLATION, RETRY_EXHAUSTED, PARTIAL_DELETE, RECLAIM_INTERRUPTED,
JOURNAL_DIVERGENCE, DUPLICATE_REPLAY, DISK_FULL_PRE_BOUNDARY,
DISK_FULL_POST_BOUNDARY, RESTART_RECOVERY, HOLD_REQUESTED
```

Every durable external mutation has a request event and a later commit event. There is no direct `*_COMMITTED` transition from a state that has not durably recorded the corresponding request. In particular, `ABORT_COMMITTED` is admissible only from `ABORT_REQUESTED`; planning and handoff states first receive `ABORT_REQUESTED`, then a durable `ABORT_COMMITTED`. A cancellation after a mutation boundary is not an abort and goes to recovery.

### 6.3 Exact valid transitions

The following rows are the only non-rejection transitions. `prior_state`, `event`, and `result_state` are exact and unique.

| ID | Prior state | Event | Result state | Durable prerequisite or result |
| --- | --- | --- | --- | --- |
| T01 | NEW | INVENTORY_ACCEPTED | INVENTORY_READY | trusted read-only observation committed |
| T02 | INVENTORY_READY | PLAN_BUILT | PLAN_READY | pure plan and complete input closure committed |
| T03 | PLAN_READY | APPROVAL_REQUESTED | APPROVAL_REQUESTED | approval request identity committed |
| T04 | APPROVAL_REQUESTED | OWNER_APPROVED | APPROVED | trusted proof, account, role, scope, and replay reservation committed |
| T05 | APPROVED | JOURNAL_REQUESTED | JOURNAL_REQUESTED | journal capacity and request preimage reserved |
| T06 | JOURNAL_REQUESTED | JOURNAL_DURABLE | JOURNALED | both replicas contain the plan header and approval |
| T07 | JOURNALED | RESIZE_REQUESTED | RESIZE_REQUESTED | resize request exists before Apple call |
| T08 | RESIZE_REQUESTED | RESIZE_COMMITTED | STUB_REQUESTED | resize result and protected-set read-back committed |
| T09 | JOURNALED | STUB_REQUESTED | STUB_REQUESTED | no-resize path request exists |
| T10 | STUB_REQUESTED | STUB_COMMITTED | APPLE_STUB_READY | stub and read-back evidence committed |
| T11 | APPLE_STUB_READY | HANDOFF_REQUESTED | HANDOFF_REQUESTED | handoff descriptor and visual instructions committed |
| T12 | HANDOFF_REQUESTED | HANDOFF_COMMITTED | OWNER_HANDOFF_PENDING | owner handoff record committed |
| T13 | OWNER_HANDOFF_PENDING | IN_1TR_VERIFIED | IN_1TR | external handoff observed and exact identity verified |
| T14 | IN_1TR | LOCALPOLICY_REQUESTED | LOCALPOLICY_REQUESTED | policy request is durable before the Apple call |
| T15 | LOCALPOLICY_REQUESTED | LOCALPOLICY_COMMITTED | LOCALPOLICY_READY | policy result and protected-policy read-back committed |
| T16 | LOCALPOLICY_READY | LIVE_HANDOFF_REQUESTED | LIVE_HANDOFF_REQUESTED | signed live descriptor request committed |
| T17 | LIVE_HANDOFF_REQUESTED | LIVE_HANDOFF_COMMITTED | LIVE_HANDOFF_PENDING | offline closure and handoff commit committed |
| T18 | LIVE_HANDOFF_PENDING | IN_1TR_VERIFIED | LIVE_RUNNING | target-side identity and closure reverified |
| T19 | LIVE_RUNNING | LAYOUT_REQUESTED | LAYOUT_REQUESTED | exact layout request committed |
| T20 | LAYOUT_REQUESTED | LAYOUT_COMMITTED | LAYOUT_READY | layout, encryption, and ownership read-back committed |
| T21 | LAYOUT_READY | IMAGE_REQUESTED | IMAGE_REQUESTED | inactive image request committed |
| T22 | IMAGE_REQUESTED | IMAGE_COMMITTED | IMAGE_STAGED | image digest, length, fsync, and read-back committed |
| T23 | IMAGE_STAGED | PENDING_SLOT_COMMITTED | PENDING_BOOT | pending slot and fallback committed |
| T24 | PENDING_BOOT | BOOT_ATTEMPTED | FIRST_BOOT_PENDING | one bounded attempt selected; fallback retained |
| T25 | FIRST_BOOT_PENDING | HEALTH_STARTED | HEALTH_CHECKING | sealed boot context and health start committed |
| T26 | HEALTH_CHECKING | BOOT_SUCCEEDED | SUCCESS | core, separate marker, checks, and fallback evidence committed |
| T27 | SUCCESS | UPDATE_REQUESTED | UPDATE_PENDING | successor transaction request created; prior success immutable |
| T28 | SUCCESS | UNINSTALL_REQUESTED | UNINSTALL_PENDING | exact ownership and uninstall request committed |
| T29 | UPDATE_PENDING | OWNER_APPROVED | APPROVED | fresh approval binds new transaction generation |
| T30 | UNINSTALL_PENDING | ABORT_REQUESTED | ABORT_REQUESTED | cancellation/abort request committed before deletion |
| T31 | ABORT_REQUESTED | ABORT_COMMITTED | ABORTED | safe no-mutation result committed |
| T32 | UNINSTALL_PENDING | UNINSTALL_REQUESTED | UNINSTALL_PENDING | duplicate request is state-idempotent |
| T33 | UNINSTALL_PENDING | SPACE_RECLAIM_REQUESTED | SPACE_RECLAIM_REQUESTED | all approved objects absent and reclaim request committed |
| T34 | SPACE_RECLAIM_REQUESTED | SPACE_RECLAIM_COMMITTED | UNINSTALLED | Apple reclaim result and protected-set read-back committed |
| T35 | ROLLBACK_REQUIRED | ROLLBACK_REQUESTED | ROLLBACK_REQUIRED | fallback request committed without claiming success |
| T36 | ROLLBACK_REQUIRED | ROLLBACK_COMMITTED | ROLLED_BACK | last-known-good slot and identity read-back committed |
| T37 | ROLLED_BACK | RECOVERY_REPAIRED | NEW | old approval/lineage retired; fresh generation required |
| T38 | RECOVERY_REQUIRED | RECOVERY_REPAIRED | NEW | named recovery evidence and fresh inventory committed |
| T39 | ABORTED | RECOVERY_REPAIRED | NEW | new generation only; aborted history immutable |
| T40 | ROLLED_BACK | UPDATE_REQUESTED | UPDATE_PENDING | new update generation request committed |
| T41 | SPACE_RECLAIM_REQUESTED | SPACE_RECLAIM_REQUESTED | SPACE_RECLAIM_REQUESTED | exact duplicate reclaim request is idempotent |
| T42 | RECOVERY_REQUIRED | RECOVERY_REQUESTED | RECOVERY_REQUIRED | recovery request is durable and idempotent |
| T43 | NEW | RECOVERY_REQUESTED | RECOVERY_REQUIRED | pre-mutation recovery is durable |
| T44 | INVENTORY_READY | HOLD_REQUESTED | RECOVERY_REQUIRED | read-only evidence held without mutation |
| T45 | APPROVED | HOLD_REQUESTED | RECOVERY_REQUIRED | approval is invalidated and cannot be reused |

### 6.4 Total transition rule and fault semantics

The transition function is total:

```text
transition(prior_state, event, canonical_input) =
  the unique T-row above when its exact prior_state and event match;
  otherwise the unique fault row below when its state class and event match;
  otherwise STATE_EVENT_NOT_ALLOWED with result_state = prior_state,
    result = state-unchanged, and a durable rejection record.
```

A fault row is selected by the same phase/category/path precedence in Section 2.2. Thus every event in every admissible prior state has exactly one transition, one stable rejection, one terminal result, or one idempotent no-op. No event is ignored and no input order chooses a result.

| Fault event | Prior-state class | Result state | Code | Exact durable result |
| --- | --- | --- | --- | --- |
| `POWER_LOSS` | any non-terminal state with a request or commit boundary | RECOVERY_REQUIRED | `POWER_LOSS_RECOVERY_REQUIRED` | stop, classify last durable request/commit, preserve both replicas, require fresh observation |
| `PROCESS_DEATH` | any non-terminal state with a request or commit boundary | RECOVERY_REQUIRED | `PROCESS_DEATH_RECOVERY_REQUIRED` | same recovery rule; no in-memory state is trusted |
| `USER_CANCELLATION` | NEW through JOURNALED or HANDOFF_REQUESTED | ABORT_REQUESTED | `ACCEPT` | durable cancellation request; only `ABORT_COMMITTED` can become ABORTED |
| `USER_CANCELLATION` | RESIZE_REQUESTED through UNINSTALL_PENDING after mutation boundary | RECOVERY_REQUIRED | `CANCEL_AFTER_MUTATION` | hold, reobserve exact owned effects, no guessed delete or rollback |
| `RETRY_EXHAUSTED` | PENDING_BOOT, FIRST_BOOT_PENDING, HEALTH_CHECKING, UPDATE_PENDING | ROLLBACK_REQUIRED | `RETRY_EXHAUSTED_RECOVERY` | attempt budget is terminal for generation; select only verified last-known-good |
| `PARTIAL_DELETE` | UNINSTALL_PENDING or SPACE_RECLAIM_REQUESTED | RECOVERY_REQUIRED | `PARTIAL_DELETE_HOLD` | record exact absent/present set; no second deletion without fresh ownership proof |
| `RECLAIM_INTERRUPTED` | SPACE_RECLAIM_REQUESTED | RECOVERY_REQUIRED | `RECLAIM_INTERRUPTED` | do not infer free space; re-read request, protected set, and Apple result |
| `JOURNAL_DIVERGENCE` | any state with two replicas | RECOVERY_REQUIRED | `JOURNAL_DIVERGENCE` | no replica wins; retain bytes, quarantine transaction, require human recovery |
| `DUPLICATE_REPLAY` | any state | prior state for byte-identical committed tuple | `REPLAY_DUPLICATE_NOOP` | no external call and no counter advance |
| `DUPLICATE_REPLAY` | any state | prior state | `REPLAY_ID_MISMATCH` | same replay identity with different bytes is rejected |
| `DISK_FULL_PRE_BOUNDARY` | any request state before request commit | prior state | `DISK_FULL_PREBOUNDARY` | no mutation call; reserved rejection evidence or recovery hold if reserve itself is unavailable |
| `DISK_FULL_POST_BOUNDARY` | any state after request commit | RECOVERY_REQUIRED | `DISK_FULL_POSTBOUNDARY` | no commit claim; classify external state from fresh read-back |
| `RESTART_RECOVERY` | any non-terminal state | exact state derived from both committed replicas | `ACCEPT` | replay only durable records; uncommitted requests are not effects |
| `HOLD_REQUESTED` | any non-terminal state | RECOVERY_REQUIRED | `TRUST_BOUNDARY_FAILURE` | hold is durable and cannot authorize continuation |

The state classes in the fault table are closed sets over the 37 states listed in Section 6.1. If a future state or event is added, the schema generator must fail until its fault-class membership and default result are declared. A partial deletion is never treated as an empty deletion; an interrupted reclaim is never treated as a committed reclaim; a power loss or process death is never treated as success.

### 6.5 Durable evidence, idempotency, counters, and restart

Each request, external result, and commit record contains `{record_id, transaction_id, transaction_generation, prior_state, event, input_digest, scope_digest, phase, code, path, result, result_state, replica_a_digest, replica_b_digest, previous_record_digest, record_digest, committed_at}`. The two replicas use identical canonical bytes and hash-chain predecessor. A commit is admissible only when the request record, external result, postcondition, and commit record are present and equal in both replicas.

The transaction generation starts at 1 and is monotonic per transaction ID. A duplicate request with byte-identical tuple is a stable no-op; a different tuple under the same transaction ID, generation, or replay identity is rejected. Attempt counters, source generations, marker generations, record sequences, and slot generations have inclusive bounds and no wrap. Before each increment the executor checks the maximum; overflow preserves the prior durable value and enters recovery. Restart reads both replicas, selects neither on divergence, ignores uncommitted request records as effects, and replays only exact committed records. Approval, proof, locks, raw observations, and in-memory state are never reconstructed from a journal.

## 7. Destructive operation boundaries

The operation graph is fixed and ordered: inventory; plan; owner approval; journal; optional resize; stub; handoff; policy; live handoff; layout; image; pending slot; boot attempt; health; update or uninstall; object deletion; reclaim. Each graph edge has the request/commit pair in Section 6.3. Every edge has an allowlisted target set, identity snapshot, precondition digest, expected effect digest, rollback boundary, owner summary, and postcondition.

Deletion is exact ownership only. The executor may remove an object only when its stable ID, full identity preimage, parent, generation, role, size, source provenance, and ownership record are present in the trusted plan and fresh observation. A raw path, pattern, name, first disk, glob, environment variable, or display size has no deletion authority. Partial delete, changed parent, changed size, replacement, clone, stale observation, or ambiguous match produces the Section 2 result before the next mutation.

The sole secret route is a bounded OS-owned pipe whose endpoint, lifetime, zeroization, crash behavior, swap behavior, descriptor inheritance, logs, telemetry, support export, and cancellation behavior are future acceptance requirements. Credentials never occur in argv, environment, journal, plan, error message, cache, or support payload. Network acquisition and mutable remote metadata are forbidden after final consent; a network attempt after consent is `NETWORK_AFTER_CONSENT`.

## 8. Canonical future fixture contract

### 8.1 Fixture record schema

The future canonical fixture record is a closed 14-column row. Column order is fixed and every row has width 14:

| # | Field | Closed value or rule |
| ---: | --- | --- |
| 1 | `fixture_id` | unique `FAMILY-NNN`, family prefix from the manifest, ordinal starts at 001 |
| 2 | `family` | exact family from the 13-row manifest below |
| 3 | `executor` | exact producer/executor identity; current design value is `NOT_IMPLEMENTED` |
| 4 | `consumer` | exact consumer identity; current design value is `NOT_IMPLEMENTED` |
| 5 | `implementation_status` | `NOT_IMPLEMENTED`, `DESIGN_MODEL`, `TOOLING_BLOCK`, `RUNTIME_PASS`, or `RUNTIME_FAIL`; current every row is `NOT_IMPLEMENTED` |
| 6 | `prior_state` | one exact Section 6.1 state |
| 7 | `attempted_input_event` | one exact Section 6.2 event plus canonical single mutation |
| 8 | `result_state` | one exact state or `NO_STATE` for parse rejection before state load |
| 9 | `phase` | exactly one of P0 through P6 |
| 10 | `code` | exactly one Section 2.2 registry code |
| 11 | `path` | exact `JsonPath`, including `$` when the fault is framing or state-level |
| 12 | `result` | one exact Section 2.1 result |
| 13 | `durable_evidence` | typed record IDs and replica outcome; never raw secret or invented digest |
| 14 | `restart_observation` | exact post-restart state/replay result and source manifest row identity |

Every materialized row also carries `source_row_id = fixture-manifest/<family>/<ordinal>` inside column 14. `source_row_id` is the immutable line/row identity; it is not a filesystem path. The canonical output is sorted by family order, then numeric ordinal. IDs, `(code,path,phase)`, and source row identities are unique. No family is open-ended.

The current design-model row shape is:

```text
fixture_id=EXAMPLE-NOT-A-CORPUS-ROW | family=TRANSACTION | executor=NOT_IMPLEMENTED |
consumer=NOT_IMPLEMENTED | implementation_status=NOT_IMPLEMENTED | prior_state=NEW |
attempted_input_event=INVENTORY_ACCEPTED:single-canonical-input | result_state=INVENTORY_READY |
phase=P6 | code=ACCEPT | path=$ | result=allow |
durable_evidence=DESIGN_MODEL_ONLY:no-runtime-record | restart_observation=source_row_id=fixture-manifest/TRANSACTION/example; restart=NOT_IMPLEMENTED
```

This is a schema example, not one of the 106 corpus rows. It intentionally contains no actual digest, signature, artifact, or runtime claim.

### 8.2 Closed deterministic fixture manifest

The future materializer expands the following exact ordered family manifest. Counts are fixed and sum to 108. Each generated row inherits `executor=NOT_IMPLEMENTED`, `consumer=NOT_IMPLEMENTED`, and `implementation_status=NOT_IMPLEMENTED` until a real implementation and accepted report exist.

| Order | Family | Count | Coverage |
| ---: | --- | ---: | --- |
| 01 | `TRANSACTION` | 40 | one row for every closed state, including request/commit, terminal, and recovery entry/result behavior |
| 02 | `FAULT` | 8 | process death, retry exhaustion, journal divergence, duplicate replay, terminality, unknown event, generation overflow, hold |
| 03 | `POWER` | 4 | power loss before request commit, after request commit, after external call, during restart recovery |
| 04 | `CANCELLATION` | 4 | pre-mutation cancel, request/commit abort, post-boundary cancel, replayed cancel |
| 05 | `PARTIAL_DELETE` | 4 | none deleted, subset deleted, wrong object deleted, delete result unavailable |
| 06 | `RECLAIM` | 4 | request missing, request durable, reclaim interrupted, reclaim committed |
| 07 | `DISK_FULL` | 4 | before request, between replicas, after request, before commit |
| 08 | `JOURNAL` | 4 | torn record, divergent replicas, stale chain, restart reconstruction |
| 09 | `DUPLICATE` | 4 | identical request, identical commit, replay ID mismatch, document ID reuse |
| 10 | `F02_SEAM` | 12 | missing executor/consumer/status, alias drift, schema lock drift, generated lock drift, authority drift, stable-ID preimage drift, boot bound overflow, provenance drift, stale/replayed lock, unsealed Trusted value, wrong role, wrong scope |
| 11 | `HANDOFF` | 8 | missing identity, missing digest field, preimage drift, wrong board/target/repository scope, duplicate producer, ambiguous producer, stale artifact, false executable status |
| 12 | `GRAMMAR` | 8 | unknown field, duplicate member, unknown enum, array reorder, invalid path, integer overflow, unknown code, reordered simultaneous faults |
| 13 | `DELIVERY` | 4 | missing schema/fixture manifest, missing generated binding, absent CI context, absent QA/physical evidence |

The materializer must expand each row from a deterministic seed named by family and ordinal, use one mutation per row, and compute the expected result from Sections 2 and 6. No row may combine alternate mutations. The absence of a runner means the entire 108-row corpus is `NOT_IMPLEMENTED`, not PASS.

### 8.3 Fault and boundary coverage rule

The 108 rows must cover every Section 6 state as a prior state or result state, every Section 6 event as an attempted event or total-rejection event, every request/commit boundary in T01-T45, both journal replicas, and the destructive boundaries for resize, stub, policy, handoff, layout, image, boot, deletion, and reclaim. The manifest is closed: a row outside these families, a missing family, a changed count, reordered family, duplicate ID, duplicate expected tuple, missing executor/consumer/status, or status `RUNTIME_PASS` without an acceptance artifact fails the corpus gate.

## 9. Handoff identity and 28/28 PROGRAM equality

### 9.1 Immutable handoff record

Every handoff is a closed record with exact fields `{handoff_id, producer, consumer, artifact_id, document_id, record_id, type, schema_input_lock_digest, generated_binding_lock_digest, canonical_content_digest, payload_digest, digest_preimage_grammar, project_id, repository_id, board_id, target_id, slice_id, operation, candidate_id, channel, phase, code, path, result, issued_at, expires_at, freshness_rule, replay_identity, acceptance_artifact, residual_owner, due_before_gate}`. `artifact_id`, `document_id`, `record_id`, and the digest values are required future supplied fields; no actual digest is invented here.

The canonical content preimage is `ASCII("omarchy-handoff-content/v1") || 0x00 || JCS(content_without_content_digest)`. The payload preimage is `ASCII("omarchy-handoff-payload/v1") || 0x00 || JCS(payload_without_payload_digest)`. `canonical_content_digest` and `payload_digest` are independent. A future producer must supply both exact values and the signed acceptance artifact; a field marked future-supplied is absent authority, not a digest.

`HandoffScope` is exact and non-null: `{project_id, repository_id, board_id, target_id, slice_id, operation, candidate_id, channel}`. `board_id` is an exact board, never a family; `target_id` is the exact target artifact/document/record identity; `operation` is the exact operation; candidate and channel are exact, not defaults. A duplicate producer for the same `(consumer, scope, type, operation)` is rejected. Two producers for one identity with different bytes are ambiguous and rejected; two rows with the same handoff ID are duplicate and rejected. A producer cannot emit an artifact for a scope it does not own, and a consumer cannot widen or reinterpret the scope.

### 9.2 Exact dependency table

The 28 dependency sets below are copied as comparison-only sets from the pinned PROGRAM authority. The `PROGRAM dependency set` and `Exact producer` columns must remain byte-for-byte equal after materialization: equality is structural evidence only and does not make a dependency available. Every row includes every immutable identity field through the `HandoffScope` reference and has `result=hold` until its future signed acceptance artifact exists.

| ID | PROGRAM dependency set | Exact producer | Consumer | Artifact/document/record identity | Locks | Digest preimage | HandoffScope | Phase/code/path/result | Freshness/replay | Acceptance artifact | Residual owner | Due-before gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-02 | F-01 | F-01 | F-02 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from F-01->F-02 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | F-02 owner | F-02 foundation |
| F-03 | F-02 | F-02 | F-03 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from F-02->F-03 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | F-03 owner | F-03 trust-root |
| F-04 | F-02 | F-02 | F-04 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from F-02->F-04 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | F-04 owner | F-04 builder |
| F-05 | F-03,F-04,F-06,Q-00,Q-01 | F-03,F-04,F-06,Q-00,Q-01 | F-05 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->F-05 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | F-05 owner | candidate assembly |
| F-06 | F-01 | F-01 | F-06 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from F-01->F-06 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | F-06 owner | compliance |
| F-07 | F-05,P-03,P-05,I-09,B-04,Q-04,Q-05,Q-06,Q-07,Q-08 | F-05,P-03,P-05,I-09,B-04,Q-04,Q-05,Q-06,Q-07,Q-08 | F-07 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->F-07 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | coordinator | stable promotion |
| P-04 | F-02 | F-02 | P-04 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from F-02->P-04 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | P-04 owner | diagnostics |
| P-06 | P-02 | P-02 | P-06 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from P-02->P-06 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | P-06 owner | clean install |
| P-07 | P-05,P-06 | P-05,P-06 | P-07 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->P-07 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | P-07 owner | migration |
| I-01 | F-01 | F-01 | I-01 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from F-01->I-01 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | I-01 owner | transaction design |
| I-02 | I-01,F-03,F-06 | I-01,F-03,F-06 | I-02 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->I-02 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | I-02 owner | signed app |
| I-03 | F-02,Q-00,I-01,I-07 | F-02,Q-00,I-01,I-07 | I-03 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->I-03 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | I-03 owner | inventory |
| I-04 | I-02,I-03,I-07 | I-02,I-03,I-07 | I-04 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->I-04 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | I-04 owner | Apple transaction |
| I-05 | F-04,F-05,I-04 | F-04,F-05,I-04 | I-05 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->I-05 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | I-05 owner | live install |
| I-06 | I-04,I-05 | I-04,I-05 | I-06 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->I-06 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | I-06 owner | recovery |
| I-07 | I-01 | I-01 | I-07 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from I-01->I-07 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | I-07 owner | credentials |
| I-08 | I-01,I-07,P-04 | I-01,I-07,P-04 | I-08 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->I-08 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | I-08 owner | UX |
| I-09 | Q-00,I-02,I-03,I-04,I-05,I-06,I-07,I-08,P-06,P-07 | Q-00,I-02,I-03,I-04,I-05,I-06,I-07,I-08,P-06,P-07 | I-09 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->I-09 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | coordinator | installer acceptance |
| B-04 | B-03 | B-03 | B-04 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from B-03->B-04 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | B-04 owner | boot implementation |
| Q-00 | F-02 | F-02 | Q-00 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from F-02->Q-00 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-00 owner | board admission |
| Q-01 | F-02,Q-00 | F-02,Q-00 | Q-01 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->Q-01 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-01 owner | criteria |
| Q-02 | Q-01 | Q-01 | Q-02 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from Q-01->Q-02 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-02 owner | evidence ingestion |
| Q-03 | Q-00,Q-01 | Q-00,Q-01 | Q-03 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->Q-03 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-03 owner | fleet |
| Q-04 | B-02,B-04,K-02,G-02,I-09,Q-02,Q-03 | B-02,B-04,K-02,G-02,I-09,Q-02,Q-03 | Q-04 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->Q-04 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-04 owner | physical cohort 04 |
| Q-05 | B-04,B-05,K-03,G-03,I-09,Q-02,Q-03 | B-04,B-05,K-03,G-03,I-09,Q-02,Q-03 | Q-05 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->Q-05 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-05 owner | physical cohort 05 |
| Q-06 | B-04,B-06,K-04,G-04,I-09,Q-02,Q-03 | B-04,B-06,K-04,G-04,I-09,Q-02,Q-03 | Q-06 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->Q-06 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-06 owner | physical cohort 06 |
| Q-07 | B-04,B-07,K-05,G-05,I-09,Q-02,Q-03 | B-04,B-07,K-05,G-05,I-09,Q-02,Q-03 | Q-07 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->Q-07 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-07 owner | physical cohort 07 |
| Q-08 | B-04,B-08,K-06,G-05,I-09,Q-02,Q-03 | B-04,B-08,K-06,G-05,I-09,Q-02,Q-03 | Q-08 | artifact_id/document_id/record_id=SUPPLIED_AT_ADMISSION | schema-input-lock + generated-output-lock | content/v1 + payload/v1 JCS preimages | exact project/repo/board/target/slice/operation/candidate/channel from producers->Q-08 | P5/HANDOFF_INPUT_MISSING/$.handoff/result=hold | issued<=clock<expiry; replay reservation | SUPPLIED_AT_ADMISSION | Q-08 owner | physical cohort 08 |

Handoff count is exactly 28, IDs are unique, and the dependency column is the PROGRAM comparison column. The table does not assert that any of the 28 producer artifacts exist.

## 10. Product and recovery contract

Inventory, acquisition, and plan generation are pure with respect to APFS, boot, and system mutation. Final consent is one explicit typed owner decision over the complete plan, scope, topology, artifact closure, target identities, operation order, policy, channel, and expiry. Security, encryption, telemetry, and external-disk consequences are separate decisions.

The visible state sequence is launch, readiness, admission, storage plan, acquisition, consent, Apple authorization, provisioning, recovery handoff, Linux installation, first boot, failure/recovery, update, uninstall, and support export. GUI and CLI expose the same typed state and exact error. No terminal prompt, manual continuation, missing download, stale cache, unknown board, or partial health result can produce a success message.

Telemetry is off by default. Support export is local, redacted, previewable, and separately consented. Raw credentials, assertions, private keys, serials, raw paths, hostnames, usernames, home paths, MAC addresses, raw command output, evidence bytes, and encryption material are excluded from logs, journal, telemetry, and projections.

Recovery requires preserving macOS fallback, recording the exact last durable boundary, showing the exact external-owner action, reobserving the full topology and lock set, and obtaining a new generation and approval. DFU or other human recovery is a named escalation, never an automated success path.

## 11. Executable-delivery acceptance design

### 11.1 Future artifact paths and status

The following paths are exact future deliverables. They are specified here only; none exists in this design-only slice.

| Future path | Required content | Current status |
| --- | --- | --- |
| `schemas/installer-transaction/v1/transaction.schema.json` | closed state, event, journal, counter, and result schema | NOT_IMPLEMENTED |
| `schemas/installer-transaction/v1/fixture.schema.json` | 14-column fixture record and closed family manifest schema | NOT_IMPLEMENTED |
| `schemas/installer-transaction/v1/handoff.schema.json` | immutable 28-row handoff record schema and scope grammar | NOT_IMPLEMENTED |
| `schemas/installer-transaction/v1/rejection-registry.json` | machine-readable exact code/phase/path/result registry | NOT_IMPLEMENTED |
| `bindings/generated-output.lock` | ratified generated binding lock and output digests | BLOCKED_F02_AUTHORITY_UNRESOLVED |
| `fixtures/installer-transaction/manifest.json` | exact 108-row corpus manifest and seeds | NOT_IMPLEMENTED |
| `fixtures/installer-transaction/accepted/` | accepted canonical rows | NOT_IMPLEMENTED |
| `fixtures/installer-transaction/hostile/` | single-mutation fault rows | NOT_IMPLEMENTED |
| `tools/installer-transaction/validate` | parser, JCS, schema, precedence, and totality validator | NOT_IMPLEMENTED |
| `tools/installer-transaction/run-faults` | power/process/cancel/disk/reclaim/delete injection harness | NOT_IMPLEMENTED |
| `tests/installer-transaction/` | property, replay, restart, secret-route, and consumer-guard tests | NOT_IMPLEMENTED |
| `.github/workflows/installer-transaction.yml` | clean-checkout required contexts and artifact retention | NOT_IMPLEMENTED |
| `reports/installer-transaction/` | exact report schema, manifest digest, tool/runtime lock, and results | NOT_IMPLEMENTED |

No future artifact may be admitted from a working tree with unrelated changes, untracked generated output, mutable source refs, missing lock bytes, or a changed input lock. A clean checkout is required before generation and again before report signing.

### 11.2 Exact future commands and environments

The future reproducible container must publish its image digest, OS image digest, Python/JSON Schema/JCS runtime versions, signature verifier version, generator version, compiler/toolchain versions, and command argv in a signed toolchain lock. The minimum command sequence is:

```text
git diff --check
git status --short --branch
python3 tools/installer-transaction/validate --schema schemas/installer-transaction/v1/transaction.schema.json --fixtures fixtures/installer-transaction/manifest.json --handoffs docs/omarchy-installer-transaction-design.md
python3 tools/installer-transaction/run-faults --manifest fixtures/installer-transaction/manifest.json --require-all-boundaries --require-restart
python3 tools/installer-transaction/report --input reports/installer-transaction/raw.json --output reports/installer-transaction/final.json
```

The validator must check exact row width/order/count/uniqueness, state/event totality, request/commit pairing, counter bounds, earliest-failure precedence, fixture family closure, all destructive boundaries, 28/28 dependency equality, code/phase/path/result closure, generated binding equality, and no false executable status. The fault runner must inject power loss, process death, cancellation, retry exhaustion, partial deletion, interrupted reclaim, journal divergence, duplicate/replayed transaction, and disk-full before/after every durable boundary.

### 11.3 Required reports and physical evidence

Every report is a closed record with report ID, source checkout commit, input lock IDs/digests, generated binding IDs/digests, container/runtime/tool versions, exact argv, fixture manifest digest, row count, pass/fail counts, unexpected accepts, rejected mutations, redaction result, signature, and retention policy. A design-model report must set `implementation_status=DESIGN_MODEL`, `runtime_observation=NOT_EXECUTABLE`, and `promotion_effect=NONE`.

Required future gates are: static schema and binding conformance; state-machine property tests; fault injection; replay/idempotency; journal recovery; secret leak and redaction; network-denied post-consent; signed Apple lock verification; clean-checkout CI; independent QA; and physical qualification on the exact board/target tuple with recovery, rollback, peripherals, power, storage, and boot evidence. Signed locks, QA reports, and physical evidence are external artifacts and absent here. VM boot, compile success, chip recognition, mock storage, or a design-model check cannot satisfy physical qualification.

CI required contexts are exact future names: `installer-schema`, `installer-generated-bindings`, `installer-fixtures`, `installer-state-totality`, `installer-fault-recovery`, `installer-secret-boundary`, `installer-clean-checkout`, `installer-independent-qa`, and `installer-physical-evidence-gate`. Missing, skipped, renamed, or untrusted contexts hold the slice.

## 12. Hostile scratch mutation ledger and observed signals

The following mutations are mandatory single-field or single-event scratch probes. A future runner must mutate an exact canonical fixture in disposable scratch, not the tracked design. The current observed result is recorded honestly: the text model rejects the planted mutation where stated; target runtime is NOT EXECUTABLE because no runner or implementation exists.

| Probe | Hostile mutation | Expected signal | Observed design-model signal | Target runtime |
| --- | --- | --- | --- | --- |
| H01 | remove request record and leave commit | `JOURNAL_DIVERGENCE`, P6, `$.journal.request` | DESIGN_MODEL: reject; unexpected accepts 0 | NOT_EXECUTABLE |
| H02 | remove commit record after external result | `DISK_FULL_POSTBOUNDARY`, P6, `$.journal.commit` | DESIGN_MODEL: hold/recovery; unexpected accepts 0 | NOT_EXECUTABLE |
| H03 | inject power loss at every listed boundary | `POWER_LOSS_RECOVERY_REQUIRED`, P6, `$.fault` | DESIGN_MODEL: recovery required for 4/4 boundary classes | NOT_EXECUTABLE |
| H04 | inject process death at every listed boundary | `PROCESS_DEATH_RECOVERY_REQUIRED`, P6, `$.fault` | DESIGN_MODEL: recovery required; unexpected accepts 0 | NOT_EXECUTABLE |
| H05 | cancel before and after first mutation | `ACCEPT` then `CANCEL_AFTER_MUTATION` | DESIGN_MODEL: abort request versus recovery; unexpected accepts 0 | NOT_EXECUTABLE |
| H06 | exhaust attempt budget | `RETRY_EXHAUSTED_RECOVERY`, P6, `$.attempt_counter` | DESIGN_MODEL: rollback required; unexpected accepts 0 | NOT_EXECUTABLE |
| H07 | delete only a subset of owned objects | `PARTIAL_DELETE_HOLD`, P6, `$.deleted_set` | DESIGN_MODEL: recovery required; unexpected accepts 0 | NOT_EXECUTABLE |
| H08 | interrupt reclaim between request and commit | `RECLAIM_INTERRUPTED`, P6, `$.reclaim` | DESIGN_MODEL: no free-space claim; unexpected accepts 0 | NOT_EXECUTABLE |
| H09 | replay same transaction bytes | `REPLAY_DUPLICATE_NOOP` | DESIGN_MODEL: idempotent no-op; unexpected accepts 0 | NOT_EXECUTABLE |
| H10 | replay same ID with changed bytes | `REPLAY_ID_MISMATCH`, P3, `$.replay_id` | DESIGN_MODEL: reject; unexpected accepts 0 | NOT_EXECUTABLE |
| H11 | omit executor, consumer, or status | `PARSE_SCHEMA_FAILURE`, P1, `$.executor`/`$.consumer`/`$.implementation_status` | DESIGN_MODEL: reject 3/3 omissions | NOT_EXECUTABLE |
| H12 | substitute installer-local F-02 alias | `BINDING_INTEGRITY_FAILURE`, P5, `$.schema_set_digest` | DESIGN_MODEL: hold; unexpected accepts 0 | NOT_EXECUTABLE |
| H13 | drift schema-input or generated-output lock | `BINDING_INTEGRITY_FAILURE`, P5, `$.lock` | DESIGN_MODEL: reject; unexpected accepts 0 | NOT_EXECUTABLE |
| H14 | change one stable-ID preimage field | `AMBIGUOUS_IDENTITY`, P4, `$.stable_id` | DESIGN_MODEL: reject; unexpected accepts 0 | NOT_EXECUTABLE |
| H15 | set boot source generation above uint64 maximum | `RESOURCE_LIMIT`, P1, `$.source_generation` | DESIGN_MODEL: reject; unexpected accepts 0 | NOT_EXECUTABLE |
| H16 | replace boot counter with zero after an attempt | `BOOT_COUNTER_FAILURE`, P4, `$.attempt.counter` | DESIGN_MODEL: hold; unexpected accepts 0 | NOT_EXECUTABLE |
| H17 | omit handoff identity or use a missing digest field | `HANDOFF_INPUT_MISSING`, P5, `$.handoff.artifact_id` | DESIGN_MODEL: hold; unexpected accepts 0 | NOT_EXECUTABLE |
| H18 | use wrong board, target, repository, or slice scope | `CROSS_DOCUMENT_MISMATCH`, P5, `$.handoff.project_id` | DESIGN_MODEL: reject; unexpected accepts 0 | NOT_EXECUTABLE |
| H19 | add a duplicate producer for one scope | `DUPLICATE_SEMANTIC_KEY`, P1, `$.handoffs[1].producer` | DESIGN_MODEL: reject; unexpected accepts 0 | NOT_EXECUTABLE |
| H20 | add an unknown field plus an enum fault, then reorder both inputs | `UNKNOWN_FIELD`, P1, `$.fixture.unexpected`, result=reject | DESIGN_MODEL: same phase/path/code for both input orders | NOT_EXECUTABLE |
| H21 | use a stale Apple lock or replay its reservation | `FRESHNESS_FAILURE`, P3, `$.lock.expires_at` | DESIGN_MODEL: hold/reject at earliest stale field; unexpected accepts 0 | NOT_EXECUTABLE |
| H22 | mark a design row `RUNTIME_PASS` without report artifact | `DELIVERY_ARTIFACT_MISSING`, P6, `$.implementation_status` | DESIGN_MODEL: reject false executable status | NOT_EXECUTABLE |

The scratch model baseline is `DESIGN_MODEL PASS` for the declared grammar and precedence rules, with 22/22 hostile mutation classes rejected and 0 unexpected model accepts. This is not runtime PASS, not implementation evidence, and not qualification.

## 13. Delivery and residual census

| Contract or evidence boundary | Design status | Delivery status | Blocking reason |
| --- | --- | --- | --- |
| total state/event/fault/reclaim transaction relation | DESIGN_MODEL PASS | NOT_IMPLEMENTED | no runner, journal, or fault harness |
| request/commit durability and restart recovery | DESIGN_MODEL PASS | NOT_IMPLEMENTED | no two-replica implementation or report |
| owner proof, target account, role, scope, freshness, replay | DESIGN_MODEL PASS | HANDOFF_INPUT_MISSING | no ratified generated seam or external trust source |
| exact four stable-ID preimages and provenance | DESIGN_MODEL PASS | HANDOFF_INPUT_MISSING | no authoritative generated contract or adapter |
| boot counter/source generation/BootContext/marker separation | DESIGN_MODEL PASS | NOT_IMPLEMENTED | no boot record constructor or runtime marker |
| Apple baseline/command/authorization locks | DESIGN_MODEL PASS | APPLE_LOCK_MISSING | no signed owner-approved lock bytes |
| 108-row canonical future fixture corpus | DESIGN_MODEL PASS | NOT_IMPLEMENTED | no schema, materializer, or runner |
| 28 immutable handoff records and dependency equality | DESIGN_MODEL PASS | HANDOFF_INPUT_MISSING | no producer artifacts, IDs, digests, or acceptance artifacts |
| code/phase/path/result closure | DESIGN_MODEL PASS | NOT_IMPLEMENTED | no generated rejection registry or validator |
| clean-checkout CI and generated bindings | DESIGN_MODEL PASS | TOOLING_BLOCK | required CI, compiler, JCS, schema, and binding tools absent |
| QA, signed locks, and physical qualification | DESIGN_MODEL PASS | QUALIFICATION_EVIDENCE_MISSING | no signed report, hardware evidence, or qualified tuple |
| support, release, merge, and DONE claims | HONESTLY NOT CLAIMED | FAIL-CLOSED | this document is design-only |

The current repository contains no installer transaction runner, canonical schema package, generated binding package, fixture runner, fault injector, signed lock bytes, acceptance report, CI required context, QA report, or physical qualification evidence. Missing tools remain `TOOLING_BLOCK`; they do not become passes by textual design.

## 14. Required future acceptance decision

The coordinator may reconsider I-01 only after an owner-ratified F-02 import artifact and generated locks, implementation of the exact state/event relation, the 106-row runner, all signed handoffs, the Apple lock set, clean-checkout CI, independent QA, and physical evidence are present and independently reviewed. Until then, the only admissible status is design correction specified, implementation NOT IMPLEMENTED, F-02 unresolved, Apple locks unresolved, qualification absent, release readiness REJECT, and DONE not claimed.

No value in this document is a signature, digest, approval, board support claim, release candidate, or physical result. No local correction can promote an external authority or opaque boundary.
