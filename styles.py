import streamlit as st

from i18n import render_language_picker, render_language_settings, tr

MENU_SECTIONS = [
    (
        "section_start",
        [
            {"path": "main.py", "label_key": "module_landing", "icon": "🌿"},
            {"path": "pages/01_Home.py", "label_key": "module_home", "icon": "🏠"},
            {"path": "pages/21_AI_Agro_Assistant.py", "label_key": "module_ai_assistant", "icon": "🤖"},
            {"path": "pages/22_Farm_Operations_Center.py", "label_key": "module_ops_center", "icon": "🧭"},
        ],
    ),
    (
        "section_monitoring",
        [
            {"path": "pages/02_NDVI_Auto.py", "label_key": "module_ndvi_pro", "icon": "🌿"},
            {"path": "pages/04_Zones_Field.py", "label_key": "module_vra_zones", "icon": "🧩"},
            {"path": "pages/16_NDVI_Trends_Alerts.py", "label_key": "module_ndvi_trends", "icon": "📉"},
            {"path": "pages/23_Yield_Map_Import.py", "label_key": "module_yield_import", "icon": "🌾"},
            {"path": "pages/05_Soil_SoilGrids.py", "label_key": "module_soilgrids", "icon": "🧱"},
            {"path": "pages/06_Soil_Map_Field.py", "label_key": "module_soil_map", "icon": "🗺️"},
            {"path": "pages/11_Weather.py", "label_key": "module_weather", "icon": "🌦️"},
        ],
    ),
    (
        "section_operations",
        [
            {"path": "pages/03_Field_Manager_Map.py", "label_key": "module_field_manager", "icon": "🗺️"},
            {"path": "pages/24_Field_Groups_Compare.py", "label_key": "module_field_groups", "icon": "🧭"},
            {"path": "pages/25_Tractor_Autosteer_Assist.py", "label_key": "module_autosteer", "icon": "🚜"},
            {"path": "pages/12_Planner_Journal.py", "label_key": "module_planner", "icon": "📒"},
            {"path": "pages/15_Alerts_Notifications.py", "label_key": "module_smart_alerts", "icon": "🔔"},
            {"path": "pages/14_Field_Timeline.py", "label_key": "module_timeline", "icon": "🗓️"},
            {"path": "pages/07_AI_Photo.py", "label_key": "module_photo_diag", "icon": "📷"},
            {"path": "pages/18_Nutrition_Recommendations.py", "label_key": "module_nutrition", "icon": "🌱"},
        ],
    ),
    (
        "section_analytics",
        [
            {"path": "pages/08_Yield_Prediction.py", "label_key": "module_yield_prediction", "icon": "📈"},
            {"path": "pages/17_Field_Economics.py", "label_key": "module_economics", "icon": "💹"},
            {"path": "pages/20_PDF_Reports.py", "label_key": "module_pdf_reports", "icon": "📄"},
            {"path": "pages/09_Calculators.py", "label_key": "module_calculators", "icon": "🧮"},
            {"path": "pages/10_Smart_Calculators.py", "label_key": "module_smart_calculators", "icon": "🧠"},
            {"path": "pages/13_Diagnostics.py", "label_key": "module_diagnostics", "icon": "🛠️"},
        ],
    ),
    (
        "section_admin",
        [
            {"path": "pages/26_Settings.py", "label_key": "module_settings", "icon": "⚙️"},
            {"path": "pages/19_Users_Access.py", "label_key": "module_users_access", "icon": "👤"},
        ],
    ),
]



def apply_styles(render_menu: bool = True):
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Manrope:wght@500;700;800&display=swap');

:root{
  --bg:#070A14;
  --panel: rgba(255,255,255,.06);
  --stroke: rgba(255,255,255,.10);
  --text:#EAF7F2;
  --muted: rgba(234,247,242,.65);
  --shadow: 0 16px 45px rgba(0,0,0,.40);
  --accent:#00FF88;
  --accent2:#00C3FF;
}

html, body, .stApp{
  background:
    radial-gradient(1100px 650px at 10% 10%, rgba(0,255,136,.14), transparent 55%),
    radial-gradient(1100px 650px at 90% 20%, rgba(0,195,255,.14), transparent 55%),
    linear-gradient(135deg,#050711 0%, #0B1020 40%, #0F1B3A 100%);
  color: var(--text);
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

.block-container{max-width:1400px; padding-top: 1.0rem; padding-bottom: 4.0rem;}
header[data-testid="stHeader"]{background:transparent;}
#MainMenu{visibility:hidden;}
footer{visibility:hidden;}

@keyframes topNavReveal{
  from { opacity: 0; transform: translateY(-14px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes dropMenu{
  from { opacity: 0; transform: translateY(-10px) scale(.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.top-nav-shell{
  position: sticky;
  top: .55rem;
  z-index: 900;
  margin: 0 0 10px 0;
  padding: 10px 12px 12px;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,.11);
  background:
    radial-gradient(700px 180px at 10% -10%, rgba(0,255,136,.14), transparent 75%),
    radial-gradient(700px 180px at 90% -10%, rgba(0,195,255,.14), transparent 75%),
    rgba(8,12,22,.82);
  box-shadow: 0 18px 50px rgba(0,0,0,.34);
  backdrop-filter: blur(10px);
  animation: topNavReveal .52s cubic-bezier(.22,.61,.36,1) both;
}
.top-nav-brand{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.top-nav-brand-logo{
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: Manrope, Inter, sans-serif;
  font-weight: 800;
  color: #03120f;
  background: linear-gradient(135deg, rgba(0,255,136,.95), rgba(0,195,255,.88));
  box-shadow: 0 10px 26px rgba(0,0,0,.28);
}
.top-nav-brand-title{
  font-family: Manrope, Inter, sans-serif;
  font-weight: 800;
  letter-spacing: .2px;
  color: var(--text);
  line-height: 1.05;
}
.top-nav-brand-sub{
  color: var(--muted);
  font-size: 12px;
  margin-top: 2px;
}

.top-nav-link a[data-testid="stPageLink-NavLink"],
.top-nav-cta a[data-testid="stPageLink-NavLink"]{
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 12px;
  min-height: 42px;
  padding: 7px 10px !important;
  margin-top: 2px;
  background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease, background .2s ease;
}
.top-nav-link a[data-testid="stPageLink-NavLink"]:hover{
  transform: translateY(-1px);
  border-color: rgba(0,255,136,.42);
  background: linear-gradient(90deg, rgba(0,255,136,.15), rgba(0,195,255,.11));
  box-shadow: 0 10px 24px rgba(0,0,0,.28);
}
.top-nav-cta a[data-testid="stPageLink-NavLink"]{
  border-color: rgba(0,255,136,.42);
  background: linear-gradient(90deg, rgba(0,255,136,.28), rgba(0,195,255,.20));
  box-shadow: 0 12px 28px rgba(0,0,0,.27);
}
.top-nav-link a[data-testid="stPageLink-NavLink"] p,
.top-nav-cta a[data-testid="stPageLink-NavLink"] p{
  color: var(--text);
  font-weight: 700;
  font-size: 13px;
}

.top-nav-pop [data-testid="stPopover"] > div > button{
  width: 100%;
  border: 1px solid rgba(255,255,255,.1);
  border-radius: 12px;
  min-height: 42px;
  background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
  color: var(--text);
  font-weight: 700;
  letter-spacing: .1px;
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease, background .2s ease;
}
.top-nav-pop [data-testid="stPopover"] > div > button:hover{
  transform: translateY(-1px);
  border-color: rgba(0,255,136,.42);
  background: linear-gradient(90deg, rgba(0,255,136,.15), rgba(0,195,255,.11));
  box-shadow: 0 10px 24px rgba(0,0,0,.28);
}

div[data-testid="stPopoverContent"]{
  border: 1px solid rgba(255,255,255,.12) !important;
  border-radius: 18px !important;
  background:
    radial-gradient(500px 140px at 10% 0%, rgba(0,255,136,.12), transparent 75%),
    radial-gradient(500px 140px at 90% 0%, rgba(0,195,255,.12), transparent 75%),
    rgba(8,12,22,.97) !important;
  backdrop-filter: blur(10px);
  box-shadow: 0 22px 45px rgba(0,0,0,.40) !important;
  animation: dropMenu .22s ease-out both;
}
div[data-testid="stPopoverContent"] a[data-testid="stPageLink-NavLink"]{
  border: 1px solid rgba(255,255,255,.09);
  border-radius: 11px;
  min-height: 36px;
  margin: 4px 0;
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
}
div[data-testid="stPopoverContent"] a[data-testid="stPageLink-NavLink"]:hover{
  border-color: rgba(0,255,136,.36);
  background: linear-gradient(90deg, rgba(0,255,136,.12), rgba(0,195,255,.09));
}
div[data-testid="stPopoverContent"] a[data-testid="stPageLink-NavLink"] p{
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.st-key-mobile_dock{
  display: none;
}
.st-key-mobile_dock .mobile-dock-shell{
  margin-top: 8px;
}
.st-key-mobile_dock [data-testid="stPageLink-NavLink"],
.st-key-mobile_dock [data-testid="stPopover"] > div > button{
  min-height: 48px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.12);
  background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.03));
  box-shadow: 0 8px 22px rgba(0,0,0,.30);
}
.st-key-mobile_dock [data-testid="stPageLink-NavLink"] p{
  font-size: 11px;
  font-weight: 700;
  line-height: 1.05;
  text-align: center;
}
.st-key-mobile_dock [data-testid="stPopover"] > div > button{
  font-size: 11px;
  font-weight: 700;
}

@media (max-width: 980px){
  .top-nav-shell,
  .top-nav-pop,
  .top-nav-cta,
  .sidebar-brand{
    display: none;
  }
  section[data-testid="stSidebar"]{
    display: none;
  }
  .footer{
    display: none;
  }
  .block-container{
    padding-bottom: 8.2rem;
  }
  .st-key-mobile_dock{
    display: block;
    position: fixed;
    left: 8px;
    right: 8px;
    bottom: calc(8px + env(safe-area-inset-bottom));
    z-index: 1001;
    padding: 8px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,.14);
    background:
      radial-gradient(700px 180px at 10% -10%, rgba(0,255,136,.16), transparent 75%),
      radial-gradient(700px 180px at 90% -10%, rgba(0,195,255,.16), transparent 75%),
      rgba(8,12,22,.84);
    box-shadow: 0 18px 45px rgba(0,0,0,.45);
    backdrop-filter: blur(12px);
    animation: topNavReveal .4s ease both;
  }
}

section[data-testid="stSidebar"]{
  background:
    radial-gradient(900px 500px at 20% 10%, rgba(0,255,136,.10), transparent 60%),
    linear-gradient(180deg, rgba(10,14,25,.88) 0%, rgba(8,12,22,.88) 100%);
  border-right: 1px solid rgba(255,255,255,.09);
}
section[data-testid="stSidebar"] > div{ padding-top: 12px; }

div[data-testid="stSidebarNav"]{
  display: none !important;
}

.menu-hint{
  color: var(--muted);
  font-size: 12px;
  margin: 2px 4px 8px;
}

section[data-testid="stSidebar"] [data-testid="stExpander"]{
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 14px;
  background: rgba(255,255,255,.03);
  margin-bottom: 8px;
  overflow: hidden;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary{
  font-weight: 700;
  letter-spacing: .15px;
}

@keyframes navItemIn{
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}

section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]{
  border: 1px solid rgba(255,255,255,.08);
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  border-radius: 12px;
  min-height: 38px;
  padding: 6px 10px !important;
  margin: 4px 0;
  animation: navItemIn .35s ease both;
  transition: transform .2s ease, border-color .2s ease, background .25s ease, box-shadow .25s ease;
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover{
  transform: translateX(4px);
  border-color: rgba(0,255,136,.35);
  background: linear-gradient(90deg, rgba(0,255,136,.14), rgba(0,195,255,.12));
  box-shadow: 0 8px 20px rgba(0,0,0,.25);
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"]{
  border-color: rgba(0,255,136,.55);
  background: linear-gradient(90deg, rgba(0,255,136,.24), rgba(0,195,255,.18));
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.1), 0 10px 24px rgba(0,0,0,.32);
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] p{
  color: var(--text);
  font-weight: 600;
}

.sidebar-brand{
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 20px;
  box-shadow: 0 18px 55px rgba(0,0,0,.35);
  padding: 12px 12px 10px 12px;
  margin-bottom: 10px;
  position: relative;
  overflow: hidden;
}
.sidebar-brand:before{
  content:"";
  position:absolute; inset:-2px;
  background:
    radial-gradient(600px 220px at 20% 0%, rgba(0,255,136,.22), transparent 60%),
    radial-gradient(600px 220px at 80% 0%, rgba(0,195,255,.22), transparent 60%);
  filter: blur(8px);
  opacity: .9;
  z-index: 0;
}
.sidebar-brand *{position:relative; z-index:1;}
.brand-row{display:flex; align-items:center; gap:10px;}

@keyframes agroGlow{
  0%   { filter: drop-shadow(0 0 0 rgba(0,255,136,.0)) drop-shadow(0 0 0 rgba(0,195,255,.0)); transform: translateY(0) scale(1); }
  50%  { filter: drop-shadow(0 0 18px rgba(0,255,136,.28)) drop-shadow(0 0 18px rgba(0,195,255,.22)); transform: translateY(-1px) scale(1.02); }
  100% { filter: drop-shadow(0 0 0 rgba(0,255,136,.0)) drop-shadow(0 0 0 rgba(0,195,255,.0)); transform: translateY(0) scale(1); }
}
.brand-logo{
  width:44px;height:44px;border-radius: 14px;
  display:flex;align-items:center;justify-content:center;
  background: linear-gradient(135deg, rgba(0,255,136,.25), rgba(0,195,255,.25));
  border: 1px solid rgba(255,255,255,.14);
  box-shadow: 0 12px 30px rgba(0,0,0,.25);
  font-size: 20px;
  animation: agroGlow 1.8s ease-in-out infinite;
}
.brand-title{
  font-family: Manrope, Inter, sans-serif;
  font-weight: 800;
  letter-spacing: .2px;
  font-size: 16px;
  margin:0;
  line-height: 1.1;
}
.brand-sub{color: var(--muted); font-size: 12px; margin-top: 2px;}

@keyframes heroReveal{
  from { opacity: 0; transform: translateY(22px) scale(.985); filter: blur(6px); }
  to   { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
}
@keyframes heroSweep{
  0% { background-position: -220% 0; }
  100% { background-position: 220% 0; }
}
@keyframes byFade{
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.hero-wrap{
  position: relative;
  margin: 2px 0 14px;
  padding: 18px 18px 14px;
  border-radius: 24px;
  border: 1px solid rgba(255,255,255,.12);
  background:
    radial-gradient(500px 150px at 20% 0%, rgba(0,255,136,.12), transparent 75%),
    radial-gradient(500px 150px at 80% 0%, rgba(0,195,255,.12), transparent 75%),
    rgba(255,255,255,.04);
  box-shadow: 0 20px 45px rgba(0,0,0,.35);
  backdrop-filter: blur(6px);
  overflow: hidden;
  animation: heroReveal .75s cubic-bezier(.22,.61,.36,1) both;
}
.hero-wrap:before{
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 35%, rgba(255,255,255,.18) 50%, transparent 65%);
  background-size: 220% 100%;
  mix-blend-mode: screen;
  pointer-events: none;
  animation: heroSweep 1.9s ease 1;
}
.hero-title{
  margin: 0;
  font-family: Manrope, Inter, sans-serif;
  font-weight: 800;
  letter-spacing: .2px;
  font-size: clamp(24px, 4vw, 44px);
  line-height: 1.08;
  background: linear-gradient(90deg, #EAF7F2 0%, #D6FFF0 40%, #B9F3FF 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  text-shadow: 0 8px 30px rgba(0,255,136,.14);
}
.hero-by{
  margin-top: 8px;
  font-size: 14px;
  color: rgba(234,247,242,.8);
  letter-spacing: .25px;
  animation: byFade .9s ease .35s both;
}

.card{
  background: var(--panel);
  border: 1px solid var(--stroke);
  border-radius: 18px;
  box-shadow: var(--shadow);
  padding: 16px 18px;
}
.muted{color: var(--muted);}

.footer{
  position: fixed; left: 0; right: 0; bottom: 0;
  padding: 10px 14px;
  background: rgba(10,14,25,.65);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255,255,255,.08);
  text-align: center;
  color: var(--muted);
  font-size: 12px;
}
</style>
""",
        unsafe_allow_html=True,
    )

    if render_menu:
        render_top_menu()
        render_sidebar_menu()
        render_mobile_menu()


def sidebar_brand():
    st.markdown(
        """
<div class="sidebar-brand">
  <div class="brand-row">
    <div class="brand-logo">A</div>
    <div>
      <div class="brand-title">AgroOS</div>
      <div class="brand-sub">By Astrakhov</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_sidebar_menu():
    with st.sidebar:
        sidebar_brand()
        render_language_settings(expanded=False, widget_key="lang_select_sidebar", show_hint=False)
        with st.expander(tr("quick_modules"), expanded=False):
            st.markdown(f'<div class="menu-hint">{tr("compact_menu_hint")}</div>', unsafe_allow_html=True)
            for section, items in MENU_SECTIONS:
                st.caption(tr(section))
                for item in items:
                    st.page_link(item["path"], label=tr(item["label_key"]), icon=item["icon"])

def render_top_menu():
    st.markdown(
        """
<div class="top-nav-shell">
  <div class="top-nav-brand">
    <div class="top-nav-brand-logo">A</div>
    <div>
      <div class="top-nav-brand-title">AgroOS</div>
      <div class="top-nav-brand-sub">By Astrakhov</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    nav_cols = st.columns([1, 1, 1, 1, 1, 1.35], gap="small")

    for col, (section, items) in zip(nav_cols[:-1], MENU_SECTIONS):
        with col:
            st.markdown('<div class="top-nav-pop">', unsafe_allow_html=True)
            with st.popover(tr(section), use_container_width=True):
                left, right = st.columns(2)
                split_at = (len(items) + 1) // 2
                with left:
                    for item in items[:split_at]:
                        st.page_link(item["path"], label=tr(item["label_key"]), icon=item["icon"])
                with right:
                    for item in items[split_at:]:
                        st.page_link(item["path"], label=tr(item["label_key"]), icon=item["icon"])
            st.markdown("</div>", unsafe_allow_html=True)

    with nav_cols[-1]:
        st.markdown('<div class="top-nav-cta">', unsafe_allow_html=True)
        st.page_link("pages/21_AI_Agro_Assistant.py", label=tr("open_ai_assistant"), icon="🤖")
        st.markdown("</div>", unsafe_allow_html=True)


def render_mobile_menu():
    with st.container(key="mobile_dock"):
        st.markdown('<div class="mobile-dock-shell"></div>', unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5, gap="small")

        with m1:
            st.page_link("pages/01_Home.py", label=tr("nav_home"), icon="🏠")
        with m2:
            st.page_link("pages/02_NDVI_Auto.py", label=tr("nav_ndvi"), icon="🌿")
        with m3:
            st.page_link("pages/03_Field_Manager_Map.py", label=tr("nav_map"), icon="🗺️")
        with m4:
            st.page_link("pages/21_AI_Agro_Assistant.py", label=tr("nav_ai"), icon="🤖")
        with m5:
            with st.popover(tr("more"), use_container_width=True):
                render_language_picker(widget_key="lang_select_mobile")
                st.caption(tr("menu_sections"))
                for section, items in MENU_SECTIONS:
                    st.caption(tr(section))
                    for item in items:
                        st.page_link(item["path"], label=tr(item["label_key"]), icon=item["icon"])


