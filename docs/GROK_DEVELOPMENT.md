# Grok development collaboration

This helper sends one bounded development request to xAI. It returns code proposals or findings for Codex to integrate. It has no model-controlled shell, file-write, deployment, or browser tools. Website AI providers are unchanged.

## One-time local setup (Windows)

Run from this worktree in your own PowerShell terminal:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\grok-dev.ps1 -SetupKey
```

Paste the API key at the hidden prompt, not into chat or a command argument. Windows encrypts it for the current user in `%LOCALAPPDATA%\SpeakEasy\grok-api-key.xml`, outside the repository. An existing process or user `XAI_API_KEY` also works. To replace the stored key, run setup again. To remove it, delete that one credential file.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\grok-dev.ps1 -Check
```

`-Check` makes no network request; it does not validate the key with xAI. After setup, `-SmokeTest` makes one small, billable request without sending source code.

## Routine use

Copy `docs/grok-task.example.json` into `.local-sync/grok/task.json` and adapt the task and file ranges. Paths are relative to this worktree. `start` and `end` are inclusive line numbers; omit both only for small files. A request can specify `model` to use a different accessible Grok model.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\grok-dev.ps1 -DryRun -RequestFile .local-sync/grok/task.json
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\grok-dev.ps1 -RequestFile .local-sync/grok/task.json
```

The terminal prints a compact result path and usage record. Responses and numeric usage metadata are saved under ignored `.local-sync/grok/`. No source changes are applied automatically. Exit code 2 means the response was incomplete; inspect it before using it. Never silently repeat a failed, timed-out, or incomplete request, because the first request may have been billed.

## Division of work and limits

- Grok: scoped code drafts, isolated bug analysis, concise local reviews, relevant test cases.
- Codex: task scoping, cross-module decisions, checking and integrating proposals, running tests, releases.
- One request at a time per bounded task; no recursive agents or full-history uploads.
- Default model: `grok-4.7`, checked against the official model catalog on 2026-09-23. Models 4.5/4.6/4.7 use low reasoning effort. Account access still needs live verification.
- At most 6 file excerpts and 60000 UTF-8 bytes of instructions plus input. Default output budget 2048 tokens, configurable from 128 to 4096. These are request limits, not a guaranteed dollar ceiling.
- One API request, a 90-second client timeout, no automatic retries, no tools, and `store: false` for response retrieval storage. A timeout does not guarantee server-side cancellation.
- Common secret paths and credential patterns are rejected. This is a precaution, not a complete secret detector; inspect the selected excerpts before sending them.
- xAI API usage is charged separately. Codex still consumes usage for coordination and validation, so savings depend on the task and the amount of rework. Use the xAI console for account spending controls.

References: [xAI Responses API](https://docs.x.ai/developers/rest-api-reference/inference/responses), [model catalog and pricing](https://docs.x.ai/developers/models).
