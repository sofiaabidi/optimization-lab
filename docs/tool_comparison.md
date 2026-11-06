# AI Tool Comparison

A standalone 0/1 knapsack problem was implemented independently using Codex (GPT-5.6 Sol Medium, as displayed in the captured UI) and Antigravity (Claude Sonnet 4.6 Thinking).

Both implementations used dynamic programming and passed their stated standard test cases. Codex handled the zero-capacity, zero-weight-item edge case more completely. Antigravity generated a Python file and executed its tests.

Both tasks completed in one prompt iteration. Exact response times were not recorded, so no timing comparison is claimed.

- Codex evidence: [`prompts/tool_comparison/codex_screenshot.png`](../prompts/tool_comparison/codex_screenshot.png)
- Antigravity evidence: [`prompts/tool_comparison/antigravity_screenshot.png`](../prompts/tool_comparison/antigravity_screenshot.png)
- Detailed discussion: [final technical report](../reports/Optimization_Techniques_Assignment8_Report_Final.pdf)
