import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# STYLING & THEME
# =========================================================
st.markdown("""
    <style>
    /* Main Layout Refinement */
    .stApp { background-color: #fcfdfd; }
    
    /* Emerald Minimalist Buttons */
    div.stButton > button {
        background-color: #059669;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.6rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background-color: #047857;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.2);
        transform: translateY(-1px);
    }
    
    /* Chat UI - Modern Bubbles */
    .chat-container {
        padding: 1.5rem;
        background: white;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .bubble {
        margin-bottom: 1rem;
        padding: 0.8rem 1rem;
        border-radius: 12px;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .user-bubble {
        background-color: #f1f5f9;
        color: #334155;
        margin-left: auto;
        border-bottom-right-radius: 2px;
    }
    .partner-bubble {
        background-color: #ecfdf5;
        color: #065f46;
        margin-right: auto;
        border-bottom-left-radius: 2px;
        border-left: 4px solid #10b981;
    }
    .meta-text {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 4px;
        letter-spacing: 0.05em;
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# STATE MANAGEMENT
# =========================================================
def init_state():
    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []
    if "last_msg_ts" not in st.session_state:
        st.session_state.last_msg_ts = 0
    if "current_match_id" not in st.session_state:
        st.session_state.current_match_id = None

def reset_matchmaking():
    conn.execute("UPDATE profiles SET status='waiting', match_id=None WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    st.session_state.current_match_id = None
    st.session_state.chat_log = []
    st.rerun()

# =========================================================
# LIVE CHAT FRAGMENT (Optimized Performance)
# =========================================================
@st.fragment(run_every=3)
def live_chat_fragment(match_id):
    """Refreshes only the chat window every 3s without reloading the whole page."""
    # Fetch new messages
    new_rows = conn.execute("""
        SELECT sender, message, created_ts FROM messages 
        WHERE match_id=? AND created_ts > ? ORDER BY created_ts ASC
    """, (match_id, st.session_state.last_msg_ts)).fetchall()

    if new_rows:
        for s, m, ts in new_rows:
            st.session_state.chat_log.append((s, m))
            st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)

    # Display Chat
    for sender, msg in st.session_state.chat_log:
        is_me = (sender == st.session_state.user_name)
        b_class = "user-bubble" if is_me else "partner-bubble"
        label = "You" if is_me else sender
        
        st.markdown(f"""
            <div class="bubble {b_class}">
                <div class="meta-text">{label}</div>
                {msg}
            </div>
        """, unsafe_allow_html=True)

# =========================================================
# MAIN LOGIC
# =========================================================
def matchmaking_page():
    init_state()
    
    # 1. SEARCHING PHASE
    if not st.session_state.current_match_id:
        st.subheader("Partner Matchmaking")
        
        # Check if someone matched us
        row = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", (st.session_state.user_id,)).fetchone()
        if row:
            st.session_state.current_match_id = row[0]
            st.rerun()

        st.info("Searching for an available study partner...")
        if st.button("Find Partner"):
            res = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.status='waiting' AND p.user_id!=?", (st.session_state.user_id,)).fetchone()
            if res:
                target_id, target_name = res
                mid = f"chat_{min(st.session_state.user_id, target_id)}_{int(time.time())}"
                
                # Double handshake update
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id=?", (mid, st.session_state.user_id))
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id=?", (mid, target_id))
                conn.commit()
                
                st.session_state.current_match_id = mid
                st.balloons()
                st.rerun()
            else:
                st.warning("No partners available. Please stay on this page to remain visible to others.")

    # 2. LIVE SESSION PHASE
    else:
        st.markdown(f"### Study Session: {st.session_state.user_name}")
        
        col_chat, col_tools = st.columns([2.5, 1], gap="large")
        
        with col_chat:
            with st.container(border=True):
                live_chat_fragment(st.session_state.current_match_id)
            
            with st.form("send_form", clear_on_submit=True):
                msg = st.text_input("Message", placeholder="Discuss your topic...", label_visibility="collapsed")
                if st.form_submit_button("Send Message"):
                    if msg:
                        conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                     (st.session_state.current_match_id, st.session_state.user_name, msg, int(time.time())))
                        conn.commit()
                        st.rerun()

        with col_tools:
            st.markdown("#### Resources")
            up = st.file_uploader("Upload File", label_visibility="collapsed")
            if up:
                st.success("File shared!")
            
            st.divider()
            
            # AI Assistant Quick-Access
            st.markdown("#### AI Help")
            ai_q = st.text_input("Ask AI", label_visibility="collapsed", placeholder="Explain...")
            if st.button("Get Answer"):
                st.info(ask_ai(ai_q))

            st.divider()
            if st.button("End & Quiz", use_container_width=True):
                # Generate Quiz Logic here
                st.session_state.finished = True
                st.rerun()

matchmaking_page()
