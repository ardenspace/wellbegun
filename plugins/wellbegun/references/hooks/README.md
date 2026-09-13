# Enforcement hooks

wellbegun ships optional **generic, grep-based reference scripts**. Prefer existing effective lint, type and schema checks. Adapt a reference only for active areas and concrete enforcement needs, choosing relevant globs and paths. These scripts do not prove semantic registry compliance; no hook installation or foundation phase is required for unrelated work.

The two reference checks:

- `check-hardcoded-values.sh` — flags raw design values (hex colors, px/rem literals) outside the token source file.
- `check-registry-sync.sh` — fails when a file exists in a common folder but is absent from that folder's registry roster.

## Wiring option 1: host editing-time hook

Use this when the active host exposes a supported after-edit hook. In Claude Code, the scripts can run after every file edit. They print violations to **stderr and exit 2** — for `PostToolUse` hooks that is the combination Claude Code feeds back into the agent's context, so drift is corrected the moment it happens (a plain exit 1 would only show the user a message). In the target project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "bash scripts/hooks/check-hardcoded-values.sh" }
        ]
      }
    ]
  }
}
```

Codex plugins do not bundle an equivalent hook configuration. In Codex projects, relevant-entry guidance can live in the area's existing `AGENTS.md`; add pre-commit wiring only when applicable and authorized. Do not create `.claude/settings.json` or `CLAUDE.md` solely for a Codex run.

## Wiring option 2: git pre-commit hook

Catches everything the editing-time hook misses and covers human edits too. In the target project:

```bash
cat > .git/hooks/pre-commit <<'EOF'
#!/usr/bin/env bash
bash scripts/hooks/check-hardcoded-values.sh || exit 1
bash scripts/hooks/check-registry-sync.sh || exit 1
EOF
chmod +x .git/hooks/pre-commit
```

Install only checks selected by the spec for this project, preserving existing hooks instead of overwriting them. The snippet illustrates a new hook; merge needed commands into an existing one. Git and host hooks are optional capabilities, not prerequisites for basic execution. Reuse valid check results and do not repeat a whole suite merely because review changes layers.

## Notifications (optional, documented — not forced)

When a run stops on an L/XL decision (see wellrun), the user may want a push notification. If the active host exposes a notification hook, it can be pointed at any channel the user already has — ntfy, Telegram, Slack. Claude Code's `Notification` hook is one example; wellbegun documents the seam and deliberately does not pick a channel:

```json
{
  "hooks": {
    "Notification": [
      { "hooks": [ { "type": "command", "command": "curl -s -d 'wellbegun: run stopped on a pending decision' ntfy.sh/YOUR_TOPIC" } ] }
    ]
  }
}
```

When the active host has no notification hook, skip this option. The `.wellbegun/pending/` mailbox remains the durable stop signal.
