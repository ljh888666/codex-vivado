---
name: vivado-workflow
description: "Operate Vivado projects through an existing vivado-mcp connection; use for project inspection, synthesis, implementation, and FPGA development workflows."
---

# Vivado workflow

Package provenance: machine=PC2. This identifies the authoring environment, not the machine running this skill. Read the current repository instructions and plugin configuration before using machine-specific paths or board facts.

## Route the requested work

- Inspect the actual connected tool catalog and input schemas. Backend versions and optional patches expose different parameters and tool counts; a skill does not install or create tools. Use the current schema rather than arguments copied from another machine.
- Read existing project scripts, logs, reports, XDC, and output timestamps first. Historical analysis and static file checks do not require a Vivado process. Use $vivado-reports for those tasks.
- If project state must change, prefer a suitable connected MCP tool. A supported Tcl execution tool is appropriate for project operations absent from the catalog. Do not start a second MCP server through a one-call CLI bridge for session operations: sessions belong to the long-lived server process.
- Run synthesis or implementation only when requested or needed to complete the authorized task. Reuse matching completed runs and checkpoints where valid. Project-run tools do not automatically implement checkpoint-based Tcl flows.
- Use $vivado-hardware for programming, JTAG, ILA, VIO, or board validation. Development authorization alone does not authorize board access.

## Before a live operation

Discover the actual project, Vivado executable/version, part, active sessions, and existing runs. Keep all paths passed to Vivado/Tcl, including temporary and backend paths, ASCII. Preserve original vendor RTL; make scoped derived files when necessary.

Vivado access is globally serial in this workflow. Coordinate with the user or other active clients before opening or using the shared installation. This plugin does not provide a cross-process or cross-host lock. Never assume its launcher excludes DSH, GUI, xsct, or another Codex session; do not terminate their processes automatically.

Prefer existing project Tcl scripts over recreating flows. Verify Tcl commands and version-specific properties from AMD documentation through $amd-doc-search when public queries are appropriate. A configuration baseline of Vivado 2023.1 is not proof of the locally running version.

## Build and verify

For a supported project-run tool, submit with its asynchronous option (for example, `wait=false` only when present in the schema), retain the session/run/job identifiers, then poll the corresponding status tool. A returned identifier means submitted, not complete. A timeout does not prove the command stopped. Do not duplicate the run until its state is known.

Judge success using process status, run status, errors, artifact existence, and reports together. A protocol-level success containing `[ERROR]` is a failed operation. Keep complete logs in the authorized output directory; preserve hashes for bitstreams, ELF, and important comparison artifacts. Finalize using the requested design/board criteria, not file existence alone.

Record machine identity, tool/version, project/part, inputs, command, artifact hash, and evidence location. Explain why each material change follows from evidence. Label causal findings as follows: L0 speculative candidate (do not record as a finding); L1 compatible hypothesis; L2 at least two orthogonal positive/negative controls, pending exhaustive check/retest; L3 directly observed mechanism with known alternatives excluded, pending repaired retest; L4 controls, unique compatible explanation, and repaired retest complete. Do not turn exclusion of one cause into proof of another.
