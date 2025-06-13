
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import qrcode
import os

# Đường dẫn cố định đến các file
LOGO_PATH = "assets/logo.png"
BACKGROUND_PATH = "assets/background.png"
FONT_PATH = "assets/DejaVuSans-Bold.ttf"

# === HÀM TIỆN ÍCH ===
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

def build_vietqr_payload(merchant_id, bank_bin, add_info):
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

# === TẠO QR ===
def create_qr_image(data):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((int(img_qr.width * 0.4), int(img_qr.height * 0.15)))
    pos = ((img_qr.width - logo.width) // 2, (img_qr.height - logo.height) // 2)
    img_qr.paste(logo, pos, mask=logo)
    return img_qr

# === GẮN VÀO BACKGROUND ===
def render_final_image(qr_img, merchant_id, acc_name):
    background = Image.open(BACKGROUND_PATH).convert("RGBA")
    qr_img = qr_img.resize((540, 540))
    background.paste(qr_img, (460, 936), mask=qr_img)

    draw = ImageDraw.Draw(background)
    font1 = ImageFont.truetype(FONT_PATH, 45)
    font2 = ImageFont.truetype(FONT_PATH, 60)
    draw.rectangle([(460, 1580), (1000, 2000)], fill="white")
    draw.text((490, 1650), "Tài khoản định danh:", fill=(0, 102, 102), font=font1)
    draw.text((410, 1730), merchant_id, fill=(0, 102, 102), font=font2)
    return background

# === GIAO DIỆN STREAMLIT ===
st.title("🎨 Tạo ảnh QR VietQR có logo & nền")

merchant_id = st.text_input("🔢 Số tài khoản định danh", max_chars=15)
acc_name = st.text_input("👤 Tên chủ tài khoản")
add_info = st.text_input("📝 Nội dung chuyển tiền", value="Thanh toan don hang")
bank_bin = "970418"  # Mặc định: Vietcombank

if st.button("Tạo ảnh QR"):
    if merchant_id and acc_name:
        payload = build_vietqr_payload(merchant_id, bank_bin, add_info)
        qr_img = create_qr_image(payload)
        final_img = render_final_image(qr_img, merchant_id, acc_name)
        st.image(final_img, caption="Ảnh QR đã tạo", use_column_width=True)

        # Cho phép tải
        final_img.save("output.png")
        with open("output.png", "rb") as f:
            st.download_button("📥 Tải ảnh", f, file_name="vietqr.png")
    else:
        st.error("Vui lòng nhập đủ số tài khoản và tên.")
