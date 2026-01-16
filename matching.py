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
# DATABASE AUTO-REPAIR & MUTUAL CONSENT SCHEMA
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    # Messages table
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
    # Profiles table additions for mutual consent
    cursor.execute("PRAGMA table_info(profiles)")
    cols = [c[1] for c in cursor.fetchall()]
    if "accepted" not in cols:
        conn.execute("ALTER TABLE profiles ADD COLUMN accepted INTEGER DEFAULT 0")
    
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
# PERMANENT EMERALD UI
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
        }
        .emerald-card h1, .emerald-card h2, .emerald-card h3 { color: #064e3b !important; font-weight: 800 !important; margin-top:0;}
        
        /* Emerald Button & Ripple */
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 14px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            width: 100% !important;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #059669 !important;
            box-shadow: 0 10px 20px rgba(16, 185, 129, 0.3) !important;
        }

        .chat-scroll-area {
            background: #f1f5f9 !important;
            border-radius: 12px;
            padding: 20px;
            height: 450px;
            overflow-y: auto;
            margin-bottom: 20px;
            border: 1px solid #e2e8f0;
        }
        .bubble { padding: 12px; border-radius: 12px; margin-bottom: 10px; max-width: 85%; position: relative; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #d1d5db; border-bottom-left-radius: 2px; }
        .file-link { color: #064e3b; font-weight: bold; text-decoration: underline; cursor: pointer; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# CORE LOGIC: MUTUAL CONFIRMATION
# =========================================================
def find_partner():
    uid = st.session_state.user_id
    # Reset acceptance status before searching
    conn.execute("UPDATE profiles SET status='waiting', accepted=0, match_id=NULL WHERE user_id=?", (uid,))
    
    peer = conn.execute("""
        SELECT p.user_id, a.name FROM profiles p 
        JOIN auth_users a ON a.id = p.user_id 
        WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
    """, (uid,)).fetchone()
    
    if peer:
        m_id = f"sess_{int(time.time())}"
        st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
        st.session_state.current_match_id = m_id
        conn.execute("UPDATE profiles SET status='confirming', match_id=? WHERE user_id=?", (m_id, uid))
        conn.execute("UPDATE profiles SET status='confirming', match_id=? WHERE user_id=?", (m_id, peer[0]))
        conn.commit()
        return True
    return False

# =========================================================
# CHAT & FILE FRAGMENT
# =========================================================
@st.fragment(run_every=2)
def render_live_chat():
    m_id = st.session_state.get("current_match_id")
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", (m_id,)).fetchall()
    
    st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)
    for sender, message, f_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cls = "bubble-me" if is_me else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{message if message else ""}', unsafe_allow_html=True)
        if f_path:
            fname = os.path.basename(f_path)
            st.markdown(f'📄 <a href="file://{f_path}" class="file-link">{fname}</a>', unsafe_allow_html=True)
            with open(f_path, "rb") as f:
                st.download_button(f"Download {fname}", f, file_name=fname, key=f"dl_{time.time()}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# UI PAGES
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Scan the network to find a peer for collaborative learning.")
    if st.button("Search Compatible Partner"):
        if find_partner():
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.info("Searching... You are now in the queue.")
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Match Found!")
    st.write(f"Would you like to connect with **{st.session_state.peer_info['name']}**?")
    
    # Check if BOTH have accepted
    peer_status = conn.execute("SELECT accepted FROM profiles WHERE user_id=?", (st.session_state.peer_info['id'],)).fetchone()
    my_status = conn.execute("SELECT accepted FROM profiles WHERE user_id=?", (st.session_state.user_id,)).fetchone()

    if my_status and my_status[0] == 1:
        st.warning("Waiting for partner to confirm...")
        if peer_status and peer_status[0] == 1:
            st.session_state.session_step = "live"
            st.rerun()
    else:
        if st.button("Establish Connection"):
            conn.execute("UPDATE profiles SET accepted=1 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.rerun()
    
    if st.button("Cancel Match"):
        conn.execute("UPDATE profiles SET status='waiting', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
        conn.commit()
        st.session_state.session_step = "discovery"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_live():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Collaborating: {st.session_state.peer_info['name']}")
    render_live_chat()
    
    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            txt = st.text_input("Message", label_visibility="collapsed", placeholder="Type message...", key="l_msg")
        with c2:
            up_file = st.file_uploader("Upload", label_visibility="collapsed", key="chat_file")
        with c3:
            if st.button("Send"):
                f_save_path = None
                if up_file:
                    f_save_path = os.path.join(UPLOAD_DIR, up_file.name)
                    with open(f_save_path, "wb") as f: f.write(up_file.getbuffer())
                if txt or up_file:
                    conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, txt, f_save_path, int(time.time())))
                    conn.commit()
                    st.rerun()

    if st.button("Finish Session"):
        st.session_state.session_step = "summary"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Analysis")
    st.feedback("stars")
    if st.button("Start AI Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Assessment")
    if st.button("Complete & Exit"):
        conn.execute("UPDATE profiles SET status='active', accepted=0, match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
        conn.commit()
        st.session_state.session_step = "discovery"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN ENTRY
# =========================================================
def matchmaking_page():
    sync_db_schema()
    inject_ui()
    ensure_session_state()

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
