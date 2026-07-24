# Hermes-to-Pi Config Propagation Matrix

> **Audit scope:** All Hermes config keys (across root config and all 6 hswarm profiles) mapped to Pi equivalents. Determines which keys affect Pi behavior and whether they should be propagated.
>
> **Sources:**
> - `/Users/rath/.hermes/config.yaml` (root)
> - `/Users/rath/.hermes/profiles/hswarm-{orch,eng,arch,rsrch,qa,vrfy}/config.yaml` (6 profiles)
> - `~/.pi/agent/settings.json` (Pi persistent config)
> - `pi --help` output (Pi CLI flags)
>
> **Date:** 2026-07-24

---

## 1. Model Configuration

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `model.provider` | all | `custom` | `--provider <name>` / `settings.defaultProvider` | `wafer` | NO | Hermes uses custom DeepSeek provider; Pi uses its own provider registry. These are independent stacks — Hermes shouldn't override Pi's provider. |
| `model.default` | root, orch | `deepseek-v4-flash` | `--model <pattern>` / `settings.defaultModel` | `GLM-5.2` | NO | Different model selection systems. Pi has its own model discovery (via provider catalog). Forcing a Hermes model onto Pi would constrain what Pi can use. |
| | eng, arch, rsrch, qa, vrfy | `deepseek-v4-pro` | | | NO | |
| `model.base_url` | all | `https://api.deepseek.com` | env vars per provider | varies per provider | NO | Hermes's base_url is provider-specific (DeepSeek). Pi uses separate env vars per provider. No mapping. |
| `model.api_key` | all | `${DEEPSEEK_API_KEY}` | `DEEPSEEK_API_KEY` env var | env var | NO | Both use the same env var name. Pi auto-resolves `DEEPSEEK_API_KEY` from environment. Hermes should NOT pass the key as a CLI flag — it's already in the env. |
| `agent.reasoning_effort` | all | `medium` | `--thinking <level>` | per-session default | YES | Direct semantic mapping. Hermes `medium` -> Pi `medium`. When Hermes spawns a Pi subagent, it could set `--thinking` to match. Low risk. |
| `agent.verbose` | all | `false` | `--verbose` flag | off | YES | Direct flip. Low risk. |

**Risk note:** Model configs diverge because Hermes and Pi serve different roles — Hermes is a multi-agent orchestrator using DeepSeek, Pi is a coding agent using its own provider chain. These should remain independent.

---

## 2. Agent Behavior

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `agent.max_turns` | root, eng, arch, rsrch, qa, vrfy | `150` | `settings.maxTurns` | `150` | YES | Same concept, same default (150). When Hermes delegates to Pi, should match or Hermes > Pi to prevent premature shutdown. Already aligned. |
| | orch | `80` | | | YES | Orch profile has lower turns. Should explicitly propagate when spawning Pi to avoid mismatch. |
| `agent.personalities.*` | all | 13 personalities (catgirl, concise, creative, helpful, hype, kawaii, noir, philosopher, pirate, shakespeare, surfer, teacher, technical, uwu) | `--system-prompt <text>` | default coding prompt | CONDITIONAL | Only propagate if the selected Hermes personality is NOT "technical" (Pi's default role). Hermes personalities control agent demeanor; Pi has no personality system. Hermes should inject its active personality text as Pi's `--system-prompt` or `--append-system-prompt`. Low risk. |
| `agent.personalities.technical` | all | "You are a technical expert." | Pi built-in prompt | default coding assistant prompt | CONDITIONAL | Only if user explicitly set a non-technical personality. Pi's default system prompt is a coding assistant — redundant to propagate "technical". |
| `code_execution.max_tool_calls` | all | `50` | `--tools` / tool allowlist | all tools enabled by default | NO | Hermes's code_execution is for the built-in execute_code tool. Pi tools are entirely different (read/bash/edit/write). No mapping. |
| `code_execution.timeout` | all | `300` | N/A | unbounded | NO | Pi has no per-tool timeout config. Pi's tool-call timeout is baked into the runtime. |

**Cross-profile divergence:** The orch profile (`agent.max_turns: 80`) is significantly lower than other profiles (`150`). When Pi is spawned from the orch profile, the turn limit could cut Pi sessions short. Recommended: either raise orch to 150 or explicitly pass `--session-id` with turn tracking.

---

## 3. Delegation

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `delegation.max_concurrent_children` | all (root uses `max_iterations` instead) | `2` | N/A | single-instance | NO | Hermes controls how many Pi instances can run concurrently. This is an orchestrator-level constraint, not a Pi-level setting. Pi has no multi-instance support. |
| `delegation.max_spawn_depth` | profiles | `1` | N/A | no sub-delegation | NO | Pi cannot delegate to sub-agents. Hermes-level constraint only. |
| `delegation.max_iterations` | root only | `50` | `settings.maxTurns` | `150` | YES | Semantically equivalent to Pi's maxTurns. Root config uses `max_iterations` instead of `max_concurrent_children`. This is the per-child turn budget. Should map to Pi's maxTurns when delegating. |

**Risk note:** Root config uses `delegation.max_iterations: 50`, which is lower than Pi's `maxTurns: 150`. If Hermes spawns Pi and Pi checks no limiter, Pi will run longer than Hermes expects. If Hermes passes Pi's `maxTurns = 50`, Pi will stop sooner. Recommended: align values.

---

## 4. Terminal

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `terminal.cwd` | all | `.` | N/A | current shell directory | NO | Pi inherits cwd from the shell that launches it. Hermes's `cwd: .` means the same thing — current working directory. No propagation needed. |
| `terminal.timeout` | all | `180` | N/A | unbounded | NO | Hermes timeout applies to its own terminal() tool. Pi runs as a subprocess — the timeout should be set at the parent's subprocess level, not passed as a Pi flag. |
| `terminal.backend` | all | `local` | N/A | always local | NO | Pi only supports local execution. |
| `terminal.lifetime_seconds` | all | `300` | N/A | N/A | NO | Hermes container lifecycle. Not applicable to Pi. |

---

## 5. Security / Tool Guardrails

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `tool_loop_guardrails.hard_stop_after.exact_failure` | all | `5` | `--tools` / `--exclude-tools` | all tools enabled | NO | Different mechanisms. Hermes tracks failure streaks per tool call; Pi uses allowlist/denylist of tool names. Could inform Pi's `--exclude-tools` for same behavior. |
| `tool_loop_guardrails.hard_stop_after.idempotent_no_progress` | all | `5` | N/A | no progress detection | NO | Pi has no idempotent-no-progress detection. |
| `tool_loop_guardrails.hard_stop_after.same_tool_failure` | all | `8` | N/A | no per-tool failure tracking | NO | Pi doesn't track same-tool failures separately. |
| `tool_loop_guardrails.hard_stop_enabled` | all | `false` | N/A | no equivalent | NO | Guardrails disabled in Hermes too. |
| `tool_loop_guardrails.warn_after.*` | all | `2` (exact_failure, idempotent_no_progress, same_tool_failure) | N/A | no warning system | NO | Pi has no equivalent. |
| `tool_loop_guardrails.warnings_enabled` | all | `true` | N/A | N/A | NO | |
| `tools.default.disabled` | eng, arch, rsrch, qa, vrfy | `[computer_use]` | `--exclude-tools` / `--xt` | none excluded | YES | Conceptually similar. Pi's `--exclude-tools` could mirror Hermes's disabled tools list. Low risk — Pi doesn't have a `computer_use` tool, so it would be a no-op. |

**Risk note:** Hermes guardrails are disabled anyway (`hard_stop_enabled: false`). Pi defaults to no protection. If Pi needs safety rails, they'd need to be set independently.

---

## 6. Memory & Context

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `memory.provider` | all | `mnemosyne` | `pi-hermes-memory` extension | installed via npm | YES | The pi-hermes-memory extension bridges Pi to Hermes Mnemosyne. The choice of memory provider in Hermes determines which backend pi-hermes-memory connects to. Already aligned — both use Mnemosyne. |
| `memory.enabled` | all | `true` | `pi-hermes-memory` extension | installed | CONDITIONAL | If Hermes disables memory, Pi should also skip memory extension. Currently both enabled. |
| `context.engine` | all | `lcm` | `pi-lean-ctx` extension | installed via npm | NO | Different mechanisms. Hermes LCM compresses conversation context; pi-lean-ctx pre-fetches file context to avoid re-reads. Complementary, not equivalent. |
| `compression.enabled` | all | `true` | N/A | N/A | NO | Hermes conversation compression has no Pi analogue. Pi sessions are simpler (last-turns only). |
| `compression.protect_first_n` | all | `3` | N/A | N/A | NO | |
| `compression.protect_last_n` | all | `20` | N/A | N/A | NO | |
| `compression.target_ratio` | all | `0.2` | N/A | N/A | NO | |
| `compression.threshold` | all | `0.5` | N/A | N/A | NO | |
| `prompt_caching.cache_ttl` | all | `5m` | N/A | N/A | NO | Pi doesn't expose prompt caching config. |

---

## 7. Plugins & Skills

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `plugins.enabled` | root | `[hermes-lcm, mnemosyne]` | `packages` in settings.json | 7 packages | CONDITIONAL | Pi packages are installed via npm (not config). Hermes plugins are runtime-loaded. When a Hermes plugin has a Pi extension equivalent (e.g., pi-hermes-memory <-> mnemosyne), they should be kept in sync. Currently: pi-hermes-memory is installed whether or not mnemosyne plugin is enabled in all profiles. |
| | orch | `[hermes-lcm, mnemosyne, pier]` | | | CONDITIONAL | |
| | eng, qa | `[hermes-lcm, mnemosyne, pier]` | | | CONDITIONAL | |
| | arch, rsrch, vrfy | `[hermes-lcm, mnemosyne]` | | | CONDITIONAL | |
| `skills.creation_nudge_interval` | all | `15` | `--skill <path>` | no skill nudge | NO | Pi loads skills explicitly via CLI flag. No nudge/prompt to create skills. |
| `mcp_servers.*` | root only | `lean-ctx` | `--mcp-config <value>` (via extension) | loaded via settings | YES | Root config declares a lean-ctx MCP server. Pi loads it via the MCP extension config. Should be kept in sync. Already aligned via packages: `pi-lean-ctx` npm package + pi-lsp-extension. |

---

## 8. Web & Browser

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `web.backend` | all | `ddgs` | `pi-web-access` extension | installed via npm | NO | Pi's web access is provided by an extension package, not config-controlled. Hermes picks the search backend; Pi uses its own fetch-based approach. |
| `web.use_gateway` | all | `false` | N/A | N/A | NO | Gateway routing is Hermes infrastructure. |
| `browser.cloud_provider` | all | `local` | N/A | no browser tool | NO | Pi has no browser tool. |
| `browser.inactivity_timeout` | all | `120` | N/A | N/A | NO | |
| `browser.use_gateway` | all | `false` | N/A | N/A | NO | |

---

## 9. Display & Streaming

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `display.streaming` | all | `true` | N/A | always streaming | NO | Pi always streams tokens (CLI-only). Hermes display config is for the UI/shell layer. |
| `display.show_reasoning` | all | `false` | Pi does not show reasoning by default | off | NO | Different rendering. |
| `display.skin` | all | `default` | N/A | N/A | NO | |
| `streaming.enabled` | all | `false` | N/A | always streaming | NO | Different piping — Hermes streaming is for Discord/Telegram output; Pi is CLI-only. |

---

## 10. Session & Cron

| Hermes Key | Profiles | Hermes Value(s) | Pi Equivalent | Pi Current Value | Propagate? | Rationale |
|---|---|---|---|---|---|---|
| `session_reset.mode` | all | `none` | `--continue` / `--resume` | per-command | NO | Different session models. Hermes has automatic session management; Pi sessions are opt-in. |
| `session_reset.idle_minutes` | all | `1440` | `--session` / `--no-session` | ephemeral by default | NO | |
| `session_reset.at_hour` | all | `4` | N/A | N/A | NO | |
| `cronjob` / `kanban.*` | profiles with kanban | various | N/A | N/A | NO | Pi has no scheduling or multi-agent system. These are purely Hermes infrastructure. |
| `group_sessions_per_user` | all | `true` | N/A | N/A | NO | |

---

## 11. Keys with No Pi Equivalent (Excluded)

These Hermes keys have no Pi mapping and should **never** be propagated:

| Hermes Section | Reason |
|---|---|
| `onboarding.seen` | Internal state tracking |
| `updates.*` | Hermes update management |
| `stt.*` | Speech-to-text (not applicable) |
| `platform_toolsets.*` | Gateway tool routing (not applicable) |
| `known_plugin_toolsets.*` | Plugin tool discovery |
| `_config_version` | Internal versioning |
| `container_*` (under terminal) | Docker container resources |
| `docker_mount_cwd_to_workspace` | Docker-specific |
| `home_mode` | Terminal home dir convention |

---

## Summary of Propagated Keys

Keys recommended for **YES** / **CONDITIONAL** propagation:

| Priority | Hermes Key | Pi Target | Action |
|---|---|---|---|
| HIGH | `agent.max_turns` | `settings.maxTurns` | Match or Hermes >= Pi when delegating |
| HIGH | `agent.reasoning_effort` | `--thinking <level>` | Pass CLI flag when spawning Pi |
| MEDIUM | `agent.personalities.*` | `--system-prompt` / `--append-system-prompt` | Inject non-default personality as Pi system prompt |
| MEDIUM | `memory.provider` | pi-hermes-memory extension | Keep backend in sync |
| LOW | `agent.verbose` | `--verbose` flag | Pass when Hermes verbose is true |
| LOW | `tools.default.disabled` | `--exclude-tools` (--xt) | Mirror disabled tool list (no-op for Pi) |
| LOW | `delegation.max_iterations` | `settings.maxTurns` | Align for consistent turn budgets |
| LOW | `mcp_servers` | MCP config via extension | Keep lean-ctx MCP server registration in sync |
| CONDITIONAL | `plugins.enabled` vs `packages` in settings.json | Sync Pi package installs with Hermes plugin state | Only when a direct extension equivalent exists |

---

## Cross-Profile Config Summary

The 6 hswarm profiles + root config share ~90% of keys, but these diverge — all relevant to Pi propagation:

| Key | Root | orch | eng | arch | rsrch | qa | vrfy | Risk |
|---|---|---|---|---|---|---|---|---|
| `model.default` | deepseek-v4-flash | deepseek-v4-flash | deepseek-v4-pro | deepseek-v4-pro | deepseek-v4-flash | deepseek-v4-pro | ? | Low — Pi has own model selection |
| `agent.max_turns` | 150 | 80 | 150 | 150 | 150 | 150 | 150 | MEDIUM — orch spawns Pi with lower budget |
| `plugins.enabled` | lcm, mnemo | lcm, mnemo, pier | lcm, mnemo, pier | lcm, mnemo | lcm, mnemo | lcm, mnemo, pier | lcm, mnemo | Low — plugin != Pi package |
| `mcp_servers` | lean-ctx | absent | absent | absent | absent | absent | absent | Low — Pi already has lean-ctx via npm |

**Key finding:** The orch profile's `agent.max_turns: 80` is the only divergence that could affect Pi behavior negatively. All other divergences are Hermes-internal.

---

## Recommendation Summary

1. **Do NOT pass Hermes model config to Pi.** They run on independent provider stacks. Let Pi use its own `settings.json` defaults.

2. **Map `agent.max_turns` to Pi's maxTurns when delegating.** Set Pi's turns >= Hermes's remaining budget to prevent premature termination. Currently the orch profile (80 turns) could clip Pi sessions.

3. **Map `agent.reasoning_effort` to `--thinking`.** Simple 1:1 mapping — Hermes `medium` -> Pi `medium`.

4. **Map Hermes personality to `--system-prompt`** only when the personality is not "technical" (Pi's default). Prevents redundant overrides.

5. **Keep `memory.provider` in sync with pi-hermes-memory extension config.** Already aligned.

6. **Monitor Pi's `settings.json` lifecycle.** Currently no `~/.pi/settings.json` (project-local) exists. The global `~/.pi/agent/settings.json` is the stable source. Hermes should only ever modify the project-local override, not the global settings file.
