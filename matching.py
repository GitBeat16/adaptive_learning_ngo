import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# PROFESSIONAL EMERALD UI (CSS)
# =========================================================
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #fcfdfd; }
    
    /* Navigation Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    /* Professional Chat Box */
    .chat-wrapper {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 20px;
        height: 500px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    /* Message Bubbles */
    .message-row { display: flex; flex-direction: column; width: 100%; margin-bottom: 5px; }
    
    .bubble {
        padding: 12px 16px;
        border-radius: 12px;
        font-size: 0.95rem;
        max-width: 75%;
        line-height: 1.5;
    }
    
    .user-style {
        background-color: #059669; /* Emerald 600 */
        color: #ffffff;
        align-self: flex-end;
        border-bottom-right-radius: 2px;
    }
    
    .partner-style {
        background-color: #f1f5f9;
        color: #1e293b;
        align-self: flex-start;
        border-bottom-left-radius: 2px;
        border: 1px solid #e2e8f0;
    }

    .label-text {
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 3px;
        color: #64748b;
    }
    .user-label { align-self: flex-end; color: #059669; }

    /* Emerald Button Customization */
    div.stButton > button {
        background-color: #059669;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 500;
        transition: background 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #047857;
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# STATE INITIALIZATION (Critical Fix)
# =========================================================
def ensure_state():
    """Ensures all keys exist to prevent AttributeError."""
    keys = {
        "chat_log": [],
        "last_ts": 0,
        "ai_history": [],
        "current_match_id": None,
        "user_id": st.session_state.get("user_id", None),
        "user_name": st.session_state.get("user_name", "User")
    }
    for key, default in keys.items():
        if key not in st.session_state:
            st.session_state[key] = default

# Call this at the top level
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
# SIDEBAR - AI ASSISTANT
# =========================================================
with st.sidebar:
    st.markdown("### Study Assistant")
    with st.container():
        ai_in = st.text_input("Ask AI", placeholder="Concept explanation...", key="side_ai_input", label_visibility="collapsed")
        if st.button("Query Assistant", use_container_width=True) and ai_in:
            with st.spinner("Processing..."):
                response = ask_ai(ai_in)
                st.session_state.ai_history.append((ai_in, response))
    
    st.divider()
    for q, a in reversed(st.session_state.ai_history[-3:]):
        with st.expander(f"Q: {q[:20]}...", expanded=False):
            st.write(a)

# =========================================================
# LIVE CHAT ENGINE
# =========================================================
@st.fragment(run_every=3)
def render_live_chat(match_id):
    # Fetching new messages only
    new_messages = conn.execute("""
        SELECT sender, message, created_ts FROM messages 
        WHERE match_id=? AND created_ts > ? ORDER BY created_ts ASC
    """, (match_id, st.session_state.last_ts)).fetchall()

    if new_messages:
        for s, m, ts in new_messages:
            st.session_state.chat_log.append((s, m))
            st.session_state.last_ts = max(st.session_state.last_ts, ts)

    # UI Rendering
    st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)
    for sender, msg in st.session_state.chat_log:
        is_me = (sender == st.session_state.user_name)
        b_class = "user-style" if is_me else "partner-style"
        l_class = "user-label" if is_me else ""
        label = "You" if is_me else sender
        
        st.markdown(f"""
            <div class="message-row">
                <div class="label-text {l_class}">{label}</div>
                <div class="bubble {b_class}">{msg}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# MAIN APP VIEW
# =========================================================
def matchmaking_page():
    # Final safety check
    ensure_state()
    
    if not st.session_state.current_match_id:
        # Check if match was assigned while waiting
        sync_check = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", 
                                  (st.session_state.user_id,)).fetchone()
        if sync_check and sync_check[0]:
            st.session_state.current_match_id = sync_check[0]
            st.rerun()

        st.title("Collaborative Learning")
        st.markdown("Connect with available peers for synchronized study sessions.")
        
        if st.button("Initialize Matchmaking", use_container_width=True):
            peer = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.status='waiting' AND p.user_id!=?", (st.session_state.user_id,)).fetchone()
            if peer:
                m_id = f"session_{min(st.session_state.user_id, peer[0])}_{int(time.time())}"
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?,?)", (m_id, st.session_state.user_id, peer[0]))
                conn.commit()
                st.session_state.current_match_id = m_id
                st.rerun()
            else:
                st.info("System is searching for active peers. Please maintain this connection.")
    
    else:
        # Active Session UI
        header_l, header_r = st.columns([5, 1])
        header_l.subheader("Synchronized Session")
        if header_r.button("Terminate"):
            reset_session()

        # Chat Window
        render_live_chat(st.session_state.current_match_id)
        
        # Unified Input Footer
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            input_col, file_col, send_col = st.columns([4, 1, 1])
            with input_col:
                message_text = st.text_input("Message", placeholder="Discuss your topic...", label_visibility="collapsed", key="chat_input_field")
            with file_col:
                st.file_uploader("Upload", label_visibility="collapsed")
            with send_col:
                if st.button("Send", use_container_width=True):
                    if message_text:
                        conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)", 
                                     (st.session_state.current_match_id, st.session_state.user_name, message_text, int(time.time())))
                        conn.commit()
                        st.rerun()

if __name__ == "__main__":
    matchmaking_page()
