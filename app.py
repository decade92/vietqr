import streamlit as st
import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
FONT_PATH = os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf")
BG_PATH = os.path.join(ASSETS_DIR, "background.png")

def format_tlv(tag, value):
    return f"{tag}{len(value):02d}{value}"

def crc16_ccitt(data: str) -> str:
    crc = 0xFFFF
    for b in data.encode("utf-8"):
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if (crc & 0x8000) else crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"

def build_vietqr_payload(merchant_id, bank_bin, add_info, amount=""):
    payload = ""
    payload += format_tlv("00", "01")
    payload += format_tlv("01", "12")  # Dynamic QR
    guid = format_tlv("00", "A000000727")
    acc_info = format_tlv("00", bank_bin) + format_tlv("01", merchant_id)
    nested_38 = guid + format_tlv("01", acc_info) + format_tlv("02", "QRIBFTTA")
    payload += format_tlv("38", nested_38)
    payload += format_tlv("52", "0000")
    payload += format_tlv("53", "704")
    if amount:
        payload += format_tlv("54", amount)
    payload += format_tlv("58", "VN")
    payload += format_tlv("62", format_tlv("08", add_info))
    payload += "6304"
    payload += crc16_ccitt(payload)
    return payload

def generate_qr_with_logo(data):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((int(img_qr.width * 0.45), int(img_qr.height * 0.15)))
    pos = ((img_qr.width - logo.width) // 2, (img_qr.height - logo.height) // 2)
    img_qr.paste(logo, pos, mask=logo)

    buf = BytesIO()
    img_qr.save(buf, format="PNG")
    buf.seek(0)
    return buf

def create_qr_with_background(data, acc_name, merchant_id):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA").resize((540, 540))

    logo = Image.open(LOGO_PATH).convert("RGBA").resize((240, 80))
    qr_img.paste(logo, ((qr_img.width - logo.width) // 2, (qr_img.height - logo.height) // 2), mask=logo)

    base = Image.open(BG_PATH).convert("RGBA")
    base.paste(qr_img, (460, 936), mask=qr_img)

    draw = ImageDraw.Draw(base)
    font1 = ImageFont.truetype(FONT_PATH, 45)
    font2 = ImageFont.truetype(FONT_PATH, 60)

    # Căn giữa toàn ảnh theo chiều ngang
    def center_x(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        return (base.width - text_width) // 2

    # Nội dung
    label_1 = "Tên tài khoản:"
    value_1 = acc_name.upper()
    label_2 = "Tài khoản định danh:"
    value_2 = merchant_id

    # Vẽ nền trắng đủ rộng phía dưới
    draw.rectangle([(0, 1500), (base.width, 2000)], fill="white")

    # Vẽ các dòng text, căn giữa toàn ảnh
    draw.text((center_x(label_1, font1), 1520), label_1, fill=(0, 102, 102), font=font1)
    draw.text((center_x(value_1, font2), 1580), value_1, fill=(0, 102, 102), font=font2)
    draw.text((center_x(label_2, font1), 1680), label_2, fill=(0, 102, 102), font=font1)
    draw.text((center_x(value_2, font2), 1740), value_2, fill=(0, 102, 102), font=font2)

    buf = BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return buf




st.title("🇻🇳 Tạo ảnh VietQR đẹp chuẩn NAPAS ")
st.title("🇻🇳 Dành riêng BIDV Thái Bình")

merchant_id = st.text_input("🔢 Số tài khoản định danh:")
acc_name = st.text_input("👤 Tên tài khoản (tuỳ chọn):")
add_info = st.text_input("📝 Nội dung chuyển khoản (tuỳ chọn):")
amount = st.text_input("💵 Số tiền (tuỳ chọn):", "")
bank_bin = st.text_input("🏦 Mã ngân hàng (mặc định BIDV 970418):", "970418")

if st.button("🎉 Tạo mã QR"):
    if not merchant_id:
        st.warning("❗ Vui lòng nhập đầy đủ thông tin TK.")
    else:
        qr_data = build_vietqr_payload(merchant_id.strip(), bank_bin.strip(), add_info.strip(), amount.strip())
        qr1 = generate_qr_with_logo(qr_data)
        qr2 = create_qr_with_text(qr_data, acc_name, merchant_id)
        qr3 = create_qr_with_background(qr_data, merchant_id)

        st.subheader("📌 Mẫu 1: QR Rút gọn")
        st.image(qr1, caption="QR VietQR chuẩn")

        st.subheader("🧾 Mẫu 2: QR có thông tin tài khoản bên dưới")
        st.image(qr2, caption="QR kèm tên và định danh")

        st.subheader("🌅 Mẫu 3: QR mèo thân tài")
        st.image(qr3, caption="QR nền tùy chỉnh")
