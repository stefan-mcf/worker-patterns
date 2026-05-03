# Browser Routing Boundary

Worker Patterns may detect when a task looks browser-related and recommend a browser-capable route. It does not include a browser automation runtime.

## In scope

- detect browser/web-app signals in objective text;
- add safety notes to the selected plan;
- render a dry-run route that says browser-capable tooling may be appropriate later.

## Out of scope

- opening websites;
- entering credentials;
- accepting cookies or terms;
- scraping live user data;
- clicking buttons;
- mutating remote state;
- bypassing access controls.

## Recommended workflow

1. Use the selector to identify whether browser capability is needed.
2. Inspect the dry-run plan.
3. Route the work to an explicitly approved browser harness or manual workflow.
4. Keep credentials and real website actions outside this package.
