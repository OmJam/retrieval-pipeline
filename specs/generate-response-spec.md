# Spec: `generate_response()`

**File:** `generator.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user query and a list of retrieved rule chunks, generate a response that directly answers the question using only the retrieved text as context. The response must be grounded — it should not draw on the model's general knowledge of board games, only on what was retrieved.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's original question |
| `retrieved_chunks` | `list[dict]` | Ranked list of chunks from `retrieve()`, each with `"text"`, `"game"`, and `"distance"` |

**Output:** `str`

A plain string containing the response to show the user. The response should:
- Answer the question using only the retrieved rule text
- Identify which game the answer comes from
- Acknowledge clearly when the answer is not found in the loaded rules

Returns a fallback string (not an error) when `retrieved_chunks` is empty.

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Context formatting

*How will you format the retrieved chunks before passing them to the LLM? Describe the structure — not the code. Consider: will you label chunks by game? Include distance scores? Separate chunks with delimiters?*

```
Each chunk is presented as a numbered block with a game label, separated by
blank lines. Distance scores are omitted — they're an internal implementation
detail that would confuse the model. The format is:

[1] Game: Catan
<chunk text>

[2] Game: Risk
<chunk text>

Numbering helps the model reference specific chunks. The game label on each
block makes citation explicit without requiring the model to infer it. The
context block is placed before the question in the user message, separated
by a clear "Question:" label.

Research on RAG prompting (e.g. Lost in the Middle, 2023) shows models attend
better to structured, labeled sources than to a flat concatenated block.
```

---

### System prompt — grounding instruction

*Write the exact system prompt instruction you will use to prevent the model from answering beyond the retrieved text. This is the most important design decision in this function.*

```
You are RulesBot, a board game rules assistant. Your ONLY source of information
is the rule text provided in the user message. Do not draw on your training data,
general knowledge, or anything you know about board games outside of what is
explicitly written in the provided excerpts — not even to fill in obvious gaps,
confirm facts you already know, or add helpful context. If the exact answer is
not stated in the provided rule text, respond: "That isn't covered in the loaded
rules for the games I have." Never guess, infer, or extrapolate beyond what is
written.
```

Pressure-tested failure modes and mitigations:
- "The rules say X, which is standard in most editions..." → blocked by "not even
  to add helpful context"
- Answering from training when chunks are weak → blocked by "not even to confirm
  facts you already know"
- Inferring from partial info ("the rules mention dice so presumably...") → blocked
  by "never infer or extrapolate"

---

### System prompt — citation instruction

*Write the exact instruction you will use to tell the model to identify which game its answer comes from.*

```
Always identify the game by name at the start of your answer
(e.g., "In Catan, ..."). If your answer draws from chunks belonging to
multiple games, name each game as you reference it.
```

---

### Fallback behavior

*What should the response say when the answer isn't found in the loaded rule books? Write the exact fallback message.*

```
Two levels:

1. Empty chunks (collection is empty or retrieve() returned []): handled before
   the API call — return immediately with:
   "I couldn't find anything relevant in the loaded rule books. Try rephrasing
   your question — or check that your ingestion pipeline is working."

2. Chunks present but don't answer the question: the grounding instruction
   tells the model to say:
   "That isn't covered in the loaded rules for the games I have."
   This is enforced by the system prompt, not hardcoded in the function.
```

---

### Handling low-relevance chunks

*`retrieved_chunks` may include chunks with high distance scores (weak relevance). Will you filter these out before building context, pass them all in, or handle them another way? What are the tradeoffs?*

```
Pass all chunks through without filtering. The grounding instruction already
handles the "chunks don't answer the question" case — the model says so rather
than hallucinating. Filtering here would duplicate logic and risks silently
removing a relevant chunk just because its distance score is high.

Tradeoff: more noise in the context window, but no risk of dropping the one
chunk that actually contains the answer. Consistent with retrieve()'s own
no-threshold decision — the whole pipeline uses the same philosophy: surface
the best candidates and let the LLM decide.
```

---

### Message structure

*Describe how you will structure the messages list for the API call — what goes in the system message vs. the user message?*

```
System message: grounding instruction + citation instruction (static, never
  changes between calls — defines the model's role and constraints).

User message: the formatted context block followed by the question, structured as:

  RULE EXCERPTS:

  [1] Game: Catan
  <chunk text>

  [2] Game: Risk
  <chunk text>

  Question: <query>

Keeping context and question in the user message (rather than splitting them
across system/user) mirrors how the model was trained to process
retrieval-augmented prompts and makes the grounding boundary clear: the system
message is the law, the user message is the evidence and the question.
```

---

## Implementation Notes

*Fill this in after implementing and testing.*

**Test query and response:**

```
Query: What happens when you roll a 7 in Catan?
Response: "In Catan, when a 7 is rolled, no resources are produced. Every player
with more than 7 resource cards in hand must discard half (rounded down). The
player who rolled moves the robber to any terrain hex and steals one resource."
Correctly grounded? Yes — all three facts (no resources, discard rule, robber
move + steal) are contained in the 300-char Catan chunks retrieved.
Cited the right game? Yes — "In Catan" leads the answer.

Grounding stress test:
Query: Can you trade cards with players who are not in the game?
Response: Correctly said it isn't covered in the loaded rules. The Monopoly
trading chunk surfaced (dist: 0.522) but the model didn't use it to improvise
an answer — it noted the specific scenario wasn't addressed.
```

**One thing you changed from your original spec after seeing the actual output:**

```
Nothing needed to change — the system prompt held up on the first run.
The grounding stress test (a question with no good answer in the rules) produced
the expected "That isn't covered" response rather than an improvised answer.
The one observation worth noting: the model's out-of-scope response was slightly
verbose (it enumerated what Monopoly and Clue don't say, rather than a single
clean "I don't know"). A future revision could add "Be concise." to the system
prompt.
```
