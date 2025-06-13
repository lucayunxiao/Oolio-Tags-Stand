# app.py
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import qrcode
import uuid
from io import BytesIO
import requests

st.set_page_config(page_title="Table QR Generator", layout="centered")
st.title("🍽️ Table QR Code Generator")

# ---- Inputs ----
col1, col2 = st.columns(2)

with col1:
    table_count = st.number_input("Number of Tables", 1, 100, 1)
    include_wifi = st.checkbox("Include WiFi QR")
    if include_wifi:
        ssid = st.text_input("WiFi SSID", value="My_Wifi")
        password = st.text_input("WiFi Password", value="My_Wifi_Password")
        encryption = st.selectbox("Encryption Type", ["WPA", "WEP"])
        wifi_data = f"WIFI:T:{encryption};S:{ssid};P:{password};;"

with col2:
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

def get_text_height(text, font):
    bbox = font.getbbox(text)
    return bbox[3] - bbox[1]

def draw_centered_page(table_number, wifi_qr, loyalty_qr, menu_qr):
    width, height = 600, 800
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)

    def draw_text(text, y):
        w = draw.textbbox((0, 0), text, font=font)[2]
        draw.text(((width - w) // 2, y), text, font=font, fill="black")
        return y + get_text_height(text, font) + 10

    y = 30
    y = draw_text(f"Table {table_number}", y)

    if wifi_qr or loyalty_qr:
        y = draw_text("Step 1", y)
        if wifi_qr and loyalty_qr:
            img.paste(wifi_qr, (100, y))
            img.paste(loyalty_qr, (300, y))
            y += 210
            draw.text((130, y), "WiFi", font=font, fill="black")
            draw.text((330, y), "Loyalty", font=font, fill="black")
            y += 40
        elif wifi_qr:
            img.paste(wifi_qr, (200, y))
            y += 210
            y = draw_text("WiFi", y)
        elif loyalty_qr:
            img.paste(loyalty_qr, (200, y))
            y += 210
            y = draw_text("Loyalty", y)
        y = draw_text("Step 2", y)

    y = draw_text("Scan for Menu", y)
    img.paste(menu_qr, (200, y))
    return img

# ---- Generate ----
if st.button("Generate PDF"):
    pdf_buf = BytesIO()
    from PyPDF2 import PdfMerger
    import os

    merger = PdfMerger()
    temp_files = []

    for table_number in range(1, table_count + 1):
        wifi = generate_basic_qr(wifi_data) if include_wifi else None
        loyalty = generate_basic_qr(loyalty_url) if include_loyalty else None
        menu_url = f"https://tags.oolio.io/{uuid.uuid4()}"
        menu_qr = generate_menu_qr_with_logo(menu_url, "https://ooliovideoshb.s3.ap-southeast-2.amazonaws.com/OPOS+-+Back+Office/Oolio_Logo-removebg.png", 200)
        page = draw_centered_page(table_number, wifi, loyalty, menu_qr)

        img_buf = BytesIO()
        page.save(img_buf, format="PNG")
        img_buf.seek(0)

        if table_number == 1:
            st.image(img_buf, caption=f"Preview: Table {table_number}", use_column_width=True)

        pdf_buf_single = BytesIO()
        page.save(pdf_buf_single, format="PDF")
        pdf_buf_single.seek(0)
        temp_files.append(pdf_buf_single)
        merger.append(pdf_buf_single)


    merger.write(pdf_buf)
    pdf_buf.seek(0)

    st.success("PDF generated successfully!")
    st.download_button("Download PDF", pdf_buf, file_name="All_Tables_Menu.pdf", mime="application/pdf")
