import os
import time
import base64
import requests
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


def generate_voice(client, script):

    print("\n🎙️ Ses oluşturuluyor...")

    interaction = client.interactions.create(
        model="gemini-3.8-flash-lite-tts",
        input=[
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": script,
                        "annotations": [
                            {
                                "type": "speech_metadata",
                                "style": "natural, energetic, clear YouTube Shorts narration",
                            }
                        ],
                    }
                ],
            }
        ],
        response_format={
            "type": "audio"
        },
        generation_config={
            "speech_config": [
                {
                    "voice": "Kore"
                }
            ]
        },
    )

    if not interaction.output_audio:
        raise RuntimeError("❌ TTS ses üretmedi!")

    audio_data = base64.b64decode(
        interaction.output_audio.data
    )

    os.makedirs("output", exist_ok=True)

    voice_path = "output/voice.wav"

    with open(voice_path, "wb") as file:
        file.write(audio_data)

    print(f"✅ Ses kaydedildi: {voice_path}")


def download_pixabay_test():

    print("\n🎬 Pixabay video aranıyor...")

    api_key = os.environ.get("PIXABAY_API_KEY")

    if not api_key:
        raise RuntimeError("PIXABAY_API_KEY bulunamadı!")

    params = {
        "key": api_key,
        "q": "wifi technology",
        "video_type": "film",
        "per_page": 5,
    }

    response = requests.get(
        "https://pixabay.com/api/videos/",
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("hits"):
        raise RuntimeError("❌ Pixabay video bulamadı!")

    video = data["hits"][0]

    video_url = video["videos"]["medium"]["url"]

    print("✅ Pixabay video bulundu!")
    print("⬇️ Video indiriliyor...")

    os.makedirs("output/visuals", exist_ok=True)

    output_path = "output/visuals/clip1.mp4"

    video_response = requests.get(
        video_url,
        timeout=60
    )

    video_response.raise_for_status()

    with open(output_path, "wb") as file:
        file.write(video_response.content)

    print(f"✅ Video kaydedildi: {output_path}")


def main():

    print("🚀 HOW DOES IT WORK? Shorts Bot")

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY bulunamadı!")

    client = genai.Client(api_key=api_key)

    print("\n🧠 Script oluşturuluyor...")

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

    generate_voice(client, script)

    download_pixabay_test()

    print("\n" + "=" * 50)
    print("🎉 TEST TAMAMLANDI!")
    print("=" * 50)


if __name__ == "__main__":
    main()
