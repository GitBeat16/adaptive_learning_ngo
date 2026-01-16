import streamlit as st
import time
import os
import json
from database import conn
from ai_helper import ask_ai

# Ensure upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# DATABASE SCHEMA AUTO-FIX
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(profiles)")
    cols = [c[1] for c in cursor.fetchall()]
    updates = {
        "status": "TEXT DEFAULT 'waiting'",
        "match_id": "TEXT",
        "interests": "TEXT DEFAULT 'General Study'",
        "bio": "TEXT DEFAULT 'Ready to learn!'"
    }
    for col, definition in updates.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} {definition}")
    
    # Updated messages table to include file paths
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            sender TEXT,
            message TEXT,
            file_path TEXT,
            created_ts INTEGER
        )
    """)
    conn.commit()

sync_db_schema()

# =========================================================
# FORCED EMERALD UI (OVERRIDE PINK & REMOVE EMOJIS)
# =========================================================
st.markdown("""
    <style>
    /* Force Background and Text Colors */
    .stApp {
        background-color: #f8fafc !important;
    }
    
    /* Force Emerald Buttons */
    div.stButton > button {
        background-color: #10b981 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.2) !important;
    }
    
    div.stButton > button:hover {
        background-color: #059669 !important;
        color: white !important;
        transform: translateY(-1px) !important;
    }

    /* Message Bubbles */
    .chat-container {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 20px;
        height: 400px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
    }
    
    .bubble {
        padding: 10px 15px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 75%;
    }
    
    .bubble-me {
        background-color: #10b981 !important;
        color: white !important;
        align-self: flex-end;
        border-bottom-right-radius: 2px;
    }
    
    .bubble-peer {
        background-color: #f1f5f9 !important;
        color: #1e293b !important;
        align-self: flex-start;
        border-bottom-left-radius: 2px;
        border: 1px solid #e2e8f0 !important;
    }

    /* Section Cards */
    .emerald-card {
        background: white !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border-left: 5px solid #10b981 !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# LOGIC & HELPERS
# =========================================================
def ensure_state():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"
    if "ai_history" not in st.session_state: st.session_state.ai_history = []

def reset_matchmaking():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for key in ["current_match_id", "peer_info", "quiz_data", "summary"]:
        st.session_state[key] = None
    st.session_state.session_step = "discovery"
    st.rerun()

# =========================================================
# UI PAGES
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.subheader("Discovery Phase")
    st.write("Find a study partner based on your unique learning profile.")
    
    if st.button("Search for Partner", type="primary"):
        peer = conn.execute("""
            SELECT p.user_id, a.name, p.bio, p.interests 
            FROM profiles p JOIN auth_users a ON a.id=p.user_id 
            WHERE p.status='waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()
        
        if peer:
            st.session_state.peer_info = {"id": peer[0], "name": peer[1], "bio": peer[2], "ints": peer[3]}
            st.session_state.current_match_id = f"session_{int(time.time())}"
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.info("No active peers found. You are now in the waiting pool.")
            conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    p = st.session_state.peer_info
    st.markdown(f"### Match Found: {p['name']}")
    st.write(f"**Bio:** {p['bio']}")
    st.write(f"**Interests:** {p['ints']}")
    st.divider()
    
    c1, c2 = st.columns(2)
    if c1.button("Accept Match", type="primary"):
        st.balloons()
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    if c2.button("Decline"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def live_chat_fragment():
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                         (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for sender, message, file_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cl = "bubble-me" if is_me else "bubble-peer"
        
        if message:
            st.markdown(f'<div class="bubble {cl}"><b>{sender}</b><br>{message}</div>', unsafe_allow_html=True)
        if file_path:
            file_name = os.path.basename(file_path)
            st.markdown(f'<div class="bubble {cl}" style="font-size: 12px; opacity: 0.9;">Shared File: {file_name}</div>', unsafe_allow_html=True)
            with open(file_path, "rb") as f:
                st.download_button(label="Download File", data=f, file_name=file_name, key=f"dl_{file_name}_{time.time()}")
            
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.subheader(f"Session with {st.session_state.peer_info['name']}")
    
    live_chat_fragment()

    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            txt = st.text_input("Message", placeholder="Enter message...", label_visibility="collapsed", key="chat_in")
        with c2:
            file = st.file_uploader("Upload", label_visibility="collapsed", key="file_up")
        with c3:
            if st.button("Send", type="primary"):
                path = None
                if file:
                    path = os.path.join(UPLOAD_DIR, file.name)
                    with open(path, "wb") as f:
                        f.write(file.getbuffer())
                
                if txt or file:
                    conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, txt, path, int(time.time())))
                    conn.commit()
                    st.rerun()
    
    if st.button("End Session"):
        st.session_state.session_step = "summary"
        st.rerun()

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Summary")
    if not st.session_state.get("summary"):
        history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
        st.session_state.summary = ask_ai(f"Summarize this study session: {' '.join([m[0] for m in history if m[0]])}")
    
    st.write(st.session_state.summary)
    st.feedback("stars")
    
    if st.button("Take Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if st.button("Return Home"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Check")
    # Quiz Logic...
    if st.button("Complete"): 
        reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def matchmaking_page():
    ensure_state()
    with st.sidebar:
        st.title("AI Assistant")
        q = st.text_area("Request AI Support")
        if st.button("Execute Query"):
            st.write(ask_ai(q))

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
