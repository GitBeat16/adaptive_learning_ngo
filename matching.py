import streamlit as st
import time
import os
import json
from database import conn
from ai_helper import ask_ai
from streamlit_lottie import st_lottie

# Ensure upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# ASSETS & UI
# =========================================================
def load_lottie(url_or_file):
    # This is a placeholder for your lottie loading logic
    # In a real app, you'd use a JSON file or URL
    return None 

def inject_emerald_theme():
    st.markdown("""
        <style>
        /* Main Container Emerald Theme */
        .stApp { background-color: #f0fdf4; }
        
        .emerald-card {
            background: white !important;
            padding: 30px !important;
            border-radius: 20px !important;
            border-top: 10px solid #059669 !important;
            box-shadow: 0 10px 25px rgba(5, 150, 105, 0.1) !important;
            margin-bottom: 25px;
            color: #064e3b;
        }
        
        .emerald-card h1, .emerald-card h2, .emerald-card h3 { 
            color: #064e3b !important; 
            font-weight: 800 !important; 
        }

        /* Buttons Styling */
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: 2px solid #059669 !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            transition: all 0.3s ease;
        }
        
        div.stButton > button:hover {
            background-color: #059669 !important;
            transform: translateY(-2px);
        }

        /* Chat Bubbles */
        .chat-scroll { background: #ecfdf5 !important; border: 1px solid #d1fae5 !important; border-radius: 12px; padding: 15px; height: 350px; overflow-y: auto; margin-bottom: 20px; }
        .bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; font-family: sans-serif; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #064e3b; border: 1px solid #d1fae5; border-bottom-left-radius: 2px; }
        
        /* Quiz Styling */
        .quiz-container { background: #ffffff; border: 2px solid #10b981; padding: 20px; border-radius: 15px; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# DATA & AI
# =========================================================
def get_user_status(uid):
    res = conn.execute("SELECT status, accepted, match_id FROM profiles WHERE user_id=?", (uid,)).fetchone()
    if res: return res
    conn.execute("INSERT INTO profiles (user_id, status, accepted) VALUES (?, 'active', 0)", (uid,))
    conn.commit()
    return ('active', 0, None)

def generate_session_quiz():
    msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                       (st.session_state.current_match_id,)).fetchall()
    chat_transcript = "\n".join([f"{m[0]}: {m[1]}" for m in msgs])
    
    prompt = f"""
    Create a 3-question MCQ quiz based on this study session:
    {chat_transcript}
    Return ONLY a JSON array of objects:
    [{"question": "...", "options": ["A", "B", "C"], "answer": "A"}]
    """
    try:
        response = ask_ai(prompt)
        # Clean the response to ensure it's valid JSON
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        return json.loads(response[json_start:json_end])
    except:
        return [{"question": "What was the main topic?", "options": ["Topic A", "Topic B"], "answer": "Topic A"}]

# =========================================================
# PAGE MODULES
# =========================================================

def show_discovery():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Network Scanning")
    st.write("Searching for compatible nodes in the emerald network.")
    
    if st.button("Initialize Search"):
        peer = conn.execute("""
            SELECT p.user_id, a.name FROM profiles p 
            JOIN auth_users a ON a.id = p.user_id 
            WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()
        
        if peer:
            m_id = f"sess_{int(time.time())}"
            st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
            st.session_state.current_match_id = m_id
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, st.session_state.user_id))
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, peer[0]))
            conn.commit()
            st.session_state.session_step = "confirmation"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_live_session():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Active Link: {st.session_state.peer_info['name']}")
    
    # Simple message display (logic kept from your version)
    msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                       (st.session_state.current_match_id,)).fetchall()
    
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg in msgs:
        cls = "bubble-me" if sender == st.session_state.user_name else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    msg = st.text_input("Secure Message", placeholder="Type content...", key="chat_input")
    if st.button("Transmit"):
        if msg:
            conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                        (st.session_state.current_match_id, st.session_state.user_name, msg, int(time.time())))
            conn.commit()
            st.rerun()

    st.divider()
    if st.button("Finalize Session"):
        st.session_state.session_step = "rating"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_rating():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Evaluation")
    st.write(f"Please rate your collaboration with {st.session_state.peer_info['name']}")
    
    rating = st.slider("Select Rating", 1, 5, 5)
    feedback = st.text_area("Observations (Optional)")
    
    if st.button("Submit Evaluation"):
        # Save rating to session_ratings table
        conn.execute("""
            INSERT INTO session_ratings (match_id, rater_id, rating, feedback) 
            VALUES (?, ?, ?, ?)
        """, (st.session_state.current_match_id, st.session_state.user_id, rating, feedback))
        conn.commit()
        
        with st.spinner("Generating AI Knowledge Check..."):
            st.session_state.quiz_data = generate_session_quiz()
        
        st.session_state.session_step = "quiz"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Verification")
    
    quiz = st.session_state.get('quiz_data', [])
    score = 0
    
    with st.form("quiz_form"):
        user_answers = []
        for i, q in enumerate(quiz):
            st.write(f"**Q{i+1}: {q['question']}**")
            ans = st.radio("Select Answer", q['options'], key=f"q_{i}")
            user_answers.append(ans)
        
        if st.form_submit_button("Verify Answers"):
            for i, q in enumerate(quiz):
                if user_answers[i] == q['answer']:
                    score += 1
            st.success(f"Verification Complete. Score: {score}/{len(quiz)}")
            st.session_state.quiz_done = True

    if st.session_state.get('quiz_done'):
        if st.button("Return to Matchmaking"):
            # Reset user for next match
            conn.execute("UPDATE profiles SET status='active', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.session_state.session_step = "discovery"
            del st.session_state.quiz_done
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN ROUTER
# =========================================================
def matchmaking_page():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "rating": show_rating()
    elif step == "quiz": show_quiz()
