# Security Policy

## Supported versions

The project is in initial public alpha. Security fixes target the default branch and the latest tagged release.

## Reporting a vulnerability

Please report suspected vulnerabilities through GitHub Security Advisories if enabled for the repository, or by opening a private communication channel with the maintainer. Do not include live credentials, tokens, or exploitable secrets in public issues.

## Design boundary

Hermes Worker Patterns is designed to be dry-run safe:

- it selects worker patterns;
- it renders prompts and execution plans;
- it does not launch workers;
- it does not mutate Hermes configuration;
- it does not create external tasks;
- it does not use website credentials or execute browser actions;
- it does not push branches, publish packages, or open pull requests.

A vulnerability report is especially useful if it shows that package behavior crosses this boundary unexpectedly.

## Secrets policy

Do not commit credentials, API keys, access tokens, private local paths, or real user data. Trace logging redacts common secret patterns, but callers should still avoid placing sensitive data in objectives or notes.
