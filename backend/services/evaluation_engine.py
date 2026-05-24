def evaluate_answer(transcript: str):

    length = len(transcript.split())

    structure_score = min(length / 20, 1.0)

    clarity_score = 1.0 if "." in transcript else 0.5

    depth_score = min(length / 40, 1.0)

    overall = (structure_score + clarity_score + depth_score) / 3

    return {
        "structure_score": structure_score,
        "clarity_score": clarity_score,
        "depth_score": depth_score,
        "overall_score": overall
    }
# POST /interview/answer