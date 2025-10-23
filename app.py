from pydub import AudioSegment
import streamlit as st
from openai import OpenAI
from dotenv import dotenv_values
from getpass import getpass
import os
import base64


def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


## Tło główne aplikacji i sidebar z obrazem odnoszącym się do nauki języków

# Ustalenie ścieżki katalogu skryptu
current_dir = os.path.dirname(os.path.abspath(__file__))

# Ścieżki do plików jpg w tym katalogu
main_bg_path = os.path.join(current_dir, "kino.jpg")       
sidebar_bg_path = os.path.join(current_dir, "sidebar.jpg")   

# Konwertowanie obrazów do base64
main_bg = get_base64_of_bin_file(main_bg_path)
sidebar_bg = get_base64_of_bin_file(sidebar_bg_path)

# Kod CSS ustawiający tło aplikacji
st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{main_bg}");
        background-size: cover;
        background-attachment: fixed;
    }}
    [data-testid="stSidebar"] {{
        background-image: url("data:image/jpg;base64,{sidebar_bg}");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Tytuł aplikacji
st.title("Generator napisów do filmów")

# Wprowadzenie klucza OpenAI z obsługą wyjątków
openai_key = st.text_input("Wprowadź swój klucz OpenAI", type="password")
if not openai_key:
    st.warning("Musisz podać klucz OpenAI, aby kontynuować.")
    st.stop()

try:
    openai_client = OpenAI(api_key=openai_key)
# Testowe wywołanie API - lista modeli służy do weryfikacji klucza
    openai_client.models.list()
    st.success("Klucz API zaakceptowany. Aplikacja działa.")
except Exception as e:
    st.error(f"Nieprawidłowy klucz OpenAI lub błąd połączenia:\n{e}")
    st.stop()


# Ustawienia modelu transkrypcji oraz formatu napisów
def generate_subtitles(audio_path, lang_code):
    with open(audio_path, "rb") as f:
        transcript = openai_client.audio.transcriptions.create(
            file=f,
            model="whisper-1",
            response_format="srt",
            language=lang_code
        )
    return transcript


# Ustawienia modelu chata
def translate_text(text, target_lang_code):
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful translator.Do not add your own comments to the translated text."},
            {
                "role": "user",
                "content": f"Translate the following text to {target_lang_code}:\n\n{text}"
            },
        ],
        temperature=0,
    )
    return response.choices[0].message.content


# Inicjowanie języka jeśli nie jema go w session_state
if 'selected_lang' not in st.session_state:
    st.session_state['selected_lang'] = 'polski'

with st.sidebar:
    st.header("Wybierz język napisów")
    selected_lang = st.selectbox(
        "Język napisów",
        ["polski", "angielski"],
        index=["polski", "angielski"].index(st.session_state['selected_lang'])
    )
    st.session_state['selected_lang'] = selected_lang  # Zapamiętujemy w stanie sesji

lang_map = {"polski": "pl", "angielski": "en"}
lang_code = lang_map[st.session_state['selected_lang']]

# wybór pliku do pobrania
uploaded_file = st.file_uploader("Wybierz plik wideo/audio", type=["mp4", "mp3"])

# Procedura wyodrębniania pliku audio po pobraniu
if uploaded_file:
    st.write("Nazwa:", uploaded_file.name)
    if uploaded_file.name.lower().endswith(".mp4"):
        st.video(uploaded_file)
    else:
        st.audio(uploaded_file)

    audio = AudioSegment.from_file(uploaded_file)
    output_audio_path = uploaded_file.name.rsplit(".", 1)[0] + ".mp3"
    audio.export(output_audio_path, format="mp3")
    st.write(f"Wyodrębniono plik audio i zapisano jako: {output_audio_path}")

    # Generowanie napisów 
    if "original_srt_text" not in st.session_state:
        with st.spinner("Generowanie napisów..."):
            st.session_state.original_srt_text = generate_subtitles(output_audio_path, "pl")
            st.session_state.srt_text = st.session_state.original_srt_text
            st.session_state.lang_code_prev = "pl"

    # Tłumaczenie za każdym razem, gdy wybrany język odbiega od poprzednio wybranego
    if lang_code != st.session_state.lang_code_prev:
        st.session_state.download_ready = False
        st.session_state.download_finished = False
        with st.spinner(f"Tłumaczenie na {st.session_state['selected_lang']}..."):
            translated = translate_text(st.session_state.original_srt_text, lang_code)
            st.session_state.srt_text = translated
            st.session_state.lang_code_prev = lang_code

    # Przedstawienie wyodrębnionych napisów
    srt_text_new = st.text_area("Napisy SRT:", st.session_state.srt_text, height=400)
    st.session_state.srt_text = srt_text_new

    st.text("Możesz edytować powyższe napisy lub zmienić ich język.")
    st.text("Potwierdź poprawność pliku i zapisz plik na dysk.")

    # Przycisk poprawności pliku tekstowego oraz zatwierdzania zmian
    if st.button("Potwierdź poprawność pliku tekstowego"):
        st.session_state.download_ready = True

    # Przycisk i procedura zapisu na dysku
    if st.session_state.get('download_ready', False):
        st.download_button(
            label="Zapisz plik na dysk",
            data=st.session_state.srt_text,
            file_name="subtitles.srt",
            on_click=lambda: st.session_state.update(download_finished=True, download_ready=False),
            type="primary",
            icon=":material/download:",
        )
    # Potwierdzenie poprawności zapisania pliku
    if st.session_state.get('download_finished', False):
        st.success("Plik został poprawnie zapisany na Twoim dysku")

else:
    st.info("Proszę wybrać plik z napisem 'Wybierz plik wideo/audio' powyżej, aby rozpocząć.")



