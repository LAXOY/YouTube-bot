import os
import time
import base64
import requests
import subprocess
import wave

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


def generate_with_model(client, model, prompt):

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):

        try:

            print(f"🤖 {model} | Deneme {attempt}/{max_attempts}")

            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )

            if not response.text:
                raise RuntimeError("Model boş cevap döndürdü!")

            print(f"✅ Başarılı model: {model}")

            return response.text.strip()

        except Exception as error:

            error_text = str(error)

            print("⚠️ Model başarısız:")
            print(error_text)

            retryable_errors = [
                "429", "500", "502", "503", "504",
                "UNAVAILABLE", "RESOURCE_EXHAUSTED", "INTERNAL"
            ]

            if not any(code in error_text for code in retryable_errors):
                raise

            if attempt < max_attempts:
                print("⏳ 10 saniye bekleniyor...")
                time.sleep(10)

    return None


def generate_text(client, prompt):

    for model in MODELS:

        print("\n" + "=" * 50)
        print(f"🚀 MODEL DENENİYOR: {model}")
        print("=" * 50)

        result = generate_with_model(client, model, prompt)

        if result:
            return result

        print(f"❌ {model} kullanılamadı.")
        print("➡️ Sıradaki modele geçiliyor...")

    raise RuntimeError("❌ Tüm Gemini modelleri başarısız oldu.")


def generate_script(client):

    return generate_text(client, PROMPT)


def generate_turkish_translation(client, script):

    print("\n🇹🇷 Türkçe altyazı hazırlanıyor...")

    prompt = f"""
Translate the following English YouTube Shorts narration into natural,
concise Turkish.

Rules:
- Preserve the meaning accurately.
- Keep the same paragraph structure.
- Do NOT explain anything.
- Return ONLY the Turkish translation.

English narration:
{script}
"""

    return generate_text(client, prompt)


def generate_visual_queries(client, script):

    print("\n🔎 Konuya uygun görüntü arama kelimeleri hazırlanıyor...")

    prompt = f"""
You are selecting stock-video search queries for a YouTube Short.

Read this narration and create exactly 6 short English Pixabay video
search queries that visually match the topic.

Rules:
- Queries must be directly related to the narration.
- Prefer concrete visual subjects such as router, smartphone,
  wireless signal, computer network, internet data, technology.
- Do not use abstract phrases.
- Do not use numbering.
- Return exactly 6 lines, one query per line.
- Return ONLY the queries.

Narration:
{script}
"""

    raw = generate_text(client, prompt)

    queries = []

    for line in raw.splitlines():

        line = line.strip()
        line = line.lstrip("-•0123456789. ").strip()

        if line and line not in queries:
            queries.append(line[:80])

    fallback = [
        "wifi router",
        "wireless internet",
        "smartphone wifi",
        "computer network",
        "internet technology",
        "wireless signal",
    ]

    for item in fallback:
        if len(queries) >= 6:
            break
        if item not in queries:
            queries.append(item)

    return queries[:6]


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

        response_format={"type": "audio"},

        generation_config={
            "speech_config": [
                {"voice": "Kore"}
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


def download_pixabay_videos(queries):

    print("\n🎬 Konuya uygun Pixabay videoları aranıyor...")

    api_key = os.environ.get("PIXABAY_API_KEY")

    if not api_key:
        raise RuntimeError("PIXABAY_API_KEY bulunamadı!")

    visuals_dir = "output/visuals"

    os.makedirs(visuals_dir, exist_ok=True)

    downloaded = []

    for index, query in enumerate(queries, start=1):

        print(f"\n📡 Görüntü {index}/6: {query}")

        params = {
            "key": api_key,
            "q": query,
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
            print("⚠️ Bu aramada video bulunamadı, geçiliyor.")
            continue

        video = data["hits"][0]
        video_url = video["videos"]["medium"]["url"]

        raw_path = f"{visuals_dir}/raw{index}.mp4"
        final_path = f"{visuals_dir}/clip{index}.mp4"

        video_response = requests.get(
            video_url,
            timeout=60
        )

        video_response.raise_for_status()

        with open(raw_path, "wb") as file:
            file.write(video_response.content)

        print("✅ Video indirildi.")

        print("📱 Dikey formata hazırlanıyor...")

        command = [
            "ffmpeg",
            "-y",
            "-stream_loop", "-1",
            "-i", raw_path,
            "-t", "8",
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920",
            "-r", "30",
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            final_path,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(result.stderr)
            print("⚠️ Bu video işlenemedi, geçiliyor.")
            continue

        downloaded.append(final_path)

    if not downloaded:
        raise RuntimeError("❌ Hiç uygun Pixabay videosu indirilemedi!")

    print(f"\n✅ Toplam {len(downloaded)} görüntü hazır.")

    return downloaded


def create_visual_concat(video_paths):

    concat_path = "output/visuals/concat.txt"

    with open(concat_path, "w", encoding="utf-8") as file:

        for path in video_paths:
            file.write(
                f"file '{os.path.abspath(path)}'\n"
            )

    return concat_path


def get_audio_duration():

    audio_path = "output/voice.wav"

    with wave.open(audio_path, "rb") as audio:

        frames = audio.getnframes()
        rate = audio.getframerate()

        return frames / float(rate)


def format_srt_time(seconds):

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return (
        f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    )


def create_subtitle_file(text, filename, words_per_line):

    print(f"\n📝 Altyazı oluşturuluyor: {filename}")

    duration = get_audio_duration()
    words = text.split()

    if not words:
        raise RuntimeError("❌ Altyazı metni boş!")

    word_duration = duration / len(words)
    lines = []

    for i in range(0, len(words), words_per_line):

        chunk = words[i:i + words_per_line]

        start = i * word_duration
        end = min(
            (i + len(chunk)) * word_duration,
            duration
        )

        lines.append(
            f"{len(lines) + 1}\n"
            f"{format_srt_time(start)} --> {format_srt_time(end)}\n"
            f"{' '.join(chunk)}\n"
        )

    subtitle_path = f"output/{filename}"

    with open(subtitle_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))

    print(f"✅ Altyazı hazır: {subtitle_path}")


def create_final_video(video_paths):

    print("\n🎞️ Final video oluşturuluyor...")

    audio_path = "output/voice.wav"
    english_subtitle = "output/subtitles.srt"
    turkish_subtitle = "output/subtitles_tr.srt"
    output_path = "output/final_short.mp4"

    concat_path = create_visual_concat(video_paths)

    subtitle_filter = (
        "subtitles=output/subtitles.srt:"
        "force_style='FontName=Arial,FontSize=15,Bold=1,"
        "Alignment=2,MarginV=105'"
    )

    turkish_filter = (
        "subtitles=output/subtitles_tr.srt:"
        "force_style='FontName=Arial,FontSize=10,Bold=1,"
        "Alignment=2,MarginV=55'"
    )

    video_filter = (
        "scale=1080:1920:"
        "force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        + subtitle_filter
        + ","
        + turkish_filter
    )

    command = [
        "ffmpeg",
        "-y",

        "-stream_loop", "-1",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_path,

        "-i", audio_path,

        "-vf", video_filter,

        "-map", "0:v:0",
        "-map", "1:a:0",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",

        "-c:a", "aac",
        "-b:a", "128k",

        "-shortest",
        output_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(result.stderr)

        raise RuntimeError(
            "❌ FFmpeg final video oluşturamadı!"
        )

    print(f"✅ FINAL VIDEO: {output_path}")


def main():

    print("🚀 HOW DOES IT WORK? Shorts Bot")

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY bulunamadı!")

    client = genai.Client(api_key=api_key)

    print("\n🧠 Script oluşturuluyor...")

    script = generate_script(client)

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

    turkish = generate_turkish_translation(
        client,
        script
    )

    with open(
        "output/turkish_translation.txt",
        "w",
        encoding="utf-8"
    ) as file:
        file.write(turkish)

    visual_queries = generate_visual_queries(
        client,
        script
    )

    with open(
        "output/visual_queries.txt",
        "w",
        encoding="utf-8"
    ) as file:
        file.write("\n".join(visual_queries))

    print("\n🔎 Görsel sorguları:")
    for query in visual_queries:
        print("  •", query)

    generate_voice(
        client,
        script
    )

    create_subtitle_file(
        script,
        "subtitles.srt",
        4
    )

    create_subtitle_file(
        turkish,
        "subtitles_tr.srt",
        6
    )

    video_paths = download_pixabay_videos(
        visual_queries
    )

    create_final_video(
        video_paths
    )

    print("\n" + "=" * 50)
    print("🎉 SHORTS OLUŞTURULDU!")
    print("=" * 50)


if __name__ == "__main__":
    main()
