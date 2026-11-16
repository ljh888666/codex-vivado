---
name: amd-doc-search
description: "Find AMD/Xilinx official documentation for Vivado Tcl, IP parameters, timing, CDC, AXI, Aurora, MIG, and hardware debug; use public non-confidential queries with version checks."
---

# AMD documentation search

Package provenance: machine=PC2. This skill uses a local helper to query AMD's hosted documentation search; queries leave the machine. Use public product terminology only. Do not send private RTL, project identifiers, confidential logs, NDA material, secrets, or restricted design details. For those requests, use an approved local documentation source or ask for a sanitized public query.

## Resolve and run the bundled helper

Resolve this skill's actual directory from the loaded `SKILL.md` path. The helper is at `../../scripts/amd_doc_search.py` relative to that directory, inside the same plugin. Use the configured Python interpreter with an absolute helper path; do not assume the shell's current directory is the plugin. Inspect `--help` for the installed helper's exact options before the first invocation. The helper requires no Vivado process.

Search a focused command, property, protocol, or IP term. Include the intended version and family through supported options and in the query when useful. If the service is unavailable, use the user's installed AMD manuals or official `docs.amd.com` / `adaptivesupport.amd.com` pages and identify that fallback. Do not invent search results or imply a failed search verified a fact.

## Verify every result

Treat search version/family filters as hints. Inspect each returned result's own `version` and `family` metadata and the destination page, and record missing metadata as unknown. Verify the document/IP identity and the exact command/property context, not just a matching title. Cite the genuine AMD destination URL. Clearly distinguish a newer example, a default, and a rule verified for the installed release.

The reference project's declared baseline is Vivado 2023.1 with `xcku060-ffva1156-2-i`; these are comparison targets, not runtime discoveries. Bind any implementation claim to the user's actual Vivado version, FPGA family/part, IP/BD instance and parameters, and the local verification action or evidence. Kintex UltraScale and UltraScale+ are distinct families: do not silently substitute one result for the other.

AMD documentation is authoritative for documented command/protocol semantics; it does not establish local board pins, actual IP configuration, hardware identity, or measured behavior. If documentation and local measurements differ, check version/device/IP alignment, then report both sources with their scope. Without the official source and project binding, describe the idea as a hypothesis or proposed experiment rather than a root cause.
