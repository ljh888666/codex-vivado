---
name: vivado-reports
description: "Analyze existing Vivado logs, timing reports, CDC reports, XDC, and resource evidence without launching Vivado; use for report review and offline diagnosis."
---

# Vivado reports

Package provenance: machine=PC2. Determine the actual machine and source artifact for every reported observation.

## Stay on the available evidence

Locate the requested files using project scripts and paths. Preserve originals and write analysis only in an authorized output directory. This skill needs no Vivado process. Use supported offline MCP parameters when available (for example a report file or explicit XDC paths), otherwise parse files using local tools. Check the current schema before invoking a tool; do not create a session solely because the offline route is unfamiliar.

Capture file path, hash, modification time, report tool/version, part, design stage, run/checkpoint, and relevant constraints when present. Missing fields remain unknown. Separate reports from different designs or stages; a post-synthesis estimate is not a post-route result. A saved checkpoint or a successful bitstream write alone does not prove timing closure.

## Extract and cross-check

- Timing: report setup WNS/TNS and hold WHS/THS separately, with units, failing endpoints, and source lines. Distinguish unconstrained paths, missing clocks, pulse-width findings, and parser failures from a passing result. Compare baselines only after matching design stage, part, clocks, constraints, and run context.
- Logs: collect every error and critical warning relevant to the request, preserving source line references and surrounding context. A clean tail is not proof the entire run passed; inspect terminal status and scan the full log.
- CDC: retain clock domains, crossing type, severity, and instances. A reported synchronization pattern is evidence to inspect, not proof of functional correctness. Do not add false paths or clock groups solely to remove a warning.
- XDC: use explicit files for static checks where supported. Identify parser limitations and conditional/procedural content requiring version-specific interpretation. Do not declare a command or Tcl construct legal/illegal from memory or from another project's historical note; verify the installed version against official documentation when needed.
- Utilization: identify the hierarchy and whether counts come from synthesis or implementation. Keep resource totals and percentages tied to the stated part.

Read full source data. If the requested response is shorter, retain the complete findings in a file and label the response as a summary with total counts and its evidence path. Do not silently drop findings because a backend truncates output: inspect its limits, request complete evidence when supported, or read the original file. Requesting a small diagnostic sample does not authorize calling it the full report.

## Explain without overclaiming

Separate observation, hypothesis, discriminating experiment, and conclusion. Cite exact source lines and report fields for numerical claims. A single-sided comparison supports only an L1 hypothesis; use the causal evidence levels in $vivado-workflow for stronger claims. If the next necessary step would start a process or change the design, state why and follow the authorized workflow instead of silently expanding this offline review.
