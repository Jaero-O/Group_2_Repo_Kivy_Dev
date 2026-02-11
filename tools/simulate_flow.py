# Load `main.py` by path to avoid import issues when running as a script.
import importlib.util
import os
from kivy.app import App
import time

print('Starting simulated app flow')
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
main_path = os.path.join(project_root, 'main.py')
spec = importlib.util.spec_from_file_location('main_mod', main_path)
main_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_mod)
MangofyApp = main_mod.MangofyApp
app = MangofyApp()
# Make App.get_running_app() return our instance
App._running_app = app

# Prepare verbose log file
log_path = os.path.join(project_root, 'tools', 'simulate_flow.log')
lf = open(log_path, 'w', encoding='utf-8')
def log(*args, **kwargs):
    print(*args, **kwargs)
    try:
        print(*args, **kwargs, file=lf)
        lf.flush()
    except Exception:
        pass

log('Calling build()')
root = app.build()
log('Calling finish_loading()')
app.finish_loading(0)

log('Screens loaded:', [w.name for w in app.sm.screens])
log('Current screen:', app.sm.current)

# Navigate to home
app.sm.current = 'home'
log('Navigated to', app.sm.current)

# Navigate to scan
app.sm.current = 'scan'
log('Navigated to', app.sm.current)

# Simulate selecting an image
sample_image = 'ml/leaf-detection/scripts/20211231_123305 (Custom).jpg'
log('Selecting image:', sample_image)
scan_screen = app.sm.get_screen('scan')
# Ensure the app is the running app for screen methods
App._running_app = app
scan_screen.select_image(sample_image)
log('After select_image: analysis_image_path =', app.analysis_image_path)
log('Current screen now:', app.sm.current)

# Trigger scanning on_enter manually if it didn't get called
scanning = app.sm.get_screen('scanning')
try:
    scanning.on_enter()
    log('Scanning on_enter called')
except Exception as e:
    print('Error calling scanning.on_enter():', e)

# Insert a test tree and a record into the DB synchronously
db = app.db_manager
log('DB path:', db.db_path)
log('Adding test tree (sync)')
tid = db.add_tree_sync('Simulated Tree')
log('Tree id:', tid)

log('Inserting sample record via bulk_insert_records')
recs = [{'disease_name': 'Healthy', 'severity_name': 'Healthy', 'severity_percentage': 0.0, 'image_path': sample_image}]
db.bulk_insert_records(recs, tree_id=tid)

# Fetch records for the tree synchronously
# Use synchronous mode to get immediate return value
log('Fetching records for tree id', tid)
# Use synchronous mode to get immediate return value
orig_sync = db.synchronous
db.synchronous = True
result = None

def on_recs(res):
    global result
    result = res

# get_records_for_tree_async calls on_success_callback with (out, tree_name)
# get_records_for_tree_async calls on_success_callback with (out, tree_name)
db.get_records_for_tree_async(tid, on_success_callback=lambda r: log('Records callback:', r))
# restore
db.synchronous = orig_sync

log('Simulation complete')
log('Verbose simulation log written to', log_path)
lf.close()
