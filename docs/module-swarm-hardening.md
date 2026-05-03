# Module-Swarm Hardening

`module-swarm` is for decomposable work across disjoint scopes. The selector treats high lane counts as decomposition hints, not permission to launch all lanes at once.

## Safety rules

- Require explicit scope ownership before broad parallelization.
- Use conservative waves when merge-conflict risk is high or ownership is ambiguous.
- Keep implementation and review lanes independent when review is requested.
- Render dry-run plans only; a caller decides whether to execute.

## Scale policy

The selector can recommend:

- `low_cost_disjoint`: larger active waves for clearly disjoint, low-risk scopes.
- `low_cost_conservative`: smaller active waves when conflict or risk is higher.

These are policy labels used by tests and plan rendering. They do not imply that this package can allocate provider capacity or launch workers.

## Example

Thirty-two independent documentation sections may be represented as 32 requested lanes, but the execution plan can still cap active lanes and require integration between waves.

## Review boundary

External review can be valuable, but it should be represented as a separate review route or overlay. It should not be silently substituted into implementation lanes.
