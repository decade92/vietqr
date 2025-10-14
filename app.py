import streamlit as st
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io, os, base64, cv2, numpy as np
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="VietQR BIDV", page_icon="assets/bidvfa.png", layout="centered")
st.markdown(
    """
    <style>
    /* Xoá khoảng trắng trên cùng */
    .block-container {
        padding-top: 0rem;
    }
    header[data-testid="stHeader"] {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
FONT_PATH = os.path.join(ASSETS_DIR, "Roboto-Bold.ttf")
FONT_LABELPATH = os.path.join(ASSETS_DIR, "RobotoCondensed-Regular.ttf")
BG_PATH = os.path.join(ASSETS_DIR, "background.png")
BG_THAI_PATH = os.path.join(ASSETS_DIR, "backgroundthantai.png")
BG_LOA_PATH = os.path.join(ASSETS_DIR, "backgroundloa.png")
BG_TINGBOX_PATH = os.path.join(ASSETS_DIR, "tingbox.png")

# ======== QR Logic Functions ========
def clean_amount_input(raw_input):
    if not raw_input:
        return ""
    try:
        # Xử lý định dạng: "1.000.000,50" => "1000000.50"
        cleaned = raw_input.replace(".", "").replace(",", ".")
        value = float(cleaned)
        return str(int(value))  # Lấy phần nguyên
    except ValueError:
        return None
        
def format_tlv(tag, value): return f"{tag}{len(value):02d}{value}"
def sanitize_input(text):
    return ''.join(text.split())

def crc16_ccitt(data):
    crc = 0xFFFF
    for b in data.encode():
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"

def parse_tlv(payload):
    i = 0
    tlv_data = {}
    while i + 4 <= len(payload):
        tag = payload[i:i+2]
        length_str = payload[i+2:i+4]
        try:
            length = int(length_str)
        except ValueError:
            raise ValueError(f"Lỗi TLV: không thể chuyển '{length_str}' thành số nguyên tại vị trí {i}")
        
        value_start = i + 4
        value_end = value_start + length
        if value_end > len(payload):
            raise ValueError(f"Lỗi TLV: độ dài value vượt quá payload tại tag {tag}")
        
        value = payload[value_start:value_end]
        tlv_data[tag] = value
        i = value_end
    return tlv_data


def extract_vietqr_info(payload):
    parsed = parse_tlv(payload)
    info = {"account": "", "bank_bin": "", "name": "", "note": "", "amount": ""}
    if "38" in parsed:
        nested_38 = parse_tlv(parsed["38"])
        if "01" in nested_38:
            acc_info = parse_tlv(nested_38["01"])
            info["bank_bin"] = acc_info.get("00", "")
            info["account"] = acc_info.get("01", "")
    if "62" in parsed:
        add = parse_tlv(parsed["62"])
        info["note"] = add.get("08", "")
    if "54" in parsed:
        info["amount"] = parsed["54"]
    return info

def decode_qr_auto(uploaded_image):
    # Convert to OpenCV image
    uploaded_image.seek(0)
    file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
    image_cv2 = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    # Step 1: OpenCV
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(image_cv2)
    if data:
        try:
            if data.startswith("00"):
                _ = parse_tlv(data)  # Gọi thử để xác thực cấu trúc TLV
                return data.strip(), "✅ Đọc bằng OpenCV"
        except Exception as e:
            # Nếu sai TLV, tiếp tục thử ZXing
            st.info(f"⚠️ OpenCV phát hiện QR nhưng không hợp chuẩn TLV: {e}")

    # Step 2: ZXing fallback
    try:
        uploaded_image.seek(0)
        img = Image.open(uploaded_image).convert("RGB")
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        img_bytes = buffered.getvalue()

        files = {'f': ('qr.jpg', img_bytes, 'image/jpeg')}
        response = requests.post("https://zxing.org/w/decode", files=files)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            result_tag = soup.find("pre")
            if result_tag:
                zxing_data = result_tag.text.strip()
                try:
                    if zxing_data.startswith("00"):
                        _ = parse_tlv(zxing_data)  # Xác thực TLV
                        return zxing_data, "✅ Đọc bằng ZXing"
                except Exception as e:
                    return None, f"❌ ZXing đọc nhưng sai chuẩn TLV: {e}"
    except Exception as e:
        return None, f"❌ ZXing lỗi: {e}"

    return None, "❌ Không thể đọc QR bằng OpenCV hoặc ZXing. QR được giải mã nhưng không đúng chuẩn VietQR"
    
def round_corners(image, radius):
    rounded = Image.new("RGBA", image.size, (0, 0, 0, 0))
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, image.size[0], image.size[1]], radius=radius, fill=255)
    rounded.paste(image, (0, 0), mask=mask)
    return rounded

def build_vietqr_payload(merchant_id, bank_bin, add_info, amount=""):
    p = format_tlv
    payload = p("00", "01") + p("01", "12")
    acc_info = p("00", bank_bin) + p("01", merchant_id)
    nested_38 = p("00", "A000000727") + p("01", acc_info) + p("02", "QRIBFTTA")
    payload += p("38", nested_38) + p("52", "0000") + p("53", "704")
    if amount: payload += p("54", amount)
    payload += p("58", "VN") + p("62", p("08", add_info)) + "6304"
    return payload + crc16_ccitt(payload)

def generate_qr_with_logo(data):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    logo = Image.open(LOGO_PATH).convert("RGBA").resize((int(img.width*0.45), int(img.height*0.15)))
    img.paste(logo, ((img.width - logo.width) // 2, (img.height - logo.height) // 2), logo)
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return buf

def create_qr_with_text(data, acc_name, merchant_id):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=21, border=3)
    qr.add_data(data); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    logo = Image.open(LOGO_PATH).convert("RGBA").resize((int(img.width*0.45), int(img.height*0.15)))
    img.paste(logo, ((img.width - logo.width) // 2, (img.height - logo.height) // 2), logo)
    lines = [("Tên tài khoản:", 48, "black"), (acc_name.upper(), 60, "#007C71"), ("Tài khoản định danh:", 48, "black"), (merchant_id, 60, "#007C71")]
    spacing = 20
    total_text_height = sum([size for _, size, _ in lines]) + spacing * (len(lines) - 1)
    canvas = Image.new("RGBA", (img.width, img.height + total_text_height + 65), "white")
    canvas.paste(img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    y = img.height + 16
    for text, size, color in lines:
        font = ImageFont.truetype(FONT_PATH, size)
        x = (canvas.width - draw.textbbox((0, 0), text, font=font)[2]) // 2
        draw.text((x, y), text, fill=color, font=font)
        y += size + spacing
    buf = io.BytesIO(); canvas.save(buf, format="PNG"); buf.seek(0)
    return buf

def create_qr_with_background(data, acc_name, merchant_id, store_name):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(data); qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA").resize((540, 540))
    qr_img = round_corners(qr_img, 40)
    logo = Image.open(LOGO_PATH).convert("RGBA").resize((240, 80))
    qr_img.paste(logo, ((qr_img.width - logo.width) // 2, (qr_img.height - logo.height) // 2), logo)
    base = Image.open(BG_PATH).convert("RGBA")
    base.paste(qr_img, (460, 936), qr_img)
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(FONT_PATH, 60)
    cx = lambda t, f: (base.width - draw.textbbox((0, 0), t, font=f)[2]) // 2
    draw.text((cx(acc_name.upper(), font), 1665), acc_name.upper(), fill=(0, 102, 102), font=font)
    draw.text((cx(merchant_id, font), 1815), merchant_id, fill=(0, 102, 102), font=font)
    store_font = ImageFont.truetype(FONT_PATH, 70)
    draw.text((cx(store_name.upper(), store_font), 265), store_name.upper(), fill="#007C71", font=store_font)
    buf = io.BytesIO(); base.save(buf, format="PNG"); buf.seek(0)
    return buf

def create_qr_with_background_thantai(data, acc_name, merchant_id, store_name):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA").resize((480, 520))
    logo = Image.open(LOGO_PATH).convert("RGBA").resize((240, 80))
    qr_img.paste(logo, ((qr_img.width - logo.width) // 2, (qr_img.height - logo.height) // 2), logo)
    base = Image.open(BG_THAI_PATH).convert("RGBA")
    base.paste(qr_img, (793, 725), qr_img)
    draw = ImageDraw.Draw(base)
    font = ImageFont.truetype(FONT_PATH, 60)
    cx = lambda t, f: (base.width - draw.textbbox((0, 0), t, font=f)[2]) // 2
    draw.text((cx(acc_name.upper(), font), 1665), acc_name.upper(), fill=(0, 102, 102), font=font)
    draw.text((cx(merchant_id, font), 1815), merchant_id, fill=(0, 102, 102), font=font)
    store_font = ImageFont.truetype(FONT_PATH, 70)
    draw.text((cx(store_name.upper(), store_font), 265), store_name.upper(), fill="#007C71", font=store_font)
    buf = io.BytesIO(); base.save(buf, format="PNG"); buf.seek(0)
    return buf

def create_qr_with_background_loa(data, acc_name, merchant_id, store_name="", support_name="", support_phone=""):
    # Tạo QR
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=0
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA").resize((560, 560))

    # Thêm logo lên QR
    logo = Image.open(LOGO_PATH).convert("RGBA").resize((240, 80))
    qr_img.paste(
        logo,
        ((qr_img.width - logo.width) // 2, (qr_img.height - logo.height) // 2),
        logo
    )

    # Mở nền
    base = Image.open(BG_LOA_PATH).convert("RGBA")
    qr_x, qr_y = 175, 285  # Vị trí QR trên nền
    base.paste(qr_img, (qr_x, qr_y), qr_img)

    draw = ImageDraw.Draw(base)

    # Hàm tính font giảm nếu tên dài
    def get_font(text, max_width, base_size):
        font_size = base_size
        font = ImageFont.truetype(FONT_PATH, font_size)
        text_width = draw.textbbox((0, 0), text, font=font)[2]
        while text_width > max_width and font_size > 20:
            font_size -= 2
            font = ImageFont.truetype(FONT_PATH, font_size)
            text_width = draw.textbbox((0, 0), text, font=font)[2]
        return font, font_size

    # Căn giữa QR
    max_text_width = qr_img.width
    y_offset = qr_y + qr_img.height + 20

    label_font_size = 28
    font_label = ImageFont.truetype(FONT_LABELPATH, label_font_size)

    # Tên tài khoản
    if acc_name and acc_name.strip():
        label_acc = "Tên tài khoản:"
        draw.text((qr_x + (qr_img.width - draw.textbbox((0,0), label_acc, font=font_label)[2]) // 2,
                   y_offset),
                  label_acc, fill="black", font=font_label)

        y_offset += label_font_size + 8
        font_acc, acc_font_size = get_font(acc_name.upper(), max_text_width, 32)
        x_acc = qr_x + (qr_img.width - draw.textbbox((0,0), acc_name.upper(), font=font_acc)[2]) // 2
        draw.text((x_acc, y_offset), acc_name.upper(), fill=(0,102,102), font=font_acc)
        y_offset += acc_font_size + 15

    # Số tài khoản
    if merchant_id and merchant_id.strip():
        label_merchant = "Số tài khoản:"
        draw.text((qr_x + (qr_img.width - draw.textbbox((0,0), label_merchant, font=font_label)[2]) // 2,
                   y_offset),
                  label_merchant, fill="black", font=font_label)
        y_offset += label_font_size + 8
        font_merchant, merchant_font_size = get_font(merchant_id, max_text_width, 32)
        x_merchant = qr_x + (qr_img.width - draw.textbbox((0,0), merchant_id, font=font_merchant)[2]) // 2
        draw.text((x_merchant, y_offset), merchant_id, fill=(0,102,102), font=font_merchant)
        y_offset += merchant_font_size + 20

    # Tọa độ tùy chỉnh cho cán bộ hỗ trợ
    support_name_x, support_name_y = 500, 1136
    support_phone_x, support_phone_y = 570, 1173

    if support_name and support_name.strip():
        font_support_name = ImageFont.truetype(FONT_LABELPATH, 32)
        draw.text((support_name_x, support_name_y), support_name, fill=(0,102,102), font=font_support_name)

    if support_phone and support_phone.strip():
        font_support_phone = ImageFont.truetype(FONT_LABELPATH, 32)
        draw.text((support_phone_x, support_phone_y), support_phone, fill=(0,102,102), font=font_support_phone)

    # Lưu ảnh ra buffer
    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return buf

def create_qr_tingbox(data, merchant_id):
    # Tạo QR
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=0
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA").resize((500, 500))

    # Mở nền ảnh có sẵn
    base = Image.open(BG_TINGBOX_PATH).convert("RGBA")

    # Paste QR vào nền, căn giữa theo X và vị trí Y tùy chỉnh
    qr_x = 200
    qr_y = 285  # điều chỉnh tùy ý
    base.paste(qr_img, (qr_x, qr_y), qr_img)

    draw = ImageDraw.Draw(base)

    # Hàm tính font giảm nếu tên quá dài
    def get_font(text, max_width, base_size):
        font_size = base_size
        font = ImageFont.truetype(FONT_PATH, font_size)
        text_width = draw.textbbox((0,0), text, font=font)[2]
        while text_width > max_width and font_size > 12:
            font_size -= 1
            font = ImageFont.truetype(FONT_PATH, font_size)
            text_width = draw.textbbox((0,0), text, font=font)[2]
        return font

    # Vẽ merchant_id dưới QR, căn giữa
    if merchant_id and merchant_id.strip():
        max_text_width = qr_img.width
        font_merchant = get_font(merchant_id, max_text_width, 32)
        text_width = draw.textbbox((0,0), merchant_id, font=font_merchant)[2]
        x_merchant = qr_x + (qr_img.width - text_width) // 2
        y_merchant = qr_y + qr_img.height + 20
        draw.text((x_merchant, y_merchant), merchant_id, fill=(0,102,102), font=font_merchant)

    # Lưu buffer
    buf = io.BytesIO()
    base.save(buf, format="PNG")
    buf.seek(0)
    return buf
    
# ==== Giao diện người dùng ====
if os.path.exists(FONT_PATH):
    font_css = f"""
    <style>
    @font-face {{
        font-family: 'RobotoCustom';
        src: url(data:font/ttf;base64,{base64.b64encode(open(FONT_PATH, "rb").read()).decode()}) format('truetype');
    }}
    * {{ font-family: 'RobotoCustom'; }}
    </style>
    """
    st.markdown(font_css, unsafe_allow_html=True)

# Tiêu đề 1: Tên ứng dụng
st.markdown(
    """
    <div style="display: flex; align-items: center; justify-content: left; margin-bottom: 10px;">
        <span style="font-family: Roboto, sans-serif; font-weight: bold; font-size: 22px; color: white;">
            🇻🇳 Tạo ảnh VietQR đẹp chuẩn NAPAS
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# Tiêu đề 2: BIDV Thái Bình + logo
st.markdown(
    """
    <div style="display: flex; align-items: center;">
        <img src="data:image/png;base64,{logo_data}" style="max-height:20px; height:20px; width:auto; margin-right:10px;">
        <span style="font-family: Roboto, sans-serif; font-weight: bold; font-size:20px; color:#007C71;">
            Dành riêng cho BIDV Thái Bình
        </span>
    </div>
    """.format(
        logo_data=base64.b64encode(open("assets/logo_bidv.png", "rb").read()).decode()
    ),
    unsafe_allow_html=True
)


uploaded_result = st.file_uploader("📤 Tải ảnh QR VietQR", type=["png", "jpg", "jpeg"], key="uploaded_file")
if uploaded_result and uploaded_result != st.session_state.get("last_file_uploaded"):
    st.session_state["last_file_uploaded"] = uploaded_result
    qr_text, method = decode_qr_auto(uploaded_result)
    st.write(method)
    if qr_text:
        try:
            info = extract_vietqr_info(qr_text)
            bank_bin = info.get("bank_bin", "")
            bank_map = {
                            "970418": "BIDV",
                            "970436": "Vietcombank",
                            "970415": "VietinBank",
                            "970405": "Agribank",
                            "970422": "MB Bank",
                            "970407": "Techcombank",
                            "970423": "TPBank",
                            "970424": "Shinhan Bank",
                            "970441": "VIB",
                            "970432": "VPBank",
                            "970443": "SHB",
                            "970431": "Eximbank",
                            "970438": "BaoVietBank",
                            "970454": "VietCapitalBank",
                            "970429": "SCB",
                            "970421": "VRB",
                            "970425": "ABBank",
                            "970412": "PVcomBank",
                            "970414": "OceanBank",
                            "970428": "NamABank",
                            "970437": "HDBank",
                            "970433": "VietBank",
                            "970459": "ABBANK",
                            "970448": "OCB",
                            "970409": "BacABank",
                            "970442": "Hong Leong Bank VN",
                            "970430": "PG Bank",
                            "970446": "Co-op Bank",
                            "422589": "CIMB VN",
                            "970434": "Indovina Bank",
                            "970457": "Woori VN",
                            "970458": "UOB VN",
                            "970466": "KEB Hana HCM",
                            "970467": "KEB Hana HN",
                            # Tiếp tục bổ sung nếu cần...
                        }

            if bank_bin != "970418":
                bank_name = bank_map.get(bank_bin, f"Mã BIN {bank_bin}")
                st.error(f"""
                ⚠️ Mã QR này thuộc về: {bank_name}  
                Ứng dụng chỉ hỗ trợ QR từ BIDV (Mã BIN: 970418)
                """)
            else:
                st.session_state["account"] = info.get("account", "")
                st.session_state["bank_bin"] = bank_bin
                st.session_state["note"] = info.get("note", "")
                st.session_state["amount"] = info.get("amount", "")
                st.session_state["name"] = info.get("name", "")
                st.session_state["store"] = info.get("store", "")
                st.success("✅ Đã trích xuất dữ liệu từ ảnh QR.")
        except Exception as e:
            st.warning(f"⚠️ QR được giải mã nhưng không đúng chuẩn VietQR: {e}")



# Nhập số tài khoản (giữ nguyên key để Streamlit nhớ giá trị)
account = st.text_input("🔢 Số tài khoản", value=st.session_state.get("account", ""), key="account")

# Làm sạch dữ liệu: bỏ khoảng trắng dư thừa
account = ''.join(account.split())
name = st.text_input("👤 Tên tài khoản (nếu có)", value=st.session_state.get("name", ""), key="name")
store = st.text_input("🏪 Tên cửa hàng (nếu có)", value=st.session_state.get("store", ""), key="store")
note = st.text_input("📝 Nội dung (nếu có)", value=st.session_state.get("note", ""), key="note")
bank_bin = ''.join(st.session_state.get("bank_bin", "970418").split())
amount = ''.join(str(st.session_state.get("amount", "")).split())
merchant_id = ''.join(account.split())  # nếu bạn dùng account làm merchant_id

# === Danh sách cán bộ hỗ trợ ===
staff_list = {
    "": ("", ""),
    "Vũ Hoàng Phát - PGD Tiền Hải": ("Vũ Hoàng Phát", "0986.155.838"),
    "Lê Thị Liên - PGD Tiền Hải": ("Lê Thị Liên", "0976.239.278"),
    "Chu Thị Thu Hiền - BIDV Tiền Hải": ("Chu Thị Thu Hiền", "0989.557.699"),
}

selected_staff = st.selectbox("👨‍💼 Cán bộ hỗ trợ", list(staff_list.keys()), key="staff_selected")
staff_name, staff_phone = staff_list[selected_staff]
# Xử lý đầu vào số tiền
amount_input_raw = st.text_input("💰 Số tiền (nếu có)", value=st.session_state.get("amount", ""), key="amount_input")
amount_cleaned = clean_amount_input(amount_input_raw)

if amount_input_raw and amount_cleaned is None:
    st.error("❌ Số tiền không hợp lệ. Vui lòng chỉ nhập số (dùng dấu . hoặc , nếu có).")
else:
    st.session_state["amount"] = amount_cleaned or ""


if st.button("🎉 Tạo mã QR"):
    if not account.strip():
        st.warning("⚠️ Vui lòng nhập số tài khoản.")
    else:
        qr_data = build_vietqr_payload(account.strip(), bank_bin.strip(), note.strip(), amount.strip())
        st.session_state["qr1"] = generate_qr_with_logo(qr_data)
        st.session_state["qr2"] = create_qr_with_text(qr_data, name.strip(), account.strip())
        st.session_state["qr3"] = create_qr_with_background(qr_data, name.strip(), account.strip(), store.strip())
        st.session_state["qr4"] = create_qr_with_background_thantai(qr_data, name.strip(), account.strip(), store.strip())
        st.session_state["qr5"] = create_qr_with_background_loa(
            qr_data,
            name.strip(),
            account.strip(),
            store.strip(),
            staff_name.strip(),
            staff_phone.strip(),
        )
        st.session_state["qr6"] = create_qr_tingbox(qr_data, account.strip())
        st.success("✅ Mã QR đã được tạo thành công.")

# ==== Hiển thị ảnh QR nếu có ====
if "qr1" in st.session_state:
    with st.expander("🏷️ Mẫu 1: QR có logo"):
        st.image(st.session_state["qr1"], caption="Mẫu QR có logo", use_container_width=True)
if "qr2" in st.session_state:
    with st.expander("📄 Mẫu 2: QR có chữ"):
        st.image(st.session_state["qr2"], caption="Mẫu QR có chữ", use_container_width=True)
if "qr3" in st.session_state:
    with st.expander("🐱 Mẫu 3: QR mèo thần tài"):
        st.image(st.session_state["qr3"], caption="Mẫu QR mèo thần tài", use_container_width=True)
if "qr4" in st.session_state:
    with st.expander("🐯 Mẫu 4: QR thần tài"):
        st.image(st.session_state["qr4"], caption="Mẫu QR nền thần tài", use_container_width=True)
if "qr5" in st.session_state:
    with st.expander("🔊 Mẫu 5: QR nền loa thanh toán"):
        st.image(st.session_state["qr5"], caption="Mẫu QR loa thanh toán", use_container_width=True)
if "qr6" in st.session_state:
    with st.expander("📱 Mẫu 6: QR Tingbox"):
        st.image(st.session_state["qr6"], caption="Mẫu QR Tingbox", use_container_width=True)
