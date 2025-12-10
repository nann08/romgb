import base64
import os
import sys

# CONFIG
BUILD_DIR = "build"
OUTPUT_FILENAME = "NannBoy_mGBA.html"

print("--- Nann Boy Builder (Anti-Freeze Edition) ---")

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
     * Nann Boy Engine Core (Anti-Freeze)
     */
    const WASM_DATA = "{wasm_b64}";
    
    function getWasmBinary() {{
        try {{
            const raw = atob(WASM_DATA);
            const len = raw.length;
            const bytes = new Uint8Array(len);
            for(let i=0; i<len; i++) bytes[i] = raw.charCodeAt(i);
            return bytes;
        }} catch(e) {{
            console.error("WASM Decode Failed", e);
            return null;
        }}
    }}

    // ENGINE CONFIGURATION
    var Module = {{
        canvas: document.getElementById('rom-canvas'),
        wasmBinary: getWasmBinary(),
        noInitialRun: true, // <--- CRITICAL FIX: Stops auto-run freeze
        print: (t) => console.log(t),
        printErr: (t) => console.error(t),
        onRuntimeInitialized: function() {{
            console.log("✅ WASM Runtime Initialized");
        }}
    }};

    // STARTUP
    window.addEventListener('DOMContentLoaded', async () => {{
        try {{
            if(typeof mGBA !== 'function') throw new Error("mgba.js content missing or invalid");
            
            // Initialize the factory, but due to noInitialRun it won't start the game loop yet
            window.Emulator = await mGBA(Module);
            console.log("✅ Engine Ready for Command");
            
        }} catch(e) {{
            console.error("Engine Init Failed:", e);
            alert("Engine Error: " + e.message);
        }}
    }});

    // GAME LAUNCHER (Called by index.html)
    window.startMgbaGame = async function(romData, romName) {{
        try {{
            if (!window.Emulator) {{
                console.log("Waiting for engine...");
                window.Emulator = await mGBA(Module);
            }}
            
            // 1. Write file to virtual memory
            window.Emulator.FS.writeFile(romName, romData);
            
            // 2. Call the main function with the filename
            console.log("Booting: " + romName);
            
            // Depending on the version of mgba.js, one of these will start the loop
            try {{
                window.Emulator.callMain([romName]); 
            }} catch(e) {{
                // Fallback if callMain isn't exposed directly
                console.warn("callMain failed, trying cwrap...", e);
                window.Emulator.cwrap('loadGame', 'number', ['string'])(romName);
            }}
            
            return true;
        }} catch(e) {{
            console.error("Start Game Error:", e);
            alert("Failed to start: " + e.message);
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
