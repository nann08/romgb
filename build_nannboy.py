import base64
import os
import sys

# --- CONFIGURATION ---
# We will auto-detect these, but these are defaults
BUILD_DIR = "build"
OUTPUT_FILENAME = "NannBoy_mGBA.html"

def find_file(filename, search_paths):
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None

print("--- Nann Boy Builder (Smart Edition) ---")

# 1. LOCATE FILES (Auto-detect logic)
# Check for index.html in current folder OR build folder
html_path = find_file("index.html", [
    "index.html", 
    os.path.join(BUILD_DIR, "index.html")
])

# Check for mgba.js in build folder
js_path = find_file("mgba.js", [
    os.path.join(BUILD_DIR, "mgba.js"),
    "mgba.js"
])

# Check for mgba.wasm in build folder
wasm_path = find_file("mgba.wasm", [
    os.path.join(BUILD_DIR, "mgba.wasm"),
    "mgba.wasm"
])

# Error checking
if not html_path:
    print(f"ERROR: Could not find 'index.html'. Please put it in the same folder as this script or inside '{BUILD_DIR}'.")
    sys.exit(1)
if not js_path or not wasm_path:
    print(f"ERROR: Could not find 'mgba.js' or 'mgba.wasm' inside the '{BUILD_DIR}' folder.")
    sys.exit(1)

print(f"Found HTML: {html_path}")
print(f"Found Engine: {js_path}")
print(f"Found WASM: {wasm_path}")

# 2. READ FILES
def read_file(path, binary=False):
    mode = "rb" if binary else "r"
    encoding = None if binary else "utf-8"
    with open(path, mode, encoding=encoding) as f:
        return f.read()

print("Reading resources...")
mgba_js_content = read_file(js_path)
wasm_bytes = read_file(wasm_path, binary=True)
wasm_b64 = base64.b64encode(wasm_bytes).decode("utf-8")
original_html = read_file(html_path)

# 3. PREPARE INJECTION (Fixes the "Properties Null" error)
injection_script = f"""
<script>
    /**
     * Nann Boy mGBA Integration (Smart Build)
     */
    const WASM_B64 = "{wasm_b64}";
    
    function getWasmBlobUrl() {{
        const binary = atob(WASM_B64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {{
            bytes[i] = binary.charCodeAt(i);
        }}
        const blob = new Blob([bytes], {{ type: 'application/wasm' }});
        return URL.createObjectURL(blob);
    }}

    var Module = {{
        canvas: document.getElementById('rom-canvas'), // FIXED ID
        locateFile: function(path) {{
            if(path.endsWith('.wasm')) return getWasmBlobUrl();
            return path;
        }},
        print: (text) => console.log("[mGBA]", text),
        printErr: (text) => console.error("[mGBA Error]", text)
    }};

    const KEY_MAP = {{
        'Up': 38, 'Down': 40, 'Left': 37, 'Right': 39,
        'A': 88, 'B': 90, 'Start': 13, 'Select': 8
    }};

    function triggerInput(label, isDown) {{
        const code = KEY_MAP[label];
        if (!code) return;
        const eventType = isDown ? 'keydown' : 'keyup';
        window.dispatchEvent(new KeyboardEvent(eventType, {{ keyCode: code, which: code, bubbles: true }}));
    }}

    document.addEventListener('DOMContentLoaded', () => {{
        // Ensure Canvas exists
        const canvasEl = document.getElementById('rom-canvas');
        if(canvasEl) Module.canvas = canvasEl;

        // UI Inputs
        document.querySelectorAll('.dpad-btn, .btn-round, .btn-pill').forEach(btn => {{
            const label = btn.getAttribute('data-label');
            const handler = (e, isDown) => {{
                if(e.cancelable) e.preventDefault();
                isDown ? btn.classList.add('pressed') : btn.classList.remove('pressed');
                triggerInput(label, isDown);
            }};
            btn.addEventListener('mousedown', (e) => handler(e, true));
            btn.addEventListener('mouseup', (e) => handler(e, false));
            btn.addEventListener('touchstart', (e) => handler(e, true));
            btn.addEventListener('touchend', (e) => handler(e, false));
        }});

        // File Loading
        const romInput = document.getElementById('file-input-rom'); // FIXED ID
        const loadBtn = document.getElementById('btn-load-rom-action'); // FIXED ID
        const loadingOverlay = document.getElementById('loading-overlay');
        const startScreen = document.getElementById('start-screen');
        const powerLed = document.getElementById('power-led');

        if(loadBtn && romInput) {{
            const newBtn = loadBtn.cloneNode(true);
            loadBtn.parentNode.replaceChild(newBtn, loadBtn);
            newBtn.addEventListener('click', () => romInput.click());
        }}

        if(romInput) {{
            const newInput = romInput.cloneNode(true);
            romInput.parentNode.replaceChild(newInput, romInput);
            newInput.addEventListener('change', async (e) => {{
                const file = e.target.files[0];
                if (!file) return;

                document.querySelectorAll('.menu-ui').forEach(el => el.style.display = 'none');
                if(loadingOverlay) {{
                    loadingOverlay.style.display = 'flex';
                    loadingOverlay.innerHTML = '<span class="text-white">Loading ROM...</span>';
                }}
                
                const buffer = await file.arrayBuffer();
                const data = new Uint8Array(buffer);

                if (!window.mGBA) {{ alert("Engine Error"); return; }}

                try {{
                    if (!window.Emulator) window.Emulator = await mGBA(Module);
                    const filename = file.name;
                    window.Emulator.FS.writeFile(filename, data);
                    const runGame = window.Emulator.cwrap('loadGame', 'number', ['string']);
                    
                    if (runGame(filename)) {{
                        if(loadingOverlay) loadingOverlay.style.display = 'none';
                        if(startScreen) startScreen.style.display = 'none';
                        if(canvasEl) canvasEl.style.display = 'block';
                        if(powerLed) powerLed.classList.add('on');
                    }}
                }} catch (err) {{
                    console.error(err);
                    alert("Error: " + err.message);
                }}
            }});
        }}
    }});
</script>
<script>
{mgba_js_content}
</script>
"""

if "</body>" in original_html:
    final_html = original_html.replace("</body>", f"{injection_script}</body>")
else:
    final_html = original_html + injection_script

print(f"Writing {OUTPUT_FILENAME}...")
with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(final_html)

print("SUCCESS! Link generated.")
