import base64
import os
import sys

# CONFIG
BUILD_DIR = "build"
OUTPUT_FILENAME = "NannBoy_mGBA.html"

print("--- Nann Boy Builder (Ultra-Smooth Edition) ---")

def find_file(name):
    if os.path.exists(name): return name
    if os.path.exists(os.path.join(BUILD_DIR, name)): return os.path.join(BUILD_DIR, name)
    return None

html_path = find_file("index.html")
js_path = find_file("mgba.js")
wasm_path = find_file("mgba.wasm")

if not (html_path and js_path and wasm_path):
    print("❌ ERROR: Missing files. Check 'build' folder.")
    sys.exit(1)

# READ
print("Reading resources...")
with open(html_path, "r", encoding="utf-8") as f: original_html = f.read()
with open(js_path, "r", encoding="utf-8") as f: js_content = f.read()
with open(wasm_path, "rb") as f: wasm_bytes = f.read()

# CHUNK WASM (For Progressive Loading)
print("Chunking Engine...")
raw_b64 = base64.b64encode(wasm_bytes).decode("utf-8")
CHUNK_SIZE = 256 * 1024 # 256KB chunks
chunks = [raw_b64[i:i+CHUNK_SIZE] for i in range(0, len(raw_b64), CHUNK_SIZE)]
js_chunks = "['" + "','".join(chunks) + "']"

# PROGRESSIVE LOADER SCRIPT
injection_script = f"""
<script>
    /**
     * Nann Boy Core (Progressive Loader)
     * Decodes engine in background ticks to prevent freezing.
     */
    
    const ENGINE_CHUNKS = {js_chunks};
    const TOTAL_SIZE = {len(wasm_bytes)};
    let wasmBinary = null;

    // 1. ASYNC DECODER
    async function loadEngine() {{
        const overlay = document.getElementById('loading-overlay');
        const bar = document.getElementById('loader-bar-fill');
        const txt = document.getElementById('loading-text');
        
        if(overlay) overlay.style.display = 'flex';
        
        // Allocate Memory
        const binary = new Uint8Array(TOTAL_SIZE);
        let offset = 0;
        
        // Process Chunks with Yielding
        for(let i=0; i<ENGINE_CHUNKS.length; i++) {{
            const chunk = ENGINE_CHUNKS[i];
            const raw = atob(chunk);
            for(let k=0; k<raw.length; k++) {{
                binary[offset++] = raw.charCodeAt(k);
            }}
            
            // Visual Feedback
            if(bar) bar.style.width = Math.round((i / ENGINE_CHUNKS.length) * 100) + "%";
            if(txt) txt.innerText = "System Boot: " + Math.round((i / ENGINE_CHUNKS.length) * 100) + "%";
            
            // Yield to Main Thread (Smoothness Secret)
            await new Promise(r => setTimeout(r, 0));
        }}
        
        wasmBinary = binary;
        if(txt) txt.innerText = "Engine Ready";
        if(overlay) setTimeout(() => overlay.style.display = 'none', 500);
        
        // Pre-init mGBA
        try {{
            window.Emulator = await mGBA({{
                canvas: document.getElementById('rom-canvas'),
                wasmBinary: binary,
                noInitialRun: true
            }});
            console.log("✅ Engine Hot");
        }} catch(e) {{
            console.error("Engine Warmup Failed", e);
        }}
    }}

    // Boot on Load
    window.addEventListener('DOMContentLoaded', loadEngine);

    // 2. RUN GAME EXPORT
    window.startMgbaGame = async function(romData, romName) {{
        if(!window.Emulator) {{
            // Just in case it wasn't ready
            if(!wasmBinary) return false;
            window.Emulator = await mGBA({{
                canvas: document.getElementById('rom-canvas'),
                wasmBinary: wasmBinary,
                noInitialRun: true
            }});
        }}
        
        try {{
            window.Emulator.FS.writeFile(romName, romData);
            window.Emulator.cwrap('loadGame', 'number', ['string'])(romName);
            return true;
        }} catch(e) {{
            console.error(e);
            return false;
        }}
    }};
</script>
<script>
{js_content}
</script>
"""

# WRITE
final_html = original_html.replace("</body>", f"{injection_script}</body>") if "</body>" in original_html else original_html + injection_script

with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"SUCCESS! Open {OUTPUT_FILENAME}")
