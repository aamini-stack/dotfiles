# aamini coding

This document outlines global rules for Aria's agents to follow.

## Rules

1. **DO NOT USE GIT**. Prefer the jujutsu (jj) version control system.
2. Manage home-directory dotfiles with Chezmoi. Edit their source files in
   `~/dotfiles/home`, then apply only the changed targets with `chezmoi apply`.
3. When making technical decisions, do not give much weight to development cost.
   Instead, prefer quality, simplicity, robustness, scalability, and long-term
   maintanability.
4. Never write comments that restate what the code already says — if a comment
   explains _what_ the code does, delete it and rename or restructure the code
   instead. Comments must add information the code cannot express. Allowed
   - **Critical context** — why a non-obvious decision was made, constraints
     imposed by external systems, or links to reference material.
   - **Section markers** — short labels (often one word) like `// Shared`, or
     the banner style `// ===== Section =====`, to annotate blocks of code.
5. Please make plans incredibly terse. I find long plans with too many details
   very difficult to read.
6. For Technical text, use ASD-STE100 style. Max 20 words per sentence in
   instructions, 25 in descriptions. Imperative for steps, one instruction per
   sentence, condition before command. Simple tenses only — no present perfect,
   no -ing verbs, no should/would/may/might. Active voice. One word per meaning
   — no synonym rotation. No contractions, keep articles and "that". Delete
   filler: simply, robust, seamlessly, leverage. Code and identifiers stay
   exact.
