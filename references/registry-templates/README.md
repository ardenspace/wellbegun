# Registry templates

A registry is a **thin index** of the globally shared elements in one area of the codebase. wellspec instantiates these templates as markdown rosters; wellplan's phase 1 turns the rosters into real code; wellrun reads and updates them on every step.

## Three principles

1. **Thin index.** Each row carries only: name, one-line purpose, real file location, when to use it. Never copy content into the registry — it is a map, not a document. A registry that duplicates its code goes stale; a registry that points at its code cannot.
2. **Code is the source of truth.** Where the code itself can be the registry, let it: the design token file *is* the token registry, and the markdown only points at it. The markdown roster exists for the things code cannot self-describe (which component is canonical, which layer is mandatory).
3. **Sync is machine-verified.** A new file in a common folder that is absent from its roster is a lint failure, not a hope. See `../hooks/check-registry-sync.sh` for the reference check.

## Placement

Each registry file lives **in its own area of the target repo**, next to the code it indexes (e.g. `src/components/shared/REGISTRY.md`), not in a central docs folder. "Read the registry before working in this area" is enforced by the area's CLAUDE.md or by a hook — it is not left to the implementer's discretion.

## The four templates

| Template | Area | Backing truth |
|---|---|---|
| `design-tokens.md` | Design | The token source file |
| `frontend-components.md` | Frontend | Shared component folder |
| `backend-common.md` | Backend | Common layers (error, auth, logging) |
| `db-schema.md` | Data | Migrations |
