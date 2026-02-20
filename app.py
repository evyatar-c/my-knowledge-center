import streamlit as st
import json
import os

# הגדרות עיצוב - כותרת ויישור לימין
st.set_page_config(page_title="מרכז ידע הנדסי - אביתר", layout="wide")

# הזרקת קוד עיצוב ליישור לימין (RTL)
st.markdown("""
    <style>
    /* יישור גוף האפליקציה */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        direction: RTL;
        text-align: right;
    }
    /* יישור תפריט הצד */
    [data-testid="stSidebar"] {
        direction: RTL;
        text-align: right;
    }
    /* תיקון כיוון לסימני פיסוק ורשימות */
    p, li, h1, h2, h3, h4, h5, h6 {
        direction: RTL;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)

def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

st.title("📚 מרכז ידע הנדסת מכונות")

data = load_data()

if data:
    st.sidebar.header("ניווט")
    category = st.sidebar.selectbox("בחר קטגוריה", list(data.keys()))
    topic = st.sidebar.selectbox("בחר נושא", list(data[category].keys()))

    st.header(f"נושא: {topic}")
    st.divider()
    st.markdown(data[category][topic])
else:
    st.warning("קובץ הנתונים (data.json) לא נמצא.")
