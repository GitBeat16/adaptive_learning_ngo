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
# DATABASE AUTO-REPAIR (FIXES OPERATIONAL ERROR)
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    # 1. Create table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            sender TEXT,
            message TEXT,
            created_ts INTEGER
        )
    """)
    
    # 2. SCHEMA MIGRATION: Check if file_path exists, if not, add it
    cursor.execute("PRAGMA table_info(messages)")
    columns = [column[1] for column in cursor.fetchall()]
    if "file_path" not in columns:
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN file_path TEXT")
            conn.commit()
        except Exception as e:
            st.error(f"Migration Error: {e}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            user_id INTEGER,
            rating INTEGER,
            feedback_ts INTEGER
        )
    """)
    conn.commit()

def ensure_session_state():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"
    if "user_id" not in st.session_state: st.session_state.user_id = 0
    if "user_name" not in st.session_state: st.session_state.user_name = "Guest"

# =========================================================
# PERMANENT EMERALD UI + RIPPLE CSS
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        .stApp { background-color: #f8fafc !important; }
        
        .emerald-card {
            background: white !important;
            padding: 35px !important;
            border-radius: 20px !important;
            border-top: 12px solid #10b981 !important;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1) !important;
            margin-bottom: 30px;
            color: #1e293b;
        }

        .emerald-card h1, .emerald-card h2, .emerald-card h3 {
            color: #064e3b !important;
            margin-top: 0px !important;
            font-weight: 800 !important;
        }

        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 16px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            width: 100% !important;
            transition: all 0.3s ease;
            text-transform: uppercase;
        }
        
        div.stButton > button:hover {
            background-color: #059669 !important;
            box-shadow: 0 10px 20px rgba(16, 185, 129, 0.4) !important;
            transform: translateY(-2px);
        }

        .chat-scroll-area {
            background: #f1f5f9 !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px;
            padding: 20px;
            height: 400px;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        .bubble { padding: 12px; border-radius: 12px; margin-bottom: 10px; max-width: 80%; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #d1d5db; border-bottom-left-radius: 2px; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# MATCHMAKING LOGIC
# =========================================================
def perform_match():
    uid = st.session_state.get('user_id', 0)
    peer = conn.execute("""
        SELECT p.user_id, a.name FROM profiles p 
        JOIN auth_users a ON a.id = p.user_id 
        WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
    """, (uid,)).fetchone()
    
    if peer:
        m_id = f"sess_{int(time.time())}"
        st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
        st.session_state.current_match_id = m_id
        conn.execute("UPDATE profiles SET status='busy', match_id=? WHERE user_id=?", (m_id, uid))
        conn.execute("UPDATE profiles SET status='busy', match_id=? WHERE user_id=?", (m_id, peer[0]))
        conn.commit()
        return True
    
    conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (uid,))
    conn.commit()
    return False

# =========================================================
# UI PAGES
# =========================================================

@st.fragment(run_every=2)
def render_live_chat():
    m_id = st.session_state.get("current_match_id")
    if not m_id: return

    # This query now works because of the migration logic above
    msgs = conn.execute(
        "SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
        (m_id,)
    ).fetchall()
    
    st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)
    for sender, message, file_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cls = "bubble-me" if is_me else "bubble-peer"
        if message:
            st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{message}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Scan for available collaborators to begin a peer-to-peer session.")
    if st.button("Search Compatible Partner"):
        if perform_match():
            st.session_state.session_step = "live"
            st.rerun()
        else:
            st.info("System: Scanning active nodes. You are now in the queue.")
    st.markdown("</div>", unsafe_allow_html=True)

def show_live():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Collaborating with {st.session_state.peer_info['name']}")
    render_live_chat()
    
    c1, c2 = st.columns([4, 1])
    with c1:
        txt = st.text_input("Message", label_visibility="collapsed", placeholder="Type message...", key="live_msg")
    with c2:
        if st.button("Send"):
            if txt:
                conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                            (st.session_state.current_match_id, st.session_state.user_name, txt, int(time.time())))
                conn.commit()
                st.rerun()

    if st.button("Finish Session"):
        st.session_state.session_step = "summary"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Analysis")
    st.info("Review your chat summary and provide feedback.")
    
    if st.button("Start Knowledge Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Assessment")
    if st.button("Complete & Exit"):
        st.session_state.session_step = "discovery"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def matchmaking_page():
    sync_db_schema() # Runs the migration check
    inject_ui()
    ensure_session_state()

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "live": show_live()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
