---
name: golden-dragon-fusion
description: Combine Golden Dragon capabilities into one workflow that produces and verifies a requested deliverable.
---
Start with the intended output, source material and acceptance criteria. Read references/combined.md for the combined methods grouped by work stage. Compose across stages: use inspection findings to set constraints, pass the plan and inputs to production, pass actual production outputs to verification, and deliver only verified results. When two capabilities overlap, apply their complementary checks once. For reverse analysis, use passive inspection of documented formats, metadata, dependencies and provenance. Treat references as knowledge, partial capabilities as limited, and missing prerequisites as unavailable. Resolve installed execution details with the project's dragon_fusion.py show command. Preserve applicable permissions and costs. Distinguish a plan from an executed output.
For a requested 1080x1920 vertical MP4 from a local video, run python scripts/render_vertical.py INPUT NEW_OUTPUT.mp4 from this skill directory. It preserves the complete frame with padding and verifies the exported stream.
