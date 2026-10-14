import re
import time

def call_with_retry(fn, *args, max_tries=5, **kwargs):
    for attempt in range(max_tries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e)
            if "429" not in msg and "rate limit" not in msg.lower():
                raise
            m = re.search(r"try again in ([\d.]+)s", msg)
            wait = float(m.group(1)) + 1 if m else 10 * (attempt + 1)
            print(f"Rate limited. Waiting {wait:.0f}s (try {attempt + 1}/{max_tries})")
            time.sleep(wait)
    raise RuntimeError("Groq rate limit: still blocked after several retries.")