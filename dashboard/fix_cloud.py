content = open('dashboard/dashboard.py', encoding='utf-8').read()

# 1. Add dotenv + db import after existing imports
old_imp = 'import streamlit as st\nimport pandas as pd\nimport os, json, time, sys'
new_imp = ('import streamlit as st\nimport pandas as pd\nimport os, json, time, sys\n'
           'from dotenv import load_dotenv\nload_dotenv()')
content = content.replace(old_imp, new_imp)

# 2. Add db import after config import
old_cfg = 'from utils.config import set_active_vehicle, get_active_vehicle'
new_cfg = ('from utils.config import set_active_vehicle, get_active_vehicle\n'
           'from db import load_alerts, is_cloud_connected')
content = content.replace(old_cfg, new_cfg)

# 3. Replace load_log() call in main() with load_alerts(vid)
content = content.replace('    df           = load_log()', '    df           = load_alerts(vid)')

open('dashboard/dashboard.py', 'w', encoding='utf-8').write(content)
print('Done')
