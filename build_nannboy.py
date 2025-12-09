import base64
import os
import sys

# CONFIG
BUILD_DIR = "build"
OUTPUT_FILENAME = "NannBoy_mGBA.html"

print("--- Nann Boy Builder (Final Engine Injection) ---")

# 1. FIND FILES
def find_file(name):
    if os.path.exists(name): return name
    if os.path.exists(os.path.join(BUILD_DIR, name)): return os.path.join(BUILD_DIR, name)
    return None

html_path = find_file("index.html")
js_path = find_file("mgba.js")
wasm_path = find_file("mgba.wasm")

if not (html_path and js_path and wasm_path):
    print("❌ ERROR: Files missing. Check 'build' folder.")
    sys.exit(1)

# 2. READ & ENCODE
print("Reading files...")
with open(html_path, "r", encoding="utf-8") as f: original_html = f.read()
with open(js_path, "r", encoding="utf-8") as f: js_content = f.read()
with open(wasm_path, "rb") as f: wasm_bytes = f.read()

wasm_b64 = base64.b64encode(wasm_bytes).decode("utf-8")

# 3. INJECTION SCRIPT (Pure Engine - No UI Logic)
injection_script = f"""
<script>
    /**
     * Nann Boy Engine Core
     * Injected by build_nannboy.py
     */
    const WASM_DATA = "{wasm_b64}";
    
    // Helper to turn Base64 back into binary for the emulator
    function getWasmBinary() {{
        const raw = atob(WASM_DATA);
        const len = raw.length;
        const bytes = new Uint8Array(len);
        for(let i=0; i<len; i++) bytes[i] = raw.charCodeAt(i);
        return bytes;
    }}

    var Module = {{
        canvas: document.getElementById('rom-canvas'),
        wasmBinary: getWasmBinary(),
        print: (t) => console.log(t),
        printErr: (t) => console.error(t)
    }};

    // PRE-LOAD ENGINE IMMEDIATELY
    // This ensures the emulator is ready before you even click 'Load'
    window.addEventListener('DOMContentLoaded', async () => {{
        try {{
            window.Emulator = await mGBA(Module);
            console.log("✅ Engine Pre-Loaded Successfully");
        }} catch(e) {{
            console.error("Engine Init Failed", e);
        }}
    }});

    // EXPOSE FUNCTION FOR UI TO CALL
    // Your index.html calls this function when a file is uploaded
    window.startMgbaGame = async function(romData, romName) {{
        try {{
            if (!window.Emulator) window.Emulator = await mGBA(Module);
            
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

# 4. WRITE OUTPUT
if "</body>" in original_html:
    final_html = original_html.replace("</body>", f"{injection_script}</body>")
else:
    final_html = original_html + injection_script

with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"SUCCESS! Open {OUTPUT_FILENAME}")
