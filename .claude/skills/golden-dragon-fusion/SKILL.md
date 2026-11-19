---
name: golden-dragon-fusion
description: Combine Golden Dragon capabilities into one workflow that produces and verifies a requested deliverable.
---
Start by reading references/working-method.md. Apply its cross-domain checks to one deliverable. Start with the intended output, source material and acceptance criteria. Read references/combined.md for the combined methods grouped by work stage. Compose across stages: use inspection findings to set constraints, pass the plan and inputs to production, pass actual production outputs to verification, and deliver only verified results. When two capabilities overlap, apply their complementary checks once. For reverse analysis, use passive inspection of documented formats, metadata, dependencies and provenance. Treat references as knowledge, partial capabilities as limited, and missing prerequisites as unavailable. When the full repository is available, resolve catalog details with apps/golden-dragon/app/dragon_fusion.py show ID. A standalone installation can work from its bundled references. Preserve applicable permissions and costs. Distinguish a plan from an executed output.
For a requested 1080x1920 vertical MP4 from a local video, run python scripts/render_vertical.py INPUT NEW_OUTPUT.mp4 from this skill directory. It preserves the complete frame with padding and verifies the exported stream.
Use python scripts/fusion.py inspect-windows FILE for read-only Windows binary identification, section inventory and SHA-256. Use python scripts/fusion.py vertical-video INPUT OUTPUT for the verified video workflow.
For a request involving vertical conversion, Windows file inspection, or both, pass the full request and its attached file paths to scripts/request.py in one call. Supply --output for video. Report only the completed fields in its JSON; handle any additional requested work separately.

## Combine the capabilities for one request

Use the catalog entries according to their role. Skills provide methods; playbooks provide sequencing; commands, programs, engines and tools provide operations. Libraries contribute reusable components. Studios and MCP services need their own configured runtime. Lessons contribute checks. Analysis tools can supply read-only format, inventory and provenance evidence. An entry marked reference or needing setup can inform a decision before a runtime is available.

For each requested output, work backward from its acceptance check. Combine compatible methods into a single sequence, binding each operation to a real input and passing its observed result forward. Preserve requests that remain unsupported in the final status. Do not silently drop them when a partial workflow succeeds.

## Installation and prerequisites

The complete skill directory is portable. For Claude Code use the repository copy under .claude/skills; for Codex use .agents/skills. For another installation copy one complete golden-dragon-fusion directory into that client's supported skill location. A plain ChatGPT conversation needs the skill content and an enabled execution connection for local operations. Publishing this repository alone does not configure that connection.

The bundled runners require Python 3.11 or newer. Windows file inspection requires pefile. Video conversion requires ffmpeg and ffprobe on PATH and a destination filesystem supporting hard links.
