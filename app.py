# vietqr/app.py
import streamlit as st
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

# === CẤU HÌNH CỐ ĐỊNH ===
FONT_PATH = "vietqr/assets/DejaVuSans-Bold.ttf"
LOGO_PATH = "vietqr/assets/logo.png"
BG_PATH = "vietqr/assets/background.png"

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

def build_payload(merchant_id, bank_bin, add_info):
    payload = ''
    payload += format_tlv("00", "01")
    payload += format_tlv("01", "11")
    acc_info = format_tlv("00", "A000000727") + format_tlv("01", f"0006{bank_bin}0115{merchant_id}") + format_tlv("02", "QRIBFTTA")
    payload += format_tlv("38", acc_info)
    payload += format_tlv("52", "0000")
    payload += format_tlv("53", "704")
    payload += format_tlv("58", "VN")
    payload += format_tlv("62", format_tlv("08", add_info))
    payload += format_tlv("63", crc16_ccitt(payload + "6304"))
    return payload

def generate_qr_with_logo(payload):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    logo = Image.open(LOGO_PATH).convert("RGBA").resize((int(qr_img.width * 0.45), int(qr_img.height * 0.15)))
    pos = ((qr_img.width - logo.width) // 2, (qr_img.height - logo.height) // 2)
    qr_img.paste(logo, pos, mask=logo)

    return qr_img

# ==== STREAMLIT UI ====
st.title("🇻🇳 Tạo VietQR chuyển khoản")
merchant_id = st.text_input("🔢 Nhập số tài khoản định danh:")
acc_name = st.text_input("👤 Tên tài khoản:")
add_info = st.text_input("📝 Nội dung chuyển tiền:")
bank_bin = st.text_input("🏦 Mã ngân hàng (mặc định 970418):", "970418")

if st.button("🎉 Tạo ảnh QR"):
    if not all([merchant_id, acc_name, add_info]):
        st.warning("Vui lòng nhập đầy đủ thông tin.")
    else:
        payload = build_payload(merchant_id.strip(), bank_bin.strip(), add_info.strip())
        qr_img = generate_qr_with_logo(payload)
        st.image(qr_img, caption="🎯 QR Code với logo", use_column_width=False)
