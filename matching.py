import streamlit as st
import time
from datetime import datetime, timedelta
from database import cursor, conn

# ---- SAFE SCHEMA MIGRATION ----
def migrate_profiles_table():
    try:
        cursor.execute("ALTER TABLE profiles ADD COLUMN status TEXT DEFAULT 'waiting'")
    except:
        pass  # column already exists

    try:
        cursor.execute("ALTER TABLE profiles ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except:
        pass  # column already exists

    conn.commit()

migrate_profiles_table()

# =========================================================
# CONSTANTS
# =========================================================
SUBJECTS = ["Mathematics", "English", "Science"]
MATCH_THRESHOLD = 50
SESSION_TIMEOUT_MIN = 60

# =========================================================
# DB SAFETY: CREATE REQUIRED TABLES IF NOT EXIST
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT,
    sender TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# =========================================================
# CLEANUP STALE USERS (ZOMBIE PREVENTION)
# =========================================================
def cleanup_stale_profiles():
    expiry = datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MIN)
    cursor.execute("""
        DELETE FROM profiles
        WHERE status='waiting' AND created_at < ?
    """, (expiry,))
    conn.commit()

# =========================================================
# DELETE USER + CHAT (EXPLICIT CLEANUP)
# =========================================================
def delete_user_session(user_id, match_id=None):
    cursor.execute("DELETE FROM profiles WHERE user_id=?", (user_id,))
    if match_id:
        cursor.execute("DELETE FROM messages WHERE match_id=?", (match_id,))
    conn.commit()

# =========================================================
# LOAD ALL ACTIVE PROFILES
# =========================================================
def load_profiles():
    cursor.execute("""
        SELECT 
            a.id,
            a.name,
            p.role,
            p.grade,
            p.time,
            p.strong_subjects,
            p.weak_subjects,
            p.teaches,
            p.status
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
        WHERE p.status='waiting'
    """)
    rows = cursor.fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "role": r[2],
            "grade": r[3],
            "time": r[4],
            "strong": r[7].split(",") if r[7] else r[5].split(",") if r[5] else [],
            "weak": r[6].split(",") if r[6] else []
        })
    return users

# =========================================================
# MATCH SCORING (REAL LOGIC)
# =========================================================
def calculate_match_score(mentor, mentee):
    score = 0
    reasons = []

    # Weak ↔ Strong (CRITICAL)
    for s in mentee["weak"]:
        if s in mentor["strong"]:
            score += 50
            reasons.append(f"{mentor['name']} strong in {s}")

    if score == 0:
        return 0, []

    # Same grade
    if mentor["grade"] == mentee["grade"]:
        score += 20
        reasons.append("Same grade")

    # Same time
    if mentor["time"] == mentee["time"]:
        score += 20
        reasons.append("Same time slot")

    return score, reasons

# =========================================================
# FIND BEST MATCH (COMPETITIVE)
# =========================================================
def find_best_match(current_user, all_users):
    cleanup_stale_profiles()

    best = None
    best_score = 0
    best_reasons = []

    for other in all_users:
        if other["user_id"] == current_user["user_id"]:
            continue
        if other["role"] == current_user["role"]:
            continue

        mentor = other if other["role"] == "Teacher" else current_user
        mentee = current_user if current_user["role"] == "Student" else other

        score, reasons = calculate_match_score(mentor, mentee)

        if score > best_score:
            best = other
            best_score = score
            best_reasons = reasons

    if best_score >= MATCH_THRESHOLD:
        return best, best_score, best_reasons

    return None, 0, []

# =========================================================
# CHAT HELPERS
# =========================================================
def load_messages(match_id):
    cursor.execute("""
        SELECT sender, message, created_at
        FROM messages
        WHERE match_id=?
        ORDER BY created_at ASC
    """, (match_id,))
    return cursor.fetchall()

def send_message(match_id, sender, message):
    cursor.execute("""
        INSERT INTO messages (match_id, sender, message)
        VALUES (?, ?, ?)
    """, (match_id, sender, message))
    conn.commit()

# =========================================================
# MAIN MATCHMAKING PAGE
# =========================================================
def matchmaking_page():

    st.markdown("""
    <div class="card">
        <h2>Peer Learning Matchmaking</h2>
        <p>We intelligently match students and mentors in real time.</p>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # LOAD CURRENT USER PROFILE
    # -------------------------------------------------
    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches, status
        FROM profiles
        WHERE user_id=?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    if not profile:
        st.warning("Please complete your profile first.")
        return

    role, grade, time_slot, strong, weak, teaches, status = profile

    current_user = {
        "user_id": st.session_state.user_id,
        "name": st.session_state.user_name,
        "role": role,
        "grade": grade,
        "time": time_slot,
        "strong": teaches.split(",") if teaches else strong.split(",") if strong else [],
        "weak": weak.split(",") if weak else []
    }

    # -------------------------------------------------
    # IF ALREADY MATCHED → CHAT
    # -------------------------------------------------
    if "match_id" in st.session_state and st.session_state.match_id:

        st.subheader("Live Chat")

        msgs = load_messages(st.session_state.match_id)
        chat_box = st.container(height=420)

        with chat_box:
            for m in msgs:
                sender, msg, _ = m
                if sender == current_user["name"]:
                    st.markdown(f"<div class='chat-bubble-me'>{msg}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-bubble-partner'><b>{sender}:</b> {msg}</div>", unsafe_allow_html=True)

        with st.form("chat_form", clear_on_submit=True):
            txt = st.text_input("Message")
            if st.form_submit_button("Send") and txt:
                send_message(st.session_state.match_id, current_user["name"], txt)
                st.rerun()

        if st.button("🛑 End Session", type="secondary"):
            delete_user_session(current_user["user_id"], st.session_state.match_id)
            st.session_state.match_id = None
            st.rerun()

        return

    # -------------------------------------------------
    # FIND MATCH BUTTON
    # -------------------------------------------------
    if st.button("🔍 Find Best Match", use_container_width=True):

        all_users = load_profiles()
        match, score, reasons = find_best_match(current_user, all_users)

        if match:
            match_id = f"{current_user['user_id']}-{match['user_id']}"

            cursor.execute("""
                UPDATE profiles SET status='matched'
                WHERE user_id IN (?, ?)
            """, (current_user["user_id"], match["user_id"]))
            conn.commit()

            st.session_state.match_id = match_id

            st.success("🎉 Match Found!")

            st.markdown(f"""
            <div class="card">
                <h4>Compatibility Score: {score}%</h4>
                <strong>Matched With:</strong> {match['name']}
                <ul>
                    {''.join(f"<li>{r}</li>" for r in reasons)}
                </ul>
            </div>
            """, unsafe_allow_html=True)

            time.sleep(1)
            st.rerun()

        else:
            st.warning("No suitable match found right now. Try again later.")

