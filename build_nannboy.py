import base64
import os

# --- CONFIGURATION ---
JS_PATH = os.path.join("build", "mgba.js")
WASM_PATH = os.path.join("build", "mgba.wasm")
HTML_PATH = "index.html" 
OUTPUT_FILENAME = "NannBoy_mGBA.html"

def read_file(path, binary=False):
    mode = "rb" if binary else "r"
    encoding = None if binary else "utf-8"
    try:
        with open(path, mode, encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {path}. Make sure the file exists.")
        exit(1)

print("--- Nann Boy Builder (mGBA Fixed Edition) ---")

# 1. Load Resources
print(f"Reading {JS_PATH}...")
mgba_js_content = read_file(JS_PATH)

print(f"Reading {WASM_PATH}...")
wasm_bytes = read_file(WASM_PATH, binary=True)
wasm_b64 = base64.b64encode(wasm_bytes).decode("utf-8")

print(f"Reading {HTML_PATH}...")
original_html = read_file(HTML_PATH)

# 2. Prepare the Injection Code
# UPDATED: Matches IDs in your specific index.html (rom-canvas, file-input-rom, etc.)

injection_script = f"""
<script>
    /**
     * Nann Boy mGBA Integration (Fixed IDs)
     */

    // --- 1. EMBEDDED ENGINE RESOURCES ---
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

    // --- 2. mGBA CONFIGURATION ---
    // FIXED: Now points to 'rom-canvas' instead of 'canvas'
    var Module = {{
        canvas: document.getElementById('rom-canvas'), 
        locateFile: function(path) {{
            if(path.endsWith('.wasm')) return getWasmBlobUrl();
            return path;
        }},
        print: (text) => console.log("[mGBA]", text),
        printErr: (text) => console.error("[mGBA Error]", text)
    }};

    // --- 3. INPUT MAPPING ---
    const KEY_MAP = {{
        'Up': 38, 'Down': 40, 'Left': 37, 'Right': 39,
        'A': 88, 'B': 90, 'Start': 13, 'Select': 8
    }};

    function triggerInput(label, isDown) {{
        const code = KEY_MAP[label];
        if (!code) return;
        
        const eventType = isDown ? 'keydown' : 'keyup';
        const event = new KeyboardEvent(eventType, {{ 
            keyCode: code, 
            which: code, 
            bubbles: true 
        }});
        window.dispatchEvent(event);
    }}

    // --- 4. INITIALIZATION & UI HOOKS ---
    document.addEventListener('DOMContentLoaded', () => {{
        
        // Ensure Canvas is visible and correctly identified
        const canvasEl = document.getElementById('rom-canvas');
        if(canvasEl) {{
            // Re-assign in case DOM wasn't ready during Module def
            Module.canvas = canvasEl;
        }} else {{
            console.error("FATAL: <canvas id='rom-canvas'> not found!");
        }}

        // -- UI CONTROLS --
        const btns = document.querySelectorAll('.dpad-btn, .btn-round, .btn-pill');
        btns.forEach(btn => {{
            const label = btn.getAttribute('data-label');
            
            const start = (e) => {{
                if(e.cancelable) e.preventDefault();
                btn.classList.add('pressed');
                triggerInput(label, true);
                if(navigator.vibrate) navigator.vibrate(10);
            }};
            
            const end = (e) => {{
                if(e.cancelable) e.preventDefault();
                btn.classList.remove('pressed');
                triggerInput(label, false);
            }};

            btn.addEventListener('mousedown', start);
            btn.addEventListener('touchstart', start);
            btn.addEventListener('mouseup', end);
            btn.addEventListener('touchend', end);
            btn.addEventListener('mouseleave', end);
        }});

        // -- FILE LOADING (FIXED IDS) --
        // FIXED: Using 'file-input-rom' instead of 'rom-input'
        const romInput = document.getElementById('file-input-rom');
        
        // FIXED: Using 'btn-load-rom-action' instead of 'btn-load-rom'
        const loadBtn = document.getElementById('btn-load-rom-action');
        
        const loadingOverlay = document.getElementById('loading-overlay');
        const startScreen = document.getElementById('start-screen');
        const powerLed = document.getElementById('power-led');
        const menuUI = document.getElementById('main-menu');
        const loadMenu = document.getElementById('load-game-menu');

        // Hook up the "Load Cartridge" button
        if(loadBtn && romInput) {{
            // Remove old listeners by cloning (hacky but effective for injected scripts)
            const newBtn = loadBtn.cloneNode(true);
            loadBtn.parentNode.replaceChild(newBtn, loadBtn);
            
            newBtn.addEventListener('click', () => {{
                romInput.click();
            }});
        }}

        // Handle File Selection
        if(romInput) {{
            // Clone to remove previous listeners from index.html
            const newInput = romInput.cloneNode(true);
            romInput.parentNode.replaceChild(newInput, romInput);

            newInput.addEventListener('change', async (e) => {{
                const file = e.target.files[0];
                if (!file) return;

                // Close all menus
                document.querySelectorAll('.menu-ui').forEach(el => el.style.display = 'none');
                
                if(loadingOverlay) {{
                    loadingOverlay.style.display = 'flex';
                    loadingOverlay.innerHTML = '<span class="text-white">Loading ROM...</span>';
                }}
                
                const buffer = await file.arrayBuffer();
                const data = new Uint8Array(buffer);

                if (!window.mGBA) {{
                    alert("Engine Error: mgba.js not loaded.");
                    return;
                }}

                try {{
                    // Initialize Emulator
                    if (!window.Emulator) {{
                        window.Emulator = await mGBA(Module);
                    }}
                    
                    // Write ROM
                    const filename = file.name;
                    window.Emulator.FS.writeFile(filename, data);
                    
                    // Start Game
                    const runGame = window.Emulator.cwrap('loadGame', 'number', ['string']);
                    
                    if (runGame(filename)) {{
                        console.log("Game Running: " + filename);
                        if(loadingOverlay) loadingOverlay.style.display = 'none';
                        if(startScreen) startScreen.style.display = 'none';
                        if(canvasEl) canvasEl.style.display = 'block'; // Make sure canvas is visible
                        if(powerLed) powerLed.classList.add('on');
                    }} else {{
                        throw new Error("mGBA failed to load ROM.");
                    }}

                }} catch (err) {{
                    console.error(err);
                    alert("Error loading game: " + err.message);
                    if(loadingOverlay) loadingOverlay.style.display = 'none';
                }}
            }});
        }}
    }});
</script>

<!-- 5. INJECT ENGINE CODE (mgba.js) -->
<script>
{mgba_js_content}
</script>
"""

# 3. Inject Logic
if "</body>" in original_html:
    final_html = original_html.replace("</body>", f"{injection_script}</body>")
else:
    final_html = original_html + injection_script

# 4. Write Final File
print(f"Writing {OUTPUT_FILENAME}...")
with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"Done! Open {OUTPUT_FILENAME} in your browser.")
