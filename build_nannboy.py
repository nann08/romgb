import base64
import os

# --- CONFIGURATION ---
JS_PATH = os.path.join("build", "mgba.js")
WASM_PATH = os.path.join("build", "mgba.wasm")
OUTPUT_FILENAME = "NannBoy_mGBA.html"

def read_file(path, binary=False):
    mode = "rb" if binary else "r"
    encoding = None if binary else "utf-8"
    try:
        with open(path, mode, encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Could not find {path}. Make sure the 'build' folder exists.")
        exit(1)

print("--- Nann Boy Builder ---")

# 1. Load Engine Resources
print(f"Reading {JS_PATH}...")
mgba_js_content = read_file(JS_PATH)

print(f"Reading {WASM_PATH}...")
wasm_bytes = read_file(WASM_PATH, binary=True)
wasm_b64 = base64.b64encode(wasm_bytes).decode("utf-8")

# 2. Define The HTML Template (Based on your Nann08 index.html)
# We are replacing the old <script> block with the new mGBA logic.
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="Nann Boy">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#7f1d1d">
    <title>Nann Emulator (mGBA)</title>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    
    <style>
        /* --- ORIGINAL NANN BOY STYLES --- */
        *, *::before, *::after {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; -webkit-touch-callout: none; user-select: none; }}
        :root {{ --screen-color: #ffffff; --screen-shadow: #0f380f; --safe-top: env(safe-area-inset-top, 20px); --safe-bottom: env(safe-area-inset-bottom, 20px); --console-main: #E83942; --console-dark: #b91c1c; --bg-color: #7f1d1d; --btn-color: #1c1c1c; --dpad-color: #1c1c1c; }}
        html, body {{ width: 100%; height: 100%; margin: 0; padding: 0; overscroll-behavior: none; position: fixed; overflow: hidden; background-color: var(--bg-color); transition: background-color 0.3s ease; font-family: 'Inter', sans-serif; display: flex; align-items: flex-start; justify-content: center; }}
        #console-wrapper {{ transform-origin: top center; will-change: transform; display: flex; justify-content: center; transform: translate3d(0,0,0); }}
        .gbc-body {{ --console-width: 440px; background: linear-gradient(145deg, var(--console-main) 0%, var(--console-dark) 100%); width: var(--console-width); border-radius: 20px 20px 60px 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.5), inset 2px 2px 5px rgba(255,255,255,0.3); position: relative; display: flex; flex-direction: column; align-items: center; padding-top: calc(30px + var(--safe-top)); padding-bottom: var(--safe-bottom); contain: content; transition: background 0.3s ease; }}
        .gbc-screen-lens {{ background-color: #3f3f46; width: 380px; height: 310px; border-radius: 15px 15px 50px 15px; padding: 20px 30px; box-shadow: inset 0px 0px 15px rgba(0,0,0,0.8); display: flex; flex-direction: column; align-items: center; position: relative; flex-shrink: 0; z-index: 10; transform: translate3d(0,0,0); }}
        .lens-branding {{ width: 100%; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .power-led {{ width: 10px; height: 10px; background-color: #1c1c1c; border-radius: 50%; box-shadow: inset 1px 1px 2px rgba(0,0,0,0.7); transition: background-color 0.2s; }}
        .power-led.on {{ background-color: #ff0000; box-shadow: 0 0 8px #ff3333, inset 0 0 5px rgba(255, 255, 255, 0.7); animation: led-glow 1.5s infinite alternate ease-in-out; }}
        @keyframes led-glow {{ 0% {{ box-shadow: 0 0 5px #990000; opacity: 0.8; }} 50% {{ box-shadow: 0 0 10px #ff0000; opacity: 1; }} 100% {{ box-shadow: 0 0 5px #990000; opacity: 0.8; }} }}
        
        .lcd-screen {{ 
            background-color: #000; /* Black for mGBA */
            width: 320px; height: 240px; 
            box-shadow: inset 3px 3px 10px rgba(0,0,0,0.8); 
            overflow: hidden; 
            display: flex; align-items: center; justify-content: center; 
            position: relative; transform: translate3d(0,0,0); backface-visibility: hidden; contain: paint; 
        }}
        
        /* Game Canvas: Fit to screen, pixelated */
        canvas {{ 
            display: block; 
            max-width: 100%; max-height: 100%; 
            object-fit: contain; 
            image-rendering: pixelated; 
        }}
        
        /* Menu UI Stays the Same */
        .menu-ui {{ 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            background-color: white; 
            padding: 10px 12px;
            display: none; 
            flex-direction: column; 
            align-items: center; 
            justify-content: flex-start; 
            z-index: 100; 
            overflow-y: auto; 
        }}
        
        .menu-btn {{ width: 90%; padding: 6px 0; margin: 3px 0; background-color: #f3f4f6; border: 2px solid #d1d5db; border-radius: 8px; font-weight: bold; font-size: 13px; color: #374151; text-align: center; cursor: pointer; transition: all 0.2s; flex-shrink: 0; }}
        .menu-btn:active {{ background-color: #e5e7eb; transform: scale(0.98); }}
        .theme-option {{ display: flex; align-items: center; width: 100%; padding: 8px; margin: 4px 0; border: 1px solid #eee; border-radius: 8px; cursor: pointer; flex-shrink: 0; }}
        .theme-preview {{ width: 24px; height: 24px; border-radius: 50%; margin-right: 15px; border: 2px solid rgba(0,0,0,0.1); }}
        
        /* Original Branding & Controls CSS */
        .nann-brand {{ font-family: 'Inter', sans-serif; font-style: italic; font-weight: 900; color: rgba(0,0,0,0.6); font-size: 28px; letter-spacing: 1px; margin-top: 20px; margin-bottom: 10px; text-shadow: 1px 1px 0px rgba(255, 255, 255, 0.2), -1px -1px 0px rgba(0, 0, 0, 0.2); }}
        .controls-area {{ width: 100%; flex-grow: 1; position: relative; transform: translate3d(0,0,0); }}
        .speaker-grille {{ position: absolute; bottom: 40px; right: 25px; display: flex; gap: 8px; transform: rotate(-25deg); z-index: 10; }}
        .vent-slot {{ width: 8px; height: 60px; background-color: rgba(0,0,0,0.25); border-radius: 4px; box-shadow: inset 2px 2px 4px rgba(0,0,0,0.6), 1px 1px 0 rgba(255,255,255,0.15); }}
        .dpad {{ position: absolute; top: 40px; left: 40px; width: 130px; height: 130px; }}
        .dpad-cross {{ width: 100%; height: 100%; position: relative; }}
        .dpad-arm {{ background-color: var(--dpad-color); position: absolute; border-radius: 6px; box-shadow: 2px 4px 6px rgba(0,0,0,0.4); transition: transform 0.05s; }}
        .dpad-arm::before {{ content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 6px; box-shadow: inset 2px 2px 4px rgba(255,255,255,0.2), inset -2px -2px 4px rgba(0,0,0,0.8); pointer-events: none; }}
        .dpad-arm.pressed-arm {{ transform: translateY(2px) !important; box-shadow: 0 1px 2px rgba(0,0,0,0.4); }}
        .dpad-h {{ width: 130px; height: 40px; top: 45px; left: 0; }}
        .dpad-v {{ width: 40px; height: 130px; left: 45px; top: 0; }}
        .dpad-center {{ position: absolute; width: 40px; height: 40px; background-color: var(--dpad-color); top: 45px; left: 45px; z-index: 15; border-radius: 4px; background: radial-gradient(circle at center, var(--dpad-color) 60%, var(--dpad-color) 100%); }}
        .dpad-center::after {{ content: ''; position: absolute; top: 6px; left: 6px; width: 28px; height: 28px; border-radius: 50%; background: radial-gradient(circle, rgba(0,0,0,0.2) 0%, var(--dpad-color) 70%); box-shadow: inset 1px 1px 2px rgba(0,0,0,0.8), 1px 1px 0 rgba(255,255,255,0.1); }}
        .dpad-btn {{ position: absolute; width: 55px; height: 55px; z-index: 20; cursor: pointer; }}
        .dpad-btn.pressed {{ background-color: rgba(255, 255, 255, 0.05); border-radius: 50%; }}
        .dpad-up {{ top: -5px; left: 37px; }} .dpad-down {{ bottom: -5px; left: 37px; }} .dpad-left {{ top: 37px; left: -5px; }} .dpad-right {{ top: 37px; right: -5px; }}
        .action-buttons {{ position: absolute; top: 40px; right: 30px; width: 150px; height: 80px; transform: rotate(-20deg); }}
        .btn-round {{ width: 60px; height: 60px; background-color: var(--btn-color); border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; position: absolute; transition: transform 0.05s, box-shadow 0.05s; box-shadow: inset 3px 3px 6px rgba(255,255,255,0.2), inset -3px -3px 6px rgba(0,0,0,0.8), 3px 5px 8px rgba(0,0,0,0.4); color: rgba(255,255,255,0.1); font-size: 24px; font-weight: 900; }}
        .btn-round.pressed {{ transform: translateY(3px) !important; box-shadow: inset 3px 3px 8px rgba(0,0,0,0.6), inset -1px -1px 2px rgba(255,255,255,0.1), 0 1px 2px rgba(0,0,0,0.4); }}
        .btn-b {{ bottom: 0; left: 0; }} .btn-a {{ top: 0; right: 0; }}
        .meta-buttons {{ position: absolute; bottom: 60px; left: 50%; transform: translateX(-50%); display: flex; gap: 30px; }}
        .btn-pill {{ width: 70px; height: 18px; background-color: #4b5563; border-radius: 12px; box-shadow: inset 1px 1px 2px rgba(255,255,255,0.2), inset -1px -1px 2px rgba(0,0,0,0.8), 2px 3px 4px rgba(0,0,0,0.3); cursor: pointer; transition: transform 0.05s, box-shadow 0.05s; transform: rotate(-25deg); }}
        .btn-pill.pressed {{ transform: rotate(-25deg) translateY(2px); box-shadow: inset 2px 2px 4px rgba(0,0,0,0.6), 0 1px 1px rgba(0,0,0,0.3); }}
        .meta-label {{ font-size: 11px; color: rgba(0,0,0,0.7); font-weight: 900; letter-spacing: 1px; font-family: 'Courier New', Courier, monospace; text-shadow: 1px 1px 0 rgba(255,255,255,0.2); margin-top: 10px; transform: rotate(-25deg); text-align: center; }}
        
        #loading-overlay {{ position: absolute; inset: 0; background: rgba(0,0,0,0.8); z-index: 50; display: flex; flex-direction: column; align-items: center; justify-content: center; color: white; }}
        #debug-console {{ display: none; }} /* Hide debug */
    </style>
</head>
<body oncontextmenu="return false;">

    <div id="console-wrapper">
        <div class="gbc-body" id="gbc-body">
            <div class="gbc-screen-lens">
                <div class="lens-branding"><div class="power-led" id="power-led"></div><div class="text-xs text-zinc-400 font-bold tracking-wider">BATTERY</div></div>
                <div class="lcd-screen" id="lcd-screen">
                    <canvas id="canvas"></canvas>
                    
                    <div id="loading-overlay" style="display: none;">
                        <span id="loading-text" class="animate-pulse">BOOTING...</span>
                    </div>

                    <div id="start-screen" style="position:absolute; inset:0; background: #fff; z-index: 20; display:flex; align-items:center; justify-content:center;">
                        <div class="nann-pill"><div class="nann-logo-text">NANN BOY</div></div>
                    </div>

                    <!-- MAIN MENU UI -->
                    <div id="main-menu" class="menu-ui">
                        <h2 class="text-lg font-bold mb-3 text-gray-800 tracking-wider">MENU</h2>
                        <div class="menu-btn" id="btn-load-rom">LOAD CARTRIDGE</div>
                        <div class="menu-btn" id="btn-menu-style">CHANGE STYLE</div>
                        <button id="btn-close-main-menu" class="mt-3 px-6 py-2 bg-red-600 text-white rounded-lg shadow-lg hover:bg-red-700 transition text-sm font-bold">Close</button>
                    </div>

                    <!-- STYLE MENU -->
                    <div id="styles-menu" class="menu-ui">
                        <h2 class="text-xl font-bold mb-4 text-gray-800">STYLES</h2>
                        <div class="w-full max-h-[140px] overflow-y-auto px-4">
                            <!-- Theme options here... -->
                             <div class="theme-option" data-theme="nannboy"><div class="theme-preview" style="background: linear-gradient(145deg, #f3f4f6, #9ca3af);"></div><span class="font-bold text-gray-700">Nann Boy</span></div>
                             <div class="theme-option" data-theme="purple"><div class="theme-preview" style="background: linear-gradient(145deg, #7c3aed, #4c1d95);"></div><span class="font-bold text-gray-700">Atomic Purple</span></div>
                             <div class="theme-option" data-theme="glacier"><div class="theme-preview" style="background: linear-gradient(145deg, #a5f3fc, #0891b2);"></div><span class="font-bold text-gray-700">Glacier Blue</span></div>
                        </div>
                        <button id="btn-back-styles" class="mt-4 px-6 py-2 bg-gray-600 text-white rounded-lg shadow-lg hover:bg-gray-700 transition">Back</button>
                    </div>

                    <input type="file" id="rom-input" accept=".gb,.gbc,.gba,.zip" style="display:none">
                </div>
            </div>
            <div class="nann-brand">NANN BOY</div>
            <div class="controls-area">
                <div class="speaker-grille"><div class="vent-slot"></div><div class="vent-slot"></div><div class="vent-slot"></div><div class="vent-slot"></div><div class="vent-slot"></div><div class="vent-slot"></div></div>
                <div class="dpad"><div class="dpad-cross"><div class="dpad-arm dpad-h"></div><div class="dpad-arm dpad-v"></div><div class="dpad-center"></div><div class="dpad-btn dpad-up" data-label="Up"></div><div class="dpad-btn dpad-down" data-label="Down"></div><div class="dpad-btn dpad-left" data-label="Left"></div><div class="dpad-btn dpad-right" data-label="Right"></div></div></div>
                <div class="action-buttons"><div class="btn-round btn-b" id="btn-b" data-label="B">B</div><div class="btn-round btn-a" id="btn-a" data-label="A">A</div></div>
                <div class="meta-buttons"><div class="flex flex-col items-center"><div class="btn-pill" id="btn-select" data-label="Select"></div><div class="meta-label">SELECT</div></div><div class="flex flex-col items-center"><div class="btn-pill" id="btn-start" data-label="Start"></div><div class="meta-label">START</div></div></div>
            </div>
        </div>
    </div>

    <!-- mGBA ENGINE LOGIC -->
    <script>
        // --- 1. EMBED THE WASM BINARY ---
        const WASM_B64 = "{wasm_b64}";
        
        function getWasmBlob() {{
            const binary = atob(WASM_B64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {{
                bytes[i] = binary.charCodeAt(i);
            }}
            return new Blob([bytes], {{ type: 'application/wasm' }});
        }}

        // --- 2. mGBA MODULE CONFIG ---
        var Module = {{
            canvas: document.getElementById('canvas'),
            locateFile: function(path) {{
                if(path.endsWith('.wasm')) return URL.createObjectURL(getWasmBlob());
                return path;
            }}
        }};

        // --- 3. INPUT MAPPING ---
        // Map Nann Boy UI labels to mGBA key codes
        // Up: 38, Down: 40, Left: 37, Right: 39
        // A: 88 (X), B: 90 (Z), Start: 13 (Enter), Select: 8 (Backspace)
        const KEY_MAP = {{
            'Up': 38, 'Down': 40, 'Left': 37, 'Right': 39,
            'A': 88, 'B': 90, 'Start': 13, 'Select': 8
        }};

        function triggerInput(label, isDown) {{
            const code = KEY_MAP[label];
            if (!code) return;
            const eventType = isDown ? 'keydown' : 'keyup';
            const event = new KeyboardEvent(eventType, {{ keyCode: code, which: code, bubbles: true }});
            window.dispatchEvent(event);
        }}

        // UI Event Listeners
        const btns = document.querySelectorAll('.dpad-btn, .btn-round, .btn-pill');
        btns.forEach(btn => {{
            const label = btn.getAttribute('data-label');
            
            // Touch/Mouse Events
            const start = (e) => {{
                e.preventDefault();
                btn.classList.add('pressed'); // Visual feedback
                triggerInput(label, true);
                
                // Haptic feedback if supported
                if(navigator.vibrate) navigator.vibrate(10);
            }};
            
            const end = (e) => {{
                e.preventDefault();
                btn.classList.remove('pressed');
                triggerInput(label, false);
                
                // Menu logic for Select/Start
                if(label === 'Select' && !window.Emulator) toggleMenu('main-menu');
            }};

            btn.addEventListener('mousedown', start);
            btn.addEventListener('touchstart', start);
            btn.addEventListener('mouseup', end);
            btn.addEventListener('touchend', end);
        }});

        // --- 4. GAME LOADING ---
        const romInput = document.getElementById('rom-input');
        const loading = document.getElementById('loading-overlay');
        const startScreen = document.getElementById('start-screen');
        const powerLed = document.getElementById('power-led');

        document.getElementById('btn-load-rom').addEventListener('click', () => romInput.click());

        romInput.addEventListener('change', async (e) => {{
            const file = e.target.files[0];
            if (!file) return;

            // UI State
            document.querySelectorAll('.menu-ui').forEach(m => m.style.display = 'none');
            loading.style.display = 'flex';
            
            // Read File
            const buffer = await file.arrayBuffer();
            const data = new Uint8Array(buffer);

            // Initialize Emulator if needed
            if (!window.mGBA) {{
                // This will fail if mgba.js isn't loaded, but we inject it below
                console.error("Engine not ready");
                return;
            }}

            try {{
                // Wait for runtime to init if it hasn't
                if (!window.Emulator) {{
                    window.Emulator = await mGBA(Module);
                }}
                
                // Load ROM
                const filename = file.name;
                window.Emulator.FS.writeFile(filename, data);
                
                // Call mGBA load function (standard entry point)
                const runGame = window.Emulator.cwrap('loadGame', 'number', ['string']);
                if (runGame(filename)) {{
                    console.log("Game Loaded!");
                    loading.style.display = 'none';
                    startScreen.style.display = 'none';
                    powerLed.classList.add('on');
                }} else {{
                    throw new Error("Failed to load ROM image.");
                }}

            }} catch (err) {{
                console.error(err);
                alert("Error loading game: " + err.message);
                loading.style.display = 'none';
            }}
        }});
        
        // Helper: Menu Toggling
        function toggleMenu(id) {{
            const el = document.getElementById(id);
            el.style.display = el.style.display === 'flex' ? 'none' : 'flex';
        }}
        document.getElementById('btn-close-main-menu').addEventListener('click', () => toggleMenu('main-menu'));
        document.getElementById('btn-menu-style').addEventListener('click', () => toggleMenu('styles-menu'));
        document.getElementById('btn-back-styles').addEventListener('click', () => toggleMenu('main-menu'));
        
        // Theme Logic
        function applyTheme(t) {{
            const r = document.documentElement;
            if(t==='purple') {{ r.style.setProperty('--console-main', '#7c3aed'); r.style.setProperty('--console-dark', '#4c1d95'); }}
            else if(t==='glacier') {{ r.style.setProperty('--console-main', '#a5f3fc'); r.style.setProperty('--console-dark', '#0891b2'); }}
            else {{ r.style.setProperty('--console-main', '#E83942'); r.style.setProperty('--console-dark', '#b91c1c'); }}
        }}
        document.querySelectorAll('.theme-option').forEach(o => o.addEventListener('click', () => applyTheme(o.getAttribute('data-theme'))));

        // Start Scaling
        function scaleConsole() {{
             const wrapper = document.getElementById('console-wrapper');
             const body = document.getElementById('gbc-body');
             const scale = Math.min(1, window.innerWidth / 440);
             wrapper.style.transform = `scale(${{scale}})`;
             body.style.height = `${{window.innerHeight / scale}}px`;
        }}
        window.addEventListener('resize', scaleConsole);
        scaleConsole();

    </script>

    <!-- 5. INJECT ENGINE CODE -->
    <script>
    {mgba_js_content}
    </script>

</body>
</html>"""

# 3. Write Final File
print(f"Writing {OUTPUT_FILENAME}...")
with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Done! Open {OUTPUT_FILENAME} in your browser to play.")
