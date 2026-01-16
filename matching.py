import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# ADVANCED EMERALD CSS (FORCED STYLING)
# =========================================================
st.markdown("""
    <style>
    /* Force Emerald Buttons */
    button[kind="primary"], .stButton > button {
        background-color: #10b981 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
    }
    
    button:hover {
        background-color: #059669 !important;
        border: none !important;
    }

    /* Chat Stage Background */
    .chat-stage {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        height: 500px;
        overflow-y: auto;
        padding: 25px;
        margin-bottom: 20px;
        display: flex;
        flex-direction: column;
    }

    /* Message Styling */
    .message-container { margin-bottom: 15px; display: flex; flex-direction: column; }
    
    .my-message {
        background-color: #10b981; /* Emerald */
        color: white;
        padding: 12px 18px;
        border-radius: 15px 15px 2px 15px;
        align-self: flex-end;
        max-width: 80%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .peer-message {
        background-color: #f3f4f6; /* Light Gray */
        color: #1f2937;
        padding: 12px 18px;
        border-radius: 15px 15px 15px 2px;
        align-self: flex-start;
        max-width: 80%;
        border: 1px solid #e5e7eb;
    }

    .author-name {
        font-size: 0.75rem;
        font-weight: bold;
        margin-bottom: 4px;
        color: #6b7280;
    }
    .author-me { text-align: right; color: #10b981; }

    /* Fix for file uploader alignment */
    .stFileUploader { padding-top: 0px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# SYSTEM CORE
# =========================================================
def ensure_state():
    if "chat_log" not in st.session_state: st.session_state.chat_log = []
    if "last_ts" not in st.session_state: st.session_state.last_ts = 0
    if "ai_history" not in st.session_state: st.session_state.ai_history = []
    if "current_match_id" not in st.session_state: st.session_state.current_match_id = None

ensure_state()

def reset_session():
    if st.session_state.current_match_id:
        conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
        conn.commit()
    st.session_state.current_match_id = None
    st.session_state.chat_log = []
    st.session_state.last_ts = 0
    st.rerun()

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.title("Study Dashboard")
    st.divider()
    
    st.subheader("AI Tutor")
    ai_prompt = st.text_area("Ask for clarification", placeholder="Explain this concept...", key="side_ai", height=100)
    if st.button("Query AI", use_container_width=True):
        if ai_prompt:
            with st.spinner("Generating..."):
                res = ask_ai(ai_prompt)
                st.session_state.ai_history.append((ai_prompt, res))

    for q, a in reversed(st.session_state.ai_history[-2:]):
        with st.expander(f"Previous: {q[:15]}...", expanded=False):
            st.write(a)

# =========================================================
# LIVE CHAT FRAGMENT
# =========================================================
@st.fragment(run_every=2)
def live_chat_display(match_id):
    # Fetch new data
    updates = conn.execute("SELECT sender, message, created_ts FROM messages WHERE match_id=? AND created_ts > ? ORDER BY created_ts ASC", 
                           (match_id, st.session_state.last_ts)).fetchall()
    
    if updates:
        for s, m, ts in updates:
            st.session_state.chat_log.append((s, m))
            st.session_state.last_ts = max(st.session_state.last_ts, ts)

    # Render Chat Stage
    st.markdown('<div class="chat-stage">', unsafe_allow_html=True)
    for sender, msg in st.session_state.chat_log:
        is_me = (sender == st.session_state.user_name)
        msg_style = "my-message" if is_me else "peer-message"
        lbl_style = "author-me" if is_me else ""
        name = "You" if is_me else sender
        
        st.markdown(f"""
            <div class="message-container">
                <div class="author-name {lbl_style}">{name}</div>
                <div class="{msg_style}">{msg}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# PAGE ROUTING
# =========================================================
def matchmaking_page():
    ensure_state()
    
    if not st.session_state.current_match_id:
        # Check for passive match assignment
        check = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", (st.session_state.user_id,)).fetchone()
        if check and check[0]:
            st.session_state.current_match_id = check[0]
            st.rerun()

        st.header("Peer Discovery")
        st.info("Find a partner to start a real-time collaborative study session.")
        
        if st.button("Search for Study Partner", type="primary"):
            peer = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.status='waiting' AND p.user_id!=?", (st.session_state.user_id,)).fetchone()
            if peer:
                m_id = f"live_{min(st.session_state.user_id, peer[0])}_{int(time.time())}"
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?,?)", (m_id, st.session_state.user_id, peer[0]))
                conn.commit()
                st.session_state.current_match_id = m_id
                st.rerun()
            else:
                st.warning("Looking for active peers... please keep this window open.")
    
    else:
        # Live Session Header
        c1, c2 = st.columns([5, 1])
        c1.title("Live Study Session")
        if c2.button("Exit Room"):
            reset_session()

        # Chat Stage
        live_chat_display(st.session_state.current_match_id)
        
        # Bottom Control Panel
        with st.container():
            col_in, col_file, col_send = st.columns([4, 1, 1])
            with col_in:
                text = st.text_input("Enter message", placeholder="Discuss your topic...", label_visibility="collapsed", key="chat_msg_input")
            with col_file:
                st.file_uploader("Upload", label_visibility="collapsed")
            with col_send:
                if st.button("Send Message", type="primary", use_container_width=True):
                    if text:
                        conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)", 
                                     (st.session_state.current_match_id, st.session_state.user_name, text, int(time.time())))
                        conn.commit()
                        st.rerun()

if __name__ == "__main__":
    matchmaking_page()
