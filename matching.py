import streamlit as st
import time
import os
import requests
from database import conn

# =========================================================
# REAL-TIME MATCHMAKING LOGIC
# =========================================================
def find_compatible_peer(user_id, user_grade, user_strong, user_weak):
    """
    Finds a peer who:
    1. Is in the same grade.
    2. Has a status of 'waiting'.
    3. Peer's Strong Subject matches User's Weak Subject (and vice versa).
    """
    # Splitting strings into lists for comparison
    strong_list = [s.strip() for s in user_strong.split(',')]
    weak_list = [w.strip() for w in user_weak.split(',')]
    
    # SQL Query for multi-point compatibility
    query = """
        SELECT p.user_id, a.name, p.strong_subjects, p.weak_subjects 
        FROM profiles p 
        JOIN auth_users a ON a.id = p.user_id 
        WHERE p.status = 'waiting' 
        AND p.user_id != ? 
        AND p.grade = ?
    """
    potential_peers = conn.execute(query, (user_id, user_grade)).fetchall()
    
    for peer in potential_peers:
        p_id, p_name, p_strong, p_weak = peer
        p_strong_list = [s.strip() for s in p_strong.split(',')]
        p_weak_list = [w.strip() for w in p_weak.split(',')]
        
        # Check if Peer is strong in User's weakness AND User is strong in Peer's weakness
        match_found = any(s in weak_list for s in p_strong_list) and \
                      any(s in strong_list for s in p_weak_list)
        
        if match_found:
            return {"id": p_id, "name": p_name, "strong": p_strong, "weak": p_weak}
            
    return None

# =========================================================
# LIVE SESSION INTERFACE
# =========================================================

def show_live_session():
    st.markdown(f"### 💠 Live Session: {st.session_state.peer_info['name']}")
    
    # Real-time message fragment
    render_chat_messages() 
    
    # File & Message Input
    with st.form("session_input", clear_on_submit=True):
        col_msg, col_file = st.columns([3, 1])
        msg = col_msg.text_input("Message", label_visibility="collapsed", placeholder="Discuss your topics...")
        up_file = col_file.file_uploader("Upload", label_visibility="collapsed")
        
        if st.form_submit_button("Send 💠"):
            f_path = None
            if up_file:
                f_path = f"uploads/{up_file.name}"
                with open(f_path, "wb") as f: f.write(up_file.getbuffer())
            
            if msg or up_file:
                conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                            (st.session_state.current_match_id, st.session_state.user_name, msg, f_path, int(time.time())))
                conn.commit()
                st.rerun()

    st.divider()
    if st.button("End Session 💠", use_container_width=True):
        st.session_state.session_step = "summary"
        st.rerun()

# =========================================================
# DISCOVERY WITH CELEBRATION
# =========================================================

def show_discovery():
    st.markdown("### 💠 Find Your Match")
    st.write("Our algorithm is ready to find a peer based on your learning profile.")
    
    if st.button("Start Real-Time Matchmaking"):
        # Fetch current user's profile for matching
        u = conn.execute("SELECT grade, strong_subjects, weak_subjects FROM profiles WHERE user_id=?", (st.session_state.user_id,)).fetchone()
        
        with st.spinner("Searching for compatible peers..."):
            match = find_compatible_peer(st.session_state.user_id, u[0], u[1], u[2])
            
            if match:
                st.session_state.found_peer = match
            else:
                st.warning("No compatible peers online right now. Try adjusting your preferences.")

    if "found_peer" in st.session_state:
        p = st.session_state.found_peer
        st.markdown(f"""
            <div class='sahay-card' style='border: 2px solid #10b981; padding: 20px; border-radius: 20px;'>
                <h4>💠 Match Found: {p['name']}</h4>
                <p>They can help you with: <b>{p['strong']}</b></p>
                <p>You can help them with: <b>{p['weak']}</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Accept & Connect 💠"):
            st.session_state.session_step = "celebration"
            st.rerun()
