import base64
import os
import sys

# CONFIG
BUILD_DIR = "build"
OUTPUT_FILENAME = "NannBoy_mGBA.html"

print("--- Nann Boy Builder (Robust Lazy Loader) ---")

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

# Encode WASM
print("Encoding Engine...")
wasm_b64 = base64.b64encode(wasm_bytes).decode("utf-8")

# Prepare JS Content (Escape for Template)
# We handle the JS source separately to avoid f-string conflicts
js_escaped = js_content.replace('`', '\\`').replace('$', '\\$').replace('\\', '\\\\')

# LAZY LOADER SCRIPT TEMPLATE
# Note: we use placeholders like {{WASM}} instead of f-string for the big content
injection_template = """
<script>
    /**
     * Nann Boy Lazy Loader
     * Delays parsing of the engine until needed to prevent freezing.
     */
    
    // 1. STORE ENGINE AS TEXT (Fast)
    const WASM_DATA = "___WASM_PLACEHOLDER___";
    
    // 2. HELPER: ASYNC WASM DECODE
    async function getWasmBinary() {
        const res = await fetch("data:application/wasm;base64," + WASM_DATA);
        const buf = await res.arrayBuffer();
        return new Uint8Array(buf);
    }

    // 3. LAZY INIT FUNCTION
    window.engineReady = false;
    
    // We inject the JS code into a Blob URL to execute it without main-thread blocking
    window.initMgbaEngine = async function() {
        if(window.engineReady) return;
        
        console.log("Decoding WASM...");
        const binary = await getWasmBinary();
        
        console.log("Injecting Engine...");
        
        // Define Module config BEFORE loading script
        window.Module = {
            canvas: document.getElementById('rom-canvas'),
            wasmBinary: binary,
            noInitialRun: true,
            print: (t) => console.log(t),
            printErr: (t) => console.error(t),
            onRuntimeInitialized: () => {
                console.log("✅ Engine Init Complete");
                window.engineReady = true;
            }
        };

        // Inject JS from Blob
        const jsSource = `___JS_PLACEHOLDER___`;
        const blob = new Blob([jsSource], {type: 'text/javascript'});
        const url = URL.createObjectURL(blob);
        const script = document.createElement('script');
        script.src = url;
        document.body.appendChild(script);

        // Wait for it to load
        return new Promise(resolve => {
            script.onload = () => {
                // Wait for RuntimeInitialized
                const check = setInterval(() => {
                    if(window.engineReady) {
                        clearInterval(check);
                        URL.revokeObjectURL(url);
                        resolve();
                    }
                }, 100);
            };
        });
    };

    // 4. START GAME
    window.startMgbaGame = async function(romData, romName) {
        if(!window.engineReady) await window.initMgbaEngine();
        
        try {
            window.Module.FS.writeFile(romName, romData);
            
            // Try different entry points depending on version
            if(window.Module.callMain) {
                window.Module.callMain([romName]);
            } else {
                window.Module.cwrap('loadGame', 'number', ['string'])(romName);
            }
            return true;
        } catch(e) {
            console.error(e);
            return false;
        }
    };
</script>
"""

# Inject Data safely
injection_script = injection_template.replace("___WASM_PLACEHOLDER___", wasm_b64)
injection_script = injection_script.replace("___JS_PLACEHOLDER___", js_escaped)

# WRITE
if "</body>" in original_html:
    final_html = original_html.replace("</body>", f"{injection_script}</body>")
else:
    final_html = original_html + injection_script

with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"SUCCESS! Open {OUTPUT_FILENAME}")
