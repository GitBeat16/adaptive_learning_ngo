import streamlit as st

def support_page():

    st.header("Support Education & Health Causes")
    st.write(
        "Your contribution can transform lives. Below are verified and trusted organisations "
        "working in education, child welfare, and medical support. "
        "You will be redirected to their **official websites** for donations."
    )

    st.divider()

    # ---------- EDUCATION & CHILD WELFARE ----------
    st.subheader("Education & Child Welfare (India)")

    education_ngos = [
        ("Akshaya Patra Foundation",
         "https://www.akshayapatra.org",
         "Provides mid-day meals to improve school attendance and nutrition."),

        ("Pratham",
         "https://www.pratham.org",
         "Improves foundational literacy and numeracy for children."),

        ("Nanhi Kali",
         "https://www.nanhikali.org",
         "Supports education for underprivileged girls."),

        ("Teach For India",
         "https://www.teachforindia.org",
         "Places fellows in low-income schools to address education inequity."),

        ("Smile Foundation",
         "https://www.smilefoundationindia.org",
         "Runs Mission Education for holistic child development."),

        ("CRY (Child Rights and You)",
         "https://www.cry.org",
         "Works to ensure children’s rights, including education."),

        ("Bal Raksha Bharat (Save the Children India)",
         "https://www.balrakshabharat.org",
         "Focuses on education, child protection, and early learning.")
    ]

    for name, link, desc in education_ngos:
        st.markdown(f"**{name}**  \n{desc}")
        st.markdown(f"[Visit Official Website]({link})")
        st.write("---")

    # ---------- HEALTH & MEDICAL SUPPORT ----------
    st.subheader("Health & Medical Support Foundations")

    health_foundations = [
        ("Tata Memorial Centre",
         "https://tmc.gov.in",
         "India’s leading cancer treatment and research institution."),

        ("Indian Cancer Society",
         "https://www.indiancancersociety.org",
         "Supports cancer awareness, detection, and patient care."),

        ("Make-A-Wish India",
         "https://www.makeawishindia.org",
         "Grants wishes to children with critical illnesses."),

        ("Doctors Without Borders (MSF India)",
         "https://www.msf.in",
         "Provides medical aid in crisis situations."),

        ("GiveIndia (Verified Platform)",
         "https://www.giveindia.org",
         "Donation platform vetting NGOs across education and health.")
    ]

    for name, link, desc in health_foundations:
        st.markdown(f"**{name}**  \n{desc}")
        st.markdown(f"[Visit Official Website]({link})")
        st.write("---")

    st.markdown("""
    - **Crowdfunding Platforms**
        - [Ketto](https://www.ketto.org)
        - [Impact Guru](https://www.impactguru.com)

    - **Direct Sponsorship**
        - Sponsor a child's education via Nanhi Kali

    - **Corporate & Philanthropy Grants**
        - Partner with NGOs for long-term impact
    """)

    st.success("Thank you for supporting education.")
