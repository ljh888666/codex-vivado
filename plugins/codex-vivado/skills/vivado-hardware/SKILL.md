---
name: vivado-hardware
description: "Program or debug FPGA hardware through an existing vivado-mcp connection after the user authorizes board access; use for JTAG, ILA, VIO, and board validation."
---

# Vivado hardware

Package provenance: machine=PC2. This is not a fixed target selection. Never reuse a serial number, cable, COM port, IP address, or board identity from the reference project as a discovered fact.

## Authorization and ownership

First check whether the user's existing instruction explicitly authorizes the intended board operation. Reuse that authorization within its stated scope. If absent, complete all offline preparation, then request the specific missing board authorization before connecting, programming, arming, or driving VIO. A request to install this plugin or inspect source files does not grant board access. Physical connections, power changes, and switches remain user actions unless explicitly handled by authorized external hardware.

Use the already configured long-lived vivado-mcp backend and only the hardware tools actually in its catalog; a Tcl tool may cover a missing operation after its command is verified. Do not install another hardware service, patch the backend, or silently change global settings. Coordinate shared Vivado/JTAG ownership before live use; this plugin provides no global arbitration across clients.

## Identify and prepare

After authorization, discover the current local machine, hardware server, cable/target/device, FPGA part, and any required serial interface. Match the target to the user's intended board before writes. If multiple targets cannot be distinguished safely, stop the dependent operation and ask for that identity. Do not infer a PC1 or remote-board result from a PC2 observation.

Resolve the exact bitstream and matching probes file from the same build; record hashes and build timing status. Use ASCII paths. Prepare a recovery image or documented rollback when the task calls for programming. Verify current tool schemas and installed-version command properties before using them.

## ILA and VIO

For capture, inspect the loaded probes and their clock domains before configuring a trigger. In one live session: configure/arm, apply the authorized traffic or stimulus, wait for the trigger, upload, then export complete data. Preserve trigger configuration, sample depth, clock/domain, capture status, and exported file path/hash. A trigger that never fires is missing evidence, not a passing or failing data-path verdict. Do not transfer an armed state across separate server/session invocations.

For VIO writes, inspect widths, directions, current values, and reset/enable effects first. Apply only the requested values, read them back, and restore transient settings when the test calls for it. Do not treat historical property names or depth limits as valid for every Vivado/IP version.

## Report the observed scope

Distinguish link-up, end-to-end transport, and payload correctness; verify only the criteria actually exercised. Record machine, board identity, artifact hashes, commands/stimulus, counters, captures, and pass/fail thresholds. Include failed or untriggered criteria explicitly. Use causal evidence levels from $vivado-workflow; local link status alone cannot establish a remote board received data.
