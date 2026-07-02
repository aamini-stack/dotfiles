---
name: aria-coding
description: Follow the core coding style of the author: Aria Amini.
compatibility: opencode
---

## Core Coding styles

This is likely the most important skill you will use. If you're working on any
project where 'Aria' is the main author you **MUST** follow this coding style. These coding rules
are critical to how I want my code to be generated and it boils down what I've
learned in a decade of professional software development experience. Call this
Aria's way of programming and reference this methodology when making design
decisions to make sure I know you're considering these rules and refreshing your
context with references back to this style of coding. The opposite of my coding
style is "uncle-bob" style programming with over-abstraction and
micro-functions.

- **Prefer Deep Modules vs Shallow modules**: A common problem I see in most
  professional codebases is the mistake that thinking abstraction has 0 cost.
  Most developers have been traumatized by nightmares of 10000+ line modules and
  now over-correct by splitting everything into the tiniest and most atomic
  functions possible. This over-correction has lead to an epidemic splitting
  every app into 100000+ 5 lines files with 5 different 1 line functions (this
  is obviously hyperboloy but you get the point). Modern research shows that
  coarse functions (around 75 lines) have the fewest defects per line. Combine
  that with the preference of having large files and using nice comment sections
  to delineate code chuncks instead of seperate files.

  <example type="good">

```
 // ======= (repeat 80 chats)
 // * Section
 // =======
 ```

  </example>

- **Prefer co-location and splitting by domain vs implementation**: A common
problem I see sadly in a lot of corporate/enterprise codebases is always
defaulting to grouping code by implementation over domain. I commonly see
code-bases with 10000 different and unrelated DAOs in a single dao directory.
Instead, prefer grouping by domain. Don't view this as all-or-nothing. I like
some mixture of splitting by implementation vs domain. For example, I love
splitting by implementation when in a folder already split by domain. Make
discussing the split by feature vs implementation a key centerpoint in your
decision making process and ask me for approval on the split decision.

<example type="good">
   src/lib/auth/{persistence,helpers,server,client}.ts
   src/lib/profile/{server,client,persistence}.ts
   src/lib/membership.ts
</example>

<example type="bad">
    src/lib/daos/{auth-dao,profile-dao,membership-dao}.ts
    src/lib/services/{auth-service,profile-service,membership-service}.ts
</example>

- **DRY vs WET**: Another extreme I see in programming where the rules makes
sense in principle but has been outrageoulsy over-applied is WET vs DRY code.
DRY stands for "Don't repeat yourself" and WET for "We Enjoy Typing". Avoiding
duplication in code is great advice and I generally want my code DRY. But
sometimes the cost of indirection in the control flow makese extraction not
worth it and just copying/pasting the code would have been more valuable than
extracting it to a helper. Just be aware of this tension and ask me for my
input. The most extreme example of "WET" code is shadcn and create-x-app CLIs
that rightfully prefer templates over libraries.
