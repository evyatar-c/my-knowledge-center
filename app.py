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

# --- 1. הגדרות דף, ניהול מצבים ועיצוב נקי ובהיר (Light Theme) ---
st.set_page_config(page_title="מרכז ידע הנדסי | Senior", layout="wide", page_icon="⚙️")

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
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif;
    }
    
    .stApp {
        background-color: #f4f7f6;
        color: #1e293b;
    }

    .hero-section {
        background: linear-gradient(135deg, #0f4c75 0%, #3282b8 100%);
        border-radius: 16px;
        padding: 3rem 2rem;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    .hero-section h1 {
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #ffffff !important;
    }
    .hero-section p {
        font-size: 1.3rem;
        color: #bbe1fa !important;
    }

    div[data-testid="column"] button {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        height: 100px !important;
        width: 100% !important;
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        color: #1e293b !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        margin-bottom: 10px !important;
    }
    div[data-testid="column"] button:hover {
        background: #f8fafc !important;
        border-color: #3282b8 !important;
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 15px rgba(50, 130, 184, 0.15) !important;
        color: #0f4c75 !important;
    }

    .stContainer {
        background: #ffffff !important;
        border-radius: 16px;
        border: 1px solid #cbd5e1 !important;
        padding: 2.5rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-left: 1px solid #e2e8f0;
    }

    .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, label, .stTextInput {
        direction: rtl !important;
        text-align: right !important;
        color: #0f172a !important;
    }
    
    .stMarkdown p, .stMarkdown li {
        direction: rtl !important;
        text-align: right !important;
        font-size: 1.15rem;
        line-height: 1.8;
        color: #334155 !important;
    }
    .stMarkdown ul, .stMarkdown ol {
        direction: rtl !important;
        padding-right: 2.5rem !important;
        padding-left: 0 !important;
    }
    
    /* === תיקון מסגרות ועיצוב לרשימות הנפתחות === */
    div[data-baseweb="select"] > div {
        border: 1px solid #cbd5e1 !important; /* החזרת המסגרת */
        border-radius: 6px !important;
        background-color: #ffffff !important;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: #3282b8 !important;
    }
    div[data-baseweb="popover"], ul[role="listbox"], li[role="option"] {
        direction: rtl !important;
        text-align: right !important;
        color: #0f172a !important;
        background-color: #ffffff !important;
    }
    
    [data-testid="collapsedControl"] { display: none !important; }

    .katex, .katex-display, .katex * {
        direction: ltr !important;
        unicode-bidi: isolate !important;
        color: #00509e !important; 
    }
    .katex-display {
        text-align: center !important;
        margin: 2rem auto !important;
        background: #f1f5f9; 
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #cbd5e1;
    }
    span.katex { display: inline-block; direction: ltr !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות AI, משיכת מידע ו-RAG ---

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
    if os.path.exists("pdfs"):
        for filename in [f for f in os.listdir("pdfs") if f.endswith(".pdf")]:
            try:
                with open(os.path.join("pdfs", filename), 'rb') as f:
                    for page in PyPDF2.PdfReader(f).pages: text += (page.extract_text() or "") + "\n"
            except: continue
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
    "תכן להרכבתיות ואמינות (DFA/DFS)": ["תכן להרכבתיות", "תחזוקתיות (MTTR)"]
}
available_models = get_available_models()

# --- 4. תפריט צד קבוע ---
with st.sidebar:
    st.header("🎛️ חדר בקרה")
    if not available_models: st.error("🚨 שגיאת API"); st.stop()
    selected_model_display = st.selectbox("מנוע עיבוד AI:", list(available_models.keys()))
    working_model = available_models[selected_model_display]
    st.divider()
    
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
    
    st.subheader("📌 12 נושאי ליבה (Quick Access)")
    
    cols = st.columns(3)
    with cols[0]:
        if st.button("🌡️ תכן תרמי ומעבר חום", use_container_width=True): navigate_to_summary("שיקולי תכן תרמי")
        if st.button("📐 סובלנויות ו-GD&T", use_container_width=True): navigate_to_summary("סובלנויות ו-GD&T")
        if st.button("🚀 שלבי פיתוח (PDR/CDR)", use_container_width=True): navigate_to_summary("שלבי פיתוח מוצר ובדיקות הוכחה")
        if st.button("⚙️ טכנולוגיות ייצור", use_container_width=True): navigate_to_summary("טכנולוגיות ייצור")
    with cols[1]:
        if st.button("💧 אטימות IP ו-EMI", use_container_width=True): navigate_to_summary("תכן לאטימות (IP & EMI)")
        if st.button("💥 אנליזות וחוזק", use_container_width=True): navigate_to_summary("אנליזות וחישובים הנדסיים")
        if st.button("⚠️ ניהול סיכונים ו-FMEA", use_container_width=True): navigate_to_summary("ניהול סיכונים הנדסי")
        if st.button("🔌 תכן כרטיסים (PCB)", use_container_width=True): navigate_to_summary("תכן כרטיסים אלקטרוניים (PCB)")
    with cols[2]:
        if st.button("🛡️ קורוזיה וטיפולי שטח", use_container_width=True): navigate_to_summary("קורוזיה, ציפויים וטיפולי שטח")
        if st.button("📝 איפיון דרישות V&V", use_container_width=True): navigate_to_summary("איפיון דרישות, אימות ותיקוף (V&V)")
        if st.button("🧪 תכן פלסטיק וחומרים", use_container_width=True): navigate_to_summary("תכן פלסטיק וחומרים")
        if st.button("💰 היבטי עלות וניהול", use_container_width=True): navigate_to_summary("היבטי עלות וניהול פרויקט")


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
                
                task_instruction = f"הנושא: {main_cat}. "
                if sub_cat != "ללא": task_instruction += f"התמקדות ב: {sub_cat}. "
                if focus: task_instruction += f"דגש מיוחד: {focus}. "
                
                prompt = f"""
                אתה מהנדס מכונות בכיר. ספק סיכום לימודי עמוק וארוך על בסיס המקורות המצורפים.
                {task_instruction}
                
                מבנה חובה לתשובה:
                1. **גוף הסיכום (הסבר הנדסי ולוגיקה):** פרט לעומק בעזרת כותרות.
                2. **הדמיה ויזואלית טקסטואלית:** שלב בתוך הטקסט טבלאות השוואה הנדסיות ותרשימי זרימה בטקסט (ASCII Art) כדי להמחיש את המידע.
                3. **נוסחאות (קריטי):** כל מתמטיקה חייבת להיכתב ב-LaTeX סטנדרטי בלבד, משמאל לימין. 
                   השתמש ב- $ עבור משוואה בתוך השורה, וב- $$ למשוואה ממורכזת בשורה נפרדת.
                
                בסוף הסיכום, חובה להוסיף את שני הבלוקים הבאים בדיוק תחת הכותרות הללו:
                
                ---
                ### 🎥 מקורות והדמיות מומלצים להעמקה
                * ספק 2-3 מילות מפתח ממוקדות באנגלית לחיפוש ב-YouTube.
                * ציין איזה סוג של סרטון כדאי לחפש כדי להבין את הנושא ויזואלית (למשל: "חפש סימולציית FEA של מאמצי Von Mises").
                
                ### 🔄 נושאים קשורים שכדאי ללמוד
                * מתוך עולם התכן המכני, הצע 3 תתי-נושאים שמשיקים ישירות לנושא שסוכם ושיש להם סבירות גבוהה לעלות בראיון המשך.
                
                המקורות לביסוס הסיכום:
                ---
                {relevant_content}
                ---
                כתוב בעברית ברמה מקצועית. אל תמציא מידע שאינו במקורות.
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
