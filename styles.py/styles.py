import streamlit as st

def apply_agro_styles():
    st.markdown("""
    <style>
    /* Головний фон та шрифти */
    .stApp { background: #0e1117; color: #e0e0e0; }
    
    /* Професійні картки результатів */
    .report-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 20px;
        border-left: 5px solid #2ecc71;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    /* Адаптація під великий палець (Мобільна версія) */
    @media (max-width: 600px) {
        .stButton>button {
            width: 100% !important;
            height: 4.5rem !important;
            font-size: 1.2rem !important;
            background: linear-gradient(90deg, #2ecc71, #27ae60) !important;
            color: white !important;
            border: none !important;
        }
        .main-header { font-size: 1.8rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)