import sys

file_path = 'app.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_tabs = False
for i, line in enumerate(lines):
    if 'map_col, chart_col = st.columns([1.2, 1], gap="medium")' in line:
        new_lines.append('# Full width map container\n')
        continue
    if 'with map_col:' in line:
        new_lines.append('with st.container():\n')
        continue
    if 'st_folium(tw_map, width=None, height=530' in line:
        new_lines.append(line.replace('height=530', 'height=750'))
        continue
    if 'with chart_col:' in line:
        new_lines.append('with st.expander("📊 顯示詳細數據分析與資料表 (View Analytics & Data Tables)", expanded=False):\n')
        continue
    
    if '# 8. Full Data Tables & CSV Download (Tabs)' in line:
        in_tabs = True
        
    if '# 9. Footer' in line:
        in_tabs = False
        
    if in_tabs:
        # Don't double indent if already indented
        if line.strip() == '':
            new_lines.append(line)
        else:
            new_lines.append('    ' + line)
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Successfully reformatted layout in app.py')
