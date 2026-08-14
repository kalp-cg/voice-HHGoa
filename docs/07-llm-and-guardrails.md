# 07 — LLM & Guardrails

## LLM strategy

**v1:** Fast cloud API model — focus is RAG engineering, not local LLM training.

**Later:** Optionally try a small local model on RTX 3050 6 GB after the full pipeline works.

Grounded prompt pattern:

```text
You are a retrieval-grounded question answering system.
Answer ONLY from the supplied context.
If the answer is not present in the context,
say that you do not have enough information.
Do not invent facts.
```

## Guardrails (required — implement ≥4)

### 1. Off-topic

If retrieval finds nothing relevant (e.g. weather / jokes / unrelated), refuse with a clear KB miss message.

### 2. Retrieval confidence

```python
if retrieval_confidence < threshold:
    refuse()
```

Threshold is **tuned experimentally**, not guessed.

### 3. Grounded generation

System/user prompt constrains answers to supplied passages only.

### 4. Post-generation verification

```text
Context + Answer → Grounding Checker
  ├── grounded → return
  └── not grounded → regenerate or refuse
```

Stronger than “please don’t hallucinate” alone.

## Adversarial test set (Milestone 7)

Deliberately ask:

- Weather / jokes / off-domain
- Weak-retrieval questions

Expect refuse / “not enough information”, not hallucinations.
