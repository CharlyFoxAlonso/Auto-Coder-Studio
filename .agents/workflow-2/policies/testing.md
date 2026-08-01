<!-- workflow-2:managed version=2.0.0 -->
# Testing and evidence policy

## Evidence classes

Keep static inspection, compilation, automated tests, smoke tests, manual
verification and device verification separate. Report exact commands, exit
codes, failures, errors, skips and limitations. Compilation is not behavior;
passing tests are not proof of every possible state.

## Test design

- Add focused tests for new observable behavior.
- Add a regression test for every corrected defect when technically possible.
- Demonstrate that a critical regression test fails without the correction.
- Test public behavior, contracts, state transitions and meaningful errors.
- Cover relevant states and conditions, not only executed lines.
- Keep tests deterministic and independent of order, real time, sleeps, network,
  paid providers, user data and external services unless explicitly integration
  scoped.
- Use Arrange → Act → Assert or an equivalently clear structure.
- Avoid mocks that reproduce implementation internals.
- Treat test code with production-level readability and maintenance.

## Selection

Choose only relevant layers: unit, integration, contract, regression,
property-based, resource/recovery, performance, acceptance, manual or device.
For property-based failures, preserve the minimized input as a permanent unit
regression while retaining the general property.

## Execution order

When applicable:

```text
baseline → focused test → subsystem/integration → full suite
→ lint/type/build/security → smoke/manual/device
```

All required quality checks should be runnable through one or a few documented,
reproducible commands. Never weaken an assertion, disable a check or hide a
failure to obtain green output.
