import base64
import os
import sys

# CONFIG
BUILD_DIR = "build"
OUTPUT_FILENAME = "NannBoy_mGBA.html"

print("--- Nann Boy Builder (Lazy Loader) ---")

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

# READ
print("Reading resources...")
with open(html_path, "r", encoding="utf-8") as f: original_html = f.read()
with open(js_path, "r", encoding="utf-8") as f: js_content = f.read()
with open(wasm_path, "rb") as f: wasm_bytes = f.read()

# Encode WASM
print("Encoding Engine...")
wasm_b64 = base64.b64encode(wasm_bytes).decode("utf-8")

# LAZY LOADER SCRIPT
# This puts the JS code in a string variable, not a script tag.
# It only executes when initMgbaEngine() is called.
injection_script = f"""
<script>
    /**
     * Nann Boy Lazy Loader
     * Delays parsing of the engine until needed to prevent freezing.
     */
    
    // 1. STORE ENGINE AS TEXT (Fast)
    const MGBA_JS_SOURCE = `{js_content.replace('`', '\\`').replace('$', '\\$')}`;
    const WASM_DATA = "{wasm_b64}";

    // 2. HELPER: ASYNC WASM DECODE
    // Uses fetch() on data URI which is non-blocking in modern browsers
    async function getWasmBinary() {{
        const res = await fetch("data:application/wasm;base64," + WASM_DATA);
        const buf = await res.arrayBuffer();
        return new Uint8Array(buf);
    }}

    // 3. LAZY INIT FUNCTION
    window.engineReady = false;
    
    window.initMgbaEngine = async function() {{
        if(window.engineReady) return;
        
        console.log("Decoding WASM...");
        const binary = await getWasmBinary();
        
        console.log("Injecting Engine...");
        
        // Define Module config BEFORE loading script
        window.Module = {{
            canvas: document.getElementById('rom-canvas'),
            wasmBinary: binary,
            noInitialRun: true,
            print: (t) => console.log(t),
            printErr: (t) => console.error(t),
            onRuntimeInitialized: () => {{
                console.log("✅ Engine Init Complete");
                window.engineReady = true;
            }}
        }};

        // Inject JS from Blob (Prevents Main Thread Block)
        const blob = new Blob([MGBA_JS_SOURCE], {{type: 'text/javascript'}});
        const url = URL.createObjectURL(blob);
        const script = document.createElement('script');
        script.src = url;
        document.body.appendChild(script);

        // Wait for it to load
        return new Promise(resolve => {{
            script.onload = () => {{
                // Wait for RuntimeInitialized
                const check = setInterval(() => {{
                    if(window.engineReady) {{
                        clearInterval(check);
                        URL.revokeObjectURL(url);
                        resolve();
                    }}
                }}, 100);
            }};
        }});
    }};

    // 4. START GAME
    window.startMgbaGame = async function(romData, romName) {{
        if(!window.engineReady) await window.initMgbaEngine();
        
        try {{
            window.Module.FS.writeFile(romName, romData);
            
            // Try different entry points depending on version
            if(window.Module.callMain) {{
                window.Module.callMain([romName]);
            }} else {{
                window.Module.cwrap('loadGame', 'number', ['string'])(romName);
            }}
            return true;
        }} catch(e) {{
            console.error(e);
            return false;
        }}
    }};
</script>
"""

# WRITE
final_html = original_html.replace("</body>", f"{injection_script}</body>") if "</body>" in original_html else original_html + injection_script

with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"SUCCESS! Open {OUTPUT_FILENAME}")
