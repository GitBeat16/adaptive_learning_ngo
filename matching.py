import streamlit as st
import os
from database import cursor, conn
from ai_helper import ask_ai, generate_quiz_from_chat

UPLOAD_DIR = "uploads/sessions"
MATCH_THRESHOLD = 30

# =========================================================
# MATCHING LOGIC
# =========================================================
def load_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects, p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
        WHERE p.status = 'waiting'
    """)
    rows = cursor.fetchall()
    users = []
    for r in rows:
        users.append({
            "user_id": r[0], "name": r[1], "role": r[2], "grade": r[3],
            "time": r[4], "strong": (r[7] or r[5] or "").split(","),
            "weak": (r[6] or "").split(",")
        })
    return users

def score(u1, u2):
    s = 0
    s += len(set(u1["weak"]) & set(u2["strong"])) * 25
    s += len(set(u2["weak"]) & set(u1["strong"])) * 25
    if u1["grade"] == u2["grade"]: s += 10
    if u1["time"] == u2["time"]: s += 10
    return s

def find_best(current, users):
    best, best_s = None, 0
    for u in users:
        if u["user_id"] == current["user_id"]: continue
        sc = score(current, u)
        if sc > best_s: best, best_s = u, sc
    return (best, best_s) if best_s >= MATCH_THRESHOLD else (None, 0)

# =========================================================
# DATABASE HELPERS
# =========================================================
def load_msgs(mid):
    cursor.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY id", (mid,))
    return cursor.fetchall()

def send_msg(mid, sender, message):
    cursor.execute("INSERT INTO messages (match_id, sender, message) VALUES (?, ?, ?)", (mid, sender, message))
    conn.commit()

def end_session(match_id):
    cursor.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE match_id=?", (match_id,))
    conn.commit()

# =========================================================
# UI COMPONENTS
# =========================================================
def show_rating_ui(match_id):
    st.subheader("⭐ Rate Your Session")
    if "rating" not in st.session_state: st.session_state.rating = 0

    cols = st.columns(5)
    for i in range(5):
        star = "⭐" if i < st.session_state.rating else "☆"
        if cols[i].button(star, key=f"rate_{i}"):
            st.session_state.rating = i + 1

    if st.button("Submit Rating", use_container_width=True):
        if st.session_state.rating == 0:
            st.warning("Please select a rating.")
            return
        # Note: You need a session_ratings table in your DB for this to work
        try:
            cursor.execute("""
                INSERT INTO session_ratings (match_id, rater_id, rater_name, rating) 
                VALUES (?, ?, ?, ?)
            """, (match_id, st.session_state.user_id, st.session_state.user_name, st.session_state.rating))
            conn.commit()
            st.success("Thank you for your feedback!")
            st.session_state.rating_submitted = True
            st.rerun()
        except Exception as e:
            st.error(f"Error saving rating: {e}")

# =========================================================
# MATCHMAKING PAGE
# =========================================================
def matchmaking_page():
    # Initialize session states
    if "session_ended" not in st.session_state: st.session_state.session_ended = False
    if "quiz_completed" not in st.session_state: st.session_state.quiz_completed = False
    if "rating_submitted" not in st.session_state: st.session_state.rating_submitted = False

    st.title("🤝 Peer Learning Hub")

    cursor.execute("SELECT role, grade, time, strong_subjects, weak_subjects, teaches, match_id FROM profiles WHERE user_id = ?", (st.session_state.user_id,))
    row = cursor.fetchone()
    if not row: return st.warning("Please complete your profile first.")

    role, grade, time_slot, strong, weak, teaches, match_id = row
    user = {"user_id": st.session_state.user_id, "name": st.session_state.user_name, "role": role, "grade": grade, "time": time_slot, 
            "strong": (teaches or strong or "").split(","), "weak": (weak or "").split(",")}

    # PHASE 1: SEARCHING FOR MATCH
    if not match_id:
        if st.button("Find Best Match", use_container_width=True):
            m, s = find_best(user, load_profiles())
            if m:
                st.session_state.proposed_match, st.session_state.proposed_score = m, s
            else:
                st.info("No matches found at the moment. Try again later!")

        if st.session_state.get("proposed_match"):
            m = st.session_state.proposed_match
            st.info(f"Matched with **{m['name']}** (Score: {st.session_state.proposed_score})")
            if st.button("Confirm and Start Session"):
                mid = f"{user['user_id']}-{m['user_id']}"
                cursor.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?, ?)", (mid, user["user_id"], m["user_id"]))
                conn.commit()
                st.session_state.proposed_match = None
                st.rerun()
        return

    # PHASE 2: ACTIVE SESSION
    if not st.session_state.session_ended:
        st.subheader("💬 Live Chat")
        msgs = load_msgs(match_id)
        for s_name, m_text in msgs:
            st.write(f"**{s_name}:** {m_text}")

        with st.form("chat_input", clear_on_submit=True):
            user_msg = st.text_input("Message")
            if st.form_submit_button("Send") and user_msg:
                send_msg(match_id, user["name"], user_msg)
                st.rerun()

        st.divider()
        if st.button("🔴 End Session & Start Quiz", use_container_width=True):
            end_session(match_id)
            st.session_state.session_ended = True
            st.rerun()

    # PHASE 3: AI ASSESSMENT
    elif st.session_state.session_ended and not st.session_state.quiz_completed:
        st.subheader("📝 Post-Session Quiz")
        if "quiz_text" not in st.session_state:
            with st.spinner("AI is generating your custom quiz..."):
                session_msgs = load_msgs(match_id)
                st.session_state.quiz_text = generate_quiz_from_chat(session_msgs)
        
        st.markdown(st.session_state.quiz_text)
        
        with st.form("quiz_submission"):
            st.write("Reflect on the questions above.")
            if st.form_submit_button("I've finished the quiz"):
                st.session_state.quiz_completed = True
                st.rerun()

    # PHASE 4: RATING
    elif st.session_state.quiz_completed and not st.session_state.rating_submitted:
        show_rating_ui(match_id)
    
    # PHASE 5: ALL DONE
    else:
        st.success("Session complete! You are now back in the waiting pool.")
        if st.button("Find Another Match"):
            st.session_state.session_ended = False
            st.session_state.quiz_completed = False
            st.session_state.rating_submitted = False
            if "quiz_text" in st.session_state: del st.session_state.quiz_text
            st.rerun()
