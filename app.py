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

def create_qr_with_text(data, acc_name, merchant_id):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=11, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((int(img_qr.width * 0.45), int(img_qr.height * 0.15)))
    pos = ((img_qr.width - logo.width) // 2, (img_qr.height - logo.height) // 2)
    img_qr.paste(logo, pos, mask=logo)

    lines = [("Tên tài khoản:", 28), (acc_name.upper(), 34), ("Tài khoản định danh:", 28), (merchant_id, 34)]
    spacing = 12
    total_text_height = sum([s for (_, s) in lines]) + spacing * (len(lines) - 1)
    canvas = Image.new("RGBA", (img_qr.width, img_qr.height + total_text_height + 30), "white")
    canvas.paste(img_qr, (0, 0))
    draw = ImageDraw.Draw(canvas)
    y = img_qr.height + 10

    for text, size in lines:
        font = ImageFont.truetype(FONT_PATH, size)
        w = draw.textbbox((0, 0), text, font=font)[2]
        draw.text(((canvas.width - w) // 2, y), text, fill="#007C71", font=font)
        y += size + spacing

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)
    return buf

def create_qr_with_text(data, acc_name, merchant_id):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=11, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((int(img_qr.width * 0.45), int(img_qr.height * 0.15)))
    pos = ((img_qr.width - logo.width) // 2, (img_qr.height - logo.height) // 2)
    img_qr.paste(logo, pos, mask=logo)

    # Nội dung dòng text (4 dòng)
    lines = [
        ("Tên tài khoản:", 28, "black"),
        (acc_name.upper(), 34, "#007C71"),
        ("Tài khoản định danh:", 28, "black"),
        (merchant_id, 34, "#007C71")
    ]
    spacing = 12
    total_text_height = sum([size for _, size, _ in lines]) + spacing * (len(lines) - 1)

    canvas = Image.new("RGBA", (img_qr.width, img_qr.height + total_text_height + 30), "white")
    canvas.paste(img_qr, (0, 0))

    draw = ImageDraw.Draw(canvas)
    y = img_qr.height + 10

    for text, size, color in lines:
        font = ImageFont.truetype(FONT_PATH, size)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text(((canvas.width - text_width) // 2, y), text, fill=color, font=font)
        y += size + spacing

    buf = BytesIO()
    canvas.save(buf, format="PNG")
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
