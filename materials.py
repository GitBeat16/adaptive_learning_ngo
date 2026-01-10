import streamlit as st
from materials_data import MATERIALS

def materials_page():
    st.title("Learning Materials")

    standard = st.selectbox("Select Class", list(MATERIALS.keys()))
    subject = st.selectbox("Select Subject", list(MATERIALS[standard].keys()))

    materials = MATERIALS[standard][subject]

    st.subheader(f"Class {standard} – {subject}")

    for item in materials:
        st.markdown(f"### 🔹 {item['topic']}")

        st.markdown("**Quick Notes:**")
        for note in item["notes"]:
            st.markdown(f"- {note}")

        st.markdown(f"[Learn more]({item['link']})")
        st.divider()
