import streamlit as st
import json
import os

# הגדרות עיצוב - כותרת האתר
st.set_page_config(page_title="מרכז ידע הנדסי - אביתר", layout="wide")

# פונקציה לטעינת הנתונים
def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# הצגת הכותרת הראשית
st.title("📚 מרכז ידע הנדסת מכונות")
st.write("ברוך הבא למרכז הידע האישי שלך לזיווד אלקטרוני ותכן מכני.")

data = load_data()

if data:
    # יצירת תפריט צד לבחירה
    st.sidebar.header("ניווט")
    category = st.sidebar.selectbox("בחר קטגוריה", list(data.keys()))
    topic = st.sidebar.selectbox("בחר נושא", list(data[category].keys()))

    # הצגת התוכן שנבחר
    st.header(f"נושא: {topic}")
    st.divider()
    st.markdown(data[category][topic])
else:
    # הודעה למקרה שקובץ הנתונים עדיין לא קיים
    st.warning("קובץ הנתונים (data.json) עדיין לא נמצא. אנא צור אותו ב-GitHub והדבק לתוכו את המידע מ-NotebookLM.")
