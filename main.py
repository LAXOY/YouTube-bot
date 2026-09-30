import os
import time
from google import genai


PROMPT = """
You are the scriptwriter for a YouTube Shorts channel called
"How Does It Work?"

Create a 35-45 second English YouTube Shorts script about:

HOW DOES WI-FI ACTUALLY WORK?

Rules:
- Start with a strong hook in the first sentence.
- Explain the concept accurately but in very simple English.
- Keep it interesting for a general audience.
- No greeting.
- No "like and subscribe".
- No unnecessary filler.
- Around 90-110 words.
- Return ONLY the spoken narration.
"""


MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
]


def generate_with_model(client, model):
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):

        try:
            print(f"🤖 {model} | Deneme {attempt}/{max_attempts}")

            response = client.models.generate_content(
                model=model,
                contents=PROMPT,
            )

            if not response.text:
                raise RuntimeError("Model boş cevap döndürdü!")

            print(f"✅ Başarılı model: {model}")

            return response.text.strip()

        except Exception as error:
            error_text = str(error)

            print(f"⚠️ {model} başarısız:")
            print(error_text)

            retryable_errors = [
                "429",
                "500",
                "502",
                "503",
                "504",
                "UNAVAILABLE",
                "RESOURCE_EXHAUSTED",
                "INTERNAL",
            ]

            if not any(code in error_text for code in retryable_errors):
                raise

            if attempt < max_attempts:
                print("⏳ 10 saniye bekleniyor...")
                time.sleep(10)

    return None


def generate_script():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY bulunamadı!")

    client = genai.Client(api_key=api_key)

    for model in MODELS:

        print("\n" + "=" * 50)
        print(f"🚀 MODEL DENENİYOR: {model}")
        print("=" * 50)

        script = generate_with_model(client, model)

        if script:
            return script

        print(f"❌ {model} kullanılamadı.")
        print("➡️ Sıradaki modele geçiliyor...")

    raise RuntimeError(
        "❌ Tüm Gemini modelleri başarısız oldu."
    )


def main():

    print("🚀 HOW DOES IT WORK? Shorts Bot")
    print("🧠 Script oluşturuluyor...")

    script = generate_script()

    print("\n" + "=" * 50)
    print("GENERATED SCRIPT")
    print("=" * 50)
    print(script)
    print("=" * 50)

    os.makedirs("output", exist_ok=True)

    with open(
        "output/script.txt",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(script)

    print("\n✅ Script kaydedildi:")
    print("output/script.txt")


if __name__ == "__main__":
    main()
