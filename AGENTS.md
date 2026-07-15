# AGENTS.md

## Project conventions

- Keep generated build outputs, package artifacts, and local RimWorld files out
  of version control.
- Validate package structure with `python3 scripts/validate-package.py <package>`.
- Do not add Workshop publication identifiers until a page has been published.

## Validation workflow

- Run `scripts/install-local.sh` after gameplay changes so the current package
  is built, validated, and installed for testing.
- The user performs one lightweight RimWorld smoke test after installation:
  verify that the representative setup for the current phase works.
- Do not expand manual acceptance into an exhaustive QA matrix unless the user
  explicitly requests it.
- Do not merge a gameplay pull request until the user confirms that smoke test
  passed. Record that confirmation in the roadmap and pull request body.
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
- When the user confirms the smoke test passed, update the roadmap, commit and
  push the acceptance note, update the PR body, mark the PR ready, then ask
  whether it is ready to merge or needs additional changes.
- Before merging, inspect the clean worktree, all commits in the PR, and the
  complete diff from `main`. No hosted status checks are expected.
- If the user confirms merge, use `gh pr merge --merge --delete-branch`, then
  synchronize local `main`, delete the local feature branch if it still exists,
  and run `git remote prune origin`.
- This workflow applies to every change, including updates to `AGENTS.md` itself.
