## Summary

-

## Verification

- [ ] `python -m ruff check .`
- [ ] `python -m pytest`
- [ ] `scripts/smoke_install.sh`
- [ ] `scripts/smoke_hermes_temp_home_mcp.sh`

## Safety boundary

- [ ] This change remains dry-run safe by default.
- [ ] This change does not mutate global runtime config as a side effect of selection.
- [ ] This change does not introduce credentials, private paths, or external mutations.
