import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# --- 1. הגדרות עיצוב ויישור לימין (RTL) ---
st.set_page_config(page_title="מרכז ידע הנדסי - אביתר", layout="wide")

st.markdown("""
    <style>
    /* יישור כללי לימין */
    [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: RTL;
        text-align: right;
    }
    /* יישור טקסט, כותרות ורשימות */
    p, li, h1, h2, h3, h4, h5, h6, label, span {
        direction: RTL;
        text-align: right;
    }
    /* תיקון כיוון לתיבות בחירה */
    .stSelectbox div[data-baseweb="select"] {
        direction: RTL;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. פונקציות עזר למערכת ---

def setup_genai():
    """חיבור ל-API של גוגל דרך ה-Secrets"""
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return True
    return False

def get_gemini3_model():
    """איתור ובחירה של מודל Gemini 3 בלבד"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # סינון למודלים ממשפחת Gemini 3
        gemini3_list = [m for m in available_models if 'gemini-3' in m]
        
        # סדר עדיפויות בתוך הדור השלישי
        for preferred in ['models/gemini-3-pro', 'models/gemini-3-flash']:
            if preferred in gemini3_list:
                return preferred
        return gemini3_list[0] if gemini3_list else None
    except:
        return None

def get_pdf_text():
    """קריאת טקסט מכל ה-PDFs בתיקיית pdfs"""
    text = ""
    pdf_folder = "pdfs"
    if not os.path.exists(pdf_folder):
        os.makedirs(pdf_folder)
        return ""
    
    files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
    for filename in files:
        try:
            with open(os.path.join(pdf_folder, filename), 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    content = page.extract_text()
                    if content:
                        text += content + "\n"
        except:
            continue
    return text

# --- 3. ממשק המשתמש והלוגיקה ---

st.title("🤖 מרכז ידע הנדסי (מבוסס Gemini 3)")

if not setup_genai():
    st.error("🚨 שגיאה: API Key לא מוגדר ב-Secrets של Streamlit.")
    st.stop()

model_name = get_gemini3_model()
if not model_name:
    st.error("🚨 לא נמצא מודל Gemini 3 זמין עבור המפתח שלך.")
    st.stop()

# רשימת הקטגוריות המלאה מהסילבוס
categories = {
    "איפיון דרישות, אימות ותיקוף (V&V)": "סכם עקרונות איפיון דרישות (PRD/TRD), גזירת דרישות, מודל ה-V, ושיטות אימות (Verification) מול תיקוף (Validation).",
    "שלבי פיתוח מוצר ובדיקות": "סכם מחזור חיי פיתוח (PDR, CDR), תהליכי NPI, ובדיקות הוכחה כגון ATP, QTP ו-ESS.",
    "ניהול סיכונים הנדסי": "פרט על ניהול סיכונים טכניים, ביצוע דגמי היתכנות (POD), תוכניות הפחתה (Mitigation) וניתוח FMEA.",
    "טכנולוגיות ייצור": "סכם טכנולוגיות ייצור גורע (CNC, EDM), יציקות מתכת, וייצור מוסף כולל שיקולי DFM.",
    "סובלנויות ו-GD&T": "פרט על בקרות גיאומטריות,MMC/LMC, דאטומים, ניתוח צבירת טולרנסים (RSS/Worst Case) והתאמות.",
    "קורוזיה, ציפויים וטיפולי שטח": "סכם סוגי מתכות, מנגנוני קורוזיה, מניעת היתפסות, ושיקולים בבחירת ציפויים.",
    "תכן לאטימות (IP & EMI)": "פרט על תכן לאטימות סביבתית (IP), אטימות אלקטרומגנטית (EMI), תכן חריצים ואטמים.",
    "שיקולי תכן תרמי": "סכם מנגנוני העברת חום, ניהול תרמי במארזים, בחירת TIM וגופי קירור, וחישובי טמפרטורת צומת.",
    "תכן פלסטיק וחומרים מתקדמים": "פרט על תכן להזרקת פלסטיק (עובי דופן, זוויות חליצה), פגמי הזרקה, ופולימרים הנדסיים.",
    "תכן כרטיסים אלקטרוניים (PCB)": "סכם שיקולי תכן ומידול כרטיסים, מגבלות עריכה, קדחי דפינה, וגמיש-קשיח (Rigid-Flex).",
    "היבטי עלות וניהול פרויקט": "פרט על תהליכי Design to Cost (DTC), שימוש ב-COTS, ומבנה תוכנית עבודה (גאנט).",
    "אנליזות וחישובים הנדסיים": "סכם ביצוע אנליזות חוזק (Von Mises), אנליזות רעידות והלמים, וחישובים תרמו-מכניים.",
    "תכן להרכבתיות ואמינות (DFA/DFS)": "סכם שיטות לצמצום טעויות הרכבה, נגישות לכלי עבודה, ותכנון לתחזוקתיות (MTTR)."
}

# תפריט צד
st.sidebar.header("ניווט בנושאים")
category = st.sidebar.selectbox("בחר נושא לסיכום:", list(categories.keys()))
st.sidebar.info(f"מודל פעיל: {model_name}")

if st.sidebar.button("הפק סיכום מהמאגר"):
    with st.spinner(f"Gemini 3 מנתח את מסמכי המקור עבור {category}..."):
        all_content = get_pdf_text()
        
        if all_content.strip():
            try:
                model = genai.GenerativeModel(model_name)
                # Gemini 3 תומך בחלון קונטקסט גדול מאוד
                prompt = f"""
                אתה מהנדס מכונות בכיר ומומחה תוכן.
                התבסס אך ורק על המידע הבא מתוך מאגר ה-PDF המקצועי שלי:
                ---
                {all_content[:150000]}
                ---
                משימה: {categories[category]}
                כתוב סיכום הנדסי מקיף, מקצועי ומסודר בעברית. השתמש בכותרות, בולטים ומושגים טכניים.
                אם המידע לא מופיע במקורות, ציין זאת.
                """
                response = model.generate_content(prompt)
                st.header(category)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"שגיאה בתקשורת עם המודל: {e}")
        else:
            st.warning("לא נמצא טקסט בתיקיית pdfs. וודא שהעלית קבצי PDF ל-GitHub.")

st.sidebar.divider()
st.sidebar.caption("פותח עבור הכנה לראיונות Senior Mechanical Engineer")
