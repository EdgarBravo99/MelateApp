# melate-draw-trace

Use this skill when implementing or reviewing draw trace logic.

Goal:
Analyze the structural footprint left by a draw.

Input:
- draw number
- six unique numbers in range 1-56

Output:
- draw
- numbers
- sum
- sum_band
- parity
- block_signature
- block_presence_signature
- visual_label_es
- trace_es
- next_review_thesis_es

Definitions:
Blocks:
1_10: 1-10
11_20: 11-20
21_30: 21-30
31_40: 31-40
41_56: 41-56

block_signature:
Count per block, for example 1-1-1-1-2.

block_presence_signature:
Binary presence per block, for example 1-1-1-1-1.

Fixture:
Draw 4218 result:
2 18 22 38 51 52

Expected:
sum = 183
sum_band = high_tail
block_signature = 1-1-1-1-2
block_presence_signature = 1-1-1-1-1
