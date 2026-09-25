import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update CSS
css_old = """    .stFoliumContainer {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    }"""
css_new = """    /* Full Viewport App */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    header { display: none !important; }

    /* Move Sidebar to Right */
    [data-testid="stSidebar"] {
        right: 0 !important;
        left: auto !important;
        background-color: rgba(15, 23, 42, 0.9) !important;
        backdrop-filter: blur(10px) !important;
        border-left: 1px solid rgba(255,255,255,0.1) !important;
    }

    /* Floating left panel */
    div[data-testid="stVerticalBlock"]:has(> div > div > div > #left-panel-marker),
    div[data-testid="stVerticalBlock"]:has(#left-panel-marker) {
        position: absolute !important;
        top: 2rem !important;
        left: 2rem !important;
        width: 360px !important;
        z-index: 999 !important;
        background-color: rgba(15, 23, 42, 0.85) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }

    /* Floating Legend */
    div[data-testid="stVerticalBlock"]:has(#legend-marker) {
        position: absolute !important;
        bottom: 3rem !important;
        right: 23rem !important; /* to left of sidebar */
        z-index: 999 !important;
        background-color: rgba(15, 23, 42, 0.85) !important;
        border-radius: 12px;
        padding: 1rem;
    }
    
    /* Toggle Expander */
    div[data-testid="stExpander"] {
        position: absolute !important;
        bottom: 2rem !important;
        left: 2rem !important;
        z-index: 999 !important;
        width: calc(100vw - 28rem) !important;
        background-color: rgba(15, 23, 42, 0.95) !important;
    }

    .stFoliumContainer {
        border-radius: 0;
        height: 100vh !important;
        width: 100vw !important;
    }"""
content = content.replace(css_old, css_new)


# 2. Refactor KPI Metric Cards structure
kpi_regex = re.compile(r'col1, col2, col3, col4 = st\.columns\(4\)(.*?)st\.markdown\("<div style=\'height: 1\.2rem;\'></div>", unsafe_allow_html=True\)', re.DOTALL)
kpi_match = kpi_regex.search(content)

if kpi_match:
    kpi_block = kpi_match.group(1)
    
    # We will replace col1..col4 with a 2x2 grid inside a container
    new_kpi = """with st.container():
    st.markdown('<div id="left-panel-marker"></div>', unsafe_allow_html=True)
    st.markdown("### 🇹🇼 台灣即時氣象")
    
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
""" + kpi_block
    
    content = content[:kpi_match.start()] + new_kpi + content[kpi_match.end():]


# 3. Add Legend marker around display switcher
legend_regex = re.compile(r'# -------------------------------------------------------------------------\n\s+# Display Mode Switcher.*?unsafe_allow_html=True\)', re.DOTALL)
legend_match = legend_regex.search(content)

if legend_match:
    legend_block = legend_match.group(0)
    # indent and wrap in container
    indented_legend = "    " + legend_block.replace("\n", "\n    ")
    new_legend = f"""with st.container():
    st.markdown('<div id="legend-marker"></div>', unsafe_allow_html=True)
{indented_legend}"""
    content = content[:legend_match.start()] + new_legend + content[legend_match.end():]

# 4. Remove 'st.markdown("### 🗺️ 台灣互動天氣地圖 (Interactive Map)")' since it's now full screen and covered
content = content.replace('st.markdown("### 🗺️ 台灣互動天氣地圖 (Interactive Map)")', '')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Applied overlay refactoring to app.py")
