# Auto-Coder-Studio — Agent Instructions

This file is the entry point for agents working in this repository.

Keep task prompts short. Load only the rules required by the current task.

## 1. Mandatory routing

For every repository task, first read and apply:

- `.agents/workflow-2/core.md`
- `.agents/workflow-2/contracts/handoffs.md`
- `.agents/policies/git-safety.md`

Select exactly one canonical role:

- planning or design → `.agents/workflow-2/roles/planner.md`
- independent plan review → `.agents/workflow-2/roles/plan-reviewer.md`
- implementation or bug fixing → `.agents/workflow-2/roles/builder.md`
- verification, acceptance, architecture, quality, or security review →
  `.agents/workflow-2/roles/auditor.md`

Then load the matching Auto-Coder-Studio profile when applicable:

- Planner → `.agents/playbooks/plan.md`
- Builder → `.agents/playbooks/implement.md`
- Auditor validating an implementation → `.agents/playbooks/verify.md`
- Auditor reviewing architecture, quality, or security →
  `.agents/playbooks/audit.md`

The Plan Reviewer uses the canonical role and plan-review template; it must be
independent from Planner. Project playbooks supplement the canonical role and
must not broaden its authority or replace its handoff/verdict.

For tasks that execute or evaluate checks, also apply:

- `.agents/policies/testing.md`

Use the template for the active canonical role under
`.agents/workflow-2/templates/`. Add repository-state fields from:

- `.agents/templates/final-report.md`

When `codebase-memory-mcp` is available and useful, apply:

- `.agents/integrations/codebase-memory-mcp.md`

Do not load unrelated roles, playbooks, policies, or integrations.

## 2. Instruction priority

When instructions conflict, use this order:

1. the user’s current explicit instruction;
2. the approved plan or specification referenced by the task;
3. accepted architectural decisions and governing project documentation;
4. this `AGENTS.md`;
5. Workflow 2.0 contracts, roles, and policies;
6. project policies, playbooks, integrations, and templates;
7. existing implementation patterns.

Report material conflicts instead of resolving them silently.

## 3. Product boundary

Auto-Coder-Studio is a local coding assistant that helps inspect, generate, modify, and validate code through a controlled interface.

Preserve its core characteristics:

- local-first operation;
- explicit user control;
- limited and validated tool execution;
- transparent file changes;
- separation between generated proposals and executed actions;
- compatibility with local models and Ollama;
- safe handling of repository paths and commands.

Do not silently turn it into:

- an unrestricted autonomous agent;
- a remote-service-dependent application;
- an arbitrary shell executor;
- a system that edits outside the selected workspace;
- a framework rewrite unrelated to the current task.

## 4. Architectural direction

Preserve clear responsibilities between:

- `app.py` and UI orchestration;
- reusable logic in `core/`;
- model communication;
- parsing and validation;
- file operations;
- command execution;
- session or persistence behavior.

Prefer:

- pure logic separated from Streamlit;
- decisions separated from side effects;
- validation before execution;
- explicit data flow;
- inward dependency direction;
- small modules with one clear responsibility.

Modules in `core/` should not depend on Streamlit unless the existing architecture explicitly requires it.

Do not create new layers or abstractions without a demonstrated need.

## 5. Behavior preservation

Refactors must preserve observable behavior unless the task explicitly changes it.

Inspect and preserve, when relevant:

- function signatures;
- return values;
- visible messages;
- command names and aliases;
- help text;
- argument parsing;
- operation order;
- session-state keys;
- error behavior;
- file formats;
- custom-command expansion;
- model request and response behavior.

Do not simplify or normalize user-visible text without authorization.

## 6. Command parsing and routing

Keep these responsibilities distinct when supported by the current architecture:

1. recognizing input;
2. parsing commands and arguments;
3. resolving built-in or custom commands;
4. validating the requested action;
5. executing side effects;
6. reporting results to the UI.

Parsing components should remain pure whenever practical.

A parser must not silently:

- access disk;
- execute commands;
- call a model;
- mutate Streamlit state;
- perform network requests.

Execution belongs in an explicit orchestration or execution layer.

## 7. Command execution security

Treat command execution as a sensitive boundary.

Preserve or strengthen existing:

- allowlists;
- blocked commands and subcommands;
- path validation;
- workspace confinement;
- traversal prevention;
- argument validation;
- execution without an unnecessary shell;
- explicit user approval where required.

Do not:

- broaden an allowlist without explicit authorization;
- bypass validation;
- execute model-generated commands directly;
- enable unrestricted shell access;
- weaken protections merely to make a test pass.

Any security-sensitive behavior change requires focused tests.

## 8. File safety

All file operations must remain confined to the authorized workspace.

Validate paths before reading, creating, modifying, moving, or deleting files.

Protect against:

- absolute-path escape;
- `..` traversal;
- symbolic-link escape when relevant;
- accidental overwrite;
- deletion outside scope;
- malformed model-generated paths.

Prefer explicit actions over implicit filesystem mutation.

Never use real secrets or private user files as test fixtures.

## 9. Model boundary

Treat model output as untrusted input.

Model responses must be parsed and validated before they can affect:

- files;
- commands;
- dependencies;
- configuration;
- application state.

Do not assume that a model:

- follows the requested format;
- returns valid JSON;
- references valid paths;
- generates safe commands;
- preserves repository contracts;
- has complete project context.

When context is insufficient, prefer an explicit request for more context over invented implementation details.

## 10. Structured outputs

Do not introduce Instructor, Pydantic response models, grammar-constrained decoding, Repomix, or a new structured-output architecture unless the current task explicitly includes them.

When structured outputs are introduced by an approved task:

- define a clear schema;
- validate every response;
- handle invalid output explicitly;
- distinguish proposed actions from executed actions;
- support a safe `need_context` or equivalent result;
- test malformed and incomplete responses.

Do not mix inference redesign into unrelated refactoring work.

## 11. Local model compatibility

Preserve compatibility with the model and Ollama interfaces currently supported by the project.

Do not change without authorization:

- model defaults;
- inference parameters;
- prompt contracts;
- response parsing;
- context construction;
- provider selection;
- fallback behavior.

Performance or token optimizations must not silently change observable behavior.

## 12. Scope discipline

The current task defines the allowed scope.

Do not use a task to:

- redesign the complete application;
- move unrelated functions;
- rewrite prompts globally;
- change model providers;
- add dependencies;
- reorganize all of `core/`;
- clean legacy code outside scope;
- change UI behavior;
- introduce structured outputs;
- modify command security rules;
- update unrelated documentation.

Report out-of-scope findings instead of fixing them silently.

## 13. Documentation authority

Use the plan, specification, or architectural document explicitly referenced by the task.

When no governing document is named:

1. inspect current tests;
2. inspect current source code;
3. inspect accepted project documentation;
4. inspect recent architectural decisions.

Do not treat old proposals as implemented behavior.

Do not describe future architecture as current architecture.

## 14. Tests and validation

Use the repository’s existing Python environment and configured testing framework.

Inspect the repository before choosing commands.

At minimum, when applicable:

- run focused tests for the changed behavior;
- run the full existing test suite;
- perform syntax or import checks;
- perform a smoke test when UI or startup behavior changes.

Apply `.agents/policies/testing.md`.

Do not change the test framework or add testing dependencies without authorization.

## 15. Documentation changes

Update documentation only when:

- explicitly requested;
- public behavior changed;
- a new module boundary was introduced;
- an accepted plan requires a record of the change.

Document only what was implemented and verified.

Do not mix product roadmap ideas into implementation documentation.

## 16. Secrets and local data

Never expose, log, commit, or include in reports:

- API keys;
- access tokens;
- passwords;
- local credentials;
- private repositories;
- user file contents not required by the task;
- model-provider secrets.

Do not introduce telemetry or remote transmission without explicit authorization.

## 17. Task prompt contract

A task-specific prompt should normally contain only:

- mode;
- objective;
- referenced plan or specification;
- allowed files or area;
- task-specific contracts;
- required validation.

Example:

```text
Implement the approved command-parser cut.

Apply AGENTS.md and:
- <approved-plan>

Scope:
- app.py
- core/command_parser.py
- <related tests>

Preserve:
- commands, aliases, messages, help text, and custom-command behavior.

Run:
- focused tests
- full suite
```

Do not repeat policies already routed through this file.

## Final rule

Keep Auto-Coder-Studio local, controlled, testable, and safe.

Treat model output as untrusted, preserve existing behavior, modify only the requested scope, and verify every implementation with real evidence.

<!-- workflow-2:begin -->
## Workflow 2.0 routing

For every repository task, read `.agents/workflow-2/core.md` and
`.agents/workflow-2/contracts/handoffs.md`.

Select exactly one role file:

- planning: `.agents/workflow-2/roles/planner.md`
- plan review: `.agents/workflow-2/roles/plan-reviewer.md`
- implementation: `.agents/workflow-2/roles/builder.md`
- independent audit: `.agents/workflow-2/roles/auditor.md`

Load only the risk policies required by the task. Project-specific rules in
this file and more specific nested instruction files remain authoritative for
their scope. Do not broaden scope or overwrite existing user work.
<!-- workflow-2:end -->
