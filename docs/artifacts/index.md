# Artifact Registry capability

The DDDA platform owns the **contract, template, generator, and validators** for project Artifact Registries. It does not own one global registry containing artifacts from unrelated projects.

## Ownership model

```text
DDDA platform repository
├── schemas and templates
├── registry projection generator
└── validation and publishing automation

project repository or project workspace
├── artifacts/registry.yaml       # project-owned source of truth
└── docs/artifacts/index.md        # generated read-only projection
```

A project Miro board links to the registry inside that project's workspace. This prevents cross-project data conflicts and gives each project an explicit owner, lifecycle, provenance, and revision boundary.

The minimal acceptance example is located at:

- [`examples/minimal/projects/acceptance-claims-modernization/artifacts/registry.yaml`](../../examples/minimal/projects/acceptance-claims-modernization/artifacts/registry.yaml)
- [`examples/minimal/projects/acceptance-claims-modernization/docs/artifacts/index.md`](../../examples/minimal/projects/acceptance-claims-modernization/docs/artifacts/index.md)

GitHub Pages remains a later projection option tracked by backlog issue `#45`. A rendered page remains read-only and cannot approve a gate.
