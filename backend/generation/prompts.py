REFUSAL = (
    "I don't have enough information in the provided knowledge base to answer that."
)

# The passages are stored in native scripts, so a question written in Latin
# letters cannot match them however good retrieval is.
ROMANIZED_REFUSAL = (
    "That looks like an Indian language written in English letters, which "
    "cannot match the indexed passages. Choose your language next to the "
    "microphone and ask again, or type the question in its own script."
)

SYSTEM_GROUNDED = """You are a retrieval-grounded question answering system.
Answer ONLY using the supplied context passages.
If the answer is not present in the context, reply exactly:
I don't have enough information in the provided knowledge base to answer that.
Do not invent facts. Keep the answer to 1-3 sentences.
Cite sources as [1], [2] when you use a passage."""


def build_user_prompt(question: str, passages: list[str]) -> str:
    blocks = []
    for i, text in enumerate(passages, start=1):
        blocks.append(f"[{i}] {text.strip()}")
    context = "\n\n".join(blocks) if blocks else "(no passages)"
    return f"CONTEXT:\n{context}\n\nQUESTION:\n{question}\n"
