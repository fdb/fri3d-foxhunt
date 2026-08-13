---
name: release-to-badgehub
description: Prepare, audit, package, and document Foxhunt releases for BadgeHub. Use when asked to make a release, build or verify a bytecode-only .mpk, prepare a BadgeHub upload, check release readiness, bump or confirm a release version, or draft release notes from this repository's commits.
---

# Release to BadgeHub

Prepare the current manifest version as a reproducible, bytecode-only BadgeHub package. Automate facts and checks first; use conversation only for judgments or external facts the repository cannot prove.

## Prepare the candidate

1. Read `CLAUDE.md` and obey its release, bytecode, size, and hardware constraints.
2. Run `scripts/prepare_badgehub_release.sh` from the repository root. Pass `--base <ref>` only when the user supplies a release-note baseline or the detected baseline is clearly wrong. Never use `--allow-dirty` for a real candidate.
3. Let the script derive the version, app id, entrypoint, output name, Git commit, and notes range. Do not ask the user for values already present in its output.
4. If a check fails, report the exact blocker. Fix a mechanical repository issue when the release request authorizes it, rerun the affected check, then rerun the complete command. Do not weaken or skip a check to get a green result.
5. Read the generated `dist/badgehub-release-<version>-context.md` completely.

The upload artifact is `dist/com.enigmeta.foxhunt_<version>.mpk`. Source packages are unsupported: do not add or suggest a source `.mpk` variant.

## Perform the release review

Read [references/release-review.md](references/release-review.md) completely and follow it. This is a reasoning pass, not another scripted check.

Always inspect the actual contents of these files:

- `com.enigmeta.foxhunt/META-INF/MANIFEST.JSON`
- `scripts/build_mpk.sh` and `scripts/get_mpy_cross.sh`
- `.github/workflows/build-mpk.yml`
- the manifest entrypoint and its activity class
- `com.enigmeta.foxhunt/assets/registrar.py`
- `com.enigmeta.foxhunt/assets/store.py`
- `com.enigmeta.foxhunt/assets/creatures.py`
- `com.enigmeta.foxhunt/assets/fox_radio.py`
- `LICENSING.md`

Then inspect every changed file in the detected release range at least at diff level. Open the surrounding implementation for changes involving persistence, radio behavior, app startup, server contracts, generated assets, licensing, or packaging. Look for unfinished work, stale names or versions, debug behavior, risky defaults, server migrations that must precede the app, and claims the package does not actually satisfy.

Separate findings into:

- **Blocker**: must be fixed before upload.
- **Needs confirmation**: cannot be established locally, such as deployment state or real-badge testing.
- **Observation**: relevant but safe for this release.

Do not turn expected limitations documented in `CLAUDE.md` into blockers without evidence that this release regressed them.

## Draft the release notes

Use the context file's non-merge commits and the reviewed diffs as evidence. For a repository with no prior `v*` release tag, label the range as the initial BadgeHub release and synthesize highlights instead of dumping the entire history.

Write paste-ready notes:

1. A one-sentence summary for players.
2. Three to seven bullets grouped by player-visible outcome, not commit order.
3. A short compatibility or operator note only when it matters.

Prefer concrete Dutch game terms from `CLAUDE.md` where they help. Exclude commit hashes, internal refactors, CI chores, and implementation trivia unless they materially affect users or installation. Do not claim a fix or feature from a commit subject without verifying its diff.

## Finish conversationally

Return one compact release packet containing:

- readiness status and any blockers;
- detected version, commit, baseline, artifact path, byte size, and SHA-256;
- automated check results and manual-review conclusions;
- paste-ready release notes;
- only the remaining external steps.

The script proves package structure and reproducibility, but it cannot prove runtime compatibility. Ask for one final confirmation that the exact `.mpk` was installed and smoke-tested on the target Fri3d badge if the user has not already said so. Recommend checking launch, home, one jager hunt/radio path, one verzamelaar path, persistence after restart, and server contact. Do not upload, deploy the server, create a tag, or publish a release unless the user separately asks.
