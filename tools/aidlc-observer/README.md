# AI-DLC Observer

A local, read-only dashboard for a person supervising an [AWS Labs AI-DLC](https://github.com/awslabs/aidlc-workflows) workflow.

It shows the current phase and stage, which stages are completed, active, or still ahead, approval gates that are waiting, a chronological audit timeline, recorded decisions, and the Markdown artifacts those stages wrote. Refreshing the page reads the records again. The observer does not approve stages, and it does not write workflow, audit, or memory files.

## Install

From this directory, with Node.js 22 or newer:

```bash
npm install
```

## Run

```bash
npm run dev
```

Open http://127.0.0.1:4317. The server listens on `127.0.0.1` only.

On startup it walks upward from the current directory, then from this tool, looking for an `aidlc/` directory. Point it at another project with either of these:

```bash
npm run dev -- --workspace D:\path\to\project
```

```powershell
$env:AIDLC_OBSERVER_WORKSPACE = "D:\path\to\project"
$env:AIDLC_OBSERVER_PORT = "4317"
npm run dev
```

PowerShell's `npm` script keeps `--workspace` and `--port` for itself. Use the environment variables above, or call `npm.cmd run dev -- --workspace <path> --no-cli`.

The workspace box in the page changes what the running process reads. That choice is kept in memory only, so it is not written into the observed project. `AIDLC_OBSERVER_PORT` or `--port` chooses the port.

A production build of the same UI is:

```bash
npm run build
npm start
```

`--no-cli` skips the AI-DLC commands and uses the record files only. With the commands enabled, the page still reads record files every five seconds. It runs the three read-only commands when the page opens, when you press Refresh, and about once a minute after that. `GET /api/snapshot?cli=skip` reads files only. `cli=refresh` runs the commands now. `cli=auto` reuses a result that is less than a minute old.

On Windows the observer does not pass the workspace through `cmd.exe`. It resolves `aidlc.exe` from the shim's `active-executable` pointer, or from `AIDLC_OBSERVER_CLI_BIN`, and spawns that executable with a separate argument for `--project-dir`. An unrecognized `.cmd` launcher is refused.

## What it reads

For the active space and workflow it discovers:

- `aidlc engine intent list --json`, `aidlc engine space list --json`, and `aidlc engine runtime summary --json` when the `aidlc` command can be launched without a shell
- `aidlc/active-space`, `intents/active-intent`, and `intents.json`
- the workflow `aidlc-state.md` for the stage plan and approval markers
- every Markdown file under that workflow's `audit/` directory
- decision tables in Markdown files whose names contain `decision`
- other Markdown artifacts under the workflow record
- `runtime-graph.json` when the summary command is unavailable
- the vendored stage graph, when one is present, for stage names

Missing files, broken JSON, and audit text without event fields become warnings. The page still shows whatever could be read.

## Windows command check

Checked on 2026-10-10 with AI-DLC 2.11.0. The launcher resolved `aidlc.exe` from the shim's `active-executable` pointer and spawned that file directly (`shell` is false). `--project-dir` was a separate argument, not text inside a `cmd.exe` command. These three commands ran together against the portfolio checkout:

- `engine intent list --json --all` exited 0 and returned JSON with `active`, `space`, and `intents`.
- `engine space list --json` exited 0 and returned JSON with `active` and `spaces`.
- `engine runtime summary --json` exited 0 and returned JSON with `workflow_id`, `stages`, `sensors`, and the other summary fields.

Afterward, `git status` in that checkout was unchanged, and no file in the active intent record changed size or modification time.

## Tests

```bash
npm test
npm run typecheck
```

Tests use the fixtures in `fixtures/` (a sample workflow, a partial record, a malformed record, and an empty directory). They do not call the `aidlc` command and they check that a read does not change fixture bytes.

## Boundaries

This tool is not part of the portfolio build. It does not:

- edit AI-DLC state, hooks, configuration, audit logs, or memory files
- start, advance, or approve a workflow
- send records or telemetry to a network service
- listen on anything other than localhost

The only AI-DLC commands it will spawn are the three read-only JSON queries above. Any other command name is refused in code.

## Limitations

- The full audit log is Markdown. There is no read-only JSON export of every audit event, so the timeline parser uses the stable `**Event**` and `**Timestamp**` fields rather than the human status text.
- `aidlc engine runtime summary` counts stages that have entered the runtime graph. The stage board is the full plan from `aidlc-state.md`, which is a larger set until later stages start.
- The summary command describes the active workflow. A workflow you select that is not the active one uses that record's own files.
- The page reads record files every five seconds. It does not watch the filesystem. The three AI-DLC commands run on Refresh and about once a minute, not on every file read.
- The artifact view renders a small Markdown subset (headings, lists, tables, code, emphasis).
- Symbolic links inside a workflow record are not followed.
- Very large state or audit files are truncated in memory while reading, and the page says so.
- Per-unit construction detail appears when the state file and the audit events carry it. The observer does not invent a unit board.
