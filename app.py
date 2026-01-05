import streamlit as st
import requests
import json
import io
import zipfile

# =========================
# CONFIG
# =========================
BASE_WEB = "https://lansongxanh.1vote.vn"
CALLBACK_URL = "https://lansongxanh.1vote.vn/thi-sinh/yj3su/quang-hung-masterd-xC7N"

EVENT_API = "https://eventista-platform-api.1vote.vn"
TENANT = "tx3aJc"
EVENT_ID = "EVENT_B5vGL"

# =========================
# STREAMLIT SETUP
# =========================
st.set_page_config(page_title="LangSongXanh QR Tool", layout="wide")
st.title("🎶 Làng Sóng Xanh – Login & Tạo QR Thanh Toán")

st.markdown("""
- Email dạng **gmail alias**
- **Mỗi email chỉ tạo 1 QR**
- Tải **ZIP QR** để copy ảnh dán Zalo cho nhanh
""")

# =========================
# INPUT
# =========================
st.subheader("📧 Tạo danh sách email")

email_prefix = st.text_input(
    "Email gốc (không gồm + số và @gmail.com)",
    placeholder="mrtienkaza"
)

col1, col2 = st.columns(2)
with col1:
    start_num = st.number_input("Từ số", min_value=1, step=1, value=1)
with col2:
    end_num = st.number_input("Đến số", min_value=1, step=1, value=5)

password = st.text_input("🔑 Mật khẩu (dùng chung)", type="password")

# =========================
# PAYMENT TYPE OPTION
# =========================
payment_type = st.radio(
    "💳 Phương thức thanh toán",
    options=[
        ("zalopay", "ZaloPay"),
        ("zalopay_vietqr", "Chuyển khoản ngân hàng (VietQR)")
    ],
    format_func=lambda x: x[1],
    index=0
)[0]

start_btn = st.button("🚀 Login & Tạo QR")

# =========================
# FUNCTION: CREATE QR
# =========================
def create_vote_qr(session, access_token, payment_type):
    url = f"{EVENT_API}/v1/tenants/{TENANT}/voting/{EVENT_ID}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://lansongxanh.1vote.vn",
        "Referer": "https://lansongxanh.1vote.vn/"
    }

    payload = {
        "paymentType": payment_type,
        "pointPackageId": "VND_LARGE_01",
        "productGroupId": "136PU",
        "productId": "xC7N",
        "source": {
            "screen": "home",
            "pointPackage": {
                "id": "VND_LARGE_01",
                "point": 10,
                "amount": 3000
            }
        }
    }

    res = session.post(url, headers=headers, json=payload, timeout=15)
    return res.json()

# =========================
# PROCESS
# =========================
if start_btn:
    if not email_prefix or not password or start_num > end_num:
        st.error("❌ Thiếu thông tin hoặc khoảng số không hợp lệ")
        st.stop()

    emails = [
        f"{email_prefix}+{i}@gmail.com"
        for i in range(int(start_num), int(end_num) + 1)
    ]

    st.info(f"📌 Tổng email: {len(emails)}")
    st.info(f"💳 Phương thức thanh toán: **{payment_type}**")

    results = []
    progress = st.progress(0.0)

    for idx, email in enumerate(emails, start=1):
        st.write(f"🔄 Đang xử lý: **{email}**")

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        })

        try:
            # Get CSRF
            csrf_res = session.get(f"{BASE_WEB}/api/auth/csrf", timeout=10).json()
            csrf = csrf_res.get("csrfToken")
            if not csrf:
                raise Exception("Không lấy được CSRF")

            # Login
            session.post(
                f"{BASE_WEB}/api/auth/callback/credentials",
                data={
                    "email": email,
                    "password": password,
                    "csrfToken": csrf,
                    "redirect": "false",
                    "callbackUrl": CALLBACK_URL,
                    "json": "true"
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False,
                timeout=10
            )

            # Get session
            sess = session.get(f"{BASE_WEB}/api/auth/session", timeout=10).json()
            access_token = sess.get("user", {}).get("accessToken")
            if not access_token:
                raise Exception("Không có accessToken")

            # Create QR (1 lần)
            order = create_vote_qr(session, access_token, payment_type)

            qr_url = None
            if order.get("errorCode") == 0:
                qr_url = order["data"]["zalopayDynamicQr"]["qrCode"]

            results.append({
                "email": email,
                "qr": qr_url
            })

        except Exception as e:
            results.append({
                "email": email,
                "error": str(e)
            })

        progress.progress(idx / len(emails))

    # =========================
    # OUTPUT
    # =========================
    st.success("🎉 Hoàn tất")

    st.subheader("📲 QR Thanh Toán (mỗi email 1 QR)")

    for item in results:
        if item.get("qr"):
            st.markdown(f"**{item['email']}**")
            st.image(item["qr"], width=220)
        else:
            st.warning(f"{item['email']} ❌ Không có QR")

    # =========================
    # ZIP DOWNLOAD
    # =========================
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for item in results:
            qr = item.get("qr")
            email = item.get("email")
            if not qr:
                continue
            img = requests.get(qr, timeout=10).content
            filename = f"{email.replace('@', '_')}.png"
            zipf.writestr(filename, img)

    zip_buffer.seek(0)

    st.download_button(
        "⚡ TẢI TẤT CẢ QR (ZIP – NHANH NHẤT)",
        data=zip_buffer,
        file_name="QR_Payment.zip",
        mime="application/zip"
    )

    st.markdown("""
    ---
    💡 **Cách dùng nhanh**
    1. Tải ZIP  
    2. Mở ZIP → chọn nhiều ảnh  
    3. **Ctrl + C → Ctrl + V vào Zalo**
    """)
