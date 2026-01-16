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
    .stApp { background-color: #f0f2f5; }
    
    /* WhatsApp Style Chat Container */
    .chat-window {
        background-color: #e5ddd5;
        background-image: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png');
        background-repeat: repeat;
        padding: 20px;
        border-radius: 10px;
        height: 60vh;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        border: 1px solid #ddd;
    }

    /* Message Bubbles */
    .bubble {
        max-width: 75%;
        padding: 8px 12px;
        margin-bottom: 10px;
        border-radius: 8px;
        font-size: 0.95rem;
        position: relative;
        box-shadow: 0 1px 1px rgba(0,0,0,0.1);
        line-height: 1.4;
    }
    .user-bubble {
        background-color: #dcf8c6;
        align-self: flex-end;
        border-top-right-radius: 0;
        border-right: 3px solid #06d755;
    }
    .partner-bubble {
        background-color: #ffffff;
        align-self: flex-start;
        border-top-left-radius: 0;
        border-left: 3px solid #10b981;
    }
    .msg-meta { font-size: 0.7rem; color: #075e54; margin-bottom: 2px; font-weight: bold; text-transform: uppercase; }

    /* Emerald Buttons with Ripple Effect simulation */
    div.stButton > button {
        background-color: #06d755;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 10px 24px;
        transition: 0.3s all;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background-color: #05bc4a;
        box-shadow: 0 4px 15px rgba(6, 215, 85, 0.3);
        transform: translateY(-1px);
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# HELPERS & STATE
# =========================================================
def now():
    return int(time.time())

def init_state():
    """Initializes all required session state keys to prevent AttributeErrors."""
    if "chat_log" not in st.session_state: st.session_state.chat_log = []
    if "last_msg_ts" not in st.session_state: st.session_state.last_msg_ts = 0
    if "ai_history" not in st.session_state: st.session_state.ai_history = []
    if "current_match_id" not in st.session_state: st.session_state.current_match_id = None
    if "proposed_match" not in st.session_state: st.session_state.proposed_match = None
    if "session_ended" not in st.session_state: st.session_state.session_ended = False

def reset_session():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for key in ["current_match_id", "chat_log", "last_msg_ts", "proposed_match", "session_ended"]:
        if key in st.session_state: st.session_state[key] = None
    st.rerun()

# Initialize state immediately upon module import to fix the error
init_state()

# =========================================================
# SIDEBAR (AI CHATBOT)
# =========================================================
with st.sidebar:
    st.markdown("### 🤖 AI Study Assistant")
    ai_query = st.text_input("Ask a question...", key="sidebar_ai_q", placeholder="Explain calculus...")
    if st.button("Query AI", use_container_width=True) and ai_query:
        with st.spinner("Thinking..."):
            ans = ask_ai(ai_query)
            st.session_state.ai_history.append((ai_query, ans))
    
    st.divider()
    # Fixed slice logic to handle empty lists
    history = st.session_state.get("ai_history", [])
    for q, a in reversed(history[-3:]):
        with st.container(border=True):
            st.caption(f"You: {q}")
            st.markdown(f"**AI:** {a}")

# =========================================================
# CHAT ENGINE
# =========================================================
@st.fragment(run_every=3)
def live_chat_window(match_id):
    # Fetch only new messages since last timestamp
    rows = conn.execute("""
        SELECT sender, message, created_ts FROM messages 
        WHERE match_id=? AND created_ts > ? ORDER BY created_ts ASC
    """, (match_id, st.session_state.last_msg_ts)).fetchall()

    if rows:
        for s, m, ts in rows:
            st.session_state.chat_log.append((s, m))
            st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)

    # Render Messages
    st.markdown('<div class="chat-window">', unsafe_allow_html=True)
    for sender, msg in st.session_state.chat_log:
        is_me = (sender == st.session_state.user_name)
        bubble_class = "user-bubble" if is_me else "partner-bubble"
        display_name = "You" if is_me else sender
        st.markdown(f"""
            <div class="bubble {bubble_class}">
                <div class="msg-meta">{display_name}</div>
                <div>{msg}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# MAIN INTERFACE
# =========================================================
def matchmaking_page():
    if not st.session_state.get("user_id"):
        st.error("Please log in to access matchmaking.")
        return

    # Phase 1: Matchmaking Handshake
    if not st.session_state.current_match_id:
        st.title("Partner Discovery")
        
        # Check for incoming match sync from DB
        row = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", 
                           (st.session_state.user_id,)).fetchone()
        if row and row[0]:
            st.session_state.current_match_id = row[0]
            st.rerun()

        if st.button("Find Compatible Partner", use_container_width=True):
            # Existing compatibility logic
            res = conn.execute("""
                SELECT p.user_id, a.name FROM profiles p 
                JOIN auth_users a ON a.id=p.user_id 
                WHERE p.status='waiting' AND p.user_id!=?
            """, (st.session_state.user_id,)).fetchone()
            
            if res:
                target_id, target_name = res
                mid = f"chat_{min(st.session_state.user_id, target_id)}_{now()}"
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?,?)", 
                             (mid, st.session_state.user_id, target_id))
                conn.commit()
                st.session_state.current_match_id = mid
                st.balloons()
                st.rerun()
            else:
                st.info("Searching for peers... Stay on this page.")

    # Phase 2: Live Session (WhatsApp UI)
    else:
        # Header Controls
        h_col1, h_col2 = st.columns([4, 1])
        h_col1.subheader(f"🟢 Session: {st.session_state.current_match_id}")
        if h_col2.button("End Session"):
            # Post-session features
            full_chat = " ".join([m for _, m in st.session_state.chat_log])
            st.session_state.summary = ask_ai("Summarize this study session: " + full_chat)
            st.session_state.quiz = ask_ai("Create 3 MCQs based on: " + full_chat)
            st.session_state.session_ended = True
            reset_session()

        # Chat Area
        live_chat_window(st.session_state.current_match_id)

        # Bottom Input Bar (WhatsApp Style)
        with st.container():
            st.markdown("<br>", unsafe_allow_html=True)
            col_file, col_msg, col_send = st.columns([0.5, 4, 1])
            
            with col_file:
                up_file = st.file_uploader("📎", label_visibility="collapsed")
                if up_file:
                    st.toast("File synchronized!")

            with col_msg:
                m_input = st.text_input("Message", placeholder="Write a message...", label_visibility="collapsed", key="active_msg")

            with col_send:
                if st.button("Send"):
                    if m_input:
                        conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                     (st.session_state.current_match_id, st.session_state.user_name, m_input, now()))
                        conn.commit()
                        st.rerun()

if __name__ == "__main__":
    matchmaking_page()
