import base64
import os
import sys

# --- CONFIGURATION ---
BUILD_DIR = "build"
OUTPUT_FILENAME = "NannBoy_mGBA.html"

print("--- Nann Boy Builder (Delta-Grade / Auto-Unzip) ---")
print(f"Working Directory: {os.getcwd()}")

def find_file_recursive(target_name):
    # 1. Look in current folder
    if os.path.exists(target_name):
        return target_name
    
    # 2. Look in current folder (case insensitive)
    for f in os.listdir("."):
        if f.lower() == target_name.lower():
            return f

    # 3. Look in build folder
    if os.path.exists(BUILD_DIR):
        direct_path = os.path.join(BUILD_DIR, target_name)
        if os.path.exists(direct_path):
            return direct_path
        for f in os.listdir(BUILD_DIR):
            if f.lower() == target_name.lower():
                return os.path.join(BUILD_DIR, f)

    return None

# 1. LOCATE FILES
print("Looking for files...")
html_path = find_file_recursive("index.html")
js_path = find_file_recursive("mgba.js")
wasm_path = find_file_recursive("mgba.wasm")

# Error checking
if not html_path:
    print("\n❌ ERROR: Could not find 'index.html'")
    sys.exit(1)

if not js_path or not wasm_path:
    print("\n❌ ERROR: Could not find 'mgba.js' or 'mgba.wasm'")
    sys.exit(1)

print(f"✅ Found HTML: {html_path}")
print(f"✅ Found Engine: {js_path}")
print(f"✅ Found WASM: {wasm_path}")

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

# 3. PREPARE INJECTION (Updated for ZIP handling)
injection_script = f"""
<script>
    /**
     * Nann Boy mGBA Integration (Delta-Grade: Auto-Unzip)
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
        canvas: document.getElementById('rom-canvas'),
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
        const canvasEl = document.getElementById('rom-canvas');
        if(canvasEl) Module.canvas = canvasEl;

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

        const romInput = document.getElementById('file-input-rom');
        const loadBtn = document.getElementById('btn-load-rom-action');
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
                    loadingOverlay.innerHTML = '<span class="text-white">Processing File...</span>';
                }}
                
                let fileData = null;
                let filename = file.name;
                
                try {{
                    // --- AUTO-UNZIP LOGIC ---
                    if (file.name.toLowerCase().endsWith('.zip')) {{
                        if(loadingOverlay) loadingOverlay.innerHTML = '<span class="text-white">Unzipping...</span>';
                        
                        const zipData = await file.arrayBuffer();
                        if(!window.JSZip) throw new Error("Unzip library missing!");
                        
                        const zip = await JSZip.loadAsync(zipData);
                        
                        // Find the first valid ROM file
                        const validExts = ['.gb', '.gbc', '.gba'];
                        let targetFile = null;
                        
                        // Search for ROMs inside zip
                        zip.forEach((relativePath, zipEntry) => {{
                            if(targetFile) return; // Found one already
                            const lowerName = zipEntry.name.toLowerCase();
                            if(!zipEntry.dir && validExts.some(ext => lowerName.endsWith(ext))) {{
                                targetFile = zipEntry;
                            }}
                        }});
                        
                        if(!targetFile) throw new Error("No ROM (.gb, .gbc, .gba) found in ZIP!");
                        
                        filename = targetFile.name;
                        // Get file as Uint8Array
                        fileData = await targetFile.async("uint8array");
                        
                    }} else {{
                        // Standard Load
                        const buffer = await file.arrayBuffer();
                        fileData = new Uint8Array(buffer);
                    }}

                    if (!window.mGBA) {{ alert("Engine Error"); return; }}
                    
                    if(loadingOverlay) loadingOverlay.innerHTML = '<span class="text-white">Starting Engine...</span>';

                    // Initialize Emulator
                    if (!window.Emulator) window.Emulator = await mGBA(Module);
                    
                    // Write to Virtual File System
                    window.Emulator.FS.writeFile(filename, fileData);
                    
                    // Run
                    const runGame = window.Emulator.cwrap('loadGame', 'number', ['string']);
                    
                    if (runGame(filename)) {{
                        if(loadingOverlay) loadingOverlay.style.display = 'none';
                        if(startScreen) startScreen.style.display = 'none';
                        if(canvasEl) canvasEl.style.display = 'block';
                        if(powerLed) powerLed.classList.add('on');
                    }} else {{
                        throw new Error("Game failed to start (Check BIOS/Compatibility).");
                    }}

                }} catch (err) {{
                    console.error(err);
                    alert("Error: " + err.message);
                    if(loadingOverlay) loadingOverlay.style.display = 'none';
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
