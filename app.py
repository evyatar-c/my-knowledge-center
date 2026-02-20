import streamlit as st
import json
import os

# הגדרות עיצוב ויישור לימין
st.set_page_config(page_title="מרכז ידע הנדסי - אביתר", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: RTL;
        text-align: right;
    }
    p, li, h1, h2, h3, h4, h5, h6 {
        direction: RTL;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)

# פונקציה לטעינת ה-JSON הקבוע
def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

st.title("📚 מרכז ידע הנדסת מכונות")

# --- תפריט צד ---
st.sidebar.header("ניהול מקורות ידע")

# אפשרות 1: העלאת קובץ מקומי
uploaded_file = st.sidebar.file_uploader("העלה קובץ ידע חדש (PDF / TXT)", type=['pdf', 'txt'])

if uploaded_file is not None:
    st.sidebar.success(f"הקובץ '{uploaded_file.name}' נטען בהצלחה!")
    # כאן ניתן להוסיף בעתיד ניתוח של הקובץ בעזרת Gemini

st.sidebar.divider()

# אפשרות 2: ניווט במאגר הקיים (ה-JSON)
data = load_data()

if data:
    st.sidebar.header("ניווט במאגר")
    category = st.sidebar.selectbox("בחר קטגוריה", list(data.keys()))
    topic = st.sidebar.selectbox("בחר נושא", list(data[category].keys()))

    st.header(f"נושא: {topic}")
    st.divider()
    st.markdown(data[category][topic])
else:
    st.warning("קובץ הנתונים הקבוע (data.json) לא נמצא.")
