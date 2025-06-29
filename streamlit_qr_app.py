import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import qrcode
import uuid
from io import BytesIO
import io
import csv
import requests
from PyPDF2 import PdfMerger

st.set_page_config(page_title="Table QR Generator", layout="centered")
st.title("🍽️ Table QR Code Generator")

# ---- UI Inputs ----
# Two columns layout: left for table count, prefix, and three checkboxes; right for font settings
col1, col2 = st.columns(2)

with col1:
    table_count = st.number_input("Number of Tables", 1, 100, 1)
    table_prefix = st.text_input("Table Prefix", value="Table")

with col2:
    font_choice = st.selectbox("Font", ["Roboto", "Poppins", "Noto Sans"])

    # All three options in this column
    download_url_only = st.checkbox("Download URLs Only")

    if download_url_only:
        # Disable the other two options
        include_wifi = False
        include_loyalty = False
    else:
        include_wifi = st.checkbox("Include WiFi QR")
        if include_wifi:
            ssid = st.text_input("WiFi SSID", value="My_Wifi")
            password = st.text_input("WiFi Password", value="My_Wifi_Password")
            encryption = st.selectbox("Encryption Type", ["WPA", "WEP"])
            wifi_data = f"WIFI:T:{encryption};S:{ssid};P:{password};;"

        include_loyalty = st.checkbox("Include Loyalty QR")
        if include_loyalty:
            loyalty_url = st.text_input("Loyalty URL", value="https://rewards.oolio.io/store")

# ---- Download Google Fonts ----
def download_google_font(font_name):
    font_urls = {
        "Roboto": "https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Regular.ttf",
        "Poppins": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf",
        "Noto Sans": "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Regular.ttf"
    }
    url = font_urls.get(font_name)
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.content
    except:
        pass
    # Fallback to system default font
    with open("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "rb") as f:
        return f.read()

# ---- QR Code Generators ----
def generate_basic_qr(data, fill="#ffffff", back="#4080e8", size=200):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill, back_color=back).convert("RGB")
    return img.resize((size, size))

def generate_menu_qr_with_logo(data, logo_url, size=300):
    qr_img = generate_basic_qr(data, fill="#ffffff", back="#4080e8", size=size)
    response = requests.get(logo_url)
    logo = Image.open(BytesIO(response.content)).convert("RGBA")
    logo_size = size // 4
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
    draw = ImageDraw.Draw(qr_img)
    x = (size - logo_size) // 2
    y = (size - logo_size) // 2
    draw.rectangle((x, y, x + logo_size, y + logo_size), fill="#4080e8")
    qr_img.paste(logo, (x, y), mask=logo)
    return qr_img

def get_text_height(text, font):
    bbox = font.getbbox(text)
    return bbox[3] - bbox[1]

# ---- Page Drawing ----
def draw_centered_page(table_number, wifi_qr, loyalty_qr, menu_qr, font, table_prefix, font_title):
    width, height = 600, 800
    # Background image
    response = requests.get(
        "https://ooliovideoshb.s3.ap-southeast-2.amazonaws.com/"
        "OPOS+-+Back+Office/Oolio_Gradient_3_4.png"
    )
    bg = Image.open(BytesIO(response.content)).resize((width, height)).convert("RGB")
    draw = ImageDraw.Draw(bg)

    def draw_text(text, y, font_override=None, spacing=10):
        current_font = font_override or font
        bbox = draw.textbbox((0, 0), text, font=current_font)
        w = bbox[2] - bbox[0]
        draw.text(((width - w) // 2, y), text, font=current_font, fill="white")
        return y + (bbox[3] - bbox[1]) + spacing

    y = 30
    y = draw_text(f"{table_prefix} {table_number}", y, font_override=font_title, spacing=20)

    if wifi_qr or loyalty_qr:
        y = draw_text("Step 1", y, spacing=15)
        qr_size = 200
        spacing = 30

        if wifi_qr and loyalty_qr:
            total_width = qr_size * 2 + spacing
            start_x = (width - total_width) // 2

            wifi_label = "WiFi"
            loyalty_label = "Loyalty"
            w_bbox = draw.textbbox((0, 0), wifi_label, font=font)
            l_bbox = draw.textbbox((0, 0), loyalty_label, font=font)
            w_w = w_bbox[2] - w_bbox[0]
            l_w = l_bbox[2] - l_bbox[0]
            label_h = max(w_bbox[3] - w_bbox[1], l_bbox[3] - l_bbox[1])

            draw.text((start_x + qr_size//2 - w_w//2, y), wifi_label, font=font, fill="white")
            draw.text((start_x + qr_size + spacing + qr_size//2 - l_w//2, y),
                      loyalty_label, font=font, fill="white")

            y += label_h + 10
            bg.paste(wifi_qr, (start_x, y))
            bg.paste(loyalty_qr, (start_x + qr_size + spacing, y))
            y += qr_size + spacing

        elif wifi_qr:
            draw.text(((width - 60) // 2, y), "WiFi", font=font, fill="white")
            y += 35
            bg.paste(wifi_qr, ((width - qr_size) // 2, y))
            y += qr_size + spacing

        elif loyalty_qr:
            draw.text(((width - 100) // 2, y), "Loyalty", font=font, fill="white")
            y += 35
            bg.paste(loyalty_qr, ((width - qr_size) // 2, y))
            y += qr_size + spacing

        y = draw_text("Step 2", y, spacing=10)
        y = draw_text("Scan for Menu", y, spacing=20)
    else:
        label_h = get_text_height("Scan for Menu", font)
        total_qr_height = label_h + 200 + 20
        y = (height - total_qr_height) // 2
        y = draw_text("Scan for Menu", y, spacing=20)

    bg.paste(menu_qr, ((width - 200) // 2, y))
    return bg

# ---- Generate / Download ----
col_generate, col_download = st.columns([1, 1])
generate_clicked = col_generate.button("Generate")

if generate_clicked:
    # --- URL-only download mode ---
    if download_url_only:
        # 1. Generate list of URLs
        url_list = [
            f"https://tags.oolio.io/{uuid.uuid4()}"
            for _ in range(table_count)
        ]

        # 2. Write CSV to BytesIO using TextIOWrapper
        csv_bytes = BytesIO()
        text_buf = io.TextIOWrapper(csv_bytes, encoding='utf-8', newline='')
        writer = csv.writer(text_buf)
        writer.writerow(["Table", "Menu URL"])
        for idx, url in enumerate(url_list, start=1):
            writer.writerow([f"{table_prefix} {idx}", url])

        text_buf.flush()
        csv_bytes.seek(0)

        # 3. Provide CSV download
        col_download.download_button(
            label="Download URLs CSV",
            data=csv_bytes,
            file_name="table_menu_urls.csv",
            mime="text/csv"
        )
        st.success("✅ CSV generated successfully!")
    else:
        # --- Original PDF mode ---
        pdf_buf = BytesIO()
        merger = PdfMerger()

        # Download and load fonts
        font_bytes = download_google_font(font_choice)
        font_stream1 = BytesIO(font_bytes)
        font_stream2 = BytesIO(font_bytes)
        font = ImageFont.truetype(font_stream1, 28)
        font_title = ImageFont.truetype(font_stream2, 36)

        st.success("✅ PDF generated successfully!")
        st.error("⚠️ For each menu QR - Activate them first follow the guide below!!!")
        st.info("📘 [How to activate QR codes in Oolio]"
                "(https://help.oolio.com/tags-set-up-qr-codes-for-your-tables-oolio-help-center)")
        st.markdown(f"### Preview - {table_prefix} 1")
        preview_placeholder = st.empty()

        # Generate and merge each table page into PDF
        for table_number in range(1, table_count + 1):
            wifi = generate_basic_qr(wifi_data) if include_wifi else None
            loyalty = generate_basic_qr(loyalty_url) if include_loyalty else None
            menu_url = f"https://tags.oolio.io/{uuid.uuid4()}"
            menu_qr = generate_menu_qr_with_logo(
                menu_url,
                "https://ooliovideoshb.s3.ap-southeast-2.amazonaws.com/"
                "OPOS+-+Back+Office/Oolio_Logo-removebg.png",
                200
            )
            page = draw_centered_page(
                table_number, wifi, loyalty, menu_qr,
                font, table_prefix, font_title
            )

            if table_number == 1:
                img_buf = BytesIO()
                page.save(img_buf, format="PNG")
                img_buf.seek(0)
                with preview_placeholder:
                    st.image(img_buf, use_container_width=True)

            pdf_single = BytesIO()
            page.save(pdf_single, format="PDF")
            pdf_single.seek(0)
            merger.append(pdf_single)

        merger.write(pdf_buf)
        pdf_buf.seek(0)

        col_download.download_button(
            label="Download PDF",
            data=pdf_buf,
            file_name="All_Tables_Menu.pdf",
            mime="application/pdf"
        )