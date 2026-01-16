import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# HIGH-FIDELITY EMERALD UI (CSS)
# =========================================================
st.markdown("""
    <style>
    /* Main Layout Styling */
    .stApp { background-color: #f9fafb; }
    
    /* Navigation Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }

    /* Fixed-Height Chat Window */
    .chat-view {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 20px;
        height: 550px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* Message Bubble Logic */
    .msg-group { display: flex; flex-direction: column; width: 100%; margin-bottom: 8px; }
    
    .bubble {
        padding: 10px 16px;
        border-radius: 18px;
        font-size: 0.95rem;
        max-width: 80%;
        line-height: 1.5;
        position: relative;
    }
    
    .user-msg {
        background-color: #059669;
        color: #ffffff;
        align-self: flex-end;
        border-bottom-right-radius: 4px;
    }
    
    .partner-msg {
        background-color: #f3f4f6;
        color: #111827;
        align-self: flex-start;
        border-bottom-left-radius: 4px;
        border: 1px solid #e5e7eb;
    }

    .sender-tag {
        font-size: 0.7rem;
        font-weight: 600;
        margin-bottom: 2px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .user-tag { align-self: flex-end; color: #059669; }

    /* Button and Input Styling */
    div.stButton > button {
        background-color: #059669;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #047857;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# SYSTEM HELPERS
# =========================================================
def now(): return int(time.time())

def init_state():
    if "chat_log" not in st.session_state: st.session_state.chat_log = []
    if "last_ts" not in st.session_state: st.session_state.last_ts = 0
    if "ai_history" not in st.session_state: st.session_state.ai_history = []
    if "current_match_id" not in st.session_state: st.session_state.current_match_id = None

def reset_session():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for key in ["current_match_id", "chat_log", "last_ts"]:
        st.session_state[key] = None if key != "chat_log" else []
    st.rerun()

init_state()

# =========================================================
# SIDEBAR NAVIGATION & AI
# =========================================================
with st.sidebar:
    st.markdown("### Navigation")
    if st.button("Return to Dashboard"):
        st.switch_page("app.py")
    
    st.divider()
    st.markdown("### Study Assistant")
    with st.container():
        query = st.text_input("AI Query", placeholder="Ask anything...", key="sidebar_ai", label_visibility="collapsed")
        if st.button("Ask Assistant") and query:
            res = ask_ai(query)
            st.session_state.ai_history.append((query, res))
    
    for q_h, a_h in reversed(st.session_state.ai_history[-3:]):
        with st.expander(f"Q: {q_h[:25]}...", expanded=False):
            st.write(a_h)

# =========================================================
# CHAT RENDERING ENGINE
# =========================================================
@st.fragment(run_every=3)
def sync_live_chat(match_id):
    # Polling for new content
    rows = conn.execute("SELECT sender, message, created_ts FROM messages WHERE match_id=? AND created_ts > ? ORDER BY created_ts ASC", 
                        (match_id, st.session_state.last_ts)).fetchall()
    
    if rows:
        for s, m, ts in rows:
            st.session_state.chat_log.append((s, m))
            st.session_state.last_ts = max(st.session_state.last_ts, ts)

    # Render CSS Chat Window
    st.markdown('<div class="chat-view">', unsafe_allow_html=True)
    for sender, msg in st.session_state.chat_log:
        is_me = (sender == st.session_state.user_name)
        msg_class = "user-msg" if is_me else "partner-msg"
        tag_class = "user-tag" if is_me else ""
        label = "You" if is_me else sender
        
        st.markdown(f"""
            <div class="msg-group">
                <div class="sender-tag {tag_class}">{label}</div>
                <div class="bubble {msg_class}">{msg}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# MAIN APP LOGIC
# =========================================================
def matchmaking_page():
    if not st.session_state.current_match_id:
        # Check for background matches
        check = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", (st.session_state.user_id,)).fetchone()
        if check and check[0]:
            st.session_state.current_match_id = check[0]
            st.rerun()

        st.title("Peer Matchmaking")
        st.write("Join a session to collaborate with other students in real-time.")
        
        if st.button("Find Active Partner", use_container_width=True):
            res = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.status='waiting' AND p.user_id!=?", (st.session_state.user_id,)).fetchone()
            if res:
                mid = f"chat_{min(st.session_state.user_id, res[0])}_{now()}"
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?,?)", (mid, st.session_state.user_id, res[0]))
                conn.commit()
                st.session_state.current_match_id = mid
                st.rerun()
            else:
                st.info("Waiting for a compatible peer to join...")
    
    else:
        # Session Header
        top_l, top_r = st.columns([4, 1])
        top_l.subheader("Live Study Room")
        if top_r.button("End Session"):
            reset_session()

        # Chat Window Fragment
        sync_live_chat(st.session_state.current_match_id)
        
        # Bottom Control Bar
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            col_msg, col_file, col_btn = st.columns([5, 1, 1])
            with col_msg:
                m_txt = st.text_input("Text Message", placeholder="Share your thoughts...", label_visibility="collapsed", key="main_input")
            with col_file:
                st.file_uploader("Upload", label_visibility="collapsed")
            with col_btn:
                if st.button("Send", use_container_width=True):
                    if m_txt:
                        conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)", 
                                     (st.session_state.current_match_id, st.session_state.user_name, m_txt, now()))
                        conn.commit()
                        st.rerun()

if __name__ == "__main__":
    matchmaking_page()
