import streamlit as st
import time
from datetime import datetime, timedelta
from database import cursor, conn

MATCH_THRESHOLD = 30
SESSION_TIMEOUT_MIN = 60

# =========================================================
# CLEANUP STALE USERS
# =========================================================
def cleanup_stale_profiles():
    expiry = (datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MIN)) \
        .strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        DELETE FROM profiles
        WHERE status='waiting'
        AND datetime(created_at) < datetime(?)
    """, (expiry,))
    conn.commit()

# =========================================================
# LOAD WAITING USERS
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
            p.teaches
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
            "strong": (r[7] or r[5] or "").split(","),
            "weak": (r[6] or "").split(",")
        })
    return users

# =========================================================
# MATCH SCORING
# =========================================================
def calculate_match_score(user1, user2):
    score = 0
    reasons = []

    if user1["role"] == "Student" and user2["role"] == "Student":
        for s in user1["weak"]:
            if s and s in user2["strong"]:
                score += 25
                reasons.append(f"{user2['name']} strong in {s}")
        for s in user2["weak"]:
            if s and s in user1["strong"]:
                score += 25
                reasons.append(f"{user1['name']} strong in {s}")
    else:
        mentor = user1 if user1["role"] == "Teacher" else user2
        mentee = user2 if mentor == user1 else user1
        for s in mentee["weak"]:
            if s and s in mentor["strong"]:
                score += 30
                reasons.append(f"Strong in {s}")

    if user1["grade"] == user2["grade"]:
        score += 10
        reasons.append("Same grade")
    if user1["time"] == user2["time"]:
        score += 10
        reasons.append("Same time slot")

    return score, reasons

# =========================================================
# FIND MATCH
# =========================================================
def find_best_match(current_user, all_users):
    cleanup_stale_profiles()
    best, best_score, best_reasons = None, 0, []

    for other in all_users:
        if other["user_id"] == current_user["user_id"]:
            continue
        if current_user["role"] == "Teacher" and other["role"] == "Teacher":
            continue

        score, reasons = calculate_match_score(current_user, other)
        if score > best_score:
            best, best_score, best_reasons = other, score, reasons

    if best_score >= MATCH_THRESHOLD:
        return best, best_score, best_reasons
    return None, 0, []

# =========================================================
# CHAT HELPERS
# =========================================================
def load_messages(match_id):
    cursor.execute("""
        SELECT sender, message
        FROM messages
        WHERE match_id=?
        ORDER BY created_at
    """, (match_id,))
    return cursor.fetchall()

def send_message(match_id, sender, message):
    cursor.execute("""
        INSERT INTO messages (match_id, sender, message)
        VALUES (?, ?, ?)
    """, (match_id, sender, message))
    conn.commit()

# =========================================================
# MATCHMAKING PAGE
# =========================================================
def matchmaking_page():

    cursor.execute("""
        SELECT role, grade, time, strong_subjects, weak_subjects, teaches, match_id
        FROM profiles
        WHERE user_id=?
    """, (st.session_state.user_id,))
    profile = cursor.fetchone()

    if not profile:
        st.warning("Please complete your profile first.")
        return

    role, grade, time_val, strong, weak, teaches, match_id = profile

    current_user = {
        "user_id": st.session_state.user_id,
        "name": st.session_state.user_name,
        "role": role,
        "grade": grade,
        "time": time_val,
        "strong": (teaches or strong or "").split(","),
        "weak": (weak or "").split(",")
    }

    # ================= LIVE CHAT (MOBILE + LAPTOP SAFE) =================
    if match_id:
        st.subheader("Live Learning Room")

        cursor.execute("""
            SELECT a.name
            FROM profiles p
            JOIN auth_users a ON a.id = p.user_id
            WHERE p.match_id=? AND p.user_id!=?
        """, (match_id, current_user["user_id"]))
        partner = cursor.fetchone()

        if partner:
            st.info(f"Paired with **{partner[0]}**")

        if "is_typing" not in st.session_state:
            st.session_state.is_typing = False
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = time.time()

        if not st.session_state.is_typing:
            if time.time() - st.session_state.last_refresh > 3:
                st.session_state.last_refresh = time.time()
                st.rerun()

        chat_box = st.container(height=400)
        with chat_box:
            for sender, msg in load_messages(match_id):
                if sender == current_user["name"]:
                    st.markdown(f"**You:** {msg}")
                else:
                    st.markdown(f"**{sender}:** {msg}")

        with st.form("chat_form", clear_on_submit=True):
            message = st.text_input(
                "Type your message",
                on_change=lambda: st.session_state.update({"is_typing": True})
            )
            send = st.form_submit_button("Send")

            if send and message.strip():
                send_message(match_id, current_user["name"], message)
                st.session_state.is_typing = False
                st.rerun()

        if st.button("End Session"):
            cursor.execute("""
                UPDATE profiles
                SET status='waiting', match_id=NULL
                WHERE match_id=?
            """, (match_id,))
            conn.commit()
            st.rerun()

        return

    # ================= FIND MATCH =================
    if st.button("Find Best Match", use_container_width=True):
        all_users = load_profiles()
        match, score, reasons = find_best_match(current_user, all_users)

        if match:
            match_id = f"{current_user['user_id']}-{match['user_id']}"
            cursor.execute("""
                UPDATE profiles
                SET status='matched', match_id=?
                WHERE user_id IN (?, ?)
            """, (match_id, current_user["user_id"], match["user_id"]))
            conn.commit()
            st.success(f"Matched with {match['name']} (Score: {score})")
            st.rerun()
        else:
            st.warning("No suitable match right now.")
