# Release policy

## Versioning

Piped CE Autoloaders uses Semantic Versioning. `About/About.xml` is the single
source for the current version through its `modVersion` field. The local build
passes that value into the assembly, release archives use it in their names, and
published Git tags use the matching `vMAJOR.MINOR.PATCH` form.

- PATCH releases contain compatible bug fixes or packaging corrections.
- MINOR releases add backward-compatible gameplay or user-facing functionality.
- MAJOR releases intentionally change a save, settings, Def identity, or other
  compatibility contract, or drop an already supported RimWorld series.

Moving CE or VEF dependencies does not by itself require a release. Every mod
release records the dependency revisions used for its build and smoke test as a
known-good baseline, not as a promise that Workshop dependencies remain pinned.

## Release records

Each published version has one record that also serves as its GitHub release
notes. The record states what changed, update risks, exact build dependencies,
the tested source revision, and the representative smoke-test result.

- [1.0.2](releases/1.0.2.md) - tracked Workshop publication identity
- [1.0.1](releases/1.0.1.md) - grouped duplicate caliber options
- [1.0.0](releases/1.0.0.md) - first stable release

## Local publication workflow

The release stays inside the normal OpenCode and pull-request workflow. Hosted
CI/CD is intentionally not part of the project.

1. Update `modVersion` and add the version's release record on a feature branch.
2. Validate and commit the release candidate so the worktree is clean.
3. Build the installable ZIP and checksum with `python3 scripts/package-release.py`.
4. Install that exact candidate without rebuilding by running
   `scripts/install-local.sh --release`, then complete the release record after
   the representative RimWorld smoke test and record its checksum.
5. Commit the acceptance record, push, and merge through the ordinary
   pull-request process.
6. Synchronize a clean local `main`, rebuild the final archive, and require its
   checksum to match the tested candidate. A mismatch requires another install
   and smoke test before publication.
7. Create and push an annotated `vMAJOR.MINOR.PATCH` tag at that commit.
8. Publish the ZIP, checksum, and version record with `gh release create`.

The attached `PipedCEAutoloaders-vMAJOR.MINOR.PATCH.zip` is the installable mod.
GitHub's automatically generated source archives are repository snapshots and
must not be presented as game-ready packages.
