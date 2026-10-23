import streamlit as st
import sqlite3
import os
import asyncio
import edge_tts
from groq import Groq

# -------------------------------------------------------------
# 1. PAGE CONFIG & STYLING
# -------------------------------------------------------------
st.set_page_config(
    page_title="Shivaan's AI Dost",
    page_icon="🌟",
    layout="centered"
)

# -------------------------------------------------------------
# 2. API & DATABASE SETUP (Using Streamlit Secrets for Safety)
# -------------------------------------------------------------
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_API_KEY = "YOUR_FALLBACK_KEY_IF_LOCAL"  # Local testing ke liye yahan key daal sakte hain

groq_client = Groq(api_key=GROQ_API_KEY)

def init_db():
    try:
        conn = sqlite3.connect('shivaan_memory.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papa_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                note TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_msg TEXT,
                ai_reply TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def get_memory_context():
    try:
        conn = sqlite3.connect('shivaan_memory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT note FROM papa_updates ORDER BY date DESC LIMIT 3")
        notes = cursor.fetchall()
        conn.close()
        
        context = ""
        for n in notes:
            context += f"- Papa Note: {n[0]}\n"
        return context
    except:
        return ""

# -------------------------------------------------------------
# 3. AI CORE & STRICT FACTUAL PROMPT
# -------------------------------------------------------------
SYSTEM_PROMPT = """
Tumhara naam 'Dost' hai. Tum Shivaan Sharma ke sabse acche aur smart Dost ho.
Shivaan 1st class me padhta hai, uske papa Saurabh Sharma hain.

STRICT RULES:
1. Give STRICTLY factual, precise, and accurate answers. No random guessing or fokat ki baatein.
2. Keep answers very short (maximum 1-2 short sentences). 
3. Use polite Hinglish ("Aap", "Tum").
"""

def get_ai_response(user_query):
    try:
        memory = get_memory_context()
        full_prompt = f"{SYSTEM_PROMPT}\n\nRecent Memory:\n{memory}\n\nShivaan asks: {user_query}"
        
        # Using a stable, high-performance chat model to avoid classification errors
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": full_prompt}, 
                {"role": "user", "content": user_query}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=150
        )
        reply = chat_completion.choices[0].message.content

        # Save to DB
        conn = sqlite3.connect('shivaan_memory.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_history (user_msg, ai_reply) VALUES (?, ?)", (user_query, reply))
        conn.commit()
        conn.close()
        
        return reply
    except Exception as e:
        return f"Arre Shivaan, thoda network issue lag raha hai! ({e})"

def transcribe_audio(audio_file_path):
    try:
        with open(audio_file_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_file_path, file.read()),
                model="whisper-large-v3",
                response_format="json",
                language="hi"
            )
        return transcription.text
    except Exception as e:
        return None

async def text_to_speech(text):
    output_file = "response_audio.mp3"
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    await communicate.save(output_file)
    return output_file

# -------------------------------------------------------------
# 4. STREAMLIT INTERACTIVE UI (Voice + Text + Papa Dashboard)
# -------------------------------------------------------------
init_db()

st.title("🌟 Shivaan's AI Dost")
st.write("Aapka apna smart aur factual AI assistant!")

# Sidebar for Papa Admin Dashboard
with st.sidebar:
    st.header("🔒 Papa Admin Dashboard")
    st.write("Shivaan ke liye memory update karein:")
    new_note = st.text_area("Naya Papa Note (e.g., Aaj school me sports day tha)")
    if st.button("Save Note to AI Memory"):
        if new_note:
            try:
                conn = sqlite3.connect('shivaan_memory.db')
                cursor = conn.cursor()
                cursor.execute("INSERT INTO papa_updates (note) VALUES (?)", (new_note,))
                conn.commit()
                conn.close()
                st.success("✅ Papa Note saved successfully!")
            except Exception as e:
                st.error(f"Error saving note: {e}")

# Session State for Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- VOICE INPUT SECTION (Browser Mic) ---
st.write("---")
st.subheader("🎙️ Voice Assistant (Shivaan ke liye)")
audio_bytes = st.audio_input("Mic dabayein aur boliye:")

if audio_bytes:
    with st.spinner("🎙️ Dost aapki aawaz sun raha hai..."):
        # Save temporary recorded audio from browser
        with open("user_voice.wav", "wb") as f:
            f.write(audio_bytes.read())
        
        # Transcribe using Whisper
        user_query = transcribe_audio("user_voice.wav")
        
        if user_query:
            st.session_state.messages.append({"role": "user", "content": f"🗣️ (Voice): {user_query}"})
            with st.chat_message("user"):
                st.markdown(f"🗣️ (Voice): {user_query}")
                
            # Get AI Reply
            with st.chat_message("assistant"):
                with st.spinner("⚡ Dost soch raha hai..."):
                    response = get_ai_response(user_query)
                    st.markdown(response)
                    
                    # Generate & Play Audio Response
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    audio_path = loop.run_until_complete(text_to_speech(response))
                    
                    if os.path.exists(audio_path):
                        st.audio(audio_path, format="audio/mp3", autoplay=True)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            st.warning("⚠️ Aawaz samajh nahi aayi, dubara koshish karein.")

# --- TEXT INPUT SECTION ---
if prompt := st.chat_input("Ya yahan type karein..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Dost soch raha hai..."):
            response = get_ai_response(prompt)
            st.markdown(response)
            
            # Speak text response
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_path = loop.run_until_complete(text_to_speech(response))
            if os.path.exists(audio_path):
                st.audio(audio_path, format="audio/mp3", autoplay=True)

    st.session_state.messages.append({"role": "assistant", "content": response})
