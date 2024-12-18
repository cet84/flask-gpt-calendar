import sys
import io
import openai
import sounddevice as sd
from scipy.io.wavfile import write
import json  # JSON modülünü ekledik
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

# UTF-8 kodlamasını zorunlu olarak ayarla
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# OpenAI API anahtarı
openai.api_key = os.getenv("OPENAI_API_KEY")

# Ses kaydı fonksiyonu
def record_audio(filename="recording.wav", duration=5, sample_rate=44100):
    print("🎤 Ses kaydı başlıyor, lütfen konuşmaya başlayın...")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    write(filename, sample_rate, recording)
    print(f"✅ Ses kaydedildi: {filename}")

# OpenAI Whisper API ile metne dönüştürme
def transcribe_audio(filename):
    try:
        print("📤 Ses dosyası OpenAI'ye gönderiliyor...")
        with open(filename, "rb") as audio_file:
            response = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        print("📝 Metin Çıktısı:")
        print(response.text)
        return response.text
    except Exception as e:
        print(f"❌ Bir hata oluştu: {str(e)}")
        return None

# JSON'a kaydetme
def save_to_json(data, filename="data.json"):
    try:
        try:
            with open(filename, "r", encoding="utf-8") as file:
                existing_data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []

        existing_data.append(data)

        with open(filename, "w", encoding="utf-8") as file:
            json.dump(existing_data, file, indent=4, ensure_ascii=False)
        print(f"📁 Veriler {filename} dosyasına kaydedildi.")
    except Exception as e:
        print(f"❌ JSON'a kaydedilirken bir hata oluştu: {e}")

# Google Calendar servisi oluştur
import os

def get_calendar_service():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    # credentials.json dosyasının tam yolu
    credentials_path = os.path.join(os.path.dirname(__file__), "credentials.json")

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service

# Google Calendar'a etkinlik ekleme
def add_event_to_google_calendar(summary, description, start_date):
    try:
        service = get_calendar_service()
        event = {
            'summary': summary,
            'description': description,
            'start': {'date': start_date, 'timeZone': 'Europe/Istanbul'},
            'end': {'date': start_date, 'timeZone': 'Europe/Istanbul'},
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"📅 Etkinlik eklendi: {created_event.get('htmlLink')}")
    except Exception as e:
        print(f"❌ Google Calendar'a etkinlik eklenirken bir hata oluştu: {e}")

# GPT-4 ile analiz etme ve etkinlik ekleme
def analyze_text_with_gpt4(text):
    try:
        print("🤖 Metin GPT-4 ile analiz ediliyor...")
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that categorizes text and extracts important details like dates, people, and amounts."},
                {"role": "user", "content": f"Bu metni analiz et ve önemli detayları çıkar. Tarihi 'YYYY-MM-DD' formatında döndür:\n{text}"}
            ]
        )
        result = response.choices[0].message.content.strip()
        print("📊 GPT-4 Yanıtı:")
        print(result)

        json_data = {"original_text": text, "analysis": result}
        save_to_json(json_data)

        # Tarihi ayıkla ve Calendar'a ekle (manuel olarak tarih ekledim, GPT'den dönen tarihi kullanabilirsiniz)
        event_date = "2023-12-22"  # Örnek tarih, GPT'den gelen tarihle değiştirilebilir
        add_event_to_google_calendar("Hatırlatma", result, event_date)

    except Exception as e:
        print(f"❌ Bir hata oluştu: {str(e)}")

# Ana program akışı
if __name__ == "__main__":
    audio_file = "recording.wav"
    record_audio(audio_file, duration=5)
    transcribed_text = transcribe_audio(audio_file)
    if transcribed_text:
        analyze_text_with_gpt4(transcribed_text)