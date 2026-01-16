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
# SYSTEM & SESSION DEFENSE
# =========================================================
def ensure_session_state():
    """Prevents KeyErrors by initializing required keys if missing"""
    defaults = {
        "session_step": "discovery",
        "user_id": 0,
        "user_name": "Guest",
        "current_match_id": None,
        "peer_info": None,
        "final_summary": None,
        "quiz_data": None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# =========================================================
# FORCED EMERALD UI
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        .stApp { background-color: #f8fafc !important; }
        
        /* Emerald Card - Everything must stay inside here */
        .emerald-card {
            background: white !important;
            padding: 35px !important;
            border-radius: 20px !important;
            border-top: 12px solid #10b981 !important;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1) !important;
            margin-bottom: 30px;
        }

        .emerald-card h1, .emerald-card h2, .emerald-card h3 {
            color: #064e3b !important;
            margin-top: 0px !important;
            font-weight: 800 !important;
        }

        /* Buttons with Ripple Simulation */
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 16px !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        div.stButton > button:hover {
            background-color: #059669 !important;
            box-shadow: 0 10px 20px rgba(16, 185, 129, 0.3) !important;
            transform: translateY(-2px);
        }
        
        /* Chat Area Styling */
        .chat-container {
            background: #f1f5f9 !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px;
            padding: 15px;
            height: 450px;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# MATCHMAKING LOGIC
# =========================================================
def perform_match():
    # Defensive check: ensure user_id exists
    uid = st.session_state.get('user_id', 0)
    
    # Check for waiting peers
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
# ROUTING PAGES
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Scan for compatible collaborators to start your session.")
    
    if st.button("Search Compatible Partner"):
        if perform_match():
            st.session_state.session_step = "live"
            st.rerun()
        else:
            st.info("Status: Added to queue. Waiting for a partner...")
    st.markdown("</div>", unsafe_allow_html=True)

def show_live():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Collaborating: {st.session_state.peer_info['name']}")
    
    # Chat placeholder
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.write("System: Connection established. Start typing below.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    msg = st.text_input("Message", label_visibility="collapsed", placeholder="Enter notes...")
    if st.button("Send"):
        st.toast("Message logic executing...")

    if st.button("End Session"):
        st.session_state.session_step = "summary"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_summary_and_quiz():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Analysis")
    st.write("Reviewing your performance and key takeaways.")
    
    st.divider()
    st.subheader("Partner Rating")
    st.feedback("stars")
    
    if st.button("Take Knowledge Quiz"):
        st.balloons()
    
    if st.button("Return Home"):
        st.session_state.session_step = "discovery"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN APP ENTRY
# =========================================================
def matchmaking_page():
    inject_ui()
    ensure_session_state()

    step = st.session_state.session_step
    
    if step == "discovery":
        show_discovery()
    elif step == "live":
        show_live()
    elif step == "summary":
        show_summary_and_quiz()

if __name__ == "__main__":
    matchmaking_page()
