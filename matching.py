import streamlit as st
import os
import time
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"

# =========================================================
# DB SAFETY
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    rater_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    created_at INTEGER NOT NULL
)
""")
conn.commit()

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def update_last_seen():
    cursor.execute(
        "UPDATE profiles SET last_seen=? WHERE user_id=?",
        (now(), st.session_state.user_id)
    )
    conn.commit()

# =========================================================
# MATCHING
# =========================================================
def load_waiting_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects, p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id=p.user_id
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

def score(u1, u2):
    s = 0
    s += len(set(u1["weak"]) & set(u2["strong"])) * 25
    s += len(set(u2["weak"]) & set(u1["strong"])) * 25
    if u1["grade"] == u2["grade"]:
        s += 10
    if u1["time"] == u2["time"]:
        s += 10
    return s

def find_best_match(current):
    best, best_score = None, -1
    for u in load_waiting_profiles():
        if u["user_id"] == current["user_id"]:
            continue
        sc = score(current, u)
        if sc > best_score:
            best, best_score = u, sc
    return best, best_score

# =========================================================
# CHAT
# =========================================================
def load_msgs(mid):
    cursor.execute(
        "SELECT sender, message FROM messages WHERE match_id=? ORDER BY id",
        (mid,))
    return cursor.fetchall()

def send_msg(mid, sender, message):
    cursor.execute(
        "INSERT INTO messages (match_id, sender, message) VALUES (?,?,?)",
        (mid, sender, message))
    conn.commit()
    update_last_seen()

# =========================================================
# FILES
# =========================================================
def save_file(mid, uploader, file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = f"{UPLOAD_DIR}/{mid}_{file.name}"
    with open(path, "wb") as f:
        f.write(file.getbuffer())

    cursor.execute("""
        INSERT INTO session_files (match_id, uploader, filename, filepath)
        VALUES (?,?,?,?)
    """, (mid, uploader, file.name, path))
    conn.commit()

def load_files(mid):
    cursor.execute("""
        SELECT uploader, filename, filepath
        FROM session_files WHERE match_id=?
    """, (mid,))
    return cursor.fetchall()

# =========================================================
# END SESSION
# =========================================================
def end_session(match_id):
    st.session_state.last_session_id = match_id

    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE match_id=?
    """, (match_id,))
    conn.commit()

    st.session_state.current_match_id = None
    st.session_state.session_ended = True

# =========================================================
# AI QUIZ + SUMMARY
# =========================================================
def generate_quiz_from_chat(match_id):
    msgs = load_msgs(match_id)
    discussion = "\n".join([f"{s}: {m}" for s, m in msgs])

    raw = ask_ai(f"""
Create EXACTLY 3 MCQs from this discussion.
If discussion is short, create simple questions.

Discussion:
{discussion}
""")

    qs = []
    for b in raw.split("Q")[1:]:
        lines = b.splitlines()
        q = lines[0].split(".", 1)[-1]
        opts, ans = {}, None
        for l in lines:
            if l[:2] in ["A)", "B)", "C)", "D)"]:
                opts[l[0]] = l[2:].strip()
            if "Answer:" in l:
                ans = l.split(":")[-1].strip()
        if len(opts) == 4 and ans:
            qs.append({"question": q, "options": opts, "answer": ans})
    return qs[:3]

def render_practice_quiz(match_id):
    st.subheader("🧠 Practice Quiz")
    quiz = generate_quiz_from_chat(match_id)
    answers = {}

    for i, q in enumerate(quiz):
        st.markdown(f"**Q{i+1}. {q['question']}**")
        answers[i] = st.radio(
            "Choose",
            list(q["options"].keys()),
            format_func=lambda x: f"{x}) {q['options'][x]}",
            key=f"quiz_{i}"
        )

    if st.button("Submit Quiz"):
        score = sum(1 for i, q in enumerate(quiz) if answers.get(i) == q["answer"])
        st.metric("Score", f"{score}/3")
        if score == 3:
            st.balloons()

def render_summary(match_id):
    msgs = load_msgs(match_id)
    discussion = "\n".join([f"{s}: {m}" for s, m in msgs])
    summary = ask_ai(f"Summarize this study session:\n{discussion}")
    st.subheader("📝 Session Summary")
    st.write(summary)

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    update_last_seen()

    st.session_state.setdefault("current_match_id", None)
    st.session_state.setdefault("session_ended", False)
    st.session_state.setdefault("last_session_id", None)
    st.session_state.setdefault("selected_rating", 0)
    st.session_state.setdefault("just_matched", False)

    # 🎉 Balloons after match
    if st.session_state.just_matched:
        st.balloons()
        st.session_state.just_matched = False

    # ================= AI CHATBOT =================
    st.markdown("### 🤖 AI Study Assistant")
    with st.form("ai"):
        q = st.text_input("Ask AI")
        if st.form_submit_button("Ask") and q:
            st.success(ask_ai(q))

    st.divider()

    # ================= MATCHMAKING =================
    if not st.session_state.current_match_id and not st.session_state.session_ended:
        cursor.execute("""
            SELECT role, grade, time, strong_subjects, weak_subjects, teaches
            FROM profiles WHERE user_id=?
        """, (st.session_state.user_id,))
        row = cursor.fetchone()

        if not row:
            st.warning("Complete your profile first.")
            return

        role, grade, time_slot, strong, weak, teaches = row
        user = {
            "user_id": st.session_state.user_id,
            "name": st.session_state.user_name,
            "role": role,
            "grade": grade,
            "time": time_slot,
            "strong": (teaches or strong or "").split(","),
            "weak": (weak or "").split(",")
        }

        if st.button("🔍 Find Best Match", use_container_width=True):
            m, s = find_best_match(user)
            if m:
                st.session_state.proposed_match = m
                st.session_state.proposed_score = s
            else:
                st.info("No suitable match right now.")

        if "proposed_match" in st.session_state:
            m = st.session_state.proposed_match
            st.subheader("👤 Suggested Partner")
            st.info(f"""
**Name:** {m['name']}  
**Role:** {m['role']}  
**Grade:** {m['grade']}  
**Strong:** {', '.join(m['strong'])}  
**Weak:** {', '.join(m['weak'])}  
**Compatibility:** {st.session_state.proposed_score}
""")

            if st.button("✅ Confirm Match", use_container_width=True):
                sid = f"{min(user['user_id'], m['user_id'])}-{max(user['user_id'], m['user_id'])}-{now()}"
                cursor.execute("""
                    UPDATE profiles SET status='matched', match_id=?
                    WHERE user_id IN (?,?)
                """, (sid, user["user_id"], m["user_id"]))
                conn.commit()

                st.session_state.current_match_id = sid
                st.session_state.just_matched = True
                st.rerun()
        return

    # ================= LIVE SESSION =================
    if st.session_state.current_match_id and not st.session_state.session_ended:
        mid = st.session_state.current_match_id

        st.subheader("💬 Live Chat")
        for s, m in load_msgs(mid):
            st.markdown(f"**{s}:** {m}")

        with st.form("chat"):
            msg = st.text_input("Message")
            if st.form_submit_button("Send") and msg:
                send_msg(mid, st.session_state.user_name, msg)
                st.rerun()

        st.subheader("📁 Files")
        f = st.file_uploader("Upload")
        if f and st.button("Upload file"):
            save_file(mid, st.session_state.user_name, f)
            st.rerun()

        for u, n, p in load_files(mid):
            with open(p, "rb") as file:
                st.download_button(f"{n} ({u})", file)

        if st.button("End Session", use_container_width=True):
            end_session(mid)
        return

    # ================= POST SESSION =================
    if st.session_state.session_ended:
        sid = st.session_state.last_session_id

        st.subheader("⭐ Rate your partner")
        cols = st.columns(5)
        for i in range(5):
            if cols[i].button("⭐" if i < st.session_state.selected_rating else "☆", key=f"star_{i}"):
                st.session_state.selected_rating = i + 1

        if st.session_state.selected_rating > 0:
            if st.button("Submit Rating"):
                cursor.execute("""
                    INSERT INTO ratings (match_id, rater_id, rating, created_at)
                    VALUES (?,?,?,?)
                """, (sid, st.session_state.user_id, st.session_state.selected_rating, now()))
                conn.commit()
                st.success("Rating submitted")

                render_summary(sid)
                render_practice_quiz(sid)
