
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io, os, base64, cv2, numpy as np
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="VietQR BIDV", page_icon="assets/bidvfa.png", layout="centered")

ASSETS_DIR = "assets"
FONT_PATH = os.path.join(ASSETS_DIR, "Roboto-Bold.ttf")
LOGO_PATH = os.path.join(ASSETS_DIR, "bidvlogo.png")
BACKGROUND_PATH = os.path.join(ASSETS_DIR, "meothantai.jpg")

# Hàm tạo mã QR (giữ nguyên logic bạn đang dùng)
def generate_vietqr_image(account_name, account_no, bank_bin, amount, add_info, store_name=""):
    import segno

    qr_data = f"00020101021238{len(bank_bin):02d}{bank_bin}0208{account_no}53037045802{len(str(amount)):02d}{amount}5802VN62{len(add_info):02d}{add_info}6304"
    qr = segno.make(qr_data, error='H')
    qr_img = io.BytesIO()
    qr.save(qr_img, kind='png', scale=10, border=1)
    qr_img.seek(0)

    # Tạo ảnh nền
    background = Image.open(BACKGROUND_PATH).convert("RGB")
    draw = ImageDraw.Draw(background)
    font = ImageFont.truetype(FONT_PATH, 70)

    w, h = background.size
    qr_code = Image.open(qr_img).convert("RGBA").resize((700, 700))
    qr_x = (w - qr_code.width) // 2
    qr_y = (h - qr_code.height) // 2 + 50
    background.paste(qr_code, (qr_x, qr_y), qr_code)

    # Hiển thị tên cửa hàng nếu có
    if store_name:
        tw, _ = draw.textsize(store_name, font=font)
        draw.text(((w - tw) / 2, qr_y - 150), store_name, font=font, fill="#007C71")

    # Tên tài khoản
    if account_name:
        tw, _ = draw.textsize(account_name, font=font)
        draw.text(((w - tw) / 2, qr_y + qr_code.height + 30), account_name, font=font, fill="#007C71")

    # Số tài khoản
    if account_no:
        tw, _ = draw.textsize(account_no, font=font)
        draw.text(((w - tw) / 2, qr_y + qr_code.height + 110), account_no, font=font, fill="#007C71")

    return background

# ✅ Hàm decode ảnh QR bằng ZXing API
def decode_qr_zxing_online(uploaded_image):
    img = Image.open(uploaded_image).convert("RGB")
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    img_bytes = buffered.getvalue()

    files = {'f': ('qr.jpg', img_bytes, 'image/jpeg')}
    response = requests.post("https://zxing.org/w/decode", files=files)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        result_tag = soup.find("pre")
        return result_tag.text.strip() if result_tag else "❌ Không giải mã được (ZXing)"
    else:
        return "⚠️ Lỗi khi gọi ZXing API"

# Giao diện Streamlit
st.title("Tạo mã VietQR chuẩn BIDV")

tab1, tab2 = st.tabs(["🧾 Tạo mã QR", "🕵️ Giải mã ảnh QR"])

with tab1:
    account_name = st.text_input("Tên chủ tài khoản", "Pham Duy Long")
    account_no = st.text_input("Số tài khoản hoặc mã định danh", "PHAMDUYTRUNG")
    bank_bin = st.text_input("Mã ngân hàng (BIN)", "970418")  # BIDV mặc định
    amount = st.text_input("Số tiền (tuỳ chọn)", "50000")
    add_info = st.text_input("Nội dung chuyển khoản", "CHUYEN TIEN NHO RUT TIEN MAT")
    store_name = st.text_input("Tên cửa hàng (hiển thị trên ảnh)", "Cửa hàng Duy Long")

    if st.button("🎨 Tạo ảnh QR"):
        qr_img = generate_vietqr_image(account_name, account_no, bank_bin, amount, add_info, store_name)
        st.image(qr_img, caption="Ảnh QR VietQR", use_column_width=True)

with tab2:
    uploaded_image = st.file_uploader("Tải ảnh QR cần giải mã", type=["png", "jpg", "jpeg"])
    if uploaded_image:
        decoded = decode_qr_zxing_online(uploaded_image)
        st.subheader("📤 Nội dung QR:")
        st.code(decoded)
