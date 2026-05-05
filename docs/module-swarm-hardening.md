# Module-Swarm Hardening

`module-swarm` is the large-lane decomposition pattern for independent scopes, expressed as a runtime-agnostic contract.

The important distinction is:

- **requested lanes** = how many independent scopes the work decomposes into;
- **active lanes** = how many workers the runtime should run concurrently;
- **waves** = how the requested lanes are batched under the active-lane cap;
- **integration cadence** = whether integration happens once at the end or after every wave.

So the 32-worker hardening is still part of the concept, but it is not documented as "always launch 32 workers at once." The selector preserves 32 lanes as the decomposition shape, then applies safety policy before execution.

## Safety rules

- Require explicit scope ownership before broad parallelization.
- Use conservative waves when merge-conflict risk is high or ownership is ambiguous.
- Keep implementation and review lanes independent when review is requested.
- Render dry-run plans only; a caller/runtime decides whether to execute.
- Treat high lane count as a scale signal, not a bypass around review, integration, or provider limits.

## Scale policy

The selector can recommend:

- `low_cost_disjoint`: larger active waves for clearly disjoint, low-risk scopes.
- `low_cost_conservative`: smaller active waves when conflict or risk is higher.

These are policy labels used by tests and plan rendering. They do not imply that this package can allocate provider capacity or launch workers.

## 32-lane behavior

The hardened 32-lane cases are covered by tests and fixtures:

- `module_swarm_32_lane_disjoint_cheap`
  - 32 requested module lanes.
  - 8 max active lanes.
  - 4 waves.
  - one final integrator.
  - low-cost builder profile policy.

- `module_swarm_32_lane_high_risk`
  - 32 requested module lanes.
  - 4 max active lanes.
  - 8 waves.
  - per-wave integration cadence.
  - low-cost builder profile policy, with risk handled by smaller waves rather than premium-profile escalation.

This keeps the core lesson: broad lane fan-out is safe when it is scoped, batched, integrated, and reviewed. The package should make that shape visible before any runtime starts workers.

## Review boundary

External review can be valuable, but it should be represented as a separate review route or overlay. It should not be silently substituted into implementation lanes.
