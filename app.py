import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import io

# --- 1. تصميم الصفحة ---
st.set_page_config(page_title="Study With Me", page_icon="🎓", layout="wide")

# كود CSS لتثبيت اللون الأبيض والأسود
custom_css = """
<style>
    /* خلفية التطبيق بيضاء */
    .stApp {
        background-color: #ffffff;
        color: #000000;
    }
    
    /* لون العناوين والنصوص أسود */
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
    }
    p, li, label, .stMarkdown, .stText, .stTextInput > label {
        color: #333333 !important;
    }
    
    /* تنسيق الأزرار */
    .stButton>button {
        background-color: #f0f2f6;
        color: #31333F;
        border-radius: 8px;
        border: 1px solid #d6d6d6;
    }
    .stButton>button:hover {
        background-color: #e0e2e6;
        border-color: #b0b0b0;
    }

    /* لون الروابط */
    a { color: #0066cc !important; text-decoration: none; }
    
    /* تنسيق الفوتر (الحقوق) */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f9f9f9;
        color: #555;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #ddd;
        z-index: 100;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 2. إدارة الذاكرة ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_images" not in st.session_state:
    st.session_state.pdf_images = None

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإ
