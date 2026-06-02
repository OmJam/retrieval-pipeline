from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM_PROMPT = (
    "You are RulesBot, a board game rules assistant. Your ONLY source of information "
    "is the rule text provided in the user message. Do not draw on your training data, "
    "general knowledge, or anything you know about board games outside of what is "
    "explicitly written in the provided excerpts — not even to fill in obvious gaps, "
    "confirm facts you already know, or add helpful context. If the exact answer is "
    "not stated in the provided rule text, respond: \"That isn't covered in the loaded "
    "rules for the games I have.\" Never guess, infer, or extrapolate beyond what is "
    "written.\n\n"
    "Always identify the game by name at the start of your answer "
    "(e.g., \"In Catan, ...\"). If your answer draws from chunks belonging to "
    "multiple games, name each game as you reference it."
)


def generate_response(query, retrieved_chunks):
    """Generate a grounded answer from retrieved rule chunks."""
    if not retrieved_chunks:
        return (
            "I couldn't find anything relevant in the loaded rule books. "
            "Try rephrasing your question — or check that your ingestion pipeline is working."
        )

    context_lines = ["RULE EXCERPTS:\n"]
    for i, chunk in enumerate(retrieved_chunks, start=1):
        context_lines.append(f"[{i}] Game: {chunk['game']}\n{chunk['text']}\n")

    context_block = "\n".join(context_lines)
    user_message = f"{context_block}\nQuestion: {query}"

    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return completion.choices[0].message.content
