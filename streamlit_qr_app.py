# app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import qrcode
import uuid
from io import BytesIO
import requests
import os
from PyPDF2 import PdfMerger

st.set_page_config(page_title="Table QR Generator", layout="centered")
st.title("🍽️ Table QR Code Generator")

# ---- Inputs ----
col1, col2 = st.columns(2)

with col1:
    table_count = st.number_input("Number of Tables", 1, 100, 1)

with col2:
    font_choice = st.selectbox("Font", ["DejaVuSans-Bold", "Arial", "LiberationSans-Regular"])

    include_wifi = st.checkbox("Include WiFi QR")
    if include_wifi:
        ssid = st.text_input("WiFi SSID", value="My_Wifi")
        password = st.text_input("WiFi Password", value="My_Wifi_Password")
        encryption = st.selectbox("Encryption Type", ["WPA", "WEP"])
        wifi_data = f"WIFI:T:{encryption};S:{ssid};P:{password};;"

    include_loyalty = st.checkbox("Include Loyalty QR")
    if include_loyalty:
        loyalty_url = st.text_input("Loyalty URL", value="https://rewards.oolio.io/store")

# ---- QR Code generators ----
def generate_basic_qr(data, fill="#000000", back="#ffffff", size=200):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill, back_color=back).convert("RGB")
    return img.resize((size, size))

def generate_menu_qr_with_logo(data, logo_url, size=300):
    qr_img = generate_basic_qr(data, fill="white", back="#4080e8", size=size)
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

def get_font_path(name):
    if "arial" in name.lower():
        return "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    elif "liberation" in name.lower():
        return "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    else:
        return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def draw_centered_page(table_number, wifi_qr, loyalty_qr, menu_qr, font_path):
    width, height = 600, 800
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, 28)

    def draw_text(text, y):
        w = draw.textbbox((0, 0), text, font=font)[2]
        draw.text(((width - w) // 2, y), text, font=font, fill="black")
        return y + get_text_height(text, font) + 10

    y = 30
    y = draw_text(f"Table {table_number}", y)

    if wifi_qr or loyalty_qr:
        y = draw_text("Step 1", y)
        qr_size = 200
        spacing = 30

        if wifi_qr and loyalty_qr:
            draw.text((120, y), "WiFi", font=font, fill="black")
            draw.text((340, y), "Loyalty", font=font, fill="black")
            y += 35
            img.paste(wifi_qr, (100, y))
            img.paste(loyalty_qr, (300, y))
            y += qr_size + spacing
        elif wifi_qr:
            draw.text(((width - 60) // 2, y), "WiFi", font=font, fill="black")
            y += 35
            img.paste(wifi_qr, ((width - qr_size) // 2, y))
            y += qr_size + spacing
        elif loyalty_qr:
            draw.text(((width - 100) // 2, y), "Loyalty", font=font, fill="black")
            y += 35
            img.paste(loyalty_qr, ((width - qr_size) // 2, y))
            y += qr_size + spacing

        y = draw_text("Step 2", y)

    y = draw_text("Scan for Menu", y)
    img.paste(menu_qr, ((width - 200) // 2, y))
    return img

def get_text_height(text, font):
    bbox = font.getbbox(text)
    return bbox[3] - bbox[1]

# ---- UI Buttons Side-by-Side ----
col_generate, col_download = st.columns([1, 1])
generate_clicked = col_generate.button("Generate PDF")

if generate_clicked:
    pdf_buf = BytesIO()
    merger = PdfMerger()
    temp_files = []
    selected_font_path = get_font_path(font_choice)

    for table_number in range(1, table_count + 1):
        wifi = generate_basic_qr(wifi_data) if include_wifi else None
        loyalty = generate_basic_qr(loyalty_url) if include_loyalty else None
        menu_url = f"https://tags.oolio.io/{uuid.uuid4()}"
        menu_qr = generate_menu_qr_with_logo(menu_url, "https://ooliovideoshb.s3.ap-southeast-2.amazonaws.com/OPOS+-+Back+Office/Oolio_Logo-removebg.png", 200)
        page = draw_centered_page(table_number, wifi, loyalty, menu_qr, selected_font_path)

        if table_number == 1:
            img_buf = BytesIO()
            page.save(img_buf, format="PNG")
            img_buf.seek(0)
            st.image(img_buf, caption=f"Preview: Table {table_number}", use_container_width=True)

        pdf_buf_single = BytesIO()
        page.save(pdf_buf_single, format="PDF")
        pdf_buf_single.seek(0)
        temp_files.append(pdf_buf_single)
        merger.append(pdf_buf_single)

    merger.write(pdf_buf)
    pdf_buf.seek(0)

    st.success("✅ PDF generated successfully!")
    with col_download:
        st.download_button("Download PDF", pdf_buf, file_name="All_Tables_Menu.pdf", mime="application/pdf")