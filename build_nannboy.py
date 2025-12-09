import base64
import os
import sys

# CONFIG
BUILD_DIR = "build"
OUTPUT_FILENAME = "NannBoy_mGBA.html"

print("--- Nann Boy Builder (Bulletproof Edition) ---")

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

# Encode WASM as Base64 string for embedding
wasm_b64 = base64.b64encode(wasm_bytes).decode("utf-8")

# 3. INJECTION SCRIPT
injection_script = f"""
<script>
    /**
     * Nann Boy Core (Bulletproof)
     */
    
    // 1. Prepare WASM Binary (Prevents fetch errors)
    const WASM_DATA = "{wasm_b64}";
    function getWasmBinary() {{
        const raw = atob(WASM_DATA);
        const len = raw.length;
        const bytes = new Uint8Array(len);
        for(let i=0; i<len; i++) bytes[i] = raw.charCodeAt(i);
        return bytes;
    }}

    // 2. Define Module
    var Module = {{
        canvas: document.getElementById('rom-canvas'),
        wasmBinary: getWasmBinary(), // Direct feed! No fetch needed.
        print: (t) => console.log(t),
        printErr: (t) => console.error(t)
    }};

    // 3. Input Handling
    const KEYS = {{ 'Up':38, 'Down':40, 'Left':37, 'Right':39, 'A':88, 'B':90, 'Start':13, 'Select':8 }};
    const sendKey = (k, down) => window.dispatchEvent(new KeyboardEvent(down?'keydown':'keyup', {{keyCode: KEYS[k]}}));

    document.querySelectorAll('[data-label]').forEach(btn => {{
        const k = btn.getAttribute('data-label');
        const press = (d) => {{ 
            d ? btn.classList.add('pressed') : btn.classList.remove('pressed'); 
            sendKey(k, d); 
        }};
        btn.onmousedown = btn.ontouchstart = (e) => {{ e.preventDefault(); press(true); }};
        btn.onmouseup = btn.ontouchend = (e) => {{ e.preventDefault(); press(false); }};
    }});

    // 4. ROM Loader (Async to prevent freezing)
    const loadBtn = document.getElementById('btn-load-rom-action');
    const realInput = document.getElementById('file-input-rom');
    const overlay = document.getElementById('loading-overlay');
    const status = document.getElementById('status-log');
    
    // hijack click
    if(loadBtn) {{
        const newBtn = loadBtn.cloneNode(true);
        loadBtn.parentNode.replaceChild(newBtn, loadBtn);
        newBtn.onclick = () => realInput.click();
    }}

    if(realInput) {{
        const newInput = realInput.cloneNode(true);
        realInput.parentNode.replaceChild(newInput, realInput);
        
        newInput.onchange = async (e) => {{
            const file = e.target.files[0];
            if(!file) return;

            // SHOW LOADING SCREEN FIRST
            document.querySelectorAll('.menu-ui').forEach(x => x.style.display='none');
            overlay.style.display = 'flex';
            status.innerText = "Processing file...";
            
            // YIELD TO BROWSER (CRITICAL FIX)
            await new Promise(r => setTimeout(r, 100));

            try {{
                let data = null;
                let name = file.name;

                if(name.toLowerCase().endsWith('.zip')) {{
                    status.innerText = "Unzipping...";
                    await new Promise(r => setTimeout(r, 50)); // Yield again
                    
                    const buffer = await file.arrayBuffer();
                    const zip = await JSZip.loadAsync(buffer);
                    const romFile = Object.values(zip.files).find(f => !f.dir && f.name.match(/\.(gba|gbc|gb)$/i));
                    
                    if(!romFile) throw new Error("No ROM found in ZIP");
                    name = romFile.name;
                    data = await romFile.async("uint8array");
                }} else {{
                    const buffer = await file.arrayBuffer();
                    data = new Uint8Array(buffer);
                }}

                status.innerText = "Starting Engine...";
                await new Promise(r => setTimeout(r, 50)); // Yield again

                // INIT ENGINE ONLY NOW
                if(!window.Emulator) {{
                    window.Emulator = await mGBA(Module);
                }}
                
                window.Emulator.FS.writeFile(name, data);
                window.Emulator.cwrap('loadGame', 'number', ['string'])(name);
                
                overlay.style.display = 'none';
                document.getElementById('start-screen').style.display = 'none';
                document.getElementById('rom-canvas').style.display = 'block';

            }} catch(err) {{
                console.error(err);
                status.innerText = "ERROR:\\n" + err.message;
                status.style.color = "red";
            }}
        }};
    }}

</script>
<script>
{js_content}
</script>
"""

# 4. WRITE OUTPUT
final_html = original_html.replace("</body>", f"{injection_script}</body>") if "</body>" in original_html else original_html + injection_script

with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(final_html)

print(f"SUCCESS! Open {OUTPUT_FILENAME}")
