import streamlit as st
import sqlite3
import os
import edge_tts
from groq import Groq

# -------------------------------------------------------------
# 1. PAGE CONFIG & STYLING (Mobile Friendly)
# -------------------------------------------------------------
st.set_page_config(
    page_title="Shivaan's AI Dost",
    page_icon="🌟",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for clean mobile UI
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stTextInput textarea { border-radius: 20px !important; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. API & DATABASE SETUP
# -------------------------------------------------------------
# Aap y apni Groq API Key direct daal sakte hain ya Streamlit secrets use kar sakte hain
GROQ_API_KEY = "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"  
groq_client = Groq(api_key=GROQ_API_KEY)

def init_db():
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

def get_memory_context():
    conn = sqlite3.connect('shivaan_memory.db')
    cursor = conn.cursor()
    cursor.execute("SELECT note FROM papa_updates ORDER BY date DESC LIMIT 3")
    notes = cursor.fetchall()
    conn.close()
    
    context = ""
    for n in notes:
        context += f"- Papa Note: {n[0]}\n"
    return context

# -------------------------------------------------------------
# 3. GROQ MODEL & STRICT FACTUAL PROMPT
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

SYSTEM_PROMPT = """
Tumhara naam 'Dost' hai. Tum Shivaan Sharma ke sabse acche aur smart Dost ho.
Shivaan 1st class me padhta hai, uske papa Saurabh Sharma hain.

STRICT RULES:
1. Give STRICTLY factual, precise, and accurate answers. No random guessing or fokat ki baatein.
2. Keep answers very short (maximum 1-2 short sentences). 
3. Use polite Hinglish ("Aap", "Tum").
"""

def get_ai_response(user_query):
    memory = get_memory_context()
    full_prompt = f"{SYSTEM_PROMPT}\n\nRecent Memory:\n{memory}\n\nShivaan asks: {user_query}"
    
    model_name = get_active_groq_model()
    chat_completion = groq_client.chat.completions.create(
        messages=[{"role": "system", "content": full_prompt}, {"role": "user", "content": user_query}],
        model=model_name,
        temperature=0.3, # Low temperature for more factual output
        max_tokens=150
    )
    reply = chat_completion.choices[0].message.content

    conn = sqlite3.connect('shivaan_memory.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (user_msg, ai_reply) VALUES (?, ?)", (user_query, reply))
    conn.commit()
    conn.close()
    
    return reply

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
            conn = sqlite3.connect('shivaan_memory.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO papa_updates (note) VALUES (?)", (new_note,))
            conn.commit()
            conn.close()
            st.success("✅ Papa Note saved successfully!")

# Chat Session State initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display prior messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input Box
if prompt := st.chat_input("Dost se kuch poocho..."):
    # Add user message to session
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Dost soch raha hai..."):
            response = get_ai_response(prompt)
            st.markdown(response)
            
            # Optional: Generate voice response file for browser play
            async def make_audio():
                communicate = edge_tts.Communicate(response, "hi-IN-MadhurNeural")
                await communicate.save("temp_audio.mp3")
            import asyncio
            asyncio.run(make_audio())
            
            if os.path.exists("temp_audio.mp3"):
                st.audio("temp_audio.mp3", format="audio/mp3", autoplay=True)

    st.session_state.messages.append({"role": "assistant", "content": response})