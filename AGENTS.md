# Development collaboration

Read `PROJECT_STATUS.md` first and inspect the actual worktree status. Preserve user changes, databases, learning records, and cat assets.

The user wants Grok to share development work to reduce Codex usage. Use `scripts/grok-dev.ps1` for bounded tasks once an xAI key is configured. This is a development helper; it does not change application AI providers.

- Codex owns scope, architecture, integration, verification, and release decisions.
- Delegate useful, self-contained code drafts, local reviews, and test-case design to Grok. For trivial changes, work directly to avoid orchestration overhead.
- Supply only necessary file ranges and one concrete question/task. Never send whole conversations, repository dumps, credentials, production data, or uploads.
- Start with one Grok request per bounded task. Make a follow-up only for a specific unresolved issue; never automatically retry failures or run duplicate reviews.
- Use `-Check` to check local configuration without a network call and `-DryRun -RequestFile ...` to inspect request size. Read `docs/GROK_DEVELOPMENT.md` only when using the helper.
- Read the result once; treat it as a proposal. Verify code before applying it and run focused checks. Report actual xAI token usage when a call was made; never promise a fixed Codex savings percentage.
- If the key is missing, report that fact once and continue authorized work locally. Never ask for the key in chat.
- Development helper/configuration changes do not require production deployment. Business releases follow the existing release workflow and must coordinate worktree commits before updating production.
