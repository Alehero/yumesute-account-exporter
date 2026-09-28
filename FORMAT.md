# Export format v1

A ZIP with an exact file allowlist: `manifest.json`, `user-data.response.bin`, and optional `account-bridge.json`. Paths are flat. Importers must reject duplicate/path-traversal entries, excessive expanded sizes, unknown format versions, hash mismatches, account identity mismatches, and unsuccessful response envelopes. Read entries directly; do not blindly extract archives.

Manifest identity: `format = "yumesute-account-export"`, `format_version = 1`. `snapshot_sha256` covers the raw binary response body. `entity_counts_by_id` retains protocol numeric union IDs so new/unknown types can be preserved without forcing an older model schema. `summary` is a small human-readable subset. `user_id` must match the sole type-0 User record. The full response includes null records and is preserved unchanged.

The response is five consecutive MessagePack objects: faults, result, changed/present entities, deleted entities, notifications. Compression uses MessagePack-CSharp LZ4 extensions 98 (block array) or 99 (single block). A valid account response has an empty/null fault and a result array containing `[union_id, fields]` records (plus possible nulls). Field order, integer precision, and timestamp extension types must be preserved.

The optional bridge is `{ "user_id": <integer>, "token_sha256": "<64 lowercase hexadecimal characters>" }`. It is included only if the exact session making the user-data request matches an observed successful Authenticate response. It is not a login credential for the official service, and no raw official login token is stored. A future local-server importer can match incoming installation login tokens by hash, or use a separate account-binding mechanism if the bridge is absent.

Compatibility: `user-data.response.bin` is the same input payload used by this project's development account importer. No reconstruction from a lossy JSON conversion is needed. A release importer still needs to validate supported models, preserve unknown records, import transactionally into an empty account, and avoid overwriting existing progress. The development importer is not shipped in this capture-only repository.

Scope: the complete result of `/api/data/user` is preserved. Data fetched solely by other endpoints (for example some social/server-side history), game assets, and future changes made after this snapshot are outside this format's guarantee. The optional bridge does not replace the need to preserve the installed game and its assets.
