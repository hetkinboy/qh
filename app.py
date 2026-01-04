import streamlit as st
import requests
import json

BASE_URL = "https://lansongxanh.1vote.vn"
CALLBACK_URL = "https://lansongxanh.1vote.vn/thi-sinh/yj3su/quang-hung-masterd-xC7N"

st.set_page_config(page_title="LangSongXanh Login Tool", layout="wide")

st.title("🔐 LangSongXanh – Login & Session Collector")

st.markdown("""
- Nhập **danh sách email (mỗi dòng 1 email)**
- Mật khẩu dùng chung
- Tool sẽ login và lấy **session cho từng email**
""")

# =========================
# INPUT
# =========================
emails_raw = st.text_area(
    "📧 Danh sách email (mỗi dòng 1 email)",
    height=200,
    placeholder="email1@gmail.com\nemail2@gmail.com"
)

password = st.text_input("🔑 Mật khẩu", type="password")

start_btn = st.button("🚀 Bắt đầu login & lấy session")

# =========================
# PROCESS
# =========================
if start_btn:
    if not emails_raw.strip() or not password:
        st.error("❌ Vui lòng nhập email và mật khẩu")
        st.stop()

    emails = [e.strip() for e in emails_raw.splitlines() if e.strip()]
    st.info(f"📌 Tổng email: {len(emails)}")

    results = []

    progress = st.progress(0)
    log_box = st.empty()

    for idx, email in enumerate(emails, start=1):
        log_box.info(f"🔄 Đang xử lý: {email}")

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        })

        try:
            # 1️⃣ Get CSRF
            csrf_res = session.get(f"{BASE_URL}/api/auth/csrf", timeout=10)
            csrf_token = csrf_res.json().get("csrfToken")

            if not csrf_token:
                raise Exception("Không lấy được csrfToken")

            # 2️⃣ Login
            login_data = {
                "email": email,
                "password": password,
                "csrfToken": csrf_token,
                "redirect": "false",
                "callbackUrl": CALLBACK_URL,
                "json": "true"
            }

            login_res = session.post(
                f"{BASE_URL}/api/auth/callback/credentials",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False,
                timeout=10
            )

            # 3️⃣ Get session
            sess_res = session.get(f"{BASE_URL}/api/auth/session", timeout=10)
            sess_json = sess_res.json()

            if not sess_json:
                status = "❌ Login thất bại"
            else:
                status = "✅ Login OK"

            results.append({
                "email": email,
                "status": status,
                "session": sess_json
            })

        except Exception as e:
            results.append({
                "email": email,
                "status": f"❌ Error: {e}",
                "session": None
            })

        progress.progress(idx / len(emails))

    # =========================
    # OUTPUT
    # =========================
    st.success("🎉 Hoàn tất")

    st.subheader("📦 Kết quả session")
    st.json(results)

    st.download_button(
        "💾 Tải file session (JSON)",
        data=json.dumps(results, indent=2, ensure_ascii=False),
        file_name="sessions_langsongxanh.json",
        mime="application/json"
    )

    st.markdown("""
    ---
    ### 🔧 Gợi ý bước tiếp theo
    - Gắn **API vote** vào từng session
    - Dùng `session.cookies` để gọi API vote
    - Có thể thêm delay / proxy / random UA
    """)
