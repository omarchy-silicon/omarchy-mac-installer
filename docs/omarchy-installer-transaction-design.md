# Omarchy Silicon installer transaction design

Status: DESIGN ONLY. This document is an implementation-level proposal for I-01 through I-06. It is not installer code, a release approval, a support claim, or evidence that any installation is safe.

Design lane: `factory/design-installer-transaction`

Base reviewed: `omarchy-mac-installer` `origin/main` at `99dff2e968dafcabc2a940865b051e91ffcfafd3`

Canonical program: `omarchy-apple-platform/PROGRAM.md`, read before this design.

## 1. Scope, ownership, and hard boundaries

The installer repository owns the macOS entry point, owner-authenticated handoff, read-only inventory, APFS plan, Apple firmware acquisition and provenance record, stub OS and RecoveryOS provisioning, transaction journal, Omarchy live-image handoff, encryption setup, inactive boot slots, first-boot success marking, uninstall, recovery UX, accessibility, and installer privacy policy.

The platform repository owns `board-registry/v1`, `platform-manifest/v1`, signing policy, component lockfiles, release promotion, and qualification evidence. The installer consumes those signed interfaces and never chooses an independent component tuple.

The installer does not make a board FULL, define a hardware capability as working, promote a release, approve an artifact, or certify a physical device. Booting the desktop is an installer health result, not a platform qualification record.

The `m1n1-omarchy` repository is an opaque human-produced artifact boundary for this lane. Per the coordinator supersession fence, this design does not inspect, analyze, edit, test, clone, or make source-level claims about that repository or its contents. The implementation may consume a signed m1n1 artifact named by the platform manifest through a narrow artifact interface; a human owner must define and verify that artifact contract.

Nothing in this document delegates Omarchy release authority to Asahi, Apple, a CDN, a package manager, a bootloader, a live image, or a report server.

## 2. Design invariants

1. No privileged mutation occurs before the signed release manifest, exact board admission, read-only inventory, complete plan, destructive-operation proofs, and explicit owner approval all pass.
2. The signed platform manifest and signed board registry are the only authorities for the installable board, artifact tuple, required capabilities, image digests, and compatibility constraints.
3. A journal records intent and evidence; it never grants authority to mutate. Resume is derived from the signed plan plus a fresh disk and boot-policy observation, never from a progress spinner or an untrusted journal claim.
4. Every target is addressed by typed stable identifiers and revalidated immediately before and after each operation. `/dev/diskN`, `/dev/rdiskN`, a user path, a glob, an environment variable, a volume label, or a mutable URL is never a destructive authority.
5. Existing macOS containers, Apple internal partitions, FileVault state, unrelated Linux partitions, and unrelated ESPs are protected objects. The mutation plan contains an explicit protected-object set and fails closed if any protected object would be changed.
6. Apple-supported `diskutil`, RecoveryOS, owner authorization, LocalPolicy, `bless`, and related platform mechanisms are invoked through a typed adapter. The installer does not implement an APFS writer or bypass Apple security policy.
7. All downloaded bytes are content-addressed and authenticated before use. TLS, an HTTP status, a CDN location, an Apple URL, an upstream tag, a package-manager signature, or a successful extraction is not sufficient authentication.
8. Each durable operation is either idempotent, has a postcondition classifier, or has an explicit human-recovery transition. An uncertain destructive result is never guessed.
9. Secrets are ephemeral. macOS passwords, owner tokens, LocalPolicy material, LUKS passphrases, and recovery keys never enter the journal, command line, environment, telemetry, or ordinary logs.
10. A successful install requires the exact boot-health contract for the selected board and manifest. It must not turn a missing required feature into a warning followed by success.

## 3. Current repository baseline and reusable material

The reviewed repository is the Asahi Linux installer lineage. It is a Python installer packaged with a private Python framework, shell bootstrap scripts, Apple `diskutil`/`bputil`/`bless`/`kmutil` calls, Apple IPSW or OTA parsing, and firmware extraction helpers. Its current release documentation describes mutable `latest` and environment-selected endpoints; the new installer must replace those release semantics rather than inherit them.

### 3.1 Reuse map

| Existing material | Reuse proposal | Required containment |
|---|---|---|
| `src/system.py:SystemInfo` | Reuse the read-only query inventory concepts for IORegistry, board/chip IDs, firmware versions, boot mode, current OS, and NVRAM observations. | Normalize into a typed schema; redact or omit serial-like data; never use the current static lookup tables as support authority; never treat a chip-family match as board admission. |
| `src/diskutil.py:DiskUtil` | Reuse the `diskutil -plist`, APFS list, volume-group, partition offset, and resize-limit adapter shape. | Split read-only inventory from mutation; accept only stable IDs; reject ambiguous or stale snapshots; use Apple tools for every APFS mutation; add operation-specific pre/post proofs. |
| `src/osenum.py:OSEnum` and `OSInfo` | Reuse APFS volume-role and volume-group relationship parsing, including System/Data/Preboot/Recovery discovery. | Treat duplicate or incomplete role sets as ambiguous; never repair or mount read-write during inventory; identify an Omarchy target only through the ownership manifest and stable IDs. |
| `src/stub.py:load_ipsw`, `load_identity`, and extraction routines | Reuse the idea of selecting a device-specific Apple build identity and extracting only required files from a validated image. | Selection must be driven by the signed platform/installer manifest; verify Apple-provided signatures and internal board/chip/device fields; record source and digest provenance; do not redistribute Apple software without an approved legal/product decision. |
| `src/stub.py:install_files` | Reuse the file inventory concepts for System, Data, Preboot, and RecoveryOS stub material. | Make staging content-addressed and atomic; use a signed stub recipe; preserve Apple-required metadata only through the Apple-supported path; do not copy passwords or place credentials in the transaction. |
| `src/stub.py:collect_firmware` and `asahi_firmware/*` | Reuse pure firmware parsing and packaging where the platform manifest calls for it, including IMG4/LZFSE parsing and collection of Wi-Fi, Bluetooth, multitouch, ISP, ALS, kernel, and ASMedia files. | Keep Apple-signed source provenance and per-file SHA-256; compare output against a manifest allowlist; isolate parser failures; attach the existing MIT notices and the Python-ASN1 notice; never let extraction choose a platform version. |
| `src/osinstall.py:OSInstaller` | Reuse partition-template arithmetic, aligned size calculations, FAT formatting concepts, archive/image extraction concepts, and installer-data placement. | Convert templates into signed layout plans; stage into inactive targets; verify image digest and exact byte count before switching; reject direct writes to any target not created or proven by this transaction. |
| `src/util.py:PBZX`, `PackageInstaller`, `img4` support, and APFS VolBootable fsctl wrapper | Reuse format-specific parsing only after adding bounds, path-traversal, checksum, and resource-limit checks. | Keep Apple private fsctl behavior behind a tested adapter; do not use format parsing as release authentication; replace unsafe `assert`-based validation with typed errors and fail-closed outcomes. |
| `src/urlcache.py:URLCache` | Reuse range-request and readahead ideas for resumable content-addressed downloads. | Require an expected digest and declared length before opening the target; persist verified chunks; reject redirects outside an allowlist; do not accept `random` cache-busting or a mutable URL as an identity. |
| `src/step2/step2.sh` and `src/step2/Finish Installation.app` | Reuse the observed 1TR pairing and handoff concepts. | Replace the Terminal-launched shell flow with a signed continuation agent and an accessible status screen; make nonce, plan hash, VGID, Preboot ID, and owner approval explicit; keep manual Apple power-button actions visible and resumable. |
| `src/reporting.py` | Reuse the explicit consent and “show the data” interaction pattern. | Make telemetry opt-in by default until the owner decides otherwise; remove endpoint selection from environment variables; redact identifiers; never block or change transaction outcome on reporting. |
| `build.sh` and bootstrap scripts | Reuse build-stage separation and local development ergonomics only. | Do not reuse root bootstrap, moving `latest`, shell-piped download, unsigned metadata, or dependency downloads as release behavior. |
| `tools/cleanbp.sh` and `tools/wipe-linux.sh` | No production reuse. They are diagnostic or intentionally heuristic/destructive examples. | Replace with typed, journaled, ownership-proven uninstall and recovery operations. |
| `src/m1n1.py` | Use only as an opaque artifact adapter boundary if the human owner publishes a contract. | This lane makes no claim about the fenced `m1n1-omarchy` repository or its contents. The installer accepts only a signed artifact digest and manifest-declared interface. |

### 3.2 License and provenance inventory

The checkout's top-level `LICENSE` is MIT, and the installer Python modules carry SPDX MIT headers. `asahi_firmware/asn1.py` identifies the vendored Python-ASN1 implementation as MIT and requires its copyright/license notices. A reimplementation or extraction of these components must preserve notices in source and in the shipped third-party notices bundle.

The `artwork` submodule is a separate upstream dependency named in `.gitmodules`; its license and redistribution terms must be audited by the release owner before branding is shipped. This lane did not inspect its contents.

Apple IPSW, OTA, firmware, RecoveryOS, and related extracted assets are Apple-provided material, not MIT code. The release design therefore records source URL, redirect chain, retrieval time, source digest, Apple manifest/build identity, signature-validation result, and extracted-file digests. Whether Omarchy may redistribute any Apple asset or must fetch it directly from Apple is a ruling required before I-02 release packaging.

The Omarchy-owned installer core, signed manifests, board records, live image, package repository, and boot bundles require an Omarchy license/provenance inventory generated at release time. No upstream license, upstream build, upstream merge, or upstream tag substitutes for that inventory.

## 4. Authority model and non-authorities

### 4.1 Authorities

| Decision | Authority |
|---|---|
| Exact board identity and lifecycle | Signed `board-registry/v1` from `omarchy-apple-platform` |
| Exact component tuple, image, firmware schema, package repository, and digests | Signed `platform-manifest/v1` plus the signed installer release manifest |
| Proposed target objects and mutations | The installer-generated `installer-plan/v1`, after owner approval and fresh pre-mutation revalidation |
| Apple APFS/Recovery/LocalPolicy action semantics | Apple-supported tools and owner authentication, wrapped by the installer and observed after each call |
| Whether an artifact is acceptable to Omarchy | Omarchy release signing and platform qualification gates, not an upstream project |
| Whether a board is FULL | Physical qualification record and coordinator-controlled support ledger |
| Boot slot success | `boot-health/v1` contract executed on the target board, not a bootloader “started” bit alone |
| Recovery escalation | The board-specific human DFU runbook and Apple-supported recovery process |

### 4.2 Strict non-authorities

The following inputs may be displayed as evidence but may not authorize an install, delete, release, or support claim: `uname -m`; a static device dictionary; a chip or product marketing name; an environment variable; a raw `/dev/diskN` path; a partition label; a user-entered path; a mutable `latest` file; a moving branch or tag; a CDN/TLS success; an unsigned JSON or plist; a package-manager result; an Apple URL without digest and build-identity validation; a live image without a matching signed manifest; a successful m1n1/bootloader handoff; a running systemd service; a VM, mock, compile, or static repository test; a telemetry response; a journal record without fresh disk evidence; a prior successful install; an upstream release or merge; an Asahi release; and any source or contents of the fenced `m1n1-omarchy` repository.

## 5. Signed entry and immutable release metadata (I-02)

### 5.1 Application and CLI shape

Ship one notarized `Omarchy Silicon Installer.app` with an equivalent CLI invocation. The app and CLI invoke the same sealed transaction core and schema validators. The CLI is not a separate implementation with a second plan or authority.

The application bundle contains:

- A Developer ID-signed native launcher and all embedded executables.
- A sealed, versioned transaction core and its standard-library/runtime dependencies. The existing bundled-Python approach is a possible migration path, but every embedded executable and library must be code-signed, notarization-checked, and included in the release SBOM.
- The signed installer release manifest, pinned trust-root metadata, schema bindings, UI strings, accessibility metadata, and no executable downloaded after launch.
- A third-party notices and source-provenance bundle.

The CLI exposes `plan`, `install`, `resume`, `status`, `uninstall`, `recover`, `doctor`, and `support-bundle` operations. `plan`, `status`, and `doctor` are read-only. `install`, `resume`, and `uninstall` require an interactive owner approval or a short-lived approval capability bound to the exact plan hash, machine identity, target IDs, and operation. `--yes` may skip repeated prose prompts only after that binding is shown and confirmed; it cannot bypass Apple owner authentication.

The first entry is a signed DMG/PKG or an already-installed signed app obtained through an Omarchy-controlled immutable path. A bootstrap helper may locate the version, but it must verify the signed release pointer, artifact digest, app signature, notarization, and manifest before opening the app. There is no `curl | sh`, root shell, default root account, moving branch URL, or mutable environment-selected release.

### 5.2 Manifest verification

The installer release manifest is an envelope over the following minimum fields:

```json
{
  "schema": "omarchy-installer-release/v1",
  "release_id": "stable-YYYY.MM.DD.N",
  "channel": "stable",
  "expires_at": "RFC3339",
  "platform_manifest": {"url": "immutable URL", "sha256": "..."},
  "board_registry": {"url": "immutable URL", "sha256": "..."},
  "live_images": [{"board_key": "...", "sha256": "...", "size": 0, "url": "..."}],
  "apple_firmware_inputs": [{"board_key": "...", "source": "Apple source policy", "sha256": "..."}],
  "installer_app": {"bundle_sha256": "...", "source_revision": "..."},
  "signing": {"key_id": "...", "algorithm": "..."}
}
```

The exact cross-repository schemas remain owned by `omarchy-apple-platform`; the fields above describe installer obligations, not a competing schema authority. Verification order is: parse with resource limits; verify trust-root and signature; verify channel and expiry; verify manifest schema; fetch only allowlisted immutable URLs; verify every declared digest and length; resolve exact board and capability profile; then generate a plan. Failure at any point stops before privilege elevation or disk mutation.

Trust-root rotation follows `F-03`. The installer may contain a bootstrap root and signed successor keys, but it may not silently replace keys from a network response. Emergency revocation, offline root recovery, and expired-metadata behavior are explicit release tests.

## 6. Threat model and transaction boundary (I-01)

### 6.1 Assets to protect

The primary protected asset is the user's macOS data and bootability. Other protected assets are Apple internal/system partitions, unrelated APFS containers and volume groups, existing Linux installations, owner credentials and recovery material, board firmware integrity, boot-policy integrity, target encryption keys, release-signing keys, and accurate user-facing outcome state.

### 6.2 Threats and controls

| Threat | Control | Residual requiring evidence |
|---|---|---|
| Wrong or spoofed board admission | Exact multi-field board match against signed registry, then Linux-side recheck against the same record | Every supported board topology needs physical qualification; no family inference is sufficient. |
| CDN, redirect, mirror, or cache serves different bytes | Immutable URLs, allowlist, declared length, SHA-256, manifest signature, and Apple internal signature checks | Offline mirror and key-revocation drills. |
| Disk numbering changes between inventory and mutation | Stable identity tuple plus fresh precondition check before every operation | Apple tool output variations across OS versions need fixture coverage. |
| APFS snapshot or hidden volume causes under-sized resize | Apple resize limits plus conservative free-space proof and explicit snapshot evidence | Physical resize tests on representative macOS baselines. |
| User or process dies after a destructive call | Prepare/commit journal, postcondition classifier, replica recovery, and `RECOVERY_REQUIRED` on uncertainty | Power-cut tests during real disposable-machine calls. |
| A malicious or corrupted image overwrites active system | Signed image, inactive slot, target-ID proof, size/hash verification, and one-time switch | Boot-chain verification and board-specific image tests. |
| LocalPolicy is changed for macOS instead of Omarchy | Target VGID bound to approved plan; Apple tool called only for that VGID; postcondition checks both target and macOS policy | Per-board Apple security-state matrix. |
| Password or LUKS key leaks through process state | Apple UI authentication, stdin/secure prompt, no command-line secrets, redacted logs, memory zeroization best effort | Security review of native helper and crash dumps. |
| Uninstall removes unrelated Linux or Apple data | Ownership manifest, exact UUID set, boot-to-macOS proof, no heuristic matching, fresh pre-delete inventory | Destructive tests only on disposable lab machines. |
| UI says success after missing required component | Typed required/optional result, boot-health contract, manifest capability comparison | Full qualification remains outside this installer lane. |
| Installer telemetry becomes a tracking channel | Opt-in, minimal aggregate payload, no serial/UUID/password/partition detail, local preview, no transaction dependency | Owner decision on policy and retention. |

### 6.3 Owner and 1TR handoff

The user remains in one transaction even when Apple requires a reboot, owner authorization, or a continuous power-button gesture. The app explains why the transition is required, records a non-secret continuation token, and shows the exact plan hash and target label the user will see in the Apple boot picker.

The handoff sequence is:

1. Start unelevated in macOS, verify local console and machine-owner eligibility, and collect read-only inventory.
2. Show the complete plan, protected objects, storage changes, encryption choice, required Apple firmware input, recovery path, and rollback boundary. Require explicit owner approval of the plan hash.
3. Request Apple authorization through the supported owner-auth mechanism. Do not collect a password into installer state or pass it in an argument or environment variable.
4. Create only the minimum Apple stub and its paired RecoveryOS relationship required by the signed plan. Write the signed continuation descriptor to the Omarchy-owned control area and the Apple-visible handoff locations.
5. Set the target boot selection through the Apple-supported mechanism and ask the user to enter the target's paired RecoveryOS/1TR. The UI and CLI show state as `HANDOFF_PENDING`, not “installation complete.”
6. In 1TR, validate the continuation token, plan hash, target VGID, Preboot UUID, board identity, and owner-authorized target. If pairing or 1TR mode is wrong, do not mutate; return to a retry or recovery state.
7. Perform the Apple-required LocalPolicy and boot configuration operations for the target OS only. The macOS policy must be observed unchanged before the handoff is committed.
8. Hand off to the signed Omarchy live image. The live agent repeats board and target checks before touching Linux partitions.

The impossible-to-automate physical action is a first-class state with accessible instructions, a cancel/retry route, and no timeout that destroys data. A second Mac, a DFU cable, or Apple Configurator is never represented as already available.

## 7. Read-only inventory and plan generation (I-03)

### 7.1 Inventory contract

The macOS inventory phase may invoke read-only `ioreg`, `sysctl`, `scutil`, `nvram -p` with redaction, `bputil -d`, `diskutil list/info/apfs list/listVolumeGroups` in plist mode, and read-only filesystem metadata queries. It may not call `updatePreboot`, `addVolume`, `addPartition`, `resizeContainer`, `eraseVolume`, `bless --setBoot`, `kmutil configure-boot`, `bputil` mutation modes, `mount -u -w`, `newfs`, or a raw block-device writer.

Inventory must be repeatable and side-effect-free. If a platform command has undocumented side effects, it belongs in the mutation adapter and is prohibited during inventory until a test proves otherwise. The current repository's `check_cur_os` behavior that may call `diskutil apfs updatePreboot` is therefore not reusable in the read-only phase.

The inventory records only the minimum support and plan evidence:

```json
{
  "schema": "installer-inventory/v1",
  "observed_at": "RFC3339",
  "board": {"device_class": "...", "product_type": "...", "board_id": "...", "chip_id": "...", "firmware": "..."},
  "macos": {"version": "...", "build": "...", "boot_mode": "...", "filevault": "unknown|on|off"},
  "disk": {"stable_id": "...", "internal": true, "size": 0, "gpt_digest": "..."},
  "apfs": {"containers": [], "volume_groups": [], "volumes": []},
  "protected_ids": [],
  "candidate_free_ranges": [],
  "power": {"ac": true, "battery_percent": null},
  "network": {"ready": true},
  "source_versions": {"diskutil": "...", "bputil": "..."}
}
```

Sensitive values such as serial numbers, full NVRAM, user names, recovery tokens, and encryption material are not in the portable inventory. A local diagnostic log may retain a redacted evidence reference, never a secret.

### 7.2 Stable identifiers

Stable IDs are typed structures, not strings passed through from UI input.

| Object | Required identity fields | Revalidation rule |
|---|---|---|
| Physical whole disk | IORegistry media path, whole-disk GUID/UUID where available, internal/virtual/writable flags, capacity, and a GPT-structure digest | Resolve a fresh whole-disk object and require the identity tuple to match; capacity changes or path-only matches fail. |
| GPT partition | GPT partition UUID/PARTUUID, type GUID, start offset, size, parent whole-disk stable ID | Resolve by UUID on the same parent disk; require type, offset, and allowed size delta; never resolve by `diskN`. |
| APFS container | APFS container UUID, designated physical-store partition UUID, role/type, current capacity and free space | Resolve by container UUID and physical-store UUID; reject a changed store or duplicate UUID. |
| APFS volume | APFS volume UUID, container UUID, role set, name for display only, and mount state | Resolve by volume UUID and role; label changes do not make an object equivalent. |
| APFS volume group | Volume-group UUID, System/Data/Preboot/Recovery volume UUIDs, container UUID | Require exact role map and target pairing; duplicate or missing roles fail closed. |
| Apple RecoveryOS/Preboot relationship | Target VGID, target Recovery volume UUID, target Preboot volume UUID, paired-build evidence | Re-read `bputil` and APFS roles in 1TR; do not accept a label or boot-picker position. |
| Omarchy boot slot | ESP partition UUID, slot name `A` or `B`, manifest digest, root UUID, state marker digest | Slot writes are allowed only to inactive state recorded by fresh boot metadata. |
| Linux root/encryption target | GPT partition UUID, LUKS2 UUID, Btrfs filesystem UUID, subvolume/slot ID | Require the expected creation lineage and format digest before write, update, or delete. |

If Apple does not expose one field on a board or macOS baseline, the signed board-specific inventory adapter must define an equivalent stable tuple before that board is installable. “The field is absent” is not permission to fall back to a device number.

### 7.3 Plan structure

`installer-plan/v1` contains the signed manifest digests, exact board record, complete inventory digest, owner-visible choices, protected IDs, target IDs, ordered mutation operations, expected pre/postconditions, rollback classification, Apple handoff requirements, encryption mode, live image digest, and journal replica locations.

Before approval, render the plan in both the app and CLI with:

- Exact board key and support state.
- macOS and Apple firmware baseline, including why the selected Apple input is required.
- Current protected containers and volume groups.
- Every new or resized object with stable ID, type, offset/range, and size.
- Every object that will be written, reformatted, resized, or deleted.
- Encryption mode and the fact that the macOS container is not being encrypted or reformatted.
- Live image and platform-manifest digests.
- 1TR/owner steps, expected reboot count, rollback boundary, uninstall path, and DFU escalation.
- A statement that this is a plan pending owner approval, not a success result.

Plan generation is pure over fixture input. It must produce the same canonical plan bytes for the same signed inputs and choices. Any difference in fresh inventory after approval invalidates the plan and requires regeneration; it is not silently patched.

## 8. Mutation plan and destructive-operation proofs (I-04)

The transaction engine executes a fixed operation graph emitted by the plan. A UI may choose among plan options, but it cannot add an unplanned operation at runtime.

| Operation | Durable intent | Required proof before call | Required proof after call | Uncertain result |
|---|---|---|---|---|
| `reserve_transaction` | Record plan and protected-object set | Signed plan valid; no active transaction on the same disk | Journal replicas exist and match header | Stop and require manual cleanup of metadata only. |
| `resize_macos_container` | Move the macOS APFS container boundary to a declared size | Exact container UUID/store UUID, current capacity/free limits, no protected overlap, Apple minimum size, owner approval | Same container UUID/roles; new size within exact requested result; all protected IDs unchanged | Do not retry blindly; re-inventory and enter `RECOVERY_REQUIRED` if neither old nor expected state matches. |
| `create_stub_partition` | Create one new GPT partition in the approved free range | Fresh free range, parent disk ID, expected type/size/adjacency, no Apple internal target | New partition UUID recorded; type, range, size, and parent match | Do not erase or search by label; classify from fresh GPT. |
| `create_stub_apfs` | Format only the newly-created partition as the Apple stub container | New partition UUID from this transaction; not mounted as a protected volume | New APFS container UUID and role map match the signed recipe | Leave target quarantined and recover through Apple tools; never format a different partition. |
| `stage_apple_stub_and_recovery` | Populate System/Data/Preboot/RecoveryOS handoff material | Apple input digest and BuildIdentity match board/chip/device; target VGID exact; staging path inside new container | File digests, roles, paired RecoveryOS evidence, and control descriptor match | Remove only files proven staged by this transaction, or enter recovery if pairing is ambiguous. |
| `authorize_localpolicy` | Authorize the target OS in Apple policy | 1TR mode, target VGID, owner prompt, target-only policy diff | `bputil -d` shows intended target state and unchanged macOS policy | Stop; do not attempt a guessed inverse policy operation. |
| `create_esp_and_linux_partitions` | Create the signed layout's ESP, encrypted root, and optional state/data partitions | New/free partition IDs and exact range proofs; signed layout; no overlap | GPT IDs/types/sizes and ownership manifest match | Quarantine partial new objects; no heuristic wipe. |
| `format_luks_and_btrfs` | Initialize encryption and inactive root slots | New target UUID, user-selected encryption mode, passphrase prompt, sufficient size | LUKS2 UUID/metadata and Btrfs UUID/subvolume layout match; unlock test passes | Preserve encrypted bytes; ask for recovery key/passphrase and escalate if key state is uncertain. |
| `write_inactive_slot` | Write live image and boot bundle to inactive slot | Active slot read; target slot inactive; image and bundle digests valid; exact byte/range proof | Read-back digest, file metadata, signed slot manifest, and root mount check | Keep active slot; mark pending write invalid and retry only with the same digest. |
| `set_pending_slot` | Ask the boot chain to try the new tuple | Slot manifest verified; last-known-good slot exists; boot policy target exact | Pending marker and attempt budget read back; macOS fallback preserved | Clear only the pending marker if ownership is proven; otherwise return to recovery. |
| `mark_boot_success` | Promote a slot after first-boot health | Board ID, manifest SHA, slot, required health checks, and no fatal logs match | `boot-health/v1` success record is durable and prior good slot retained | Leave slot pending/failing; bootloader fallback remains authoritative. |
| `uninstall_owned_objects` | Remove Omarchy objects and optionally return free space | Booted macOS or its paired recovery; owner approval; all IDs prove Omarchy ownership; macOS default boot set and verified | Omarchy objects absent, macOS boots, free-space result matches Apple tool | Stop before delete if any ID or boot result is uncertain. |

### 8.1 Destructive-operation proof algorithm

Before any operation classified as destructive, the engine computes:

```text
protected_before = canonical(protected object IDs and structural facts)
target_before = canonical(target object IDs and structural facts)
intent = canonical(operation, plan hash, target IDs, expected result)
```

It refuses the call unless the operation's target set is a subset of the plan-owned set, the target set is disjoint from the protected set, the numeric byte ranges do not overlap a protected range, and the fresh observation digest equals the plan's allowed precondition. The adapter receives a typed object, not a user path. After the call it obtains a fresh observation and checks the operation-specific postcondition plus `protected_after == protected_before` for every field that the operation was not explicitly allowed to change.

The proof is intentionally conservative around APFS resize. If the Apple operation reports an error or power is lost while the boundary is moving, the engine does not infer success from a partial message. It re-observes the container and either commits the exact expected boundary, retries an idempotent Apple operation with the same proof, or transitions to recovery. It never deletes or reformats the macOS container as a “cleanup.”

## 9. Journal, crash points, and resume derivation (I-04)

### 9.1 Journal format and replicas

Use canonical JSON Lines for inspectability, with UTF-8, sorted keys, no floating-point values, and a hash chain. A future schema may use canonical CBOR only if it retains the same record semantics and offline tooling. The first record is a signed plan header; every later record includes `prev_record_sha256` and its own `record_sha256`.

```json
{
  "schema": "installer-transaction/v1",
  "txn_id": "uuid",
  "seq": 17,
  "op_id": "write_inactive_slot",
  "phase": "prepare|commit|abort|recovery",
  "plan_sha256": "...",
  "manifest_sha256": "...",
  "target_ids": ["typed stable IDs"],
  "precondition_sha256": "...",
  "expected_postcondition_sha256": "...",
  "observed_postcondition_sha256": "...",
  "result": "...",
  "prev_record_sha256": "...",
  "record_sha256": "..."
}
```

The journal contains no password, passphrase, recovery key, bearer token, raw NVRAM, serial number, or full device path. Timestamps aid support but do not determine ordering; `seq` and the hash chain do.

During macOS execution, store replicas in the user's Application Support transaction directory and in the Omarchy-owned control area after it exists. During stub/1TR/live execution, store the signed plan and journal replica in the stub's protected handoff area and the Omarchy ESP control path. Each write is followed by flush, file sync, directory sync where supported, and a read-back hash. Replica contents are evidence, not authority; a valid signed plan and fresh hardware observation remain required.

### 9.2 Resume derivation

On every launch, reboot, or live-image start:

1. Parse each replica until the first invalid, torn, or hash-mismatched record; ignore only the invalid suffix and retain its evidence for diagnostics.
2. Require identical signed headers and find the highest common hash-chain prefix. If replicas diverge before the common prefix, enter `RECOVERY_REQUIRED`; do not pick the longer file.
3. Read a fresh typed inventory and boot-policy observation. Do not trust cached `/dev` names, labels, or UI state.
4. For each `prepare` without a `commit`, run the operation's classifier: expected postcondition means append a recovery `commit`; original precondition means replay the same idempotent operation; any other state means append `recovery` and stop.
5. Derive the next operation from the fixed plan graph and the highest committed sequence. A record cannot skip an operation, authorize an unplanned operation, or choose an alternate artifact.
6. If the current board, manifest, disk identity, protected set, or plan hash differs, invalidate the transaction and show a recovery report. A changed machine is never “resumed” by editing the plan.

### 9.3 State-transition table

| State | Entry evidence | Allowed next states | Crash/restart rule |
|---|---|---|---|
| `NEW` | No transaction header | `INVENTORY_READY`, `ABORTED` | Start read-only; no mutation. |
| `INVENTORY_READY` | Valid signed manifest and typed inventory | `PLAN_READY`, `ABORTED` | Re-run inventory; no journal authority yet. |
| `PLAN_READY` | Canonical plan and destructive proofs rendered | `APPROVED`, `ABORTED` | Approval is required again if plan bytes change. |
| `APPROVED` | Owner approval bound to plan hash | `JOURNALED`, `ABORTED` | Approval token expires; no secret persisted. |
| `JOURNALED` | Header and replicas durable | `RESIZING`, `STUB_CREATING`, `RECOVERY_REQUIRED` | Re-derive from fresh observation. |
| `RESIZING` | Resize prepare record | `STUB_CREATING`, `RECOVERY_REQUIRED` | Commit only exact expected boundary; never guess. |
| `STUB_CREATING` | New-object prepare records | `APPLE_STUB_READY`, `RECOVERY_REQUIRED` | Existing new UUIDs may be adopted only if exact postconditions match. |
| `APPLE_STUB_READY` | Stub, Preboot, RecoveryOS, and handoff descriptor verified | `OWNER_HANDOFF_PENDING`, `RECOVERY_REQUIRED` | Resume from target IDs; no duplicate container creation. |
| `OWNER_HANDOFF_PENDING` | Target boot selection and visible instructions | `IN_1TR`, `ABORTED`, `RECOVERY_REQUIRED` | Reboot may be repeated; target is not complete. |
| `IN_1TR` | Paired target RecoveryOS and 1TR evidence | `LOCALPOLICY_READY`, `RECOVERY_REQUIRED` | Wrong RecoveryOS/1TR returns to handoff, without mutation. |
| `LOCALPOLICY_READY` | Target-only policy proof | `LIVE_HANDOFF_PENDING`, `RECOVERY_REQUIRED` | Re-read policy and plan before continuing. |
| `LIVE_HANDOFF_PENDING` | Signed live-image descriptor in ESP | `LIVE_RUNNING`, `RECOVERY_REQUIRED` | Existing image must pass digest check; otherwise keep Apple fallback. |
| `LIVE_RUNNING` | Board and target recheck passed | `LAYOUT_READY`, `RECOVERY_REQUIRED` | Live image reconstructs state from journal and disk. |
| `LAYOUT_READY` | LUKS/Btrfs/ESP layout and ownership proof | `IMAGE_STAGED`, `RECOVERY_REQUIRED` | Resume formatting only for exact new UUIDs; uncertain key state stops. |
| `IMAGE_STAGED` | Inactive slot read-back digest verified | `PENDING_BOOT`, `RECOVERY_REQUIRED` | Never overwrite active slot; retry same digest or stop. |
| `PENDING_BOOT` | Pending marker and attempt budget durable | `FIRST_BOOT_PENDING`, `ROLLBACK_REQUIRED` | Boot failure leaves last-known-good slot selected. |
| `FIRST_BOOT_PENDING` | New slot selected | `HEALTH_CHECKING`, `ROLLBACK_REQUIRED` | Boot-health agent increments attempts and falls back at threshold. |
| `HEALTH_CHECKING` | Exact board/manifest/slot health evidence | `SUCCESS`, `ROLLBACK_REQUIRED` | No success marker on partial health. |
| `ROLLBACK_REQUIRED` | Failed boot or required check | `ROLLED_BACK`, `RECOVERY_REQUIRED` | Bootloader selects last-known-good; installer reports residuals. |
| `SUCCESS` | Durable `boot-health/v1` success | `UNINSTALL_PENDING`, `UPDATE_PENDING`, `SUCCESS` | A later update starts a new transaction; history is retained. |
| `UNINSTALL_PENDING` | Owned-target plan and macOS boot proof | `UNINSTALLED`, `RECOVERY_REQUIRED` | Delete only after final pre-delete revalidation. |
| `UNINSTALLED` | Owned objects absent and macOS recovery/boot verified | `NEW` | A new install requires a new inventory and transaction. |
| `RECOVERY_REQUIRED` | Ambiguity or unsupported external state | `ABORTED`, `NEW` after human recovery | No automatic destructive retry. |

### 9.4 Crash-point table

| Crash point | Possible disk state | Resume decision |
|---|---|---|
| Before any prepare record | No mutation | Re-run inventory. |
| After prepare, before Apple tool starts | Original precondition | Replay only the same idempotent operation after fresh proof. |
| During network fetch | Partial cache | Discard unverified tail; resume only verified content-addressed chunks. |
| After file staging, before hash/read-back | Partial file | Delete or replace only the staged file in the owned staging path, then verify full digest. |
| During APFS resize | Old, exact new, or unknown boundary | Freshly classify; commit exact new, retry only an Apple-supported idempotent call, or require recovery. |
| After new partition creation, before UUID commit | New partition may exist | Adopt only if UUID/type/range match the prepared proof; otherwise do not touch it. |
| After stub files, before handoff marker | Partial stub | Complete only declared files or clean only proven new files; no boot switch. |
| After boot selection, before reboot | Target pending | Restore macOS selection only if the target policy/boot change is proven and the owner approves; otherwise enter recovery. |
| In 1TR after LocalPolicy call | Policy may be changed | Re-read target and macOS policy; do not repeat blindly. |
| During LUKS initialization | Key metadata may be partial | Never erase or reinitialize automatically; require exact LUKS probe and user key/recovery path. |
| During inactive-slot write | Slot partial; active slot intact | Mark pending invalid, rewrite the inactive slot from the same verified digest, or stop. |
| After pending marker, before first boot | New slot pending | Bootloader attempt budget protects last-known-good; installer remains `FIRST_BOOT_PENDING`. |
| After failed boot health | New slot may be bootable but unqualified | Fallback and preserve evidence; never mark success. |
| During uninstall deletion | Some owned objects may be absent | Re-inventory ownership set; delete only exact remaining owned IDs, or stop. |

## 10. Apple firmware, stub OS, RecoveryOS, and LocalPolicy (I-04)

### 10.1 Apple firmware provenance

The installer does not select Apple firmware from a static table, environment variable, or latest available URL. The signed installer manifest names the acceptable Apple input policy for the exact board and firmware schema. Retrieval records:

- Apple source URL, original URL, redirect chain, HTTP response metadata needed for reproducibility, and retrieval timestamp.
- Whole-input length and SHA-256.
- Apple image type, version/build, `RestoreVersion`, `BuildManifest`, variant, restore behavior, `ApBoardID`, `ApChipID`, and device class.
- Apple signature/trust validation result and the tool/version used to validate it.
- Exact extracted file paths, lengths, SHA-256 values, and the Omarchy manifest reference that requested each file.
- Whether the input was fetched directly to the user's Mac or came from an Omarchy-controlled cache, plus the cache artifact digest.

The build identity must match all relevant board/chip/device fields and the selected restore/update behavior. An Apple signature proves Apple origin; it does not prove that the artifact is an Omarchy-qualified release. Conversely, an Omarchy signature does not replace Apple validation.

The default privacy and legal posture is direct fetch from Apple and no redistribution of Apple IPSW/OTA payloads. A release owner must rule on cache and redistribution terms before I-02 ships an artifact service.

### 10.2 Stub OS and RecoveryOS

Use Apple-supported APFS operations to create a new container and the System/Data/Preboot/Recovery roles required for the target stub. The stub contains only the Apple-signed and manifest-declared materials required to appear in the boot picker, enter the paired RecoveryOS, and execute the continuation. It is not presented as a complete macOS installation.

The provisioning adapter must verify volume-group roles and UUIDs after every role creation. It writes files through an owned staging directory, fsyncs, verifies hashes, and atomically renames where the filesystem permits. It must preserve Apple metadata required by the boot process without storing owner passwords, installer secrets, or recovery keys.

The current repository's `SystemVersion.plist` hiding, `.IAPhysicalMedia` staging, RestoreBundle extraction, and `Finish Installation.app` are migration references only. The new continuation must have a typed state and plan hash, and must never display “Installation successful” before first-boot health.

### 10.3 LocalPolicy and owner authorization

LocalPolicy changes are per-target OS operations. The UI names the target volume group and states that macOS policy is expected to remain unchanged. The adapter uses only the Apple-supported owner-authenticated path available on the exact macOS/RecoveryOS baseline; it never disables security globally, passes credentials on a command line, or treats a successful command exit as sufficient.

Postcondition evidence includes target policy state, macOS policy state, target VGID, policy/build identifiers, and plan hash. If Apple presents a UI or recovery interaction not observable by the adapter, the state remains pending until a supported read-back confirms the intended target state.

## 11. Omarchy ARM live image and encrypted layout (I-05)

### 11.1 Live image contract

`omarchy-live-arm64` is a release artifact produced by the platform build/provenance pipeline. It is selected by exact board key, firmware schema, platform manifest digest, and live-image digest. The installer does not choose a generic ARM image based on `arm64`.

The image contains a minimal signed installer agent, the generated schema validators, the plan hash, the pinned platform manifest, board policy, boot-slot writer, encryption tools, diagnostics, accessibility fallback, and a recovery client. It must boot without network after its required artifacts are staged. Network is used only for fetching declared, digest-verified content.

The live agent's first actions are read-only: verify the signed continuation, re-read board identity, re-read disk/APFS/GPT IDs, compare the macOS-side plan digest and protected set, and confirm the target is the expected inactive/new object. It refuses to write if any identity or artifact differs.

Image writes use a verified stream or verified temporary file with declared length, chunk digests, final SHA-256, fsync, and read-back. A short write, disk-full result, decompression error, or filesystem error leaves the active/last-known-good slot untouched and produces a typed failure.

### 11.2 Proposed encrypted layout

The exact partition sizes and types are signed by the platform manifest and rendered in the plan. The logical design is:

```text
Apple GPT/APFS objects (existing and protected)
Omarchy-owned Apple stub APFS container
Omarchy-owned ESP
Omarchy-owned encrypted LUKS2 root partition
  Btrfs @slot-a
  Btrfs @slot-b
  Btrfs @state (only if the signed layout requires mutable state)
```

Boot artifacts are outside root snapshots and versioned in the ESP under a manifest-bound slot directory. The encrypted root uses separate immutable or replaceable slot subvolumes/images; updates never mutate the active root in place. Mutable state is explicitly separated and is not allowed to alter the boot tuple.

Encryption choices are shown before mutation:

- Unencrypted mode creates no LUKS metadata and is clearly labeled.
- Encrypted mode initializes LUKS2 only on the new Omarchy-owned target, never on macOS or Apple internal partitions.
- The passphrase is entered in the live UI, never in the plan or journal. The live agent verifies unlock before continuing and clears input buffers as far as the implementation permits.
- An optional recovery key is generated locally and shown once for the user to save. It is not uploaded, logged, placed on the ESP, or stored in an unencrypted journal. The installer does not claim SEP-backed Linux unlock unless a separate qualified contract proves it.
- If the user cannot confirm the recovery material, the transaction pauses before writing the boot switch and offers a safe abort for the new target.

## 12. Inactive boot slots and success marking (I-05)

Each installation has a last-known-good slot and a pending slot. Initial installation chooses an empty slot as pending while preserving any existing Omarchy slot if one exists. Updates write the inactive slot, verify the complete platform tuple, write a pending record with an attempt budget, and switch once.

The slot manifest includes slot name, ESP UUID, root UUID/LUKS UUID/Btrfs UUID, platform manifest SHA-256, board key, firmware schema, boot bundle digests, root image digest, and state `empty|staged|pending|good|failed`. The pending record is separate from the active boot artifacts and is atomically replaced.

The boot-health agent marks success only after:

- The running board identity exactly matches the planned board key.
- The selected slot, platform manifest, boot bundle, kernel/initramfs, firmware, and root digests match the pending record.
- The encrypted root was unlocked if encryption was selected.
- The base boot-health checks pass: storage, root integrity, initramfs, essential services, display/session startup, and no fatal kernel or boot-policy error.
- Required board-profile checks for the install stage pass, with any optional or not-yet-qualified capability reported as a typed result rather than silently omitted.
- A durable `boot-health/v1` record is written only after all required checks and the previous good slot reference remain available.

Failure increments the attempt count and selects the last-known-good slot at the boot boundary. A successful systemd start, desktop screenshot, or “installer ran” message is not the success marker. Full board capability qualification remains a separate physical test and ledger decision.

## 13. Uninstall, rollback, and DFU recovery (I-06)

### 13.1 Rollback matrix

| Failure location | Automatic behavior | User-visible result |
|---|---|---|
| Before APFS resize | Abort with no target mutation | Plan remains available for retry after inventory. |
| Resize uncertain | Re-inventory only; no destructive cleanup | “Apple storage state needs recovery review”; preserve macOS and require Apple First Aid/manual decision. |
| New stub incomplete | Remove only files/objects proven new and owned, or preserve for repair | Stub is labeled incomplete; macOS remains the selected fallback. |
| LocalPolicy or 1TR handoff failure | Return to macOS or target handoff retry without changing unrelated policy | Exact target and required user action are shown. |
| Live-image or layout failure | Keep Apple boot path and any last-known-good Omarchy slot; quarantine new objects | No success; offer repair or uninstall of proven new objects. |
| Inactive image write failure | Invalidate pending slot; active/last-good slot remains | Retry same digest or stop. |
| First boot health failure | Bootloader fallback after attempt budget | New slot remains failed for diagnostics; prior slot remains selectable. |
| Update failure after switch | Automatic last-known-good selection | One atomic tuple is retained; no package-by-package repair claim. |
| Uninstall failure | Stop before the next delete, preserve remaining owned objects | Show exact residual IDs and a recovery path. |

Rollback is not an assertion that every Apple/APFS operation is reversible. Where an Apple tool may have partially completed a boundary operation, the only safe automatic action is observation and classification. A failed inverse operation is not attempted just because the UI needs a comforting result.

### 13.2 Uninstall proof and flow

Uninstall begins from macOS or its paired RecoveryOS, never from an active Omarchy root unless it has a separate recovery path. It performs a read-only inventory and renders:

- The Omarchy transaction ID, release and manifest digests, and exact owned GPT/APFS/LUKS/Btrfs/ESP IDs.
- The macOS volume that will remain and the Apple boot-policy change required.
- Any shared ESP or shared container that is not deletable.
- Whether free space will remain free or be returned to an adjacent macOS container through an Apple-supported resize.

The ownership proof requires the target UUIDs to be the IDs created by the install transaction and the target control manifest to contain matching signed plan and ownership digests. A name containing “Omarchy,” an EFI directory name, a 2.5 GB size, or a Linux filesystem type is not proof. Pre-existing or ambiguous Linux objects are never deleted by this tool.

After owner approval, the engine first sets and verifies macOS as the default boot target, verifies the target is not the only recovery path, and only then deletes exact owned objects. It uses Apple-supported APFS/GPT operations and re-inventories after each delete. It may return free space only as a separately approved final operation. The heuristic `tools/wipe-linux.sh` is not part of the uninstall path.

### 13.3 DFU recovery runbook boundary

The installer provides a board-specific, versioned DFU runbook reference and a printable offline copy. It must not claim to repair Apple firmware from Linux or automate an unverified DFU sequence. The runbook includes:

1. Stop the transaction and record the last valid journal sequence, plan hash, board identity, and protected-object inventory.
2. Preserve the user's data and do not erase a disk while the recovery result is unknown.
3. Use a second Mac, an Apple-supported recovery application, the exact board-specific cable/port and physical sequence from the qualified runbook, and an Apple-authorized IPSW/recovery source.
4. Restore Apple firmware/RecoveryOS using the Apple process, then verify macOS boot, owner account, APFS container IDs, and LocalPolicy state.
5. Re-run a read-only installer inventory. Any Omarchy objects whose ownership proof remains exact may be repaired or uninstalled; ambiguous objects require human review.
6. Attach DFU evidence, Apple tool versions, source digests, and physical board details to the incident record. Do not mark the install recovered from a UI result alone.

Model-specific cable/port/button sequences and Apple software redistribution are deferrals to the hardware-lab and release owners. They must be filled from physical rehearsal before I-06 can be accepted.

## 14. Accessibility and privacy

### 14.1 Accessibility contract

The app must work with VoiceOver and keyboard navigation from launch through plan approval, owner handoff, encryption prompt, reboot instructions, failure, uninstall, and recovery. Every destructive control has a programmatic label, a text explanation, a plan hash, and a clear current/next state. Color is never the only state signal.

The CLI exposes the same plan, preconditions, progress states, failure codes, and recovery instructions as the GUI. It supports non-interactive read-only output for screen readers and logs progress as structured events rather than terminal cursor rewrites. Physical instructions use explicit numbered steps, no timing-dependent hidden action, and a retry/cancel path. The UI does not auto-dismiss an error, hide a required reboot, or treat an inaccessible Apple dialog as success.

Text size, contrast, reduced motion, VoiceOver focus order, and localization of security/destructive language are acceptance tests. RecoveryOS limitations require a text/CLI fallback and an offline printable handoff.

### 14.2 Privacy contract

The installer is offline-capable and telemetry-independent. Reporting is opt-in after the transaction reaches a typed result. The user sees the exact payload before sending it; failure to report never changes install, rollback, or uninstall outcome.

Allowed aggregate fields are release ID, board registry key at the least identifying granularity approved by the owner, manifest digest, typed outcome, and coarse failure code. Never send serials, disk UUIDs, partition sizes, exact free space, usernames, NVRAM, passwords, owner tokens, LocalPolicy data, LUKS metadata, recovery keys, raw logs, or source paths. A support bundle is explicit, local-first, redacted, and user-selected; its manifest lists every included file and hash.

Local logs use stable transaction IDs rather than device identifiers, redact subprocess output by default, and separate human-readable messages from structured evidence. The report server, analytics dashboard, and HTTP response are not transaction authorities.

## 15. Fixtures, fault injection, and acceptance tests

The installer test suite must remain pure and runnable without a real disk by default. Real destructive calls are allowed only on disposable lab machines with rehearsed DFU recovery and an operator-confirmed target certificate.

### 15.1 Required fixtures

| Fixture family | Cases |
|---|---|
| Board registry | Exact supported board records; same SoC with different product boards; unknown board; malformed record; expired registry; valid board with non-installable lifecycle; firmware-schema mismatch. |
| macOS inventory | Current macOS boot; ordinary RecoveryOS; paired 1TR; wrong RecoveryOS; no local console; non-owner user; stale Preboot; FileVault; missing or duplicate volume roles; old and new Apple tool output variants. |
| GPT/APFS | Pristine internal disk; free range after macOS; APFS snapshots; Time Machine snapshots; minimum-free-space boundary; multiple APFS containers; Apple internal/ISC partitions; external USB; virtual disk; duplicate/missing UUID; moved disk numbering; pre-existing unrelated Linux and ESP. |
| Plan generation | Same fixture determinism; user size/encryption choices; minimum and maximum boundaries; overlap attempts; protected-object mutation attempts; stale inventory after approval; changed capacity; unsigned or changed manifest. |
| Apple image | Valid IPSW/OTA fixture; bad whole-image digest; bad Apple signature; wrong board/chip/device class; wrong restore behavior/variant; missing declared path; duplicate path; malicious archive traversal; truncated compressed data; unsupported build. |
| Journal | Valid complete transaction; torn final record; invalid hash suffix; missing replica; divergent replicas; prepared-before-call; prepared-after-call; changed plan hash; changed stable ID; unknown operation; duplicate sequence; disk-full during journal fsync. |
| Live image and encryption | Valid signed image; mismatched digest; wrong board image; short write; disk-full; interrupted decompression; new LUKS2 target; wrong passphrase; missing recovery confirmation; uncertain LUKS metadata; Btrfs slot mismatch. |
| Boot health | Pass; kernel/initramfs mismatch; wrong board; required service absent; required capability absent; fatal kernel log; pending-attempt exhaustion; success marker write failure; previous good slot missing. |
| Uninstall and DFU | Exact owned target; label-only false positive; shared ESP; pre-existing Linux; active target; changed owner policy; missing macOS fallback; partial deletion; Apple recovery required; runbook unavailable/offline. |

### 15.2 Required tests

- Pure planning tests over versioned plist/JSON fixtures, including canonical output and explicit protected-object sets.
- Property tests proving no generated plan mutates an object outside its owned target set and that no raw path or mutable input can reach a destructive adapter.
- Adapter tests asserting inventory commands are read-only and mutation commands receive stable typed IDs plus an expected precondition digest.
- Restart-after-every-step tests, including before and after every prepare/commit boundary and every simulated reboot into macOS, 1TR, and the live image.
- Fault injection for network loss, redirects, stale metadata, bad signatures, wrong board, process death, power loss, disk-full, partial writes, malformed Apple archives, wrong encryption key, and journal divergence.
- Slot tests proving active/last-known-good data is unchanged while the inactive slot is staged, and proving attempt exhaustion selects the prior good slot.
- Accessibility tests with VoiceOver/keyboard/contrast/reduced-motion fixtures and GUI/CLI parity checks.
- Privacy tests that inject secrets and device identifiers into subprocess output and assert they are absent from journals, logs, telemetry previews, and support bundles.
- License/provenance tests that fail a release when a copied module lacks SPDX/notice metadata, a third-party source digest is missing, or an Apple asset lacks source/signature evidence.
- Destructive tests only on disposable Apple-capable lab targets with an attached recovery certificate and a practiced DFU path. A VM, compile, image extraction, or fake disk test can validate lower gates but can never produce a physical qualification record.

### 15.3 Acceptance evidence for I-01 through I-06

| Slice | Evidence required before coordinator review |
|---|---|
| I-01 | Threat model, authority/non-authority list, state graph, crash table, target proof rules, and ruling log. |
| I-02 | Signed/notarized app/CLI prototype, immutable manifest verification tests, trust-root rotation/revocation fixtures, SBOM, license inventory, and no mutable release path. |
| I-03 | Read-only inventory implementation, fixture corpus, deterministic plans, stable-ID resolver tests, and proof that inventory produces no mutating subprocess calls. |
| I-04 | Apple adapter tests on each declared macOS/RecoveryOS baseline, stub/Preboot/RecoveryOS pairing evidence, LocalPolicy target-only tests, journal/resume tests, and power-loss evidence. |
| I-05 | Signed live-image provenance, offline boot test, board recheck, encrypted/unencrypted layout tests, inactive-slot write/read-back tests, and boot-health contract evidence. |
| I-06 | Rollback/update/uninstall tests, exact ownership proof tests, disposable-machine destructive rehearsal, board-specific DFU runbook rehearsal, accessibility/privacy evidence, and residual/failure census. |

## 16. Deferrals and ruling questions

These questions must be answered by the named owner before implementation hardens an interface. They are not assumptions hidden behind this design.

1. Which exact Omarchy organization keys, threshold rules, expiry window, revocation path, and offline recovery process from F-03 does the installer embed?
2. What exact generated schemas and versioning rules will `omarchy-apple-platform` publish for `board-registry/v1`, `platform-manifest/v1`, `installer-plan/v1`, and `boot-health/v1`?
3. Which Apple-supported authorization API and helper lifecycle is approved for current and future macOS versions, and how will owner identity be proven without retaining a password?
4. Which Apple tool/version matrix is supported for APFS resize, stub creation, RecoveryOS pairing, `bputil`, `bless`, and `kmutil`, and which tool behavior is considered read-only?
5. What exact stable disk identity tuple is available on every supported Apple board and macOS baseline when serials are unavailable or must be redacted?
6. Is the target Linux layout one encrypted partition with Btrfs slots, separate root partitions, or another manifest-defined scheme? Which boot artifacts are outside root snapshots, and what is the bootloader-readable slot contract?
7. What is the human-approved m1n1 artifact contract? This lane requires only a signed input digest/interface; the fenced repository remains human-only and opaque.
8. What is the exact U-Boot/boot-health handoff for pending, attempt, success, failure, and fallback records, and who owns the implementation of those records?
9. May Apple IPSW/OTA bytes be cached or redistributed by Omarchy, or must every user fetch from Apple? What legal notices and retention rules apply to extracted firmware?
10. What is the owner-approved telemetry default, retention period, endpoint trust model, and data-subject deletion path?
11. Which boards have a qualified per-board DFU runbook, and what second-Mac/Apple Configurator version is the lab prepared to support?
12. Which capabilities are required for installer boot-health versus only for FULL physical qualification, and how are optional, unsupported, and not-tested outcomes represented?
13. What is the policy for an existing Asahi installation created by an older installer with no cryptographic ownership manifest? Default proposal: inspect and offer no automatic delete; require explicit human recovery/uninstall instructions.
14. What is the policy when macOS/APFS has already changed after a crash but the journal cannot prove whether the Apple operation completed? Default proposal: preserve data, stop, and require Apple/manual recovery rather than speculative inverse operations.

## 17. Design completion boundary

This design is ready for coordinator review when the document has an owner ruling for every question that materially changes the mutation graph, the generated canonical schemas exist, and the implementation plan preserves the invariants above. It is not ready to authorize an install merely because the Python prototype builds, an app is notarized, a board is recognized, a live image boots, or a focused test passes.

The coordinator remains the sole authority for integration and DONE. This lane reports only design evidence, changed-file census, gate results, failures, deferrals, and residual risk.
