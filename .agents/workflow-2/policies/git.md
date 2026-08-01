<!-- workflow-2:managed version=2.0.0 -->
# Git and working-tree policy

Before work, record branch, commit and status. Treat all modified and untracked
files as user-owned.

Without explicit authorization, do not commit, push, pull, merge, rebase,
reset, restore, checkout, switch, clean, stash, cherry-pick, revert, create
branches or tags, or publish releases.

For a change:

- inspect any pre-existing diff in an allowed file before editing;
- preserve unrelated hunks and line endings;
- modify only the approved surface;
- avoid global formatting, generated files and dependency churn;
- review every task-owned file with `git diff`;
- run `git diff --check`, `git diff --stat` and final `git status --short`;
- report pre-existing, task-owned and out-of-scope changes separately.

Keep a microcut coherent and reversible. Do not mix product changes, policy
migration, unrelated cleanup and historical report edits in one cut.
