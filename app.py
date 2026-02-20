import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# הגדרות יישור לימין
st.set_page_config(page_title="מרכז ידע הנדסי חכם", layout="wide")
st.markdown("""<style>body, [data-testid="stSidebar"] { direction: RTL; text-align: right; }</style>""", unsafe_allow_html=True)

# חיבור לג'מיני (את ה-Key נגדיר ב-Streamlit Cloud)
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("חסר API Key! יש להגדיר אותו ב-Settings של Streamlit.")

# פונקציה לקריאת כל ה-PDF מהתיקייה
def get_pdf_text():
    text = ""
    pdf_folder = "pdfs"
    if os.path.exists(pdf_folder):
        for filename in os.listdir(pdf_folder):
            if filename.endswith(".pdf"):
                with open(os.path.join(pdf_folder, filename), 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text += page.extract_text()
    return text

st.title("🤖 מרכז ידע הנדסי מבוסס AI")

# הגדרת הקטגוריות הקבועות שלך
categories = {
    "זיווד אלקטרוני ואטימה": "סכם באופן מקיף את כל עקרונות האטימה, סוגי אטמים ותקני IP המופיעים במסמכים.",
    "ניהול תרמי ופיזור חום": "סכם את כל שיטות קירור המארזים, חומרי TIM וחישובי מעבר חום מהמקורות.",
    "כרטיסי RF ואנטנות": "רכז את כל המידע על תכן מכני לכרטיסי RF, סיכוך אלקטרומגנטי והתקנת אנטנות."
}

category = st.sidebar.selectbox("בחר קטגוריה לסיכום מקיף:", list(categories.keys()))

if st.sidebar.button("הפק סיכום מהמאגר"):
    with st.spinner("סורק את מסמכי ה-PDF ומפיק סיכום..."):
        all_content = get_pdf_text()
        if all_content:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"התבסס אך ורק על המידע הבא: {all_content}\n\n משימה: {categories[category]}"
            response = model.generate_content(prompt)
            
            st.header(category)
            st.markdown(response.text)
        else:
            st.warning("לא נמצאו קבצי PDF בתיקיית pdfs.")
