# melate-relation-graph

Use this skill when implementing number relation graph logic.

Goal:
Represent numbers and their relationships as a local review graph.

Nodes:
- draw numbers
- played ticket numbers
- captured numbers
- missed numbers

Edges:
- same_draw
- same_block
- high_block_pair
- adjacent_high_pair
- trace_member
- captured_together
- missed_from_played_set

Output:
outputs/relation_graph_<draw>.json

Rules:
- The graph is descriptive, not predictive.
- Do not assign probability.
- Do not promote numbers automatically.
- Use relation labels and evidence text.
