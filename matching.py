import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# EMERALD WHATSAPP THEME (CSS)
# =========================================================
st.markdown("""
    <style>
    /* Main Layout */
    .stApp { background-color: #f0f2f5; }
    
    /* WhatsApp Style Chat Container */
    .chat-window {
        background-image: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png');
        background-repeat: repeat;
        padding: 20px;
        border-radius: 10px;
        height: 70vh;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
    }

    /* Message Bubbles */
    .bubble {
        max-width: 70%;
        padding: 8px 12px;
        margin-bottom: 10px;
        border-radius: 8px;
        font-size: 0.95rem;
        position: relative;
        box-shadow: 0 1px 1px rgba(0,0,0,0.1);
    }
    .user-bubble {
        background-color: #dcf8c6;
        align-self: flex-end;
        border-top-right-radius: 0;
    }
    .partner-bubble {
        background-color: #ffffff;
        align-self: flex-start;
        border-top-left-radius: 0;
    }
    .msg-meta { font-size: 0.7rem; color: #667781; margin-bottom: 2px; font-weight: bold; }

    /* Bottom Input Bar */
    .input-container {
        background-color: #f0f2f5;
        padding: 10px;
        position: fixed;
        bottom: 0;
        width: 100%;
    }

    /* Emerald Buttons */
    div.stButton > button {
        background-color: #06d755;
        color: white;
        border: none;
        border-radius: 20px;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #05bc4a;
        transform: scale(1.05);
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# CORE LOGIC
# =========================================================
def init_state():
    if "chat_log" not in st.session_state: st.session_state.chat_log = []
    if "last_msg_ts" not in st.session_state: st.session_state.last_msg_ts = 0
    if "ai_history" not in st.session_state: st.session_state.ai_history = []

def reset_session():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for key in ["current_match_id", "chat_log", "last_msg_ts", "proposed_match"]:
        if key in st.session_state: del st.session_state[key]
    st.rerun()

# =========================================================
# NAVIGATION (AI CHATBOT)
# =========================================================
with st.sidebar:
    st.title("Study Sidebar")
    st.markdown("### 🤖 AI Assistant")
    with st.container(border=True):
        ai_query = st.text_input("Ask AI anything...", key="sidebar_ai_input")
        if st.button("Get AI Help") and ai_query:
            answer = ask_ai(ai_query)
            st.session_state.ai_history.append((ai_query, answer))
        
        for q, a in reversed(st.session_state.ai_history[-3:]):
            st.markdown(f"**Q:** {q}")
            st.markdown(f"**A:** {a}")
            st.divider()

# =========================================================
# LIVE CHAT REFRESH SYSTEM
# =========================================================
@st.fragment(run_every=3)
def sync_chat(match_id):
    # Fetch all history if log is empty, else fetch new
    query = "SELECT sender, message, created_ts FROM messages WHERE match_id=? AND created_ts > ? ORDER BY created_ts ASC"
    rows = conn.execute(query, (match_id, st.session_state.last_msg_ts)).fetchall()

    if rows:
        for s, m, ts in rows:
            st.session_state.chat_log.append((s, m))
            st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)

    # Render WhatsApp style bubbles
    st.markdown('<div class="chat-window">', unsafe_allow_html=True)
    for sender, msg in st.session_state.chat_log:
        is_me = (sender == st.session_state.user_name)
        css = "user-bubble" if is_me else "partner-bubble"
        name = "You" if is_me else sender
        st.markdown(f"""
            <div class="bubble {css}">
                <div class="msg-meta">{name}</div>
                {msg}
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# MAIN APP FLOW
# =========================================================
def matchmaking_page():
    init_state()
    
    # PHASE 1: SEARCHING
    if not st.session_state.get("current_match_id"):
        st.header("Find Study Partner")
        
        # Check if someone else initiated a match
        row = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", (st.session_state.user_id,)).fetchone()
        if row:
            st.session_state.current_match_id = row[0]
            st.rerun()

        if st.button("Search for Partner", use_container_width=True):
            res = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.status='waiting' AND p.user_id!=?", (st.session_state.user_id,)).fetchone()
            if res:
                target_id, target_name = res
                mid = f"chat_{min(st.session_state.user_id, target_id)}_{int(time.time())}"
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?,?)", (mid, st.session_state.user_id, target_id))
                conn.commit()
                st.session_state.current_match_id = mid
                st.balloons()
                st.rerun()
            else:
                st.info("Searching for peers...")

    # PHASE 2: LIVE CHAT (WHATSAPP DESIGN)
    else:
        # Header
        col_title, col_exit = st.columns([4, 1])
        col_title.subheader(f"Study Session")
        if col_exit.button("End Session"):
            # Generate summary and quiz logic (previous features)
            st.session_state.summary = ask_ai("Summarize chat: " + str(st.session_state.chat_log))
            st.session_state.quiz = ask_ai("Create 3 MCQs: " + str(st.session_state.chat_log))
            reset_session()

        # Chat Window
        sync_chat(st.session_state.current_match_id)

        # Input Area (WhatsApp style combined bar)
        with st.container():
            col_up, col_in, col_btn = st.columns([1, 4, 1])
            
            with col_up:
                uploaded_file = st.file_uploader("📎", label_visibility="collapsed")
                if uploaded_file:
                    st.toast("File Attached")

            with col_in:
                msg_input = st.text_input("Type a message", placeholder="Message", label_visibility="collapsed", key="chat_in")

            with col_btn:
                if st.button("Send"):
                    if msg_input:
                        conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                     (st.session_state.current_match_id, st.session_state.user_name, msg_input, int(time.time())))
                        conn.commit()
                        st.rerun()

matchmaking_page()
