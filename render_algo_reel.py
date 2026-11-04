import cv2
import numpy as np
import subprocess
import os

def create_algo_trading_reel(output_mp4="algoedge_fvg_reel.mp4"):
    # 1080x1920 (9:16 vertical video for Reels/Shorts)
    width, height = 1080, 1920
    fps = 30
    duration_sec = 8
    total_frames = fps * duration_sec
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_raw = "temp_raw.mp4"
    out = cv2.VideoWriter(temp_raw, fourcc, fps, (width, height))
    
    # Pre-generate candlestick data for XAUUSD 5m
    np.random.seed(42)
    candles = [
        {"o": 1920.0, "h": 1924.5, "l": 1918.5, "c": 1923.0},
        {"o": 1923.0, "h": 1927.0, "l": 1922.0, "c": 1926.5},
        {"o": 1926.5, "h": 1932.0, "l": 1925.5, "c": 1930.5}, # Sweep high
        {"o": 1930.5, "h": 1931.0, "l": 1915.0, "c": 1916.0}, # Huge displacement down
        {"o": 1916.0, "h": 1922.5, "l": 1914.0, "c": 1921.0}, # Retest into FVG
        {"o": 1921.0, "h": 1921.5, "l": 1905.0, "c": 1906.0}, # Drop to TP
    ]
    
    for frame_idx in range(total_frames):
        # Dark tech background (#0b0f19)
        img = np.full((height, width, 3), (25, 15, 11), dtype=np.uint8)
        
        # Grid lines
        for y in range(300, 1500, 100):
            cv2.line(img, (80, y), (1000, y), (40, 30, 25), 1)
        for x in range(100, 1000, 150):
            cv2.line(img, (x, 300), (x, 1500), (40, 30, 25), 1)
            
        # Header Branding
        cv2.putText(img, "ALGOEDGE SYSTEMS", (100, 180), cv2.FONT_HERSHEY_DUPLEX, 1.4, (240, 240, 240), 2)
        cv2.putText(img, "QUANTITATIVE EXECUTION DESK", (100, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 200, 50), 2)
        cv2.putText(img, "PAIR: XAUUSD (Gold) | TIMEFRAME: M5", (100, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)
        
        # Progress through candles
        candles_to_show = min(len(candles), int(frame_idx / (fps * 1.2)) + 1)
        
        # Chart scaling
        min_p, max_p = 1900.0, 1935.0
        def p_to_y(price):
            return int(1400 - ((price - min_p) / (max_p - min_p)) * 1000)
        
        # Draw candles
        for i in range(candles_to_show):
            c = candles[i]
            cx = 200 + i * 130
            y_o = p_to_y(c["o"])
            y_c = p_to_y(c["c"])
            y_h = p_to_y(c["h"])
            y_l = p_to_y(c["l"])
            
            color = (80, 200, 80) if c["c"] >= c["o"] else (80, 80, 230)
            # Wick
            cv2.line(img, (cx, y_h), (cx, y_l), color, 3)
            # Body
            top = min(y_o, y_c)
            bot = max(y_o, y_c)
            cv2.rectangle(img, (cx - 30, top), (cx + 30, bot), color, -1)
            cv2.rectangle(img, (cx - 30, top), (cx + 30, bot), (255, 255, 255), 1)
            
        # Overlay Annotations based on timing
        # Liquidity Sweep
        if candles_to_show >= 3:
            cv2.line(img, (350, p_to_y(1927.0)), (850, p_to_y(1927.0)), (60, 60, 220), 2, cv2.LINE_AA)
            cv2.putText(img, "[!] BUY-SIDE LIQUIDITY SWEPT", (400, p_to_y(1932.0) - 20), cv2.FONT_HERSHEY_DUPLEX, 0.8, (80, 80, 255), 2)
            
        # Fair Value Gap Box
        if candles_to_show >= 4:
            y_fvg_top = p_to_y(1925.5)
            y_fvg_bot = p_to_y(1916.0)
            # Semi-transparent cyan box
            overlay = img.copy()
            cv2.rectangle(overlay, (450, y_fvg_top), (950, y_fvg_bot), (240, 200, 40), -1)
            cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)
            cv2.putText(img, "FAIR VALUE GAP (FVG)", (470, y_fvg_top + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        # Bot Execution Marker
        if candles_to_show >= 5:
            pulse = int(10 * np.sin(frame_idx * 0.3))
            cv2.arrowedLine(img, (720, p_to_y(1922.5) - 60 + pulse), (720, p_to_y(1922.5) + 10), (0, 255, 255), 6, tipLength=0.4)
            cv2.putText(img, "BOT ENTRY: SHORT @ 1921.8", (520, p_to_y(1922.5) - 80), cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 255, 255), 2)
            cv2.putText(img, "LATENCY: 14ms | RISK: 1.0%", (520, p_to_y(1922.5) - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)

        # Bottom Value Hook Card
        cv2.rectangle(img, (80, 1550), (1000, 1820), (35, 25, 20), -1)
        cv2.rectangle(img, (80, 1550), (1000, 1820), (230, 200, 50), 2)
        cv2.putText(img, "CODE VS. EMOTION", (120, 1620), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
        cv2.putText(img, "Manual trader: Waited 4 candles for confirmation.", (120, 1680), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (160, 160, 240), 2)
        cv2.putText(img, "AlgoEdge Bot: Executed tick at exact FVG mitigation.", (120, 1730), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (100, 240, 100), 2)
        cv2.putText(img, "Zero Hesitation. Hardcoded Invalidation.", (120, 1780), cv2.FONT_HERSHEY_DUPLEX, 0.8, (230, 200, 50), 2)
        
        out.write(img)
        
    out.release()
    
    # Re-encode to H.264 MP4 with ffmpeg for universal Instagram/Facebook Reels compatibility
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_raw,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        output_mp4
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(temp_raw):
        os.remove(temp_raw)
    print(f"Reel successfully generated: {output_mp4}")

if __name__ == "__main__":
    create_algo_trading_reel()
