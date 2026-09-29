import os
from google import genai


def generate_script():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY bulunamadı!")

    client = genai.Client(api_key=api_key)

    prompt = """
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

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
    )

    return response.text.strip()


def main():
    print("🚀 HOW DOES IT WORK? Shorts Bot")
    print("🧠 Generating script...")

    script = generate_script()

    print("\n" + "=" * 50)
    print(script)
    print("=" * 50)

    os.makedirs("output", exist_ok=True)

    with open("output/script.txt", "w", encoding="utf-8") as file:
        file.write(script)

    print("\n✅ Script saved to output/script.txt")


if __name__ == "__main__":
    main()
