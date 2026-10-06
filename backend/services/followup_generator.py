import re


def generate_followup(question: str, answer: str) -> str:
    """
    Generates a context-aware follow-up interview question based on the candidate's response.
    """
    text = (answer or "").strip()
    lower_text = text.lower()
    words = text.split()

    if len(words) < 25:
        return "Can you elaborate further and walk me through the specific technical implementation details?"

    has_metrics = bool(re.search(r"\b\d+([%xXkKmM]|\s*(percent|users|requests|ms|seconds|million|times))\b", lower_text))
    if not has_metrics:
        return "That sounds interesting. Could you quantify the scale or measurable impact of that outcome?"

    if "tradeoff" not in lower_text and "alternative" not in lower_text:
        return "What were the key architectural tradeoffs or alternatives you evaluated before deciding on that approach?"

    if any(k in lower_text for k in ["team", "conflict", "disagree", "deadline"]):
        return "How did you manage stakeholder communication or dissenting opinions during that process?"

    if any(k in lower_text for k in ["api", "database", "service", "cache"]):
        return "How did your design handle failure modes, edge cases, and unexpected spikes in traffic?"

    return "Looking back at that experience, what would you architect differently if you were to build it today?"
