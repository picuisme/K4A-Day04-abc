---
name: approved_software_catalog
track: bonus
kind: local_catalog
provider: synthetic_json
requires_env: []
inputs: [query, platform, max_results]
outputs: [matches, match_count, catalog_version, updated_at]
side_effect: false
---
# approved_software_catalog

Searches the synthetic company catalog by software name, alias, or platform.
It reports whether a package is `approved`, `restricted`, or `prohibited`, plus
the managed installation path. It never installs software and never grants an
exception for a restricted or prohibited package.
