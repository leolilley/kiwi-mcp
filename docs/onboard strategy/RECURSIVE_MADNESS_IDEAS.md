# Recursive Madness Demo Ideas

**Status:** Raw brainstorm, implement later  
**Purpose:** Show off 10-deep recursion (Claude Code caps at 2)

---

## Phase 5: Recursive Madness (What Claude Code Can't Do)

| Demo | Name | Concept |
|------|------|---------|
| 18 | Fractal Generation Chain | 10 agents each add ~5 lines to build a working fractal generator |
| 19 | Telephone Game | Message mutates through 10 agents, track corruption |
| 20 | Distributed Prime Factorization | Each agent finds ONE prime factor, passes quotient |

## Phase 6: Emergent Chaos (Let It Surprise You)

| Demo | Name | Concept |
|------|------|---------|
| 21 | Evolution Tournament | Agents compete, winners spawn mutated children |
| 22 | Rumor Spreading | Agents gossip, track info corruption patterns |
| 23 | Collaborative Storytelling | Each agent writes ONE sentence of a story |

## Phase 7: THE IMPOSSIBLE (Pure Flex)

| Demo | Name | Concept |
|------|------|---------|
| 24 | Recursive Quine | Agent spawns agent that recreates parent's code |
| 25 | Agent Archaeology | 10 layers deep, last one "digs up" first's state |
| 26 | The Ouroboros | Circular chain: Agent 10 feeds back to Agent 1, detects cycle safely |

---

## Demo Details

### Demo 18: Fractal Generation Chain
Each agent does ONE thing:
- Agent 1: Write `fractal.py` header
- Agent 2: Add base case (depth=0, draw square)
- Agent 3: Add recursive call (spawn 4 children)
- Agent 4: Add rotation logic
- Agent 5: Add color gradient
- Agent 6: Add file output setup
- Agent 7: Add main() entry point
- Agent 8: Run the script
- Agent 9: Verify output file exists
- Agent 10: Generate summary report

### Demo 19: Telephone Game
- Agent 1 gets: `"The quick brown fox jumps"`
- Each agent: **change exactly ONE word**, pass it on
- Agent 10: Report final vs original
- Track mutation log through state files

### Demo 20: Distributed Prime Factorization
- Input: 2310
- Agent 1: Find smallest factor (2), divide, pass 1155
- Agent 2: Find smallest factor (3), divide, pass 385
- ...continues until quotient = 1
- Each writes factor to `factors.txt`
- Final agent verifies: product = original

### Demo 26: The Ouroboros
```
Agent 1 → Agent 2 → ... → Agent 10 → Agent 1 (with accumulated state)
                                         ↓
                              Detects cycle, halts gracefully
```
Shows safe recursion detection in circular topologies.

---

_Saved: 2026-01-28_
