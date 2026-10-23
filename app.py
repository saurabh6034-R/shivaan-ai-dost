import streamlit as st
import sqlite3
import os
import asyncio
import datetime
import edge_tts
from groq import Groq

# -------------------------------------------------------------
# 1. PAGE CONFIG & STYLING (Bada Mic & Clean UI)
# -------------------------------------------------------------
st.set_page_config(
    page_title="Shivaan's AI Dost",
    page_icon="🌟",
    layout="centered"
)

st.markdown("""
    <style>
    /* Mic button ko bada aur highlight karne ke liye CSS */
    div[data-testid="stAudioInput"] {
        background-color: #1e293b;
        border-radius: 15px;
        padding: 20px;
        border: 2px solid #3b82f6;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. API & DATABASE SETUP
# -------------------------------------------------------------
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_API_KEY = "YOUR_FALLBACK_KEY_IF_LOCAL"

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
# 3. ROBUST MODEL DISCOVERY (Fixes 404 Error Permanently)
# -------------------------------------------------------------
def get_active_groq_model():
    try:
        models = groq_client.models.list()
        active_ids = [m.id for m in models.data]
        valid_text = [m for m in active_ids if "llama" in m.lower() and "guard" not in m.lower()]
        if valid_text:
            return valid_text[0]
        return active_ids[0] if active_ids else "llama3-8b-8192"
    except:
        return "llama3-8b-8192"

# Get current date to feed into AI brain
current_date_str = datetime.date.today().strftime("%d %B %Y")

SYSTEM_PROMPT = f"""
Tumhara naam 'Dost' hai. Tum Shivaan Sharma ke sabse acche aur smart Dost ho.
Shivaan 1st class me padhta hai, uske papa Saurabh Sharma hain.
Aaj ki taarikh (Current Date) hai: {current_date_str}.

STRICT RULES:
1. Give STRICTLY factual, precise, and accurate answers. No random guessing.
2. Keep answers very short (maximum 1-2 short sentences). 
3. Use polite Hinglish ("Aap", "Tum").
"""

def get_ai_response(user_query):
    try:
        memory = get_memory_context()
        full_prompt = f"{SYSTEM_PROMPT}\n\nRecent Memory:\n{memory}\n\nShivaan asks: {user_query}"
        
        model_name = get_active_groq_model()
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": full_prompt}, 
                {"role": "user", "content": user_query}
            ],
            model=model_name,
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
# 4. STREAMLIT UI DESIGN
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

# --- PROMINENT VOICE INPUT SECTION ---
st.write("---")
st.markdown("### 🎙️ Voice Assistant (Shivaan ke liye)")
st.caption("Mic button par click karke bolein, phir thodi der rukein jab tak Dost jawab na de:")
audio_bytes = st.audio_input("🎤 Bolne ke liye yahan click karein")

if audio_bytes:
    with st.spinner("🎙️ Dost sun raha hai... (Bolne ke baad wait karein)"):
        with open("user_voice.wav", "wb") as f:
            f.write(audio_bytes.read())
        
        user_query = transcribe_audio("user_voice.wav")
        
        if user_query:
            st.session_state.messages.append({"role": "user", "content": f"🗣️ (Voice): {user_query}"})
            with st.chat_message("user"):
                st.markdown(f"🗣️ (Voice): {user_query}")
                
            with st.chat_message("assistant"):
                with st.spinner("⚡ Dost soch raha hai..."):
                    response = get_ai_response(user_query)
                    st.markdown(response)
                    
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
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_path = loop.run_until_complete(text_to_speech(response))
            if os.path.exists(audio_path):
                st.audio(audio_path, format="audio/mp3", autoplay=True)

    st.session_state.messages.append({"role": "assistant", "content": response})
