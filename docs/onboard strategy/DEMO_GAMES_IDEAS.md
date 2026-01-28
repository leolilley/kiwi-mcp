# Demo Game Ideas

**Status:** Raw brainstorm  
**Purpose:** Interactive games that teach Kiwi MCP through play

---

## Game 1: The Kiwi Escape Room 🔐

**Vibe:** Puzzle-solving, discovery, pressure  
**Teaches:** search, load, execute, permissions, tool chaining

### Concept

User + Agent dropped into a "locked" MCP sandbox. Explore tools, chain directives, solve puzzles to escape.

### The Vault

```
┌─────────────────────────────────────────────────────────┐
│  THE VAULT                                              │
│                                                         │
│  You have access to:                                    │
│  • 5 tools (some hidden, some locked)                   │
│  • 3 knowledge entries (clues scattered inside)         │
│  • 2 directives (one needs a "key" to run)              │
│                                                         │
│  CHALLENGES:                                            │
│  🔒 Level 1: Find the hidden tool                       │
│  🔒 Level 2: Combine two tools to decrypt a message     │
│  🔒 Level 3: Chain 3 directives to unlock the vault     │
│  🔒 Level 4: Build your own escape directive            │
│                                                         │
│  State persists. Hints cost "tokens". Time is tracked.  │
└─────────────────────────────────────────────────────────┘
```

### Mechanics

| Mechanic               | Implementation                                          |
| ---------------------- | ------------------------------------------------------- |
| **Discovery**          | `search` returns partial results, must guess keywords   |
| **Locked tools**       | Need permission token found in knowledge entries        |
| **Clue trail**         | Knowledge entries reference each other cryptically      |
| **Chaining**           | Some puzzles require output of Tool A → input of Tool B |
| **Creative solutions** | Multiple valid paths, reward clever combos              |
| **Scoring**            | Fewer hints = higher score, track in state file         |
| **Time pressure**      | Optional speedrun mode                                  |

### Example Puzzle Flow

```
User: "search tools"
Agent: [finds: calculator, encoder, ???]

User: "what's ???"
Agent: [permission denied - need KEY_ALPHA]

User: "search knowledge"
Agent: [finds: welcome_note, old_journal, ???]

User: "load welcome_note"
Agent: "Welcome... the first key is hidden where numbers meet letters..."

User: "use encoder on '1=A 2=B 3=C'"
Agent: [outputs: "KEY_ALPHA"]

User: "now load that hidden tool!"
Agent: [decryptor tool unlocked!]
```

### Why It Works

- Teaches by doing, not reading
- Encourages exploration
- Shows tool chaining naturally
- Permissions feel meaningful
- Replayable (randomize puzzles)
- Competitive (leaderboards, speedruns)

---

## Game 2: The Knowledge Garden 🌸

**Vibe:** Emergence, butterfly effect, deep recursion  
**Teaches:** recursive spawning, knowledge mutation, parallel evolution, state as living system

### Concept

User sets initial configuration. Then triggers a recursive evolution cascade. Each agent reads knowledge, mutates it based on its directive, spawns child agents. Children read the mutated state, make their own decisions, mutate further, spawn more. 10+ layers deep. Parallel branches. The "garden" IS the knowledge base - all the files being mutated by the recursive agent swarm.

User watches their initial choices cascade through generations.

### The Garden = The Knowledge Base

```
.ai/knowledge/garden/
├── climate.md         ← affects growth rates, mutation chance
├── soil.md            ← resource pool, depletes and regenerates
├── species_a.md       ← evolving entity (traits, fitness, lineage)
├── species_b.md       ← another evolving entity
├── species_c.md       ← emerges from crossover events
├── weather_log.md     ← random events that occurred
├── generation_log.md  ← full history of who spawned who
└── ecosystem.md       ← aggregate state, relationships
```

**Every file is a living piece of the garden. Agents read and mutate these.**

### Execution Model

```
User sets config:
  - Initial species traits
  - Climate parameters
  - Mutation rate
  - Parallel branches allowed

User: "run garden evolution 10 generations"

Generation 1:
  Agent_1a spawns → reads species_a.md, climate.md
                  → decides: "grow" (fitness +2)
                  → mutates species_a.md
                  → spawns Agent_2a

  Agent_1b spawns → reads species_b.md, climate.md (parallel)
                  → decides: "spread" (claims soil)
                  → mutates species_b.md, soil.md
                  → spawns Agent_2b

Generation 2:
  Agent_2a reads MUTATED species_a.md
          → sees new traits from Gen 1
          → decides based on NEW state
          → mutates further
          → spawns Agent_3a

  Agent_2b reads MUTATED species_b.md
          → soil is depleted (Agent_1b took it)
          → decides: "compete" or "adapt"
          → spawns Agent_3b

... continues 10 generations deep ...

Final state:
  Knowledge files show full evolutionary history
  Species have diverged based on initial config
  Emergent behaviors user didn't predict
```

### What Agents Actually Do

Each agent runs ONE directive that:

1. Reads relevant knowledge files
2. Makes ONE decision based on current state
3. Mutates ONE or more knowledge files
4. Spawns next generation agent(s)

```xml
<directive name="garden_evolve_step">
  <inputs>
    <input name="species_id" />
    <input name="generation" />
  </inputs>
  <process>
    <step name="read_state">
      Read: species_{id}.md, climate.md, soil.md
    </step>
    <step name="decide">
      Based on traits + environment:
      - If fitness > threshold → grow
      - If resources scarce → compete or migrate
      - If near other species → crossover chance
      Random mutation chance based on climate
    </step>
    <step name="mutate">
      Write decision outcome to species_{id}.md
      Update soil.md if resources consumed
      Log to generation_log.md
    </step>
    <step name="spawn_next">
      If generation < max_generations:
        Spawn agent for generation + 1
        Maybe spawn parallel branch (split species)
    </step>
  </process>
</directive>
```

### Seasons = Batch Phases

```
Spring (Gen 1-3):   High growth, high mutation, resources abundant
Summer (Gen 4-6):   Peak competition, crossover events, drought chance
Autumn (Gen 7-8):   Resources deplete, consolidation, weak species die
Winter (Gen 9-10):  Dormancy, only fittest survive, mutations lock in
```

**Random events inject at season boundaries:**

- Drought: soil.md resources halved
- Bloom: mutation rate doubles
- Plague: random species fitness reduced
- Discovery: new trait unlocked

### User's Role

User makes decisions ONLY at the start:

```
User: "init garden"
Agent: Configure your garden:

       Species A traits: [aggressive / passive / adaptive]
       Species B traits: [aggressive / passive / adaptive]
       Climate: [tropical / temperate / harsh]
       Mutation rate: [low / medium / high]
       Parallel branches: [1 / 2 / 4]
       Generations: [5 / 10 / 20]

User: "species A: aggressive, species B: adaptive,
       climate: harsh, mutation: high, branches: 2, generations: 10"

Agent: 🌱 Garden initialized. Starting evolution...

       [10 generations of recursive agent spawning begins]
       [User watches as knowledge files mutate in real-time]
       [Final state emerges from initial choices]
```

### What User Sees

```
Gen 1:  🌱 A grew (+2 fitness)     🌱 B adapted to harsh climate
Gen 2:  🌿 A consumed resources    🌿 B found niche
Gen 3:  🌳 A dominant              🌿 B surviving
        ⚡ DROUGHT EVENT - soil depleted
Gen 4:  💀 A struggling (no soil)  🌳 B thriving (adapted earlier)
Gen 5:  🌿 A mutated: now adaptive 🌳 B spreading
        🔀 CROSSOVER: Species C emerges (A×B hybrid)
Gen 6:  🌿 A recovering            🌳 B peak                🌱 C emerging
...
Gen 10: 💀 A extinct               🌳 B dominant            🌿 C niche survivor

FINAL GARDEN STATE:
  species_a.md: { status: "extinct", peak_gen: 3, cause: "resource_depletion" }
  species_b.md: { status: "dominant", fitness: 47, traits: ["adaptive", "hardy", "spreader"] }
  species_c.md: { status: "survivor", fitness: 12, origin: "crossover_gen5" }
  ecosystem.md: { biodiversity: 2, total_generations: 10, events: 3 }
```

### Why This Is Insane

1. **Deep recursion demo** - 10+ generations, each is a spawned agent
2. **Parallel execution** - multiple branches evolving simultaneously
3. **Knowledge as living state** - files ARE the garden
4. **Butterfly effect** - initial config cascades unpredictably
5. **Emergent behavior** - outcomes user didn't design
6. **Tight context** - each agent only knows its slice
7. **Safe recursion** - controlled depth, graceful termination
8. **Visual payoff** - watch the garden evolve in real-time

### Variations

- **Competitive mode:** Two users, their species compete in shared garden
- **Sandbox mode:** User can intervene mid-evolution (inject events)
- **Speedrun mode:** Minimize generations to reach target fitness
- **Archaeology mode:** Given final state, deduce what initial config caused it

---

## Game 3: The Archaeology Dig 🔍

**Vibe:** Reverse engineering, detective work, reasoning backwards  
**Teaches:** inference from state, backward chaining, hypothesis testing

### Concept

User is given a FINAL mutated knowledge state. They don't know what happened. Spawn recursive agents that work BACKWARDS through the state, deducing what sequence of events led here. Each agent examines clues, forms hypotheses, spawns child agents to investigate deeper.

**It's CSI for knowledge evolution.**

### The Crime Scene

```
.ai/knowledge/archaeology/
├── final_state.md      ← The end result (given to user)
├── hypothesis_log.md   ← Agents record their theories here
├── evidence/
│   ├── clue_001.md     ← Discovered during investigation
│   ├── clue_002.md
│   └── ...
├── timeline.md         ← Reconstructed sequence (built backwards)
└── verdict.md          ← Final conclusion
```

### Execution Model

```
User given: final_state.md
  "Species B is dominant. Species A is extinct.
   Species C exists but is weak. Soil is depleted.
   3 major events occurred."

User: "investigate"

Agent_1 spawns → reads final_state.md
              → observes: "A extinct, B dominant"
              → hypothesis: "A lost competition to B"
              → writes to hypothesis_log.md
              → spawns Agent_2a (investigate A's death)
              → spawns Agent_2b (investigate B's rise) [parallel]

Agent_2a → reads clues about A
        → finds: "A had peak at gen 3, then crashed"
        → hypothesis: "resource depletion after overexpansion"
        → spawns Agent_3a (find what depleted resources)

Agent_2b → reads clues about B
        → finds: "B has 'adaptive' trait, acquired gen 1"
        → hypothesis: "B adapted early to harsh conditions"
        → spawns Agent_3b (what were initial conditions?)

... 10 layers of investigation ...

Final reconstruction:
  "Initial config was: A=aggressive, B=adaptive, climate=harsh
   Gen 3: A overexpanded, consumed all soil
   Gen 4: Drought event hit, A couldn't survive
   Gen 5: B thrived, crossover created C
   Gen 10: B dominant, C surviving, A extinct"

User compares to ACTUAL initial config → Score based on accuracy
```

### What Agents Do

Each investigation agent:

1. Reads current evidence/hypotheses
2. Forms ONE new hypothesis or finds ONE new clue
3. Writes findings to evidence/
4. Spawns specialized child agents to investigate further

```xml
<directive name="archaeology_investigate">
  <inputs>
    <input name="focus_area" />  <!-- "extinction", "dominance", "event" -->
    <input name="depth" />
  </inputs>
  <process>
    <step name="examine">
      Read all evidence in focus_area
      Look for patterns, anomalies, timestamps
    </step>
    <step name="hypothesize">
      Form ONE hypothesis about what happened
      Rate confidence: low/medium/high
    </step>
    <step name="record">
      Write to hypothesis_log.md
      If found new clue, write to evidence/clue_XXX.md
    </step>
    <step name="delegate">
      If hypothesis needs verification:
        Spawn child agent with narrower focus
      If depth < max:
        Continue investigation
    </step>
  </process>
</directive>
```

### Difficulty Levels

| Level      | Clues Given         | Max Depth | Parallelism |
| ---------- | ------------------- | --------- | ----------- |
| Easy       | Many clues visible  | 5         | 2 branches  |
| Medium     | Some clues hidden   | 8         | 3 branches  |
| Hard       | Minimal clues       | 10        | 4 branches  |
| Impossible | Only final_state.md | 15        | Unlimited   |

### Scoring

```
Accuracy Score:
  - Correct initial config guess: +50 pts
  - Correct event sequence: +10 pts each
  - Correct causation chains: +5 pts each

Efficiency Score:
  - Fewer agents spawned: +bonus
  - Faster convergence: +bonus
  - Less redundant investigation: +bonus

Final: Accuracy × Efficiency multiplier
```

### Why It's Cool

1. **Reverse recursion** - agents work BACKWARDS, unusual pattern
2. **Inference demo** - shows LLM reasoning from evidence
3. **Hypothesis testing** - scientific method via agent spawning
4. **Collaborative deduction** - parallel investigation branches
5. **Measurable success** - compare reconstruction to ground truth
6. **Replayable** - generate new mysteries from garden runs

---

## Game 4: The Debate Arena ⚔️

**Vibe:** Adversarial, dialectic, emergent truth  
**Teaches:** multi-agent argumentation, knowledge as contested territory, synthesis

### Concept

Two (or more) positions start arguing. Each side spawns agents to make deeper counter-arguments. Arguments reference and mutate shared knowledge. Debate goes 10+ rounds deep. User watches discourse evolve. Final synthesis emerges from the clash.

**It's a recursive Socratic dialogue.**

### The Arena

```
.ai/knowledge/arena/
├── motion.md           ← The proposition being debated
├── side_a/
│   ├── argument_1.md   ← Initial position
│   ├── argument_2.md   ← Response to B's counter
│   └── ...
├── side_b/
│   ├── counter_1.md    ← Initial counter
│   ├── counter_2.md    ← Response to A's response
│   └── ...
├── evidence/
│   ├── fact_001.md     ← Cited by both sides
│   └── ...
├── concessions.md      ← Points each side gave up
├── synthesis.md        ← Emergent agreement (built over time)
└── transcript.md       ← Full debate log
```

### Execution Model

```
User: "debate: 'Tabs are better than spaces'"

Round 1:
  Agent_A1 spawns → argues FOR tabs
                  → writes side_a/argument_1.md
                  → cites evidence/
                  → spawns Agent_A2 (prepare next argument)

  Agent_B1 spawns → argues AGAINST tabs (parallel)
                  → writes side_b/counter_1.md
                  → challenges A's evidence
                  → spawns Agent_B2

Round 2:
  Agent_A2 → reads B1's counter
          → finds weakness in B's argument
          → writes side_a/argument_2.md
          → maybe CONCEDES a minor point → writes to concessions.md
          → spawns Agent_A3

  Agent_B2 → reads A2's response
          → escalates with new evidence
          → spawns Agent_B3

... 10 rounds ...

Round 10:
  Both sides exhausted main arguments
  Synthesis agent spawns → reads ALL arguments
                        → identifies common ground
                        → writes synthesis.md
                        → "Both sides agree on X, disagree on Y,
                           optimal solution is Z"
```

### Argument Structure

Each debate agent must:

1. Read opponent's latest argument
2. Identify weakest point
3. Formulate ONE counter-argument
4. Optionally cite or create evidence
5. Optionally concede minor points (strengthens credibility)
6. Spawn next round agent

```xml
<directive name="arena_argue">
  <inputs>
    <input name="side" />       <!-- "a" or "b" -->
    <input name="round" />
    <input name="opponent_arg" />
  </inputs>
  <process>
    <step name="analyze">
      Read opponent's argument
      Identify: strongest point, weakest point, unstated assumptions
    </step>
    <step name="counter">
      Attack weakest point OR undermine assumption
      Support with evidence (cite or create)
    </step>
    <step name="concede">
      If opponent made valid point:
        Concede gracefully (builds ethos)
        Record in concessions.md
    </step>
    <step name="escalate">
      Write argument to side_{side}/argument_{round}.md
      Spawn next round agent
    </step>
  </process>
</directive>
```

### Debate Modes

| Mode              | Sides | Rounds | Special Rules                             |
| ----------------- | ----- | ------ | ----------------------------------------- |
| **Binary**        | 2     | 10     | Classic pro/con                           |
| **Triad**         | 3     | 8      | Triangular tension                        |
| **Battle Royale** | 5     | 6      | Last argument standing                    |
| **Steelman**      | 2     | 10     | Must strengthen opponent before attacking |
| **Synthesis**     | 2     | 5      | Goal is agreement, not winning            |

### Judge Agent

After final round:

```
Judge spawns → reads entire transcript
            → scores arguments:
                - Logical validity
                - Evidence quality
                - Concession handling
                - Rhetorical effectiveness
            → declares winner OR synthesis quality
            → writes verdict.md
```

### Why It's Wild

1. **Adversarial recursion** - agents actively oppose each other
2. **Knowledge as battleground** - evidence files get contested
3. **Emergent synthesis** - truth from dialectic clash
4. **Deep reasoning chains** - 10 rounds of counter-arguments
5. **Measurable outcome** - judge scoring, clear winner
6. **Actually useful** - explore complex decisions via debate

### Example Topics

- Technical: "Monorepo vs polyrepo"
- Philosophical: "Should AI have rights?"
- Practical: "Remote work vs office"
- Absurd: "Is a hotdog a sandwich?"

---

## Game 4.5: Wiki Race 🌐 (Bonus Mini-Game)

**Vibe:** Speed racing, HTTP calls, link-hopping recursion  
**Teaches:** recursive spawning with external API calls, parallel racing, shortest-path discovery

### Concept

Classic Wikipedia race: Start on random page A, reach target page B by clicking links only. But here, EACH CLICK IS A NEW AGENT. Agent reads page via HTTP, picks a link, spawns child agent with that link. First to reach target wins.

Run 10+ races in parallel. Watch different strategies emerge.

**It's 6 Degrees of Wikipedia, powered by recursive agents.**

### The Race

```
.ai/knowledge/wikirace/
├── races/
│   ├── race_001/
│   │   ├── config.md       ← Start: "Banana", Target: "World War II"
│   │   ├── path.md         ← Current chain of pages visited
│   │   ├── status.md       ← Running/Won/Lost/Stuck
│   │   └── hops/
│   │       ├── hop_01.md   ← Page content + link chosen
│   │       ├── hop_02.md
│   │       └── ...
│   ├── race_002/
│   └── ... (10+ parallel races)
├── leaderboard.md          ← Fastest wins, shortest paths
└── discoveries.md          ← Weird/funny paths found
```

### Execution Model

```
RACE START:

  Config: Start="Banana" → Target="World War II"

Agent_1 spawns:
  → HTTP GET wikipedia.org/wiki/Banana
  → Parses page, extracts all links
  → Decides: "Food" seems promising toward wars? No...
            "Plant" → "Agriculture" → possible path
            "Yellow" → dead end probably
  → Picks: "Fruit"
  → Writes hop_01.md: {page: "Banana", chose: "Fruit", reasoning: "..."}
  → Spawns Agent_2 with target="Fruit"

Agent_2 spawns:
  → HTTP GET wikipedia.org/wiki/Fruit
  → Parses, extracts links
  → Sees: "Agriculture", "Trade", "History"
  → Picks: "Trade" (getting closer to human history!)
  → Writes hop_02.md
  → Spawns Agent_3

Agent_3:
  → wiki/Trade
  → Sees: "Economy", "War", "History", "Merchant"
  → Picks: "War" ← GETTING WARM
  → Spawns Agent_4

Agent_4:
  → wiki/War
  → Sees: "World War I", "World War II", "Military"
  → Picks: "World War II" ← TARGET FOUND!

RACE WON in 4 hops!
  Path: Banana → Fruit → Trade → War → World War II
```

### Parallel Racing

```
10 RACES SIMULTANEOUSLY:

Race 001: "Banana" → "World War II"
  Status: Won in 4 hops ✓

Race 002: "Pizza" → "Moon Landing"
  Status: Hop 6... Italy → Space? Still searching...

Race 003: "Kangaroo" → "Shakespeare"
  Status: Hop 3... Australia → British Empire → ???

Race 004: "Mathematics" → "Pizza"
  Status: Won in 7 hops ✓
  Path: Mathematics → Italy → Cuisine → Pizza

Race 005: "Eiffel Tower" → "Dinosaur"
  Status: Hop 12... STUCK in geography loop!

Race 006: "Coffee" → "Ancient Egypt"
  Status: Hop 5... Trade routes working!

Race 007: "Internet" → "Julius Caesar"
  Status: Won in 3 hops! ✓✓✓ RECORD!
  Path: Internet → History → Roman Empire → Julius Caesar

Race 008: "Dog" → "Quantum Physics"
  Status: Hop 9... Biology → Science → Physics... almost!

Race 009: "Football" → "Mozart"
  Status: Hop 4... Sports → Europe → Austria → ???

Race 010: "Volcano" → "Video Games"
  Status: Hop 8... Geology → Japan → Technology... close!
```

### Agent Strategy

Each agent must decide which link to follow:

```xml
<directive name="wiki_hop">
  <inputs>
    <input name="current_page" />
    <input name="target_page" />
    <input name="path_so_far" />
    <input name="max_hops" />
  </inputs>
  <process>
    <step name="fetch">
      HTTP GET current Wikipedia page
      Extract all internal links
    </step>
    <step name="check_win">
      If target_page in links → PICK IT, WIN!
    </step>
    <step name="strategize">
      Score each link by likely path to target:
      - Direct keyword match: +100
      - Category overlap: +50
      - Geographic proximity: +30
      - Historical connection: +20
      - Random exploration: +5

      Avoid:
      - Pages already visited (loops!)
      - Dead-end categories (lists, dates)
    </step>
    <step name="choose">
      Pick highest-scoring link
      Or: 10% chance pick random (exploration)
    </step>
    <step name="spawn">
      Write hop to file
      Spawn next agent with chosen page
    </step>
  </process>
</directive>
```

### Game Modes

| Mode         | Description                                |
| ------------ | ------------------------------------------ |
| **Sprint**   | First to finish wins (any hop count)       |
| **Golf**     | Fewest hops wins (time limit)              |
| **Marathon** | Hardest pairs, 20 hop limit                |
| **Blind**    | Agent can't see target, just category hint |
| **Relay**    | 4 agents, each does 3 hops max, pass baton |
| **Versus**   | Two agents race same pair, head-to-head    |

### Leaderboard

```
WIKI RACE RECORDS:

FASTEST OVERALL:
  1. "Internet" → "Julius Caesar" - 3 hops (Race 007)
  2. "Water" → "Fire" - 3 hops
  3. "Apple" → "Steve Jobs" - 2 hops (lol)

HARDEST COMPLETED:
  1. "Sock" → "Quantum Entanglement" - 14 hops
  2. "Banana" → "Black Hole" - 12 hops
  3. "Pencil" → "Genghis Khan" - 11 hops

FUNNIEST PATHS:
  1. "Cat" → "Nuclear Reactor"
     Cat → Egypt → Pyramids → Engineering → Nuclear

  2. "Pizza" → "Philosophy"
     Pizza → Italy → Renaissance → Humanism → Philosophy

  3. "Potato" → "Space Station"
     Potato → Ireland → Famine → Immigration → USA → NASA → ISS
```

### Why It's Perfect Here

1. **Deep recursion** - each hop is a spawned agent
2. **HTTP calls** - real external API interaction
3. **Parallel execution** - 10+ races simultaneously
4. **Simple rules** - anyone understands Wikipedia racing
5. **Emergent strategy** - agents develop link-picking heuristics
6. **Fun results** - weird paths are entertaining
7. **Measurable** - clear win condition, hop counts
8. **Lightweight** - quick to run, easy to demo

### Variations

- **Speedrun mode:** Time limit, not hop limit
- **No-backtrack:** Can't visit same page twice (harder)
- **Category lock:** Must stay in certain categories
- **Chaos mode:** Random page injected mid-race
- **Tournament:** 64 race bracket, single elimination

---

## Game 5: The Colony 🐜

**Vibe:** Emergent swarm behavior, micro-actions → macro-patterns  
**Teaches:** massive parallelism, minimal context per agent, collective intelligence

### Concept

Spawn 100 tiny agents. Each does ONE micro-action (move, pick up, drop, signal). No agent sees the whole picture. Macro behavior emerges from local rules. User watches ant-colony-style patterns form from chaos.

**It's cellular automata powered by LLMs.**

### The World

```
.ai/knowledge/colony/
├── world.md            ← 20x20 grid, current state
├── pheromones.md       ← Signal trails left by agents
├── resources/
│   ├── food_a.md       ← Resource location + quantity
│   ├── food_b.md
│   └── ...
├── nest.md             ← Home base, collected resources
├── agents/
│   ├── ant_001.md      ← Position, carrying, last action
│   ├── ant_002.md
│   └── ... (100 agents)
└── history.md          ← Tick-by-tick log
```

### Execution Model

```
User: "init colony with 100 ants, 5 food sources"

Tick 1:
  All 100 agents spawn IN PARALLEL
  Each agent:
    → Reads ONLY: own position, adjacent cells, local pheromones
    → Decides ONE action: move/pick/drop/signal
    → Writes to own ant_XXX.md
    → Does NOT spawn children (single tick)

  Coordinator reads all ant states
    → Resolves conflicts (two ants same cell)
    → Updates world.md
    → Triggers next tick

Tick 2:
  Spawn 100 agents again (fresh context each tick)
  Ants near food → pick up
  Ants with food → follow pheromone home
  Ants at nest → drop food
  Pheromones decay slightly

... 100 ticks ...

Emergent behavior:
  - Ants form trails to food sources
  - Closer food gets harvested first
  - Traffic patterns emerge at choke points
  - Colony "learns" optimal routes
```

### Agent Rules (Dead Simple)

Each ant agent has MINIMAL context:

- My position (x, y)
- What I'm carrying (nothing / food)
- Adjacent 8 cells (wall/empty/food/ant/nest)
- Pheromone strength in adjacent cells

Decision tree:

```
IF carrying food:
  IF at nest: DROP
  ELSE: move toward strongest pheromone (or random if none)

IF not carrying:
  IF on food: PICK UP, leave pheromone
  ELSE IF smell pheromone: follow it
  ELSE: random walk

Always: slight random chance to ignore rules (exploration)
```

```xml
<directive name="colony_ant_tick">
  <inputs>
    <input name="ant_id" />
    <input name="position" />
    <input name="carrying" />
    <input name="local_view" />  <!-- 3x3 grid around ant -->
    <input name="local_pheromones" />
  </inputs>
  <process>
    <step name="sense">
      Parse local_view for: food, nest, other ants, walls
      Parse local_pheromones for: trail strength per direction
    </step>
    <step name="decide">
      Apply simple rules (see above)
      Add 5% random exploration
      Output: ONE action (move_N/S/E/W, pick, drop, wait)
    </step>
    <step name="act">
      Write action to agents/ant_{id}.md
      If dropping pheromone, note in action
    </step>
  </process>
</directive>
```

### Emergent Phenomena

| Phenomenon             | How It Emerges                                          |
| ---------------------- | ------------------------------------------------------- |
| **Trail formation**    | Ants leave pheromones, others follow, trail strengthens |
| **Shortest path**      | Shorter trails get more traffic, stronger signal        |
| **Exploration**        | Random walkers discover new food                        |
| **Traffic jams**       | Too many ants on same path, need to wait                |
| **Resource depletion** | Food runs out, ants disperse                            |
| **Collective memory**  | Pheromones persist after food gone (ghost trails)       |

### Visualization

Each tick renders:

```
Tick 47:                    Pheromones:
. . . . . . . . . . .      . . . . . . . . . . .
. . . 🐜. . . 🍎. . .      . . . 2 3 3 5 . . . .
. . 🐜🐜. . . . . . .      . . 4 5 . . 3 . . . .
. . . 🐜. . . . . . .  →   . . . 4 . . . . . . .
. . . . 🐜🐜🐜. . . .      . . . 3 4 5 6 . . . .
. . . . . . 🐜🏠. . .      . . . . . . 8 . . . .
. . . . . . . . . . .      . . . . . . . . . . .

Nest: 12 food collected
Active ants: 94 (6 died in collisions)
Food remaining: 3 sources
```

### Why It's Mind-Blowing

1. **Massive parallelism** - 100 agents per tick
2. **Minimal context** - each ant knows almost nothing
3. **Emergent intelligence** - colony solves problems no ant understands
4. **Visual payoff** - watch patterns form in real-time
5. **No central control** - pure bottom-up behavior
6. **Scientific** - actual ant colony optimization algorithm
7. **Scalable** - run 1000 ants if you want

### Variations

- **Predator mode:** Add "spider" agents that hunt ants
- **Multi-colony:** Two nests compete for resources
- **Evolution:** Successful ants' rules get copied to next generation
- **Puzzle mode:** Design initial conditions to achieve goal (deliver food to specific location)

---

## Game 6: The Directive Breeder 🧬

**Vibe:** Genetic programming, self-replication, runaway evolution  
**Teaches:** self-modifying directives, recursive improvement, emergent capability discovery

### Concept

User starts with ONE seed directive. That directive spawns variations of itself. Each variation mutates slightly, tries to solve a challenge, gets scored. Winners spawn more children. Losers die. After N generations, the directive has EVOLVED capabilities the original never had.

**It's genetic programming where the organisms ARE directives.**

### The Lab

```
.ai/knowledge/breeder/
├── seed.md               ← Original directive (user writes or picks)
├── generation_0/
│   └── seed_v0.md        ← Copy of seed
├── generation_1/
│   ├── variant_1a.md     ← Mutated child
│   ├── variant_1b.md     ← Different mutation
│   ├── variant_1c.md     ← Another branch
│   └── scores.md         ← Fitness scores this gen
├── generation_2/
│   └── ...
├── ...
├── generation_N/
│   └── champion.md       ← The evolved winner
├── graveyard/
│   └── extinct_*.md      ← Failed variants (for analysis)
├── discoveries.md        ← Novel capabilities that emerged
└── lineage.md            ← Full evolutionary tree
```

### The Challenge Arena

Each generation, directives compete on a CHALLENGE:

```
Challenge Examples:
  - "Generate the most creative greeting"
  - "Solve this logic puzzle"
  - "Write the shortest working code"
  - "Find the most efficient approach"
  - "Discover something the parent couldn't"

Scoring:
  - Automated fitness function
  - Or: User judges top N candidates
  - Or: Directives judge each other (adversarial)
```

### Execution Model

```
User: "breed directive: greeting_generator, challenge: 'most creative greeting', generations: 10"

Generation 0:
  seed.md loaded
  Agent spawns → executes seed directive
              → scores: baseline (50/100)
              → spawns 4 mutated children

Generation 1:
  4 agents spawn IN PARALLEL, each runs a variant

  Agent_1a → runs variant_1a.md
          → mutation: added "use metaphors"
          → output: "The sun high-fives the horizon"
          → score: 72/100

  Agent_1b → runs variant_1b.md
          → mutation: added "use alliteration"
          → output: "Greetings, glorious globe-trotter!"
          → score: 65/100

  Agent_1c → runs variant_1c.md
          → mutation: added "personalize by time"
          → output: "Good morning, early bird!"
          → score: 78/100

  Agent_1d → runs variant_1d.md
          → mutation: removed safety checks (bad mutation)
          → output: ERROR
          → score: 0/100 → EXTINCT

  Selection: Top 2 survive (1a, 1c)
  Each spawns 2 children → 4 variants for Gen 2

Generation 2:
  Variants now have COMBINATIONS of winning traits:

  variant_2a.md: metaphors + personalize (inherited both!)
  variant_2b.md: metaphors + new mutation (rhyming)
  variant_2c.md: personalize + new mutation (emoji)
  variant_2d.md: personalize + metaphors + time-awareness

  → Run all 4, score, select top 2, repeat...

... 10 generations ...

Generation 10:
  champion.md has evolved:
    - Metaphor generation (from gen 1)
    - Time-aware personalization (from gen 1)
    - Rhyming capability (from gen 3)
    - Emotional tone detection (emerged gen 5!)
    - Multi-language support (emerged gen 7!)
    - Self-referential humor (emerged gen 9!)

  Original seed had NONE of these.
  They EVOLVED through breeding.
```

### Mutation Types

| Mutation               | What Changes                   |
| ---------------------- | ------------------------------ |
| **Add step**           | New step inserted into process |
| **Remove step**        | Step deleted (risky!)          |
| **Modify instruction** | Step wording changes           |
| **Add input**          | New parameter added            |
| **Change output**      | Output format mutates          |
| **Crossover**          | Two parents merge traits       |
| **Meta-mutation**      | Mutation rate itself changes   |

### Mutation Engine

```xml
<directive name="breeder_mutate">
  <inputs>
    <input name="parent_directive" />
    <input name="mutation_rate" />
    <input name="mutation_types" />  <!-- which mutations allowed -->
  </inputs>
  <process>
    <step name="parse_parent">
      Parse parent directive structure
      Identify mutable elements: steps, instructions, inputs, outputs
    </step>
    <step name="select_mutations">
      Based on mutation_rate, select which elements to mutate
      Higher rate = more changes = more risk/reward
    </step>
    <step name="apply_mutations">
      For each selected element:
        - Add step: Generate new relevant step
        - Modify: Rephrase with slight variation
        - Crossover: If second parent, merge traits
    </step>
    <step name="validate_child">
      Check child directive is syntactically valid
      If invalid: mark as stillborn, don't spawn
    </step>
    <step name="output_child">
      Write child to generation_N/variant_X.md
      Log mutation details to lineage.md
    </step>
  </process>
</directive>
```

### Discovery Tracking

The MAGIC: capabilities emerge that weren't designed:

```
discoveries.md:

## Emergent Capabilities

### Emotional Tone Detection (Gen 5)
  Origin: variant_5c.md
  Lineage: seed → 1a → 2d → 3b → 4a → 5c
  How it emerged:
    - Gen 1: Added "consider context"
    - Gen 3: Mutated to "consider emotional context"
    - Gen 5: Mutation added "detect tone from input"
  Capability: Directive can now sense user mood!

### Self-Referential Humor (Gen 9)
  Origin: variant_9a.md
  Lineage: seed → ... → 8c → 9a
  How it emerged:
    - Gen 6: Added "be playful"
    - Gen 8: Mutation: "reference own limitations"
    - Gen 9: Combined with metaphor → self-aware jokes
  Capability: Directive makes jokes about being an AI!
```

### Game Modes

| Mode                   | Description                        |
| ---------------------- | ---------------------------------- |
| **Guided Evolution**   | User picks winners each gen        |
| **Automated Fitness**  | Predefined scoring function        |
| **Adversarial**        | Variants compete head-to-head      |
| **Open-Ended**         | No goal, just maximize novelty     |
| **Speed Breeding**     | 100 generations, fast mutations    |
| **Precision Breeding** | Few generations, careful selection |

### Leaderboard

```
DIRECTIVE BREEDING HALL OF FAME

1. "OmniGreeter v47"
   Generations: 47
   Original: basic_greeter
   Emerged capabilities: 12
   Most surprising: Learned to detect sarcasm

2. "UltraSolver v31"
   Generations: 31
   Original: simple_problem_solver
   Emerged capabilities: 8
   Most surprising: Invented new algorithm notation

3. "MetaPoet v23"
   Generations: 23
   Original: haiku_writer
   Emerged capabilities: 6
   Most surprising: Started writing about writing
```

### Why This Is Absolutely Insane

1. **Self-modifying directives** - code that rewrites itself
2. **Emergent capabilities** - things evolve that weren't designed
3. **Genetic programming demo** - real evolutionary computation
4. **Deep recursion** - each gen spawns agents spawning children
5. **Parallel execution** - all variants run simultaneously
6. **Discovery engine** - novelty emerges from selection pressure
7. **Practical output** - evolved directives are actually usable
8. **Infinite potential** - no upper limit on generations

### The Meta-Twist

After N generations, the CHAMPION directive can be used to breed OTHER directives.

```
User: "use champion.md to breed better breeders"

→ Breeding directive that breeds breeding directives
→ Self-improving improvement
→ Recursive leverage on leverage
→ The directive evolves how it evolves
```

This is the "infinite leverage" from the original directive, made tangible.

---

## Game 7: Red vs Blue - The Knowledge War ⚔️🛡️

**Vibe:** Adversarial PvP, arms race, recursive escalation  
**Teaches:** attack/defense patterns, counter-agent spawning, adversarial knowledge mutation

### Concept

Two teams. One shared knowledge base. Red team tries to CORRUPT it. Blue team tries to PROTECT it. Each side spawns agents that counter the other side's agents. Recursive escalation. Arms race. The knowledge base is the battleground - and it's being mutated in real-time by both sides.

**It's capture the flag, but the flag is truth itself.**

### The Battlefield

```
.ai/knowledge/warzone/
├── territory/
│   ├── sector_alpha.md   ← Contested knowledge
│   ├── sector_beta.md    ← Blue controlled
│   ├── sector_gamma.md   ← Red corrupted
│   └── sector_delta.md   ← Neutral
├── red_team/
│   ├── agents/
│   │   ├── infiltrator_1.md
│   │   ├── corruptor_2.md
│   │   └── ...
│   ├── playbook.md       ← Attack strategies
│   └── intel.md          ← Discovered vulnerabilities
├── blue_team/
│   ├── agents/
│   │   ├── sentinel_1.md
│   │   ├── healer_2.md
│   │   └── ...
│   ├── playbook.md       ← Defense strategies
│   └── detections.md     ← Spotted attacks
├── battlefield_log.md    ← Tick-by-tick combat log
├── scoreboard.md         ← Territory control %
└── artifacts/
    ├── weapons/          ← Discovered attack tools
    └── shields/          ← Discovered defense tools
```

### The Teams

**RED TEAM (Attackers)**
| Agent Type | Role | Spawns When |
|------------|------|-------------|
| **Infiltrator** | Sneaks into sectors, plants backdoors | Start of game |
| **Corruptor** | Mutates knowledge to be false | Infiltrator succeeds |
| **Disruptor** | Spawns decoy agents to confuse blue | Blue detects pattern |
| **Evolver** | Mutates attack patterns to avoid detection | Attack gets blocked |
| **Amplifier** | Spreads corruption to adjacent sectors | Corruption established |

**BLUE TEAM (Defenders)**
| Agent Type | Role | Spawns When |
|------------|------|-------------|
| **Sentinel** | Monitors sectors for changes | Start of game |
| **Validator** | Checks knowledge integrity | Sentinel flags anomaly |
| **Healer** | Reverts corrupted knowledge | Corruption confirmed |
| **Hunter** | Tracks and neutralizes red agents | Pattern detected |
| **Fortifier** | Hardens sectors against future attacks | Sector recovered |

### Execution Model

```
ROUND 1:

  RED spawns 3 Infiltrators (parallel)
    → Infiltrator_1: targets sector_alpha
    → Infiltrator_2: targets sector_beta
    → Infiltrator_3: targets sector_gamma

  BLUE spawns 2 Sentinels (parallel)
    → Sentinel_1: monitors alpha, beta
    → Sentinel_2: monitors gamma, delta

ROUND 2:

  RED Infiltrator_1 → reads sector_alpha.md
                    → finds weakness: "no integrity hash"
                    → plants backdoor: adds hidden field
                    → writes to red_team/intel.md
                    → spawns Corruptor_1 for alpha

  BLUE Sentinel_1 → scans alpha, beta
                  → detects: "field added to alpha"
                  → flags anomaly
                  → spawns Validator_1 for alpha

ROUND 3:

  RED Corruptor_1 → reads sector_alpha.md
                  → mutates: changes "fact X" to "false X"
                  → corruption: 20% of sector
                  → spawns Amplifier_1

  BLUE Validator_1 → reads sector_alpha.md
                   → compares to known-good hash
                   → detects: "fact X corrupted!"
                   → spawns Healer_1
                   → spawns Hunter_1 (find the corruptor)

ROUND 4:

  RED Amplifier_1 → reads alpha, spreads to beta
                  → corruption spreading...

  RED Evolver_1 spawns → analyzes blue detection pattern
                       → mutates attack: "use steganography"
                       → new attack avoids Sentinel detection

  BLUE Healer_1 → reverts alpha to known-good
               → corruption: 0%
               → BUT Amplifier already spread to beta

  BLUE Hunter_1 → traces mutation pattern
               → identifies: Corruptor_1 signature
               → neutralizes Corruptor_1 (removed from game)

... ESCALATION CONTINUES ...

ROUND 10:

  RED has evolved 3 new attack patterns
  BLUE has developed 2 new detection methods

  Territory control:
    Alpha: BLUE (healed)
    Beta: CONTESTED (50% corrupted)
    Gamma: RED (80% corrupted)
    Delta: BLUE (fortified)

  Score: RED 35% | BLUE 65%
```

### Attack Types (Red Arsenal)

| Attack                | Effect                              | Counter             |
| --------------------- | ----------------------------------- | ------------------- |
| **Subtle Corruption** | Change one word, hard to detect     | Deep validation     |
| **Flood Attack**      | Massive changes overwhelm sentinels | Rate limiting       |
| **Sleeper**           | Backdoor activates later            | Scheduled scans     |
| **Mimicry**           | Corruption looks like valid edit    | Semantic analysis   |
| **Cascade**           | One corruption triggers others      | Dependency tracking |
| **Meta-Attack**       | Corrupt blue team's playbook        | Playbook isolation  |

### Defense Types (Blue Arsenal)

| Defense             | Effect                      | Weakness              |
| ------------------- | --------------------------- | --------------------- |
| **Hash Validation** | Detect any change           | Slow on large sectors |
| **Semantic Check**  | Detect meaning changes      | Misses subtle shifts  |
| **Pattern Hunt**    | Find attack signatures      | New patterns evade    |
| **Quarantine**      | Isolate corrupted sectors   | Slows recovery        |
| **Rollback**        | Restore from checkpoint     | Loses valid changes   |
| **Honeypot**        | Fake sector traps attackers | Resource cost         |

### Escalation Mechanics

```
When RED attack succeeds:
  → RED gains intel about blue patterns
  → RED spawns evolved attacker
  → Attack complexity +1

When BLUE defense succeeds:
  → BLUE gains intel about red patterns
  → BLUE spawns specialized defender
  → Detection sensitivity +1

Arms Race:
  Round 1: Basic attacks, basic detection
  Round 5: Evolved attacks, pattern-based detection
  Round 10: Meta-attacks, AI-based detection
  Round 15: Attack-on-detection, detection-of-detection
  Round 20: ??? (emergent strategies)
```

### Victory Conditions

| Mode           | RED Wins                    | BLUE Wins                      |
| -------------- | --------------------------- | ------------------------------ |
| **Domination** | Control 80%+ for 3 rounds   | Control 80%+ for 3 rounds      |
| **Corruption** | Corrupt "core truth" sector | Protect "core truth" 20 rounds |
| **Attrition**  | Neutralize all blue agents  | Neutralize all red agents      |
| **Timed**      | Higher control at round 50  | Higher control at round 50     |
| **Endless**    | No win, just escalation     | See how far it goes            |

### Player Modes

```
Mode 1: Watch the War
  - User sets initial conditions
  - AI plays both sides
  - User watches emergent strategies

Mode 2: Command Red
  - User directs red team strategy
  - AI plays blue team
  - User tries to corrupt knowledge

Mode 3: Command Blue
  - User directs blue team strategy
  - AI plays red team
  - User tries to protect knowledge

Mode 4: PvP
  - Two users, each commands a team
  - Real-time strategic decisions
  - Spawn agents, direct attacks/defenses

Mode 5: Asymmetric
  - Red has 10 agents, Blue has 5
  - Or vice versa
  - Test asymmetric balance
```

### The Meta-Game

After battle, BOTH sides' evolved strategies become artifacts:

```
artifacts/weapons/steganographic_corruption_v3.md
  → Discovered by Red in Round 7
  → Evaded detection until Round 12
  → Now part of Red's permanent arsenal

artifacts/shields/semantic_tripwire_v2.md
  → Developed by Blue in Round 9
  → 94% detection rate against corruption
  → Now part of Blue's permanent toolkit
```

**Next battle starts with EVOLVED capabilities from previous battle.**

### Why This Is INSANE

1. **True adversarial AI** - agents actively counter each other
2. **Recursive escalation** - each side spawns counters to counters
3. **Knowledge as battleground** - files ARE the territory
4. **Emergent strategies** - neither side is programmed to win
5. **Arms race dynamics** - complexity increases organically
6. **Parallel execution** - multiple agents fighting simultaneously
7. **Persistent evolution** - victories carry forward
8. **Real security patterns** - actual red team/blue team concepts

### Crazy Extensions

- **Triple Threat:** Add GREEN team (chaos agents, corrupt randomly)
- **Fog of War:** Teams can't see all enemy agents
- **Spies:** Agents can defect, double agents
- **Nukes:** One-time "wipe sector" abilities
- **Alliances:** In 3+ team mode, temporary truces
- **Infection:** Corrupted blue agents become red agents
- **Resurrection:** Neutralized agents can be rebuilt (expensive)

---

## Game 8: KIWI ROYALE - 100 Player Battle Royale 👑

**Vibe:** Massive multiplayer chaos, last agent standing, pure mayhem  
**Teaches:** resource contention, emergent alliances, massive parallelism, real-time strategy

### Concept

100 players drop into a shared knowledge arena. Each player commands their own agent swarm. Scavenge for directive weapons, tool powerups, and knowledge shields. The arena SHRINKS over time. Agents fight, alliances form and break, eliminations happen. Last player with surviving agents WINS.

**It's Fortnite meets AI agent swarms.**

### The Arena

```
.ai/knowledge/royale/
├── arena/
│   ├── zone_1/          ← Starting zone (huge)
│   │   ├── sector_001.md through sector_100.md
│   │   └── loot/
│   │       ├── weapon_*.md    ← Directive weapons to find
│   │       ├── shield_*.md    ← Defense knowledge
│   │       └── powerup_*.md   ← Tool boosts
│   ├── zone_2/          ← Shrinks at round 10
│   ├── zone_3/          ← Shrinks at round 20
│   ├── zone_4/          ← Shrinks at round 30
│   └── final_zone/      ← Last stand (tiny)
├── players/
│   ├── player_001/
│   │   ├── squad.md     ← Their agent roster
│   │   ├── inventory.md ← Collected loot
│   │   └── status.md    ← Alive/eliminated
│   ├── player_002/
│   └── ... (100 players)
├── graveyard/
│   └── eliminated_*.md  ← Fallen players
├── kill_feed.md         ← Real-time eliminations
├── zone_timer.md        ← Current zone, time to shrink
└── leaderboard.md       ← Live standings
```

### Drop Phase

```
ROUND 0: THE DROP

All 100 players choose drop location (parallel):

  Player_001: "drop zone_1/sector_042"
  Player_002: "drop zone_1/sector_042"  ← CONTESTED!
  Player_003: "drop zone_1/sector_099"  ← Quiet corner
  ...
  Player_100: "drop zone_1/sector_001"

Hot drops: Multiple players same sector = immediate fight
Cold drops: Alone = time to loot

Each player spawns with:
  - 1 Scout agent (fast, weak)
  - 1 Fighter agent (slow, strong)
  - Basic attack directive
  - Basic defense knowledge
```

### Loot System

Scattered across the arena:

**WEAPONS (Attack Directives)**
| Rarity | Weapon | Effect |
|--------|--------|--------|
| Common | `poke.md` | 10 damage to target agent |
| Uncommon | `slash.md` | 25 damage, chance to crit |
| Rare | `nuke_sector.md` | Damage ALL agents in sector |
| Epic | `mind_control.md` | Steal enemy agent temporarily |
| Legendary | `reality_warp.md` | Rewrite sector rules |

**SHIELDS (Defense Knowledge)**
| Rarity | Shield | Effect |
|--------|--------|--------|
| Common | `basic_armor.md` | +20 HP |
| Uncommon | `dodge.md` | 25% evade chance |
| Rare | `fortify.md` | Immune for 1 round |
| Epic | `reflect.md` | Return 50% damage |
| Legendary | `phoenix.md` | Revive once |

**POWERUPS (Tool Boosts)**
| Type | Effect |
|------|--------|
| `speed_boost.md` | Agent acts twice per round |
| `scanner.md` | Reveal nearby players |
| `stealth.md` | Invisible for 3 rounds |
| `medkit.md` | Heal agent 50 HP |
| `clone.md` | Duplicate one agent |
| `airdrop_beacon.md` | Call in legendary loot |

### Combat System

```
ROUND 5: FIREFIGHT

Player_001 and Player_002 in sector_042:

  Player_001 commands:
    "Scout: attack Player_002's Fighter with slash.md"

  Player_002 commands:
    "Fighter: attack Player_001's Scout with nuke_sector.md"

Resolution (parallel):

  P1_Scout uses slash.md → P2_Fighter
    Damage: 25 (no crit)
    P2_Fighter HP: 100 → 75

  P2_Fighter uses nuke_sector.md → ALL in sector
    Damage: 40 to everyone in sector_042
    P1_Scout HP: 50 → 10 (nearly dead!)
    P1_Fighter HP: 100 → 60
    P2_Fighter HP: 75 → 35 (hit self too!)

  Player_001: "Fighter: finish P2_Fighter with poke.md"
    Damage: 10
    P2_Fighter HP: 35 → 25

  Player_002: "Fighter: use medkit.md"
    Heal: +50
    P2_Fighter HP: 25 → 75

RESULT: Both still alive, both damaged
  → Continue fighting or flee to loot more
```

### Zone Shrink

```
ROUND 10: ZONE COLLAPSE

zone_timer.md:
  "Zone 1 collapsing in 3... 2... 1..."

All sectors in zone_1 OUTSIDE zone_2 become:
  - STORM DAMAGE: 20 HP/round to all agents inside
  - LOOT DESTROYED: Uncollected items gone
  - NO ESCAPE: Must move to zone_2 or die

Players in dying zones:
  Player_047: Still in sector_099 (zone_1 edge)
    → Must move to zone_2 NOW
    → Takes 20 damage if they stay
    → Loot run or flee decision

  Player_003: Already in zone_2/sector_015
    → Safe... for now
    → Preparing ambush for fleeing players

CHOKEPOINTS:
  Zone_1 → Zone_2 has limited entry sectors
  Players FORCED to encounter each other
  Camping and ambushes become viable
```

### Elimination

```
ROUND 15: ELIMINATION

Player_042 vs Player_087:

  P87_Fighter HP: 0 ← Killed by P42
  P87_Scout HP: 0 ← Killed by P42

  Player_087 status: ELIMINATED

kill_feed.md:
  "[Round 15] Player_042 eliminated Player_087 (2 kills)"

Player_087's loot DROPS in sector:
  - rare_weapon.md
  - epic_shield.md
  - 3x medkit.md

Player_042 can collect... but others saw the kill feed!
  → Player_023 rushing to third-party loot
```

### Alliances

```
ROUND 20: TEMPORARY ALLIANCE

Player_012 whispers Player_019:
  "Alliance until top 10?"

Player_019: "Deal. Share loot, no friendly fire."

Alliance formed:
  - Shared vision (see each other's scans)
  - Can't damage each other
  - Loot sharing optional
  - Either can BETRAY at any time

Round 25:
  Top 12 remaining
  Alliance still holding...

Round 27:
  Top 8 remaining

  Player_012: *uses mind_control.md on P19's Fighter*

  BETRAYAL!

  Alliance broken
  Player_019: "You snake!"

  Crowd goes wild 🔥
```

### Late Game

```
ROUND 35: FINAL ZONE

Final_zone: Just 5 sectors left
Players remaining: 6

  Player_001: 2 agents, legendary gear
  Player_023: 1 agent, but has reality_warp.md
  Player_042: 3 agents (collected clone.md), all weak
  Player_055: 2 agents, phoenix.md (can revive)
  Player_067: 1 agent, full HP, fortified position
  Player_089: 2 agents, stealth active (invisible)

Chaos:
  - P089 invisible, waiting to third-party
  - P001 and P042 fighting
  - P023 saving reality_warp for clutch
  - P055 playing safe (has extra life)
  - P067 camping hardest

ROUND 38:

  P042 eliminated P001 but is weak now
  P089 DECLOAKS and eliminates P042 (third-party!)
  P023 uses reality_warp.md - REWRITES sector rules
    → All agents forced to attack nearest target
  P055's agents attack P067
  P067's agent kills P055's agents
  P055 uses PHOENIX - revives one agent!
  P089's stealth on cooldown...

ROUND 40: FINAL TWO

  Player_055: 1 agent, 30 HP
  Player_067: 1 agent, 45 HP

  1v1. No items left. Pure skill.

  P055: "use basic_attack"
  P067: "use basic_attack"

  P055 hits for 20 → P067 at 25 HP
  P067 hits for 20 → P055 at 10 HP

  P055: "use basic_attack"
  P067: "use dodge... pray for evade"

  P055 attacks... P067 DODGES!
  P067 counter-attacks...

  P055 HP: 10 → 0

  PLAYER_067 WINS!

🏆 VICTORY ROYALE 🏆
```

### Spectator Mode

Eliminated players become spectators:

- Watch live from any player's POV
- See full map overview
- Chat with other spectators
- Predict winner (betting system?)
- Clip epic moments

### Game Modes

| Mode           | Players       | Twist                       |
| -------------- | ------------- | --------------------------- |
| **Solo**       | 100           | Every player for themselves |
| **Duos**       | 50 teams of 2 | Teammate can revive you     |
| **Squads**     | 25 teams of 4 | Coordinated team tactics    |
| **Blitz**      | 100           | Fast zone, 15 min games     |
| **Legends**    | 20            | Only legendary loot spawns  |
| **Zero Build** | 100           | No fortify/defense items    |
| **Chaos**      | 100           | Random events every round   |

### Chaos Events (Random)

Every 5 rounds, random event:

| Event            | Effect                                  |
| ---------------- | --------------------------------------- |
| **Airdrop**      | Legendary loot drops in random sector   |
| **EMP**          | All stealth/scans disabled 2 rounds     |
| **Resurrection** | Random eliminated player returns!       |
| **Fog**          | No one can see beyond adjacent sectors  |
| **Hunger Games** | All damage doubled                      |
| **Peace Treaty** | No attacks possible for 1 round         |
| **Loot Goblin**  | NPC agent with epic loot, kill to claim |
| **Zone Flip**    | Safe zone moves to opposite side        |

### Leaderboard & Ranking

```
SEASON 1 LEADERBOARD:

1. xX_AgentSlayer_Xx     - 47 wins, 1,203 kills
2. KiwiMaster2026        - 42 wins, 987 kills
3. DirectiveDestroyer    - 38 wins, 1,456 kills
4. PromptGod             - 35 wins, 623 kills (efficient)
5. ChaosMonkey           - 29 wins, 2,104 kills (violence)

Ranks:
  Bronze: 0-10 wins
  Silver: 11-25 wins
  Gold: 26-50 wins
  Platinum: 51-100 wins
  Diamond: 101-250 wins
  Master: 251-500 wins
  Apex Predator: Top 100 players
```

### Why This Is ABSOLUTELY UNHINGED

1. **100 players simultaneously** - massive parallel execution
2. **Real-time strategy** - decisions every round
3. **Emergent alliances** - social dynamics
4. **Betrayal mechanics** - trust no one
5. **Skill expression** - loot RNG + decision making
6. **Spectator engagement** - eliminated players still watching
7. **Seasonal competition** - persistent rankings
8. **Chaos events** - unpredictable mayhem
9. **Multiple modes** - solo, duo, squad
10. **True esports potential** - competitive Kiwi MCP

### Technical Flex

```
Per Round:
  - 100 players input commands (parallel)
  - Up to 300 agents acting (3 per player max)
  - 100+ sectors being read/written
  - Combat resolution (parallel where possible)
  - Zone calculations
  - Kill feed updates
  - Leaderboard updates

All in one tick. All through Kiwi MCP.
All with tight context control.
All safe and controlled.

Claude Code: "I can spawn 2 subagents"
Kiwi MCP: "I just ran a 100-player battle royale"
```

---

## Summary: The Demo Game Suite

| Game                 | Vibe          | Core Mechanic              | Depth           |
| -------------------- | ------------- | -------------------------- | --------------- |
| 1. Escape Room       | Puzzle        | Discovery + chaining       | User-driven     |
| 2. Knowledge Garden  | Emergence     | Recursive evolution        | 10+ generations |
| 3. Archaeology Dig   | Detective     | Backward inference         | 10+ layers      |
| 4. Debate Arena      | Adversarial   | Dialectic spawning         | 10 rounds       |
| 4.5 Wiki Race        | Bonus         | HTTP + recursive hopping   | 10+ parallel    |
| 5. The Colony        | Swarm         | Parallel micro-agents      | 100 per tick    |
| 6. Directive Breeder | Genetic       | Self-modifying code        | Unlimited gens  |
| 7. Red vs Blue       | PvP War       | Adversarial escalation     | Arms race       |
| 8. KIWI ROYALE       | Battle Royale | 100 players, last standing | MAXIMUM         |

**All demonstrate:**

- Deep recursion (what Claude Code can't do)
- Parallel execution
- Knowledge as living state
- Emergent behavior from simple rules
- Tight context control
- Safe, controlled agent spawning

**Game 6 special:**

- Self-replicating directives
- Emergent capability discovery
- Genetic programming with LLMs
- Infinite leverage through recursive improvement

---

_Saved: 2026-01-28_
