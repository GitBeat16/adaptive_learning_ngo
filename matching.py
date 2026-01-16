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
# THEME-ALIGNED UI STYLES
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        /* Main Emerald Header Card */
        .sahay-header {
            padding: 1.5rem;
            border-radius: 20px;
            background: linear-gradient(135deg, #0f766e, #14b8a6, #22c55e);
            color: white;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 10px 25px rgba(20,184,166,0.3);
        }
        
        /* Unified Card Style */
        .content-card {
            background: white;
            padding: 2rem;
            border-radius: 24px;
            border: 1px solid rgba(0,0,0,0.05);
            box-shadow: 0 12px 30px rgba(0,0,0,0.04);
            min-height: 500px;
        }

        /* AI Sidebar (Glassmorphism) */
        .ai-sidebar {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            padding: 1.5rem;
            border-radius: 24px;
            border: 1px solid #bbf7d0;
            height: 100%;
        }

        /* BUTTON THEME - Forcing Emerald */
        div.stButton > button {
            background: linear-gradient(135deg, #14b8a6, #0f766e) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 0.6rem 1.2rem !important;
            font-weight: 600 !important;
            transition: transform 0.2s ease !important;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(20,184,166,0.4) !important;
        }

        /* Chat Bubbles */
        .chat-container { height: 320px; overflow-y: auto; padding: 10px; margin-bottom: 15px; }
        .bubble { padding: 12px; border-radius: 18px; margin-bottom: 10px; max-width: 85%; line-height: 1.4; font-size: 0.95rem; }
        .bubble-me { background: #0f766e; color: white; margin-left: auto; border-bottom-right-radius: 4px; }
        .bubble-peer { background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px; }
        
        .ai-msg-box { background: white; border-radius: 12px; padding: 10px; margin-bottom: 8px; border-left: 4px solid #14b8a6; font-size: 0.85rem; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# AI COMPONENT (INTEGRATED UI)
# =========================================================
def render_persistent_ai():
    st.markdown("<div class='ai-sidebar'>", unsafe_allow_html=True)
    # Using your requested vector art logo style
    st.markdown("### 💠 Sahay AI Assistant")
    
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = [{"role": "bot", "content": "How can I help with your study session?"}]

    # Scrollable AI Chat
    ai_hist = st.container(height=380, border=False)
    for chat in st.session_state.ai_chat_history:
        role_icon = "🤖" if chat["role"] == "bot" else "👤"
        ai_hist.markdown(f"<div class='ai-msg-box'><b>{role_icon}</b><br>{chat['content']}</div>", unsafe_allow_html=True)

    with st.form("ai_side_input", clear_on_submit=True):
        q = st.text_input("Ask Sahay AI...", label_visibility="collapsed")
        if st.form_submit_button("Send"):
            if q:
                st.session_state.ai_chat_history.append({"role": "user", "content": q})
                st.session_state.ai_chat_history.append({"role": "bot", "content": ask_ai(q)})
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN PAGES
# =========================================================

def show_discovery():
    st.markdown("""<div class='sahay-header'><h2>Partner Discovery</h2><p>Find your study peer in real-time</p></div>""", unsafe_allow_html=True)
    st.write("Our AI matching system is scanning for active students in your grade.")
    
    if st.button("🔍 Search Compatible Partner", use_container_width=True):
        # ... logic ...
        pass

def show_live_session():
    st.markdown(f"""<div class='sahay-header'><h2>Session Active</h2><p>Learning with {st.session_state.peer_info['name']}</p></div>""", unsafe_allow_html=True)
    
    # Fragmented Chat Area
    render_chat_bubbles()

    with st.form("chat_input_form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        msg = c1.text_input("Type message...", label_visibility="collapsed")
        up = c2.file_uploader("Upload", label_visibility="collapsed")
        if st.form_submit_button("Send"):
            # ... send logic ...
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🏁 End Session", use_container_width=True):
        st.session_state.session_step = "summary"
        st.rerun()

@st.fragment(run_every=2)
def render_chat_bubbles():
    msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for sender, text in msgs:
        cls = "bubble-me" if sender == st.session_state.user_name else "bubble-peer"
        st.markdown(f"<div class='bubble {cls}'><b>{sender}</b><br>{text}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: 
        st.session_state.session_step = "discovery"

    # Create 2-Column Split
    main_col, side_col = st.columns([2.5, 1], gap="large")

    with main_col:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        step = st.session_state.session_step
        if step == "discovery": show_discovery()
        elif step == "live": show_live_session()
        # ... other steps ...
        st.markdown("</div>", unsafe_allow_html=True)

    with side_col:
        render_persistent_ai()
