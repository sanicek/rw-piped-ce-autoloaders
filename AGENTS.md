# AGENTS.md

## Project conventions

- Keep generated build outputs, package artifacts, and local RimWorld files out
  of version control.
- Validate package structure with `python3 scripts/validate-package.py <package>`.
- Do not add Workshop publication identifiers until a page has been published.
- Treat `About/About.xml` `modVersion` as the single release version. Tags and
  GitHub releases use the matching `vMAJOR.MINOR.PATCH` form.

## Engineering guardrails

- Prefer the simplest engine-native or declarative solution. Do not introduce a
  workaround whose implementation complexity, compatibility risk, or maintenance
  cost is disproportionate to the minor issue it addresses without explicit user
  approval.
- Before requesting approval for a complex workaround, explain the underlying
  issue, the proposed mechanism, its implementation and maintenance complexity,
  compatibility or failure risks, and the simpler alternatives considered. A
  general request to fix the issue does not implicitly approve the workaround.
- Any new or materially expanded Harmony patch requires explicit user approval
  before implementation. Explain why XML, inheritance, composition, or a
  supported public API cannot solve the problem; identify the target method and
  patch type; and justify the patch's scope, implementation complexity, and
  compatibility risk.
- Existing Harmony patches accepted in completed phases remain approved unless
  their targets, scope, or behavior materially change.

## Artwork workflow

- Follow `artwork/README.md` and use `scripts/artwork.sh` instead of ad hoc
  generation or image processing.
- Keep credentials, raw generations, receipts, candidates, and review sheets
  outside version control. Only explicitly approved game-ready outputs enter the
  tracked `Textures/` tree.
- Show the Scenario dry-run batch cost and obtain explicit user approval before
  paid generation. Do not treat a general request for new art as approval of the
  estimated charge.
- Present the configured candidate sheet and do not select or promote an option
  until the user explicitly chooses it.
- Validate approved artwork and package output before committing.

## Literate Programming

- Write all maintained code in a literate programming style: present each file
  and nontrivial section as a top-down narrative that introduces its purpose
  before its implementation.
- Keep explanations next to the code they govern. Document intent, invariants,
  lifecycle, compatibility constraints, failure behavior, and non-obvious
  tradeoffs rather than restating syntax.
- Document public entry points and divide multi-phase scripts or validators into
  named conceptual phases. Prefer clear names and simple code over comments
  that compensate for avoidable complexity.
- Remove dead code instead of preserving it in comments. Keep every comment
  accurate when behavior changes, and update related maintainer documentation
  when workflows, package layout, supported versions, or validation rules
  change.
- Do not add narrative comments to generated files, dependency lockfiles,
  binaries, artwork, vendored content, or checksum-frozen recovered artifacts.
  Document those files in the maintained source that produces, validates, or
  consumes them instead.

## Validation workflow

- Run `scripts/install-local.sh` after gameplay changes so the current package
  is built, validated, and installed for testing.
- The user performs one lightweight RimWorld smoke test after installation:
  verify that the representative setup for the current phase works.
- Do not expand manual acceptance into an exhaustive QA matrix unless the user
  explicitly requests it.
- Do not merge a gameplay pull request until the user confirms that smoke test
  passed. Record that confirmation in the relevant release record or durable
  design document and in the pull request body.
- Documentation-only and process-only changes do not require a RimWorld smoke
  test; validate only the affected documentation, scripts, or package structure.
- Keep validation in this local OpenCode workflow. Do not add CI services or
  hosted automation unless the user explicitly changes this policy.

## Git Workflow (Build Mode)

- `main` is protected and must never receive direct commits or pushes. All changes go through feature branches.
- When making changes in build mode:
  1. Create a branch from `main` with a conventional prefix: `feat/`, `fix/`, `chore/`, `refactor/`, or `docs/` followed by a short kebab-case description (e.g. `feat/add-arch-gaming`).
  2. Make the changes.
  3. Run the appropriate validation.
  4. After validation passes, stage the changed files and commit with a [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) message (`feat(scope): description`, `fix: description`, `chore: description`, `docs: description`, etc.).
  5. Push the branch with `git push -u origin <branch-name>`.
  6. Create a pull request with a summary and validation results. Use a draft PR
     for gameplay changes awaiting the user's smoke test; use a normal PR for
     changes that need no gameplay acceptance.
- For a gameplay PR, provide the current phase's short smoke-test setup after
  installation. Do not ask whether it is ready to merge while acceptance is
  still pending.
- If the user requests changes, reuse the existing feature branch. Make the
  changes, validate, commit, and push; the PR updates automatically.
- When the user confirms the smoke test passed, update the relevant release
  record or durable design document, commit and push the acceptance note, update
  the PR body, mark the PR ready, then ask
  whether it is ready to merge or needs additional changes.
- Before merging, inspect the clean worktree, all commits in the PR, and the
  complete diff from `main`. No hosted status checks are expected.
- If the user confirms merge, use `gh pr merge --merge --delete-branch`, then
  synchronize local `main`, delete the local feature branch if it still exists,
  and run `git remote prune origin`.
- This workflow applies to every change, including updates to `AGENTS.md` itself.

## Release workflow

- Keep releases local and operator-driven; do not add hosted CI/CD unless the
  user explicitly changes this policy.
- Prepare the version and its `docs/releases/` record on a feature branch. Record
  the exact RimWorld, CE, VEF, source, and tool versions used for the candidate.
- From a clean candidate commit, run `python3 scripts/package-release.py`, then
  `scripts/install-local.sh --release` and the representative RimWorld smoke
  test. Record the candidate checksum; do not publish an untested package.
- After acceptance is recorded and the pull request is merged, synchronize a
  clean `main`, rebuild the archive, and require its checksum to match the tested
  candidate. If it differs, install and smoke-test the final archive again.
- Create and push an annotated version tag, then use `gh release create` with the
  installable ZIP, checksum, and matching release record as its notes.
- GitHub's generated source archives are not installable RimWorld packages. The
  attached versioned ZIP is the supported GitHub download.
- Add `PublishedFileId.txt` only after the Workshop page exists; Workshop upload
  remains a separate, explicit publication step.
