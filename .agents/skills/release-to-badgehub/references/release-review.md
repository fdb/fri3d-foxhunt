# BadgeHub release review

Use this checklist as prompts for judgment. Record evidence, not merely checked boxes.

## Package and metadata

- Confirm manifest `fullname` equals the app directory and archive top-level directory.
- Confirm the semantic version is intentional and newer than the published BadgeHub release when that external fact is available.
- Confirm name, publisher, descriptions, category, icon, entrypoint, and class still describe the shipped app.
- Confirm BadgeHub will be configured for `mpos_api_0`; this is an upload-form choice and cannot be proven by the repository.
- Confirm the built archive contains assets plus `.mpy` bytecode and no Python source. Preserve `-march=xtensawin`, the firmware-matched compiler pin, and the intentional `-O3` store optimization.
- Treat a changed MicroPythonOS or MicroPython pin as a blocker until bytecode compatibility with field firmware is established.

## Startup and on-device behavior

- Trace the manifest entrypoint to the named Activity and its initial route.
- Check imports renamed or added in the release, especially lazy imports and native `art_fast` fallback behavior.
- Review persistent-data schema/default changes for old installs, partial profiles, reset behavior, and forward migration.
- Review creature ids/order, companion encoding order, radio identifiers, and server ports as durable wire/storage formats; accidental renumbering is a blocker.
- Review debug/test affordances for expiry, local-only behavior, production URLs, fake badge ids, and accidental activation on hardware.
- Check size-sensitive additions: file count matters because LittleFS bills blocks per file; large source or artwork should use existing bake/atlas paths.

## Generated assets and cross-project copies

- Confirm sprites, fonts, server companion art, server icons, silhouettes, screenshots, and their source files are synchronized where a change touches them.
- Compare the badge and server creature rosters and companion codec when either side changes.
- Confirm generated outputs are committed rather than relying on a developer-only bake during packaging.

## Server and protocol coupling

- Identify app changes that require a server route, validation rule, secret, schema column, or migration.
- Ensure a compatible server is already deployed before uploading a dependent app. For additive D1 changes, migrations precede server code; server code precedes the badge release.
- Check retry, offline, 404/409, authentication, and malformed-response behavior at changed boundaries.
- Never perform a production deployment as an implicit release check.

## Licensing and release hygiene

- Check new code, artwork, fonts, and contributor credits against `LICENSING.md`; ensure distributable license files remain in the repository.
- Scan changed files for TODO/FIXME markers, conflict markers, stale app ids, temporary endpoints, commented-out safety checks, and unexplained binary changes.
- Read commit subjects alongside diffs. Fold fixes into user-visible outcomes, and omit merges, formatting, generated-file churn, and build plumbing from player notes.
- Require a clean tracked and untracked worktree so the artifact can be reproduced from the reported commit.

## Exact-artifact smoke test

The last test must use the exact `.mpk` and target firmware, not a source checkout or USB deploy build: launch, home, jager/radio flow, verzamelaar flow, persistence after restart, and one server interaction. Record this as external confirmation; local automation cannot substitute for it.
