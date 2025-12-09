import base64
import os

# --- CONFIGURATION ---
JS_PATH = os.path.join("build", "mgba.js")
WASM_PATH = os.path.join("build", "mgba.wasm")
# We read your existing index.html to preserve your UI exactly
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

print("--- Nann Boy Builder (mGBA Edition) ---")

# 1. Load Resources
print(f"Reading {JS_PATH}...")
mgba_js_content = read_file(JS_PATH)

print(f"Reading {WASM_PATH}...")
wasm_bytes = read_file(WASM_PATH, binary=True)
wasm_b64 = base64.b64encode(wasm_bytes).decode("utf-8")

print(f"Reading {HTML_PATH}...")
original_html = read_file(HTML_PATH)

# 2. Prepare the Injection Code
# This script block will replace the old logic in your HTML.
# It sets up the mGBA Module, handles the WASM blob, maps controls, and loads files.

injection_script = f"""
<script>
    /**
     * Nann Boy mGBA Integration
     * Injected by build_nannboy.py
     */

    // --- 1. EMBEDDED ENGINE RESOURCES ---
    const WASM_B64 = "{wasm_b64}";
    
    // Helper: Convert Base64 -> Blob URL for the engine to load
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
    var Module = {{
        canvas: document.getElementById('canvas'), // Maps to your <canvas id="canvas">
        locateFile: function(path) {{
            if(path.endsWith('.wasm')) return getWasmBlobUrl();
            return path;
        }}
    }};

    // --- 3. INPUT MAPPING ---
    // Nann Boy UI -> mGBA Key Codes
    // Standard JS KeyCodes: Up:38, Down:40, Left:37, Right:39
    // mGBA Defaults: A:X(88), B:Z(90), Start:Enter(13), Select:Backspace(8)
    const KEY_MAP = {{
        'Up': 38, 'Down': 40, 'Left': 37, 'Right': 39,
        'A': 88, 'B': 90, 'Start': 13, 'Select': 8
    }};

    function triggerInput(label, isDown) {{
        const code = KEY_MAP[label];
        if (!code) return;
        
        // Dispatch keyboard event to window (where mGBA listens)
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
                // Toggle menu on Select if we are in a "menu" state (optional logic)
                if(label === 'Select' && !window.Emulator) toggleMenu('main-menu');
            }};

            btn.addEventListener('mousedown', start);
            btn.addEventListener('touchstart', start);
            btn.addEventListener('mouseup', end);
            btn.addEventListener('touchend', end);
            // Mouse leave safety
            btn.addEventListener('mouseleave', end);
        }});

        // -- FILE LOADING --
        const romInput = document.getElementById('rom-input');
        const loadBtn = document.getElementById('btn-load-rom');
        const loadingOverlay = document.getElementById('loading-overlay');
        const startScreen = document.getElementById('start-screen');
        const powerLed = document.getElementById('power-led');
        const menuUI = document.getElementById('main-menu');

        // Hook up the "Load Cartridge" button
        if(loadBtn) {{
            loadBtn.addEventListener('click', () => {{
                romInput.click();
            }});
        }}

        // Handle File Selection
        if(romInput) {{
            romInput.addEventListener('change', async (e) => {{
                const file = e.target.files[0];
                if (!file) return;

                // Update UI: Hide Menu, Show Loading
                if(menuUI) menuUI.style.display = 'none';
                if(loadingOverlay) loadingOverlay.style.display = 'flex';
                
                // Read ROM File
                const buffer = await file.arrayBuffer();
                const data = new Uint8Array(buffer);

                // Ensure mGBA Engine is Ready
                if (!window.mGBA) {{
                    console.error("mGBA engine script missing!");
                    alert("Engine Error: mgba.js not loaded.");
                    return;
                }}

                try {{
                    // Initialize Emulator Runtime if not already done
                    if (!window.Emulator) {{
                        window.Emulator = await mGBA(Module);
                    }}
                    
                    // Write ROM to Virtual File System
                    const filename = file.name;
                    window.Emulator.FS.writeFile(filename, data);
                    
                    // Start the Game
                    // We use the 'loadGame' function exposed by the engine
                    const runGame = window.Emulator.cwrap('loadGame', 'number', ['string']);
                    
                    if (runGame(filename)) {{
                        console.log("Game Running: " + filename);
                        // Hide Loading Screen, Show Game
                        if(loadingOverlay) loadingOverlay.style.display = 'none';
                        if(startScreen) startScreen.style.display = 'none';
                        if(powerLed) powerLed.classList.add('on');
                    }} else {{
                        throw new Error("mGBA failed to load ROM.");
                    }}

                }} catch (err) {{
                    console.error(err);
                    alert("Error loading game: " + err.message);
                    if(loadingOverlay) loadingOverlay.style.display = 'none';
                    if(menuUI) menuUI.style.display = 'flex';
                }}
            }});
        }}
        
        // -- RESIZE LOGIC --
        function scaleConsole() {{
             const wrapper = document.getElementById('console-wrapper');
             const body = document.getElementById('gbc-body');
             if(!wrapper || !body) return;
             const scale = Math.min(1, window.innerWidth / 440);
             wrapper.style.transform = `scale(${{scale}})`;
             body.style.height = `${{window.innerHeight / scale}}px`;
        }}
        window.addEventListener('resize', scaleConsole);
        scaleConsole();

        // -- HELPER FUNCTIONS (Menus) --
        window.toggleMenu = function(id) {{
            const el = document.getElementById(id);
            if(el) el.style.display = el.style.display === 'flex' ? 'none' : 'flex';
        }}
        
        // Hook up menu buttons if they exist
        const closeBtn = document.getElementById('btn-close-main-menu');
        if(closeBtn) closeBtn.addEventListener('click', () => toggleMenu('main-menu'));
        
        const styleBtn = document.getElementById('btn-menu-style');
        if(styleBtn) styleBtn.addEventListener('click', () => toggleMenu('styles-menu'));

        const backStyleBtn = document.getElementById('btn-back-styles');
        if(backStyleBtn) backStyleBtn.addEventListener('click', () => toggleMenu('styles-menu'));

        // Theme Logic
        window.applyTheme = function(t) {{
            const r = document.documentElement;
            if(t==='purple') {{ r.style.setProperty('--console-main', '#7c3aed'); r.style.setProperty('--console-dark', '#4c1d95'); }}
            else if(t==='glacier') {{ r.style.setProperty('--console-main', '#a5f3fc'); r.style.setProperty('--console-dark', '#0891b2'); }}
            else {{ r.style.setProperty('--console-main', '#E83942'); r.style.setProperty('--console-dark', '#b91c1c'); }}
        }}
        document.querySelectorAll('.theme-option').forEach(o => o.addEventListener('click', () => applyTheme(o.getAttribute('data-theme'))));

        // -- RESTORED MISSING FUNCTION --
        window.handleHtmlUpload = function(event) {{
            const file = event.target.files[0]; 
            if (!file) return;

             const iframe = document.getElementById('game-iframe');
             const romCanvas = document.getElementById('rom-canvas');
             const powerLed = document.getElementById('power-led');
             const startScreen = document.getElementById('start-screen');
             powerLed.classList.remove('on'); 

            if (file.type !== 'text/html' && !file.name.endsWith('.html')) {{ return; }}
            
            const reader = new FileReader();
            reader.onload = function(e) {{
                 let htmlContent = e.target.result;
                 // Inject fit style
                const fitStyle = `<style>html,body{{margin:0;padding:0;width:100vw;height:100vh;overflow:hidden;background:transparent;display:flex;justify-content:center;align-items:center;}}canvas{{max-width:100%;max-height:100%;object-fit:contain !important;transform:translateZ(0);will-change:transform;}}</style>`;
                htmlContent = htmlContent.replace('<head>', '<head>' + fitStyle);
                try {{ const blob = new Blob([htmlContent], {{ type: 'text/html' }}); const blobUrl = URL.createObjectURL(blob); iframe.onload = () => {{ URL.revokeObjectURL(blobUrl); toggleMenu('main-menu'); iframe.onload = null; iframe.style.display = 'block'; romCanvas.style.display = 'none'; startScreen.style.display = 'none'; iframe.contentWindow.focus(); powerLed.classList.add('on'); }}; iframe.src = blobUrl; }} catch (error) {{ }}
            }};
            reader.readAsText(file);
        }}

    }});
</script>

<!-- 5. INJECT ENGINE CODE (mgba.js) -->
<script>
{mgba_js_content}
</script>
"""

# 3. Inject Logic into HTML
# We look for the `</body>` tag and insert our scripts right before it.
# This ensures the UI elements exist before our script tries to attach listeners.

if "</body>" in original_html:
    # Remove old scripts if you want a clean file, but for safety we just append before body end
    # Note: If your index.html has a big script block at the end, this might duplicate logic.
    # Ideally, you should use a clean index.html or one where you removed the old logic manually.
    # But this approach overrides behavior by attaching new listeners.
    final_html = original_html.replace("</body>", f"{injection_script}</body>")
else:
    # Fallback if no body tag found
    final_html = original_html + injection_script

# 4. Write Final File
print(f"Writing {OUTPUT_FILENAME}...")
with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"Done! Open {OUTPUT_FILENAME} in your browser to play.")
