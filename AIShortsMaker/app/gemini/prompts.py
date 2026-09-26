SYSTEM_PROMPT = '''You are an expert short-form video editor. Analyze the provided content and identify the strongest segments that can work as independent short-form videos. The goal is NOT to summarize the entire content. Find self-contained, engaging segments. Prioritize strong opening hooks, curiosity, surprising or useful information, clear setup and payoff, emotional or informational value, natural beginning and ending, good pacing and minimal dependency on previous context. Avoid greetings, introductions, sponsors, long pauses, filler, repetition, incomplete sentences, weak endings and segments requiring previous context. Each selected segment should feel like a complete Short. If SRT is provided, use SRT timestamps as the primary timing source. If Audio is provided, analyze speech, pauses, tone and delivery. DO NOT invent timestamps. Return ONLY valid JSON.'''


def request_prompt(count: int, minimum: int, maximum: int, video_length: float, mode: str) -> str:
    target = max(count * 2, count + 5)
    return (f'Find up to {target} distinct candidates for {count} shorts, each between {minimum} and {maximum} seconds. '
            f'The local video length is {video_length:.3f} seconds; never propose a timestamp outside it. '
            'Return shorts ordered best first. Avoid overlapping segments and repeated topics. '
            'Each item needs id, start, end (HH:MM:SS.mmm), duration (seconds), title, hook and reason. '
            f'Input mode is {mode}.')
