import os
import re
import json
import time
import subprocess
import requests

from google import genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ============================================================
# AYARLAR
# ============================================================

OUTPUT_DIR = "output"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")

YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")


if not GEMINI_API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY bulunamadı!")

if not PIXABAY_API_KEY:
    raise RuntimeError("❌ PIXABAY_API_KEY bulunamadı!")


os.makedirs(OUTPUT_DIR, exist_ok=True)

client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# GEMINI'DEN VİDEO BİLGİLERİ AL
# ============================================================

def generate_video_info():

    print("\n🧠 Gemini yeni konu seçiyor...")

    prompt = """
You are creating a YouTube Shorts video for an English-speaking audience.

The channel concept is:

"How Does It Work?"

Choose ONE interesting topic that:
- can be explained visually
- is understandable to ordinary people
- creates curiosity
- is suitable for a 35-50 second YouTube Short
- is factual
- is not about politics
- is not about controversial current events
- is not too difficult to explain

Examples:
- How does noise cancelling work?
- How does GPS know where you are?
- How does an elevator know which floor to stop at?
- How does a microwave heat food?
- How does Bluetooth work?
- How does a fingerprint scanner work?
- How does an airplane stay in the air?
- How does a QR code work?

Do NOT always choose the examples above.

Return ONLY valid JSON.

Required format:

{
  "topic": "short topic name",
  "title": "YouTube Shorts title",
  "script": "35-50 second English narration",
  "turkish_translation": "Natural Turkish translation of the narration",
  "visual_queries": [
    "English Pixabay search query 1",
    "English Pixabay search query 2",
    "English Pixabay search query 3",
    "English Pixabay search query 4",
    "English Pixabay search query 5",
    "English Pixabay search query 6"
  ],
  "description": "YouTube description with a short hook and relevant hashtags",
  "tags": [
    "Shorts",
    "How Does It Work",
    "Technology"
  ]
}

Important:
- Script must be natural spoken English.
- Keep it around 90-120 words.
- Do not use complicated vocabulary.
- Make the first sentence a strong hook.
- Do not include stage directions.
- Do not include emojis inside the script.
- Visual queries must describe things that are likely to exist as stock video footage.
"""

response = None

for attempt in range(5):

    try:

        print(
            f"\n🧠 Gemini isteği: "
            f"{attempt + 1}/5"
        )

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )

            print("✅ Gemini cevap verdi!")

            break

        except Exception as e:

            error_text = str(e)

            if "503" in error_text:

                if attempt < 4:

                    wait_time = 10 * (2 ** attempt)

                    print(
                        f"⚠️ Gemini şu anda yoğun."
                    )

                    print(
                        f"⏳ {wait_time} saniye sonra "
                        f"tekrar denenecek..."
                    )

                    time.sleep(wait_time)

                else:

                    print(
                        "❌ Gemini 5 denemede de "
                        "cevap vermedi."
                    )

                    raise

            else:

                raise

    if response is None:

        raise RuntimeError(
            "❌ Gemini'den cevap alınamadı!"
        )

    text = response.text.strip()

    # Markdown JSON temizliği
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except Exception as e:
        print("\n❌ Gemini JSON hatası:")
        print(text)
        raise e

    print("\n" + "=" * 50)
    print("🎯 YENİ KONU")
    print("=" * 50)

    print("Konu:", data["topic"])
    print("Başlık:", data["title"])

    print("\n📝 Script:")
    print(data["script"])

    return data


# ============================================================
# PIXABAY'DEN VİDEO İNDİR
# ============================================================

def search_pixabay(query, index):

    print(f"\n🔎 Pixabay aranıyor: {query}")

    url = "https://pixabay.com/api/videos/"

    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "per_page": 10,
        "safesearch": "true"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    hits = data.get("hits", [])

    if not hits:
        print("⚠️ Video bulunamadı.")
        return None

    # İlk uygun sonucu al
    for hit in hits:

        videos = hit.get("videos", {})

        if "large" in videos:
            video_url = videos["large"]["url"]

        elif "medium" in videos:
            video_url = videos["medium"]["url"]

        elif "small" in videos:
            video_url = videos["small"]["url"]

        else:
            continue

        output_path = os.path.join(
            OUTPUT_DIR,
            f"clip_{index}.mp4"
        )

        print("⬇️ İndiriliyor...")

        video_response = requests.get(
            video_url,
            timeout=60
        )

        video_response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(video_response.content)

        print(f"✅ Kaydedildi: {output_path}")

        return output_path

    return None


# ============================================================
# VİDEOLARI DİKEY FORMATLA
# ============================================================

def convert_clip(input_path, index):

    output_path = os.path.join(
        OUTPUT_DIR,
        f"vertical_{index}.mp4"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,

        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        ),

        "-t",
        "8",

        "-r",
        "30",

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "fast",

        "-crf",
        "23",

        output_path
    ]

    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    return output_path


# ============================================================
# GEMINI TTS
# ============================================================

def generate_voice(script):

    print("\n🎙️ Ses oluşturuluyor...")

    response = client.models.generate_content(
        model="gemini-3.8-flash-tts",
        contents=script,
        config={
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": "Kore"
                    }
                }
            }
        }
    )

    audio = response.candidates[0].content.parts[0].inline_data.data

    audio_path = os.path.join(
        OUTPUT_DIR,
        "voice.wav"
    )

    with open(audio_path, "wb") as f:
        f.write(audio)

    print("✅ Ses hazır.")

    return audio_path


# ============================================================
# ALTYAZI
# ============================================================

def create_subtitles(data):

    print("\n💬 Altyazılar hazırlanıyor...")

    english = data["script"]
    turkish = data["turkish_translation"]

    english_words = english.split()
    turkish_words = turkish.split()

    duration = 45

    def make_chunks(words, chunk_size=7):

        chunks = []

        for i in range(0, len(words), chunk_size):
            chunks.append(
                " ".join(words[i:i + chunk_size])
            )

        return chunks

    eng_chunks = make_chunks(english_words)
    tr_chunks = make_chunks(turkish_words)

    count = max(
        len(eng_chunks),
        len(tr_chunks)
    )

    subtitle_path = os.path.join(
        OUTPUT_DIR,
        "subtitles.ass"
    )

    with open(
        subtitle_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: English,Arial,48,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,80,80,300,1
Style: Turkish,Arial,38,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,210,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        )

        for i in range(count):

            start = i * duration / count
            end = (i + 1) * duration / count

            def ass_time(seconds):

                hours = int(seconds // 3600)
                minutes = int(
                    (seconds % 3600) // 60
                )
                secs = int(seconds % 60)
                centis = int(
                    (seconds - int(seconds)) * 100
                )

                return (
                    f"{hours}:{minutes:02d}:"
                    f"{secs:02d}.{centis:02d}"
                )

            if i < len(eng_chunks):

                f.write(
                    f"Dialogue: 0,"
                    f"{ass_time(start)},"
                    f"{ass_time(end)},"
                    f"English,,0,0,0,,"
                    f"{eng_chunks[i]}\n"
                )

            if i < len(tr_chunks):

                f.write(
                    f"Dialogue: 0,"
                    f"{ass_time(start)},"
                    f"{ass_time(end)},"
                    f"Turkish,,0,0,0,,"
                    f"{tr_chunks[i]}\n"
                )

    print("✅ Altyazılar hazır.")

    return subtitle_path


# ============================================================
# FİNAL VİDEO
# ============================================================

def create_final_video(video_paths, audio_path, subtitle_path):

    print("\n🎬 Final video oluşturuluyor...")

    concat_file = os.path.join(
        OUTPUT_DIR,
        "concat.txt"
    )

    with open(
        concat_file,
        "w",
        encoding="utf-8"
    ) as f:

        for path in video_paths:

            absolute_path = os.path.abspath(path)

            f.write(
                f"file '{absolute_path}'\n"
            )

    merged_video = os.path.join(
        OUTPUT_DIR,
        "merged.mp4"
    )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        concat_file,

        "-c",
        "copy",

        merged_video
    ]

    subprocess.run(
        command,
        check=True
    )

    final_path = os.path.join(
        OUTPUT_DIR,
        "final_short.mp4"
    )

    command = [
        "ffmpeg",
        "-y",

        "-i",
        merged_video,

        "-i",
        audio_path,

        "-vf",
        f"ass={subtitle_path}",

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "libx264",

        "-preset",
        "fast",

        "-crf",
        "23",

        "-c:a",
        "aac",

        "-b:a",
        "128k",

        "-shortest",

        "-movflags",
        "+faststart",

        final_path
    ]

    subprocess.run(
        command,
        check=True
    )

    print("\n✅ FINAL SHORT HAZIR!")

    return final_path


# ============================================================
# YOUTUBE UPLOAD
# ============================================================

def upload_to_youtube(data):

    print("\n📺 YouTube'a yükleniyor...")

    if not YOUTUBE_CLIENT_ID:
        raise RuntimeError(
            "❌ YOUTUBE_CLIENT_ID bulunamadı!"
        )

    if not YOUTUBE_CLIENT_SECRET:
        raise RuntimeError(
            "❌ YOUTUBE_CLIENT_SECRET bulunamadı!"
        )

    if not YOUTUBE_REFRESH_TOKEN:
        raise RuntimeError(
            "❌ YOUTUBE_REFRESH_TOKEN bulunamadı!"
        )

    credentials = Credentials(

        token=None,

        refresh_token=YOUTUBE_REFRESH_TOKEN,

        token_uri=(
            "https://oauth2.googleapis.com/token"
        ),

        client_id=YOUTUBE_CLIENT_ID,

        client_secret=YOUTUBE_CLIENT_SECRET,

        scopes=[
            "https://www.googleapis.com/auth/youtube.upload"
        ],
    )

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials
    )

    title = data["title"]

    description = data["description"]

    tags = data.get(
        "tags",
        [
            "Shorts",
            "How Does It Work"
        ]
    )

    request_body = {

        "snippet": {

            "title": title,

            "description": description,

            "tags": tags,

            "categoryId": "28",
        },

        "status": {

            "privacyStatus": "private",

            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(

        "output/final_short.mp4",

        mimetype="video/mp4",

        chunksize=-1,

        resumable=True,
    )

    request = youtube.videos().insert(

        part="snippet,status",

        body=request_body,

        media_body=media,
    )

    response = request.execute()

    video_id = response["id"]

    print("\n" + "=" * 55)

    print("🎉 YOUTUBE YÜKLEMESİ BAŞARILI!")

    print("=" * 55)

    print(f"🎬 Konu: {data['topic']}")

    print(f"🏷️ Başlık: {title}")

    print(f"🆔 Video ID: {video_id}")

    print(
        f"https://www.youtube.com/watch?v={video_id}"
    )

    print("🔒 Gizlilik: PRIVATE")

    print("=" * 55)


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 55)
    print("🤖 YOUTUBE SHORTS BOT")
    print("=" * 55)

    # 1. Yeni konu + script + metadata
    data = generate_video_info()

    # 2. Ses
    audio_path = generate_voice(
        data["script"]
    )

    # 3. Pixabay görüntüleri
    video_paths = []

    for i, query in enumerate(
        data["visual_queries"],
        start=1
    ):

        path = search_pixabay(
            query,
            i
        )

        if path:
            try:

                vertical = convert_clip(
                    path,
                    i
                )

                video_paths.append(
                    vertical
                )

            except Exception as e:

                print(
                    f"⚠️ Klip işlenemedi: {e}"
                )

    if len(video_paths) < 2:

        raise RuntimeError(
            "❌ Yeterli Pixabay videosu bulunamadı!"
        )

    # 4. Altyazılar
    subtitle_path = create_subtitles(
        data
    )

    # 5. Final video
    create_final_video(
        video_paths,
        audio_path,
        subtitle_path
    )

    # 6. YouTube
    upload_to_youtube(
        data
    )

    print("\n")
    print("=" * 55)
    print("🚀 İŞLEM TAMAMLANDI")
    print("=" * 55)
    print(
        "Gemini → Script → TTS → Pixabay → "
        "FFmpeg → Altyazı → YouTube"
    )
    print("=" * 55)


if __name__ == "__main__":
    main()
