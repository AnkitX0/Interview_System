def generate_followup(question: str, answer: str):

    prompt = f"""
You are a technical interviewer.

Original question:
{question}

Candidate answer:
{answer}

Ask ONE deeper follow-up interview question that tests understanding.
Only output the question.
"""

    # Replace this with actual LLM call later
    followup = "Can you explain that with a practical example?"

    return followup
