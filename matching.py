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
# DATABASE SCHEMA (REINFORCED)
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT, sender TEXT, message TEXT, file_path TEXT, created_ts INTEGER
        )
    """)
    cursor.execute("PRAGMA table_info(profiles)")
    cols = [c[1] for c in cursor.fetchall()]
    if "accepted" not in cols:
        conn.execute("ALTER TABLE profiles ADD COLUMN accepted INTEGER DEFAULT 0")
    conn.commit()

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
        div.stButton > button:hover { background-color: #059669 !important; transform: scale(1.01); }
        .chat-scroll-area { background: #f1f5f9 !important; border-radius: 12px; padding: 20px; height: 450px; overflow-y: auto; border: 1px solid #e2e8f0; }
        .bubble { padding: 12px; border-radius: 12px; margin-bottom: 10px; max-width: 85%; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #d1d5db; border-bottom-left-radius: 2px; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# BACKGROUND LISTENER (THE KEY FIX)
# =========================================================
@st.fragment(run_every=3)
def session_listener():
    """Checks every 3 seconds if someone has requested a match with this user."""
    uid = st.session_state.user_id
    current_step = st.session_state.session_step
    
    # Check current status in DB
    status_data = conn.execute("SELECT status, match_id FROM profiles WHERE user_id=?", (uid,)).fetchone()
    
    if status_data:
        db_status, db_match_id = status_data
        
        # If DB says confirming but UI is still in discovery, force a move to confirmation
        if db_status == 'confirming' and current_step == 'discovery':
            # Find who requested the match
            peer = conn.execute("""
                SELECT p.user_id, a.name FROM profiles p 
                JOIN auth_users a ON a.id = p.user_id 
                WHERE p.match_id = ? AND p.user_id != ?
            """, (db_match_id, uid)).fetchone()
            
            if peer:
                st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
                st.session_state.current_match_id = db_match_id
                st.session_state.session_step = "confirmation"
                st.rerun()

# =========================================================
# UI PAGES
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Waiting for a match or searching for peers...")
    
    # Automatically set status to waiting so others can find this user
    conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=? AND status='active'", (st.session_state.user_id,))
    conn.commit()

    if st.button("Search Compatible Partner"):
        uid = st.session_state.user_id
        peer = conn.execute("""
            SELECT p.user_id, a.name FROM profiles p 
            JOIN auth_users a ON a.id = p.user_id 
            WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
        """, (uid,)).fetchone()
        
        if peer:
            m_id = f"sess_{int(time.time())}"
            st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
            st.session_state.current_match_id = m_id
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, uid))
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, peer[0]))
            conn.commit()
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.info("Added to queue. The system will notify you when a match is found.")
    
    # This keeps running while the user is on the discovery page
    session_listener()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Incoming Match Request")
    st.write(f"Peer **{st.session_state.peer_info['name']}** wants to start a live session with you.")
    
    # Get current mutual status
    my_acc = conn.execute("SELECT accepted FROM profiles WHERE user_id=?", (st.session_state.user_id,)).fetchone()[0]
    peer_acc = conn.execute("SELECT accepted FROM profiles WHERE user_id=?", (st.session_state.peer_info['id'],)).fetchone()[0]

    if my_acc == 1 and peer_acc == 1:
        st.success("Connection Secured! Entering session...")
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    elif my_acc == 1:
        st.warning(f"Accepted. Waiting for {st.session_state.peer_info['name']} to confirm...")
        # Auto-refresh to check peer's status
        time.sleep(2)
        st.rerun()
    else:
        if st.button("Accept and Connect"):
            conn.execute("UPDATE profiles SET accepted=1 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.rerun()
        
        if st.button("Decline"):
            conn.execute("UPDATE profiles SET status='waiting', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.session_state.session_step = "discovery"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def render_live_chat():
    m_id = st.session_state.get("current_match_id")
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", (m_id,)).fetchall()
    st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)
    for sender, msg, f_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cls = "bubble-me" if is_me else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg if msg else ""}', unsafe_allow_html=True)
        if f_path:
            with open(f_path, "rb") as f:
                st.download_button(f"Download Shared File", f, file_name=os.path.basename(f_path), key=f"dl_{time.time()}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_live():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Live Session: {st.session_state.peer_info['name']}")
    render_live_chat()
    
    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            txt = st.text_input("Message", label_visibility="collapsed", placeholder="Enter notes...", key="l_msg")
        with c2:
            up_file = st.file_uploader("Upload", label_visibility="collapsed", key="chat_file")
        with c3:
            if st.button("Send"):
                f_path = None
                if up_file:
                    f_path = os.path.join(UPLOAD_DIR, up_file.name)
                    with open(f_path, "wb") as f: f.write(up_file.getbuffer())
                if txt or up_file:
                    conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, txt, f_path, int(time.time())))
                    conn.commit()
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN ROUTER
# =========================================================
def matchmaking_page():
    sync_db_schema()
    inject_ui()
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live()
    elif step == "summary": st.write("Summary") # Placeholder
    elif step == "quiz": st.write("Quiz") # Placeholder

if __name__ == "__main__":
    matchmaking_page()
