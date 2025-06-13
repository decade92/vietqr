# vietqr/app.py
import streamlit as st
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

# === CẤU HÌNH CỐ ĐỊNH ===
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
FONT_PATH = os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf")

def format_tlv(tag, value):
    return f"{tag}{len(value):02d}{value}"

def crc16_ccitt(data: str) -> str:
    crc = 0xFFFF
    for b in data.encode('utf-8'):
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if (crc & 0x8000) else crc << 1
            crc &= 0xFFFF
    return format(crc, '04X')

def build_payload(merchant_id, bank_bin, add_info, amount=None):
    def format_tlv(tag, value):
        return f"{tag}{len(value):02d}{value}"

    def crc16_ccitt(data: str) -> str:
        crc = 0xFFFF
        for b in data.encode('utf-8'):
            crc ^= b << 8
            for _ in range(8):
                crc = (crc << 1) ^ 0x1021 if (crc & 0x8000) else crc << 1
                crc &= 0xFFFF
        return format(crc, '04X')

    payload = ""
    payload += format_tlv("00", "01")        # Payload Format Indicator
    payload += format_tlv("01", "12")        # Point of Initiation Method (QR động)

    # --- Tag 38: Merchant Account Information ---
    guid = format_tlv("00", "A000000727")

    merchant_info = (
        format_tlv("00", bank_bin) +          # Bank BIN
        format_tlv("01", merchant_id)         # Merchant ID / số tài khoản định danh
    )
    acc_info = (
        guid +
        format_tlv("01", merchant_info) +
        format_tlv("02", "QRIBFTTA")
    )
    payload += format_tlv("38", acc_info)

    payload += format_tlv("52", "0000")       # Merchant Category Code
    payload += format_tlv("53", "704")        # Currency (VND)

    if amount:
        payload += format_tlv("54", str(amount))  # Optional: Amount (QR động có thể có)

    payload += format_tlv("58", "VN")         # Country code

    # Additional Data Field – nội dung chuyển khoản
    additional_data = format_tlv("08", add_info)
    payload += format_tlv("62", additional_data)

    # CRC (Checksum)
    payload_for_crc = payload + "6304"
    crc = crc16_ccitt(payload_for_crc)
    payload += format_tlv("63", crc)

    return payload


def generate_qr_with_logo(payload):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    logo = Image.open(LOGO_PATH).convert("RGBA")

    # Kích thước logo chiếm ~45% chiều rộng và 15% chiều cao QR
    logo_width = int(qr_img.width * 0.45)
    logo_height = int(qr_img.height * 0.15)
    logo = logo.resize((logo_width, logo_height))  # ✅ Resize bằng tuple

    # Canh giữa logo trên QR
    pos = ((qr_img.width - logo_width) // 2, (qr_img.height - logo_height) // 2)
    qr_img.paste(logo, pos, mask=logo)

    return qr_img

# ==== STREAMLIT UI ====
st.title("🇻🇳 Tạo VietQR chuyển khoản")

merchant_id = st.text_input("🔢 Số tài khoản định danh:")
acc_name = st.text_input("👤 Tên tài khoản:")
add_info = st.text_input("📝 Nội dung chuyển khoản:")
bank_bin = st.text_input("🏦 Mã ngân hàng (mặc định 970418):", "970418")
account_type_label = st.selectbox("🔐 Loại tài khoản:", ["Cá nhân", "Doanh nghiệp"])
account_type = "personal" if account_type_label == "Cá nhân" else "business"

if st.button("🎉 Tạo ảnh QR"):
    if not all([merchant_id, acc_name, add_info]):
        st.warning("Vui lòng nhập đầy đủ thông tin.")
    else:
        payload = build_payload(merchant_id.strip(), bank_bin.strip(), add_info.strip())
        qr_img = generate_qr_with_logo(payload)
        st.image(qr_img, caption="🎯 QR Code với logo", use_container_width=True)
