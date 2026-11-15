import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from urllib.request import Request, urlopen

SOURCE = "en.json"
TARGETS = {"jv": "jv", "it": "it", "gu": "gu", "th": "th"}
PLACEHOLDER = re.compile(r"\{[^{}]+\}")


def translate(text, language):
    if not text or not isinstance(text, str):
        return text
    variables = []
    def protect(match):
        token = f"ZZVAR{len(variables)}ZZ"
        variables.append((token, match.group(0)))
        return token
    protected = PLACEHOLDER.sub(protect, text)
    if not protected.strip():
        return text
    url = (
        "https://translate.googleapis.com/translate_a/single?client=gtx"
        f"&sl=en&tl={language}&dt=t&q={quote(protected)}"
    )
    for attempt in range(4):
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=8) as response:
                payload = json.load(response)
            result = "".join(part[0] for part in payload[0] if part and part[0])
            for token, original in variables:
                result = result.replace(token, original)
            return result
        except Exception:
            if attempt == 3:
                return text
            time.sleep(1.5 * (attempt + 1))


def main():
    with open(SOURCE, encoding="utf-8") as handle:
        source = json.load(handle)
    keys = list(source)
    for output_language, api_language in TARGETS.items():
        translated = {}
        with ThreadPoolExecutor(max_workers=16) as pool:
            jobs = {
                pool.submit(translate, source[key], api_language): key
                for key in keys
            }
            for index, job in enumerate(as_completed(jobs), 1):
                key = jobs[job]
                translated[key] = job.result()
                if index % 100 == 0:
                    print(f"{output_language}: {index}/{len(keys)}", flush=True)
        translated = {key: translated[key] for key in keys}
        with open(f"locales/{output_language}.json", "w", encoding="utf-8") as handle:
            json.dump(translated, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"wrote locales/{output_language}.json", flush=True)


if __name__ == "__main__":
    main()
