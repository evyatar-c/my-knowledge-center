import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- 1. הגדרות דף, ניהול מצבים ועיצוב מתקדם ---
st.set_page_config(page_title="מרכז ידע הנדסי | Senior", layout="wide", page_icon="⚙️")

# אתחול Session State לניהול ניווט בדפים
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
if 'selected_main_category' not in st.session_state:
    st.session_state.selected_main_category = None
if 'selected_sub_category' not in st.session_state:
    st.session_state.selected_sub_category = "ללא"

def navigate_to_summary(main_cat, sub_cat="ללא"):
    st.session_state.selected_main_category = main_cat
    st.session_state.selected_sub_category = sub_cat
    st.session_state.current_page = 'summary'

def navigate_to_home():
    st.session_state.current_page = 'home'

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
    }
    
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }

    /* עיצוב כותרת ראשית */
    .hero-section {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 16px;
        padding: 3rem 2rem;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.1);
    }
    .hero-section h1 {
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        background: -webkit-linear-gradient(45deg, #ffffff, #a8c0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-section p {
        font-size: 1.3rem;
        color: #e2e8f0;
    }

    /* עיצוב כרטיסיות דף הבית */
    div[data-testid="column"] button {
        background: rgba(30, 41, 59, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        height: 120px !important;
        width: 100% !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        color: #64b5f6 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    div[data-testid="column"] button:hover {
        background: rgba(41, 59, 85, 0.9) !important;
        border-color: #64b5f6 !important;
        transform: translateY(-5px) !important;
        box-shadow: 0 10px 20px rgba(100, 181, 246, 0.2) !important;
    }

    /* כפתור חזרה לדף הבית */
    .back-btn {
        margin-bottom: 2rem;
    }

    /* עיצוב כרטיסיית התשובה */
    .stContainer {
        background: rgba(15, 23, 42, 0.6) !important;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.05) !important;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }

    /* יישור לימין RTL */
    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label, .stSelectbox, .stTextInput {
        direction: rtl !important;
        text-align: right !important;
    }
    .stMarkdown p, .stMarkdown li {
        direction: rtl !important;
        text-align: right !important;
        font-size: 1.15rem;
        line-height: 1.8;
    }
    .stMarkdown ul, .stMarkdown ol {
        direction: rtl !important;
        padding-right: 2.5rem !important;
        padding-left: 0 !important;
    }
    div[data-baseweb="select"] > div, div[data-baseweb="popover"], ul[role="listbox"], li[role="option"] {
        direction: rtl !important;
        text-align: right !important;
    }
    [data-testid="collapsedControl"] { display: none !important; }

    /* הגנה על נוסחאות LaTeX */
    .katex, .katex-display, .katex * {
        direction: ltr !important;
        unicode-bidi: isolate !important;
        color: #4facfe; 
    }
    .katex-display {
        text-align: center !important;
        margin: 2rem auto !important;
        background: rgba(0,0,0,0.3);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(79, 172, 254, 0.2);
    }
    span.katex { display: inline-block; direction: ltr !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות AI, משיכת מידע ו-RAG (ללא שינוי לוגי, הוסתר לשמירה על נקיון) ---

if "GOOGLE_API_KEY" in st.secrets: genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else: st.error("🚨 חסר API Key"); st.stop()

@st.cache_resource
def get_available_models():
    try:
        models = {}
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini-3' in m.name.lower():
                clean_name = m.name.split('models/')[1]
                if 'pro' in clean_name: models[f"🧠 {clean_name} (מעמיק)"] = m.name
                elif 'think' in clean_name: models[f"🤔 {clean_name} (הסקה)"] = m.name
                elif 'flash' in clean_name: models[f"⚡ {clean_name} (מהיר)"] = m.name
                else: models[clean_name] = m.name
        return models
    except: return {}

@st.cache_data(show_spinner=False)
def get_all_content():
    text = ""
    # PDF
    if os.path.exists("pdfs"):
        for filename in [f for f in os.listdir("pdfs") if f.endswith(".pdf")]:
            try:
                with open(os.path.join("pdfs", filename), 'rb') as f:
                    for page in PyPDF2.PdfReader(f).pages: text += (page.extract_text() or "") + "\n"
            except: continue
    # Links
    if os.path.exists('links.txt'):
        with open('links.txt', 'r', encoding='utf-8') as f:
            for link in [l.strip() for l in f.readlines() if l.strip()]:
                try:
                    if "youtube" in link or "youtu.be" in link:
                        vid = link.split("v=")[1].split("&")[0] if "v=" in link else link.split("/")[-1]
                        text += " ".join([t['text'] for t in YouTubeTranscriptApi.get_transcript(vid, languages=['he', 'en'])]) + "\n"
                    else:
                        soup = BeautifulSoup(requests.get(link, timeout=10).text, 'html.parser')
                        for s in soup(["script", "style"]): s.decompose()
                        text += soup.get_text() + "\n"
                except: continue
    return text

def retrieve_top_chunks(query, text, chunk_size=1500, overlap=300, top_k=20):
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size-overlap)]
    if not chunks: return ""
    if len(chunks) <= top_k: return "\n...\n".join(chunks)
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(chunks + [query])
    top_indices = sorted(cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten().argsort()[-top_k:][::-1])
    return "\n...\n".join([chunks[i] for i in top_indices])

# --- 3. מיפוי נתונים (סילבוס) ---
categories_data = {
    "איפיון דרישות, אימות ותיקוף (V&V)": ["איפיון דרישות: הבחנה בין PRD ל-TRD", "מודל ה-V", "שיטות אימות (Verification)", "תיקוף (Validation)"],
    "שלבי פיתוח מוצר ובדיקות הוכחה": ["מחזור חיי פיתוח: PDR, CDR, NPI", "בדיקות קבלה (ATP)", "בדיקות הסמכה (QTP)", "סינון סביבתי (ESS)"],
    "ניהול סיכונים הנדסי": ["צמצום סיכונים (POD)", "טבלת ניהול סיכונים", "ניתוח FMEA"],
    "טכנולוגיות ייצור": ["עיבוד שבבי ו-DFM", "יציקות מתכת", "הדפסות תלת-ממד", "הזרקות פלסטיק"],
    "סובלנויות ו-GD&T": ["בקרות גיאומטריות", "Worst Case מול RSS", "התאמות (Fits)"],
    "קורוזיה, ציפויים וטיפולי שטח": ["קורוזיה גלוונית", "שיקולים בבחירת ציפויים", "מניעת היתפסות (Galling)"],
    "תכן לאטימות (IP & EMI)": ["רמות IP", "תכן אטמים וחישובי דחיסה", "אטימות אלקטרומגנטית (EMI)"],
    "שיקולי תכן תרמי": ["מנגנוני מעבר חום", "משוואות חום ושרשרת נגדים", "טמפ' צומת ו-Heat Sinks"],
    "תכן פלסטיק וחומרים": ["תכן להזרקה", "פולימרים הנדסיים"],
    "תכן כרטיסים אלקטרוניים (PCB)": ["מגבלות עריכה", "גמיש קשיח", "ציפויים קונפורמיים"],
    "היבטי עלות וניהול פרויקט": ["Design to Cost", "BTP מול BTS", "רכיבי מדף (COTS)"],
    "אנליזות וחישובים הנדסיים": ["Von Mises", "מאמצים בבורג", "רעידות", "תרמו-מכניות"],
    "תכן להרכבתיות (DFA/DFS)": ["תכן להרכבתיות", "תחזוקתיות (MTTR)"]
}
available_models = get_available_models()

# --- 4. תפריט צד קבוע ---
with st.sidebar:
    st.header("🎛️ חדר בקרה")
    if not available_models: st.error("🚨 שגיאת API"); st.stop()
    selected_model_display = st.selectbox("מנוע עיבוד AI:", list(available_models.keys()))
    working_model = available_models[selected_model_display]
    st.divider()
    
    # חיפוש חופשי / יזום מהתפריט
    st.subheader("חיפוש ממוקד")
    side_category = st.selectbox("ספריית ידע:", list(categories_data.keys()), key="side_main")
    side_sub = st.selectbox("תת-נושא:", ["ללא"] + categories_data[side_category], key="side_sub")
    focus_text = st.text_input("מיקוד ספציפי (אופציונלי):", placeholder="הזן דגשים...")
    
    if st.button("🚀 הפק סיכום (מתפריט)", type="primary", use_container_width=True):
        st.session_state.focus_text = focus_text
        navigate_to_summary(side_category, side_sub)

# --- 5. מנתב דפים (Router) ---

# ================= דף הבית =================
if st.session_state.current_page == 'home':
    st.markdown("""
        <div class="hero-section">
            <h1>מרכז ידע הנדסי - Senior</h1>
            <p>בחר נושא להתחלת למידה והעמקה מקצועית לקראת הראיון</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📌 נושאי ליבה (Quick Access)")
    
    # יצירת גריד של כרטיסיות (3 עמודות)
    cols = st.columns(3)
    
    # כרטיסיות מותאמות אישית
    with cols[0]:
        if st.button("🌡️ תכן תרמי ומעבר חום", use_container_width=True): navigate_to_summary("שיקולי תכן תרמי")
        if st.button("📐 סובלנויות ו-GD&T", use_container_width=True): navigate_to_summary("סובלנויות ו-GD&T")
    with cols[1]:
        if st.button("💧 אטימות IP ו-EMI", use_container_width=True): navigate_to_summary("תכן לאטימות (IP & EMI)")
        if st.button("💥 אנליזות וחוזק", use_container_width=True): navigate_to_summary("אנליזות וחישובים הנדסיים")
    with cols[2]:
        if st.button("🛡️ קורוזיה וטיפולי שטח", use_container_width=True): navigate_to_summary("קורוזיה, ציפויים וטיפולי שטח")
        if st.button("📝 איפיון דרישות V&V", use_container_width=True): navigate_to_summary("איפיון דרישות, אימות ותיקוף (V&V)")


# ================= דף סיכום =================
elif st.session_state.current_page == 'summary':
    if st.button("← חזור לדף הבית", key="back_btn"):
        navigate_to_home()
        st.rerun()

    main_cat = st.session_state.selected_main_category
    sub_cat = st.session_state.selected_sub_category
    focus = st.session_state.get('focus_text', "")

    with st.spinner(f"המודל מנתח מקורות ומפיק תובנות מתקדמות..."):
        raw_content = get_all_content()
        if raw_content.strip():
            try:
                search_query = f"{main_cat} {sub_cat if sub_cat != 'ללא' else ''} {focus}".strip()
                relevant_content = retrieve_top_chunks(search_query, raw_content)
                
                # העשרת הפרומפט להוספת מדיה, נושאים קשורים והדמיות
                task_instruction = f"הנושא: {main_cat}. "
                if sub_cat != "ללא": task_instruction += f"התמקדות ב: {sub_cat}. "
                if focus: task_instruction += f"דגש מיוחד: {focus}. "
                
                prompt = f"""
                אתה מהנדס מכונות בכיר. ספק סיכום לימודי עמוק וארוך על בסיס המקורות המצורפים.
                {task_instruction}
                
                מבנה חובה לתשובה:
                1. **גוף הסיכום (הסבר הנדסי ולוגיקה):** פרט לעומק בעזרת כותרות.
                2. **הדמיה ויזואלית (חשוב!):** שלב בתוך הטקסט טבלאות השוואה הנדסיות, או תרשימי זרימה בפורמט טקסטואלי שממחישים את הקונספט.
                3. **נוסחאות:** כתוב ב-LaTeX סטנדרטי (Left-to-Right). $ למשוואה בשורה, $$ לשורה נפרדת.
                
                בסוף הסיכום, חובה להוסיף את שני הבלוקים הבאים בדיוק תחת הכותרות הללו:
                
                ---
                ### 🎥 מקורות והדמיות מומלצים להעמקה
                * ספק 2-3 מילות מפתח ממוקדות באנגלית לחיפוש ב-YouTube (לדוגמה: "O-ring squeeze simulation").
                * ציין איזה סוג של סרטון או סימולציה כדאי לחפש כדי להבין את הנושא ויזואלית.
                
                ### 🔄 נושאים קשורים שכדאי ללמוד
                * מתוך עולם התכן המכני, הצע 3 תתי-נושאים שמשיקים ישירות לנושא שסוכם ושיש להם סבירות גבוהה לעלות בראיון המשך.
                
                המקורות לביסוס הסיכום:
                ---
                {relevant_content}
                ---
                כתוב בעברית ברמה מקצועית.
                """
                
                model = genai.GenerativeModel(working_model, generation_config=genai.types.GenerationConfig(max_output_tokens=8192, temperature=0.3))
                response = model.generate_content(prompt)
                
                display_title = f"📚 {main_cat}"
                if sub_cat != "ללא": display_title += f" | {sub_cat.split(':')[0]}"
                
                with st.container(border=True):
                    st.subheader(display_title)
                    st.markdown(response.text)
                    
            except Exception as e:
                st.error(f"שגיאת עיבוד: {e}")
        else:
            st.warning("המאגר ריק. וודא העלאת קבצים.")
