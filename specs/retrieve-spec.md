# Spec: `retrieve()`

**File:** `retriever.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Given a user's natural language query, find the most relevant chunks from the vector store using semantic similarity search. Return them ranked by relevance so that `generate_response()` can use them as context.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | The user's natural language question |
| `n_results` | `int` | Maximum number of chunks to return (default: `N_RESULTS` from `config.py`) |

**Output:** `list[dict]`

Each dict in the returned list must contain exactly these keys:

| Key | Type | Description |
|-----|------|-------------|
| `"text"` | `str` | The chunk text |
| `"game"` | `str` | The game name this chunk came from |
| `"distance"` | `float` | Cosine distance score — lower means more similar to the query |

Results should be ordered from most to least relevant (lowest to highest distance). Returns an empty list `[]` if the collection contains no documents.

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Query approach

*Describe how you will use `_collection.query()` to find relevant chunks. What arguments will you pass, and why?*

```
[your answer here]
```

---

### Return structure

*Sketch out what one item in your return list looks like as a concrete example. Where does each field come from in the query results?*

```
Each item in the returned list is a plain dict with exactly three keys:

{
  "text":     "When a player rolls a 7, the robber must be moved...",
  "game":     "Catan",
  "distance": 0.12
}

- "text"     comes from results["documents"][0][i]
- "game"     comes from results["metadatas"][0][i]["game"]
- "distance" comes from results["distances"][0][i]

Results arrive already sorted lowest-to-highest distance (most-to-least relevant)
because that is ChromaDB's default ordering.
```

---

### Handling the nested result structure

*`_collection.query()` returns nested lists. Describe what index you need to access to get the actual list of results for a single query, and why the nesting exists.*

```
_collection.query() wraps every result list in an outer list — one inner list
per query string in query_texts. Because we always pass exactly one query string,
the actual list of matched chunks is always at index [0].

Example:
  raw["documents"]      →  [["chunk A", "chunk B", "chunk C"]]
  raw["documents"][0]   →  ["chunk A", "chunk B", "chunk C"]   ← what we want

So when building the return list, iterate over:
  zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
— not over the top-level lists directly, or you'd be iterating over
single-element wrapper lists instead of the actual results.
```

---

### Relevance threshold

*Will you filter out results above a certain distance score, or return all `n_results` regardless of how relevant they are? What are the tradeoffs of each approach?*

```
Return all n_results without filtering by distance threshold.

Tradeoffs:
- Simpler, always returns the same number of results,
  and lets generate_response() decide how to use weak matches.
  Works even when no chunk is a great match, but may cause hallucination
  or wrong information. 
- A hard threshold produces cleaner context but can silently return an empty 
  list, which breaks the generator or produces confusing behavior. 
  Requires careful tuning per dataset.

For this project, returning all n_results and letting the LLM handle low-quality
matches is the safer, simpler default.
```

---

### Edge cases

*How does your implementation behave when: (a) the collection is empty, (b) the query matches no chunks well, (c) the query matches chunks from multiple games?*

```
[your answer here]
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 3.*

**Test query and top result returned:**

```
Query: How does the Spymaster give clues in Codenames?
Top result game: Codenames
Distance score: 0.289
Does it make sense? Yes — all three results came from Codenames and the distances
were the lowest of any query tested (~0.289–0.351), showing that a targeted
game-specific question retrieves tightly relevant chunks.
```

**One thing about the query results that surprised you:**

```
"What happens when you roll a 7?" returned Catan as the top result (dist: 0.466)
but the second and third slots went to Risk — because those Risk chunks contain
the words "dice" and "rolled". The 300-character chunks are small enough that
some don't carry the game name or enough surrounding context to distinguish
Catan's specific robber rule from a generic dice-rolling passage. A game-specific
query that feels unambiguous to a human can still match fragments from the wrong
game when the chunks are short and share vocabulary.
```
