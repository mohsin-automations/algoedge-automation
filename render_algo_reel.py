import cv2
import numpy as np
import subprocess
import os
import sys
import json
import datetime

def get_active_mode():
    """
    Determines which of the 4 daily content pillars to generate based on:
    1. Command line arg or POST_MODE env var ('reel', 'blueprint', 'discussion', 'diagnostics')
    2. Current UTC hour:
       - 03:00 to 07:59 UTC (08:00 AM - 12:59 PM PKT) -> 'reel' (09:30 AM PKT slot)
       - 08:00 to 11:59 UTC (01:00 PM - 04:59 PM PKT) -> 'blueprint' (02:00 PM PKT slot)
       - 12:00 to 14:59 UTC (05:00 PM - 07:59 PM PKT) -> 'discussion' (06:30 PM PKT slot)
       - 15:00 to 02:59 UTC (08:00 PM - 07:59 AM PKT) -> 'diagnostics' (09:00 PM PKT slot)
    """
    env_mode = os.environ.get("POST_MODE", "").strip().lower()
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["reel", "blueprint", "discussion", "diagnostics"]:
        return sys.argv[1].lower()
    if env_mode in ["reel", "blueprint", "discussion", "diagnostics"]:
        return env_mode

    utc_hour = datetime.datetime.utcnow().hour
    if 3 <= utc_hour < 8:
        return "reel"
    elif 8 <= utc_hour < 12:
        return "blueprint"
    elif 12 <= utc_hour < 15:
        return "discussion"
    else:
        return "diagnostics"


def get_next_rotation_index(category_key: str, total_items: int) -> int:
    """
    Reads/updates local queue state (synced from AlgoEdge_Archive/AlgoEdge_Queue_State.json)
    so every single run advances to a brand-new strategy/post and NEVER repeats the previous post.
    """
    state_file = "AlgoEdge_Queue_State.json"
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    counters = state.get("counters", {})
    current_idx = int(counters.get(category_key, 0))
    next_idx = (current_idx + 1) % total_items
    counters[category_key] = next_idx
    state["counters"] = counters
    state["lastUpdatedUtc"] = datetime.datetime.utcnow().isoformat() + "Z"

    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

    return current_idx % total_items


def generate_dynamic_reel(output_mp4="algoedge_fvg_reel.mp4", caption_file="post_caption.txt"):
    width, height = 1080, 1920
    fps = 30
    duration_sec = 10
    total_frames = fps * duration_sec

    strategies = [
        {
            "id": "XAUUSD_FVG",
            "title": "XAUUSD 5M: LONDON SWEEP & FVG",
            "subtitle": "LIQUIDITY GRAB + MITIGATION ENTRY",
            "accent_bgr": (245, 200, 35),
            "zone_label": "BEARISH FAIR VALUE GAP (FVG)",
            "trigger_label": "SHORT LIMIT @ 1921.80 | SL: 1925.20",
            "stats_label": "WIN RATE: 74.2% | R:R 1:3.5 | LATENCY: 12ms",
            "candles": [
                {"o": 0.42, "h": 0.54, "l": 0.38, "c": 0.51},
                {"o": 0.51, "h": 0.68, "l": 0.49, "c": 0.65},
                {"o": 0.65, "h": 0.92, "l": 0.62, "c": 0.86},
                {"o": 0.86, "h": 0.89, "l": 0.31, "c": 0.34},
                {"o": 0.34, "h": 0.61, "l": 0.32, "c": 0.58},
                {"o": 0.58, "h": 0.59, "l": 0.11, "c": 0.14},
            ],
            "caption": (
                "Why manual Gold traders get wicked out before the real drop.\n\n"
                "During London Open, price sweeps retail buy-stops above Asian highs before creating a bearish Fair Value Gap (FVG). "
                "Our MQL5 engine waits for the sweep, detects the displacement imbalance, and executes on the exact mitigation tick with a 1.0% hardcoded risk buffer.\n\n"
                "🎁 FREE MT5 RISK & LOT CALCULATOR (.EX5):\n"
                "1. Follow AlgoEdge Systems\n"
                "2. Comment 'RISK' below\n\n"
                "Our development desk will reply with the compiled utility and setup walkthrough.\n\n"
                "#XAUUSD #GoldTrading #MQL5 #ForexPakistan #SmartMoneyConcepts #MetaTrader5"
            )
        },
        {
            "id": "US30_BREAKER",
            "title": "US30 1M: NY OPEN BREAKER BLOCK",
            "subtitle": "ALGORITHMIC INDEX DISPLACEMENT",
            "accent_bgr": (180, 105, 255),
            "zone_label": "BULLISH BREAKER + IMBALANCE",
            "trigger_label": "LONG ENTRY @ 38,540 | SL: 38,495",
            "stats_label": "PROPFIRM GUARD: ACTIVE | R:R 1:2.8 | SLIPPAGE < 1pt",
            "candles": [
                {"o": 0.65, "h": 0.68, "l": 0.42, "c": 0.45},
                {"o": 0.45, "h": 0.48, "l": 0.12, "c": 0.16},
                {"o": 0.16, "h": 0.72, "l": 0.14, "c": 0.68},
                {"o": 0.68, "h": 0.74, "l": 0.40, "c": 0.43},
                {"o": 0.43, "h": 0.85, "l": 0.41, "c": 0.82},
                {"o": 0.82, "h": 0.94, "l": 0.79, "c": 0.91},
            ],
            "caption": (
                "Trading US30 manually at the 09:30 NY Open is where most prop firm accounts breach their daily drawdown.\n\n"
                "Instead of chasing the initial spike, our US30 Liquidity Engine waits for sell-side liquidity to sweep, confirms a 1-minute Market Structure Shift (MSS), and fires on the Breaker retest.\n\n"
                "🎁 FREE PROP FIRM EQUITY GUARD SCRIPT (.EX5):\n"
                "1. Follow AlgoEdge Systems\n"
                "2. Comment 'GUARD' below\n\n"
                "We will send you the script that auto-locks your MT5 terminal before you ever breach daily drawdown.\n\n"
                "#US30 #IndexTrading #PropFirm #FTMO #FundedNext #MQL5 #AlgoTrading"
            )
        },
        {
            "id": "BTCUSD_SWEEP",
            "title": "BTCUSD 15M: RANGE LIQUIDITY ENGINE",
            "subtitle": "AUTOMATED VOLATILITY BREAKOUT",
            "accent_bgr": (50, 220, 120),
            "zone_label": "HIGH-VOLUME ORDER BLOCK ZONE",
            "trigger_label": "BOT LONG @ 69,420 | HARD TP: 71,100",
            "stats_label": "24/7 EXECUTION | ZERO EMOTION | NO MARTINGALE",
            "candles": [
                {"o": 0.50, "h": 0.56, "l": 0.44, "c": 0.48},
                {"o": 0.48, "h": 0.53, "l": 0.22, "c": 0.28},
                {"o": 0.28, "h": 0.64, "l": 0.25, "c": 0.61},
                {"o": 0.61, "h": 0.63, "l": 0.36, "c": 0.39},
                {"o": 0.39, "h": 0.78, "l": 0.38, "c": 0.75},
                {"o": 0.75, "h": 0.92, "l": 0.72, "c": 0.89},
            ],
            "caption": (
                "The biggest edge in crypto and gold automation? The bot doesn't sleep through the 3:00 AM session sweep.\n\n"
                "Our 24/7 Range Liquidity Engine identifies consolidation highs/lows, filters out low-volume fakeouts, and executes when institutional volume displaces structure.\n\n"
                "Comment 'BOT' below or DM us your manual entry checklist for a custom MQL5 scope review.\n\n"
                "#BTCUSD #CryptoTrading #AlgorithmicTrading #MQL5 #TradingBots #ForexPakistan"
            )
        },
        {
            "id": "EURUSD_EMA",
            "title": "EURUSD 15M: 50/200 EMA TREND MASTER",
            "subtitle": "DYNAMIC PULLBACK AUTOMATION",
            "accent_bgr": (255, 180, 50),
            "zone_label": "DYNAMIC EMA + STRUCTURE ALIGNMENT",
            "trigger_label": "BOT ENTRY: 1.0845 | TRAILING STOP: ACTIVE",
            "stats_label": "SPREAD FILTER: < 1.2 PIPS | AUTO BREAKEVEN",
            "candles": [
                {"o": 0.25, "h": 0.42, "l": 0.22, "c": 0.39},
                {"o": 0.39, "h": 0.58, "l": 0.36, "c": 0.55},
                {"o": 0.55, "h": 0.57, "l": 0.38, "c": 0.41},
                {"o": 0.41, "h": 0.71, "l": 0.40, "c": 0.68},
                {"o": 0.68, "h": 0.70, "l": 0.52, "c": 0.55},
                {"o": 0.55, "h": 0.89, "l": 0.54, "c": 0.86},
            ],
            "caption": (
                "Stop moving your Stop Loss to breakeven too early and getting stopped out before the trend continues.\n\n"
                "Our 50/200 EMA Trend Master only shifts Stop Loss to breakeven after a confirmed secondary Market Structure Shift (MSS)—protecting your capital while letting runners hit full Take Profit.\n\n"
                "Comment 'TREND' below or DM us to review the verified backtest logs.\n\n"
                "#EURUSD #ForexTrading #TrendTrading #MetaTrader5 #ExpertAdvisor #MQL5"
            )
        }
    ]

    idx = get_next_rotation_index("reel", len(strategies))
    strat = strategies[idx]
    with open(caption_file, "w", encoding="utf-8") as cf:
        cf.write(strat["caption"])

    temp_raw = "temp_render.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_raw, fourcc, fps, (width, height))
    candles = strat["candles"]

    for frame_idx in range(total_frames):
        img = np.full((height, width, 3), (22, 14, 10), dtype=np.uint8)

        for y in range(420, 1500, 90):
            cv2.line(img, (60, y), (1020, y), (42, 30, 22), 1)
        for x in range(80, 1020, 130):
            cv2.line(img, (x, 420), (x, 1500), (42, 30, 22), 1)

        cv2.rectangle(img, (60, 430), (1020, 595), (34, 22, 16), -1)
        cv2.rectangle(img, (60, 430), (1020, 595), strat["accent_bgr"], 2)
        cv2.putText(img, strat["title"], (85, 490), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, f"ALGOEDGE SYSTEMS | {strat['subtitle']}", (85, 535), cv2.FONT_HERSHEY_SIMPLEX, 0.72, strat["accent_bgr"], 2, cv2.LINE_AA)
        cv2.putText(img, strat["stats_label"], (85, 575), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (190, 190, 190), 1, cv2.LINE_AA)

        if frame_idx < 12:
            candles_to_show = len(candles)
        else:
            adj_frame = frame_idx - 12
            candles_to_show = min(len(candles), int(adj_frame / (fps * 1.25)) + 2)

        def norm_to_y(val):
            return int(1240 - val * 580)

        for i in range(candles_to_show):
            c = candles[i]
            cx = 160 + i * 145
            y_o, y_c = norm_to_y(c["o"]), norm_to_y(c["c"])
            y_h, y_l = norm_to_y(c["h"]), norm_to_y(c["l"])
            color = (85, 215, 95) if c["c"] >= c["o"] else (75, 75, 235)
            cv2.line(img, (cx, y_h), (cx, y_l), color, 3, cv2.LINE_AA)
            top, bot = min(y_o, y_c), max(y_o, y_c)
            cv2.rectangle(img, (cx - 34, top), (cx + 34, bot), color, -1)
            cv2.rectangle(img, (cx - 34, top), (cx + 34, bot), (245, 245, 245), 1)

        if candles_to_show >= 4:
            y_top, y_bot = norm_to_y(0.66), norm_to_y(0.42)
            overlay = img.copy()
            cv2.rectangle(overlay, (420, y_top), (990, y_bot), strat["accent_bgr"], -1)
            cv2.addWeighted(overlay, 0.28, img, 0.72, 0, img)
            cv2.rectangle(img, (420, y_top), (990, y_bot), strat["accent_bgr"], 2)
            cv2.putText(img, strat["zone_label"], (440, y_top + 42), cv2.FONT_HERSHEY_DUPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)

        if candles_to_show >= 5:
            pulse = int(7 * np.sin(frame_idx * 0.35))
            y_trig = norm_to_y(0.58)
            cv2.putText(img, strat["trigger_label"], (430, y_trig - 55 + pulse), cv2.FONT_HERSHEY_DUPLEX, 0.78, (0, 255, 255), 2, cv2.LINE_AA)

        cv2.rectangle(img, (60, 1290), (1020, 1480), (32, 22, 16), -1)
        cv2.rectangle(img, (60, 1290), (1020, 1480), (0, 255, 255), 2)
        cv2.putText(img, "FREE MT5 RISK & EQUITY GUARD (.EX5)", (90, 1345), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "Follow AlgoEdge Systems + Comment 'RISK' for direct DM", (90, 1400), cv2.FONT_HERSHEY_SIMPLEX, 0.76, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, "Custom MQL5 Bot Coding | Verified Backtests | Zero Martingale", (90, 1450), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (180, 230, 180), 1, cv2.LINE_AA)

        out.write(img)

    out.release()
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_raw,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        output_mp4
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
    print(f"[+] Reel rendered: {output_mp4} ({strat['id']})")


def generate_blueprint_infographic(output_png="algoedge_post.png", caption_file="post_caption.txt"):
    width, height = 1080, 1080
    blueprints = [
        {
            "title": "BLUEPRINT #1: ASIAN LIQUIDITY SWEEP",
            "sub": "MECHANICAL 4-STEP MQL5 EXECUTION LOGIC",
            "accent": (245, 200, 35),
            "steps": [
                ("STEP 1: RANGE MAPPING (00:00 - 08:00 UTC)", "Bot records exact Asian High & Asian Low liquidity pools."),
                ("STEP 2: STOP-HUNT DETECTION", "Price sweeps Asian High by >= 15 points without closing above buffer."),
                ("STEP 3: DISPLACEMENT & FVG CONFIRMATION", "Bearish M5 candle prints Fair Value Gap (Imbalance > 2.5x ATR)."),
                ("STEP 4: HARDCODED LIMIT EXECUTION", "Limit order placed at 50% FVG mitigation; SL above sweep wick.")
            ],
            "caption": (
                "Strategy Blueprint: How our MQL5 Liquidity Sweep Engine trades the London Open without human bias.\n\n"
                "Most retail traders buy the initial breakout above the Asian High—walking right into institutional sell orders. Here is the 4-step mechanical logic our EA executes automatically:\n\n"
                "1️⃣ Maps the 00:00–08:00 UTC Asian Range High and Low.\n"
                "2️⃣ Waits for a liquidity sweep above the high followed by rejection.\n"
                "3️⃣ Verifies a bearish Fair Value Gap (FVG) displacement candle.\n"
                "4️⃣ Fires a precision Limit entry with hardcoded 1.0% risk and zero martingale.\n\n"
                "Want this logic running on your MT5 terminal or have your own strategy to automate? Comment 'SWEEP' below or DM our desk.\n\n"
                "#SmartMoneyConcepts #XAUUSD #ForexPakistan #MQL5 #AlgoTrading #MetaTrader5"
            )
        },
        {
            "title": "BLUEPRINT #2: PROP FIRM EQUITY PROTECTOR",
            "sub": "HOW TO NEVER BREACH DAILY DRAWDOWN AGAIN",
            "accent": (80, 220, 120),
            "steps": [
                ("STEP 1: REAL-TIME TICK EQUITY MONITOR", "Queries AccountInfoDouble(ACCOUNT_EQUITY) on every incoming tick."),
                ("STEP 2: FLOATING + REALIZED LOSS CALCULATION", "Sums closed daily PnL + open floating drawdown across all symbols."),
                ("STEP 3: HARD 4.0% CIRCUIT BREAKER", "Auto-closes all open positions 1.0% before the 5.0% prop breach line."),
                ("STEP 4: TERMINAL LOCKOUT UNTIL 00:00 SERVER", "Disables new manual or bot trades for the rest of the session.")
            ],
            "caption": (
                "90% of prop firm evaluations fail because of revenge trading after 2 consecutive losses.\n\n"
                "You don't need more indicators—you need a mechanical circuit breaker. Here is how our MQL5 Prop Firm Equity Guard protects funded accounts:\n\n"
                "• Monitors combined closed + floating drawdown on every millisecond tick.\n"
                "• Automatically liquidates open tickets if drawdown hits your custom cap (e.g., 4.0%).\n"
                "• Locks terminal order execution until the next server day so you cannot revenge trade.\n\n"
                "🎁 Comment 'GUARD' below and follow AlgoEdge Systems to get the compiled MT5 Equity Guard utility.\n\n"
                "#PropFirm #FTMO #FundedNext #ForexTrading #RiskManagement #MQL5"
            )
        },
        {
            "title": "BLUEPRINT #3: DYNAMIC BREAKEVEN ENGINE",
            "sub": "STOP CHOKING WINNING TRADES TOO EARLY",
            "accent": (255, 150, 50),
            "steps": [
                ("STEP 1: INITIAL STRUCTURAL RISK LOCK", "Order opens with fixed SL behind invalidation Order Block."),
                ("STEP 2: IGNORE STATIC PIP THRESHOLDS", "Bot ignores arbitrary +10 pip moves that invite stop-hunts."),
                ("STEP 3: VERIFY INTERNAL STRUCTURE BREAK (MSS)", "Waits for a confirmed M1 candle body close beyond local swing."),
                ("STEP 4: TRAIL STOP TO ENTRY + COMMISSION", "Moves SL to exact breakeven + 2 points to cover broker spread.")
            ],
            "caption": (
                "How many times have you moved your Stop Loss to breakeven at +15 pips on Gold, gotten wicked out to the exact point, and watched price run 150 pips to your Take Profit?\n\n"
                "Static pip breakeven rules destroy your win rate. Our Dynamic Breakeven Engine only shifts your Stop Loss to entry AFTER price confirms a secondary Market Structure Shift (MSS).\n\n"
                "Need your manual trailing stop or partial-close rules coded into an automated MT5 trade manager? DM us your rules.\n\n"
                "#GoldScalping #XAUUSD #PriceAction #MetaTrader5 #ExpertAdvisor #ForexPakistan"
            )
        }
    ]

    idx = get_next_rotation_index("blueprint", len(blueprints))
    bp = blueprints[idx]
    with open(caption_file, "w", encoding="utf-8") as cf:
        cf.write(bp["caption"])

    img = np.full((height, width, 3), (20, 13, 9), dtype=np.uint8)
    for y in range(0, height, 60):
        cv2.line(img, (0, y), (width, y), (32, 22, 16), 1)
    for x in range(0, width, 60):
        cv2.line(img, (x, 0), (x, height), (32, 22, 16), 1)

    cv2.rectangle(img, (50, 45), (1030, 195), (34, 24, 18), -1)
    cv2.rectangle(img, (50, 45), (1030, 195), bp["accent"], 2)
    cv2.putText(img, "ALGOEDGE SYSTEMS // STRATEGY ARCHITECTURE", (80, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.72, bp["accent"], 2, cv2.LINE_AA)
    cv2.putText(img, bp["title"], (80, 145), cv2.FONT_HERSHEY_DUPLEX, 1.05, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, bp["sub"], (80, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (190, 190, 190), 1, cv2.LINE_AA)

    for idx_s, (s_title, s_desc) in enumerate(bp["steps"]):
        y_top = 230 + idx_s * 170
        y_bot = y_top + 145
        cv2.rectangle(img, (50, y_top), (1030, y_bot), (30, 20, 15), -1)
        cv2.rectangle(img, (50, y_top), (1030, y_bot), (65, 55, 45), 1)
        cv2.rectangle(img, (50, y_top), (62, y_bot), bp["accent"], -1)
        cv2.putText(img, s_title, (90, y_top + 55), cv2.FONT_HERSHEY_DUPLEX, 0.82, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, s_desc, (90, y_top + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (200, 210, 220), 1, cv2.LINE_AA)

    cv2.rectangle(img, (50, 925), (1030, 1035), (28, 22, 16), -1)
    cv2.rectangle(img, (50, 925), (1030, 1035), (0, 255, 255), 2)
    cv2.putText(img, "TURN YOUR MANUAL PLAYBOOK INTO AN MQL5 BOT", (80, 972), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, "DM AlgoEdge Systems for Custom EA Coding, Audits & Turnkey Licenses", (80, 1012), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 255, 255), 2, cv2.LINE_AA)

    cv2.imwrite(output_png, img)
    print(f"[+] Blueprint infographic rendered: {output_png}")


def generate_discussion_post(caption_file="post_caption.txt"):
    discussions = [
        (
            "TRADER OPEN FLOOR 📊\n\n"
            "If you could automate ONE rule in your trading playbook today so you never break it again, which one would save your equity curve the most?\n\n"
            "A) Hard Daily Drawdown Lockout (Auto-shutoff at -3% daily loss)\n"
            "B) Instant FVG / Liquidity Sweep Execution (Zero entry hesitation)\n"
            "C) Dynamic Structure-Based Trailing Stop & Partial Take-Profit\n\n"
            "Drop A, B, or C in the comments below 👇 — we'll share how we code that exact module in MQL5."
        ),
        (
            "QUANTITATIVE POLL: MANUAL VS. AUTOMATED EXECUTION ⚙️\n\n"
            "What is the #1 reason your manual trades deviate from your backtested win rate?\n\n"
            "1️⃣ Missing London/NY session setups while away from the desk\n"
            "2️⃣ Closing winning runners at 1:1 R:R out of fear of pullback\n"
            "3️⃣ Entering late after the impulse candle has already moved 30 pips\n\n"
            "Reply with 1, 2, or 3 below. If you already have a mechanical rule set, DM us to scope a custom MT5 EA build."
        ),
        (
            "MQL5 DEVELOPER DESK: OPEN Q&A 💻\n\n"
            "Are you currently running an Expert Advisor (EA) or custom indicator that suffers from:\n"
            "• OrderSend Error 130 / Invalid Stops during volatility?\n"
            "• Late candle entries or repainting signals?\n"
            "• Missing prop-firm news filter or equity protection?\n\n"
            "Describe the bug in the comments or DM us your `.mq5` / strategy checklist—our engineering desk will diagnose the execution bottleneck."
        )
    ]
    idx = get_next_rotation_index("discussion", len(discussions))
    text = discussions[idx]
    with open(caption_file, "w", encoding="utf-8") as cf:
        cf.write(text)
    print("[+] Discussion post copy generated.")


def generate_diagnostics_card(output_png="algoedge_post.png", caption_file="post_caption.txt"):
    width, height = 1080, 1080
    idx = get_next_rotation_index("diagnostics", 3)

    img = np.full((height, width, 3), (16, 12, 10), dtype=np.uint8)
    cv2.rectangle(img, (45, 45), (1035, 1035), (60, 180, 75), 2)

    cv2.putText(img, "ALGOEDGE SYSTEMS // TERMINAL DIAGNOSTICS LOG", (80, 110), cv2.FONT_HERSHEY_DUPLEX, 0.9, (80, 235, 100), 2, cv2.LINE_AA)
    cv2.putText(img, f"VERIFIED MT5 TICK EXECUTION AUDIT | MODULE #{idx + 1}", (80, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.line(img, (80, 180), (1000, 180), (60, 180, 75), 1)

    code_blocks = [
        [
            "// MQL5 Pre-Execution Spread & Slippage Guard",
            "bool VerifyExecutionSafety(string symbol, int maxSpreadPts) {",
            "   long currentSpread = SymbolInfoInteger(symbol, SYMBOL_SPREAD);",
            "   if(currentSpread > maxSpreadPts) {",
            "      Print(\"[ALGOEDGE] Execution blocked: Spread=\", currentSpread);",
            "      return(false);",
            "   }",
            "   return(CheckPropDrawdownLimit(4.0)); // Hard 4.0% Equity Guard",
            "}"
        ],
        [
            "// MQL5 Dynamic Risk-Based Lot Calculator (Fixed 1.0% Risk)",
            "double CalculateExactLot(string sym, double riskPct, double slPts) {",
            "   double equity = AccountInfoDouble(ACCOUNT_EQUITY);",
            "   double tickVal = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);",
            "   double rawLot = (equity * (riskPct / 100.0)) / (slPts * tickVal);",
            "   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);",
            "   return(MathFloor(rawLot / step) * step);",
            "}"
        ],
        [
            "// MQL5 Fair Value Gap (FVG) 3-Candle Imbalance Detector",
            "bool DetectBearishFVG(MqlRates &rates[], double minAtrMult) {",
            "   double gapSize = rates[3].low - rates[1].high;",
            "   if(gapSize <= 0) return(false);",
            "   double atr = GetCurrentATR(PERIOD_M5, 14);",
            "   return(gapSize >= (atr * minAtrMult));",
            "}"
        ]
    ]
    code_lines = code_blocks[idx % len(code_blocks)]

    cv2.rectangle(img, (75, 215), (1005, 585), (26, 22, 18), -1)
    cv2.rectangle(img, (75, 215), (1005, 585), (70, 70, 70), 1)
    for i, line in enumerate(code_lines):
        color = (120, 180, 120) if line.startswith("//") else (230, 230, 240)
        cv2.putText(img, line, (100, 265 + i * 36), cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 1, cv2.LINE_AA)

    metrics = [
        ("MODEL QUALITY:", "99.9% Real Variable Tick Data (Zero Open-Price Shortcuts)"),
        ("RISK ENGINE:", "1.0% Fixed Fractional Lot Sizing | Zero Martingale / Grid"),
        ("AVG TICK LATENCY:", "11.8 ms (Direct MqlTradeRequest Async Dispatch)"),
        ("PROP COMPLIANCE:", "Hard Daily Drawdown Breaker + High-Impact News Filter")
    ]
    for idx_m, (m_k, m_v) in enumerate(metrics):
        y = 650 + idx_m * 65
        cv2.putText(img, m_k, (80, y), cv2.FONT_HERSHEY_DUPLEX, 0.72, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(img, m_v, (350, y), cv2.FONT_HERSHEY_SIMPLEX, 0.66, (230, 230, 230), 1, cv2.LINE_AA)

    cv2.rectangle(img, (75, 910), (1005, 1005), (30, 25, 20), -1)
    cv2.putText(img, "Comment 'CODE' or DM to audit your EA or build a custom MQL5 bot.", (105, 968), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

    caption = (
        f"System Diagnostics (Module #{idx + 1}): How we engineer institutional reliability into MQL5 Expert Advisors.\n\n"
        "Before our engines ever call `OrderSend()`, the pre-execution filter validates:\n"
        "✅ Real-time `SYMBOL_SPREAD` against your maximum point cap.\n"
        "✅ Current floating + closed daily equity against your prop firm drawdown threshold.\n"
        "✅ Exact tick-level invalidation distance for mathematical 1.0% lot calculation.\n\n"
        "Comment 'CODE' or send a DM if you need an existing EA debugged or a custom strategy automated.\n\n"
        "#MQL5 #MetaTrader5 #AlgoTrading #QuantTrading #ForexPakistan #XAUUSD"
    )
    with open(caption_file, "w", encoding="utf-8") as cf:
        cf.write(caption)

    cv2.imwrite(output_png, img)
    print(f"[+] Diagnostics card rendered: {output_png}")


if __name__ == "__main__":
    mode = get_active_mode()
    print(f"[*] Active Content Pillar Mode: {mode.upper()}")
    with open("active_mode.txt", "w", encoding="utf-8") as mf:
        mf.write(mode)

    if mode == "reel":
        generate_dynamic_reel("algoedge_fvg_reel.mp4", "post_caption.txt")
    elif mode == "blueprint":
        generate_blueprint_infographic("algoedge_post.png", "post_caption.txt")
    elif mode == "discussion":
        generate_discussion_post("post_caption.txt")
    elif mode == "diagnostics":
        generate_diagnostics_card("algoedge_post.png", "post_caption.txt")
