import os
import requests
import json
import sys

PAGE_ID = os.environ.get("META_PAGE_ID", "61596362423755")
ACCESS_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN")

def publish_facebook_reel(video_path, caption):
    if not ACCESS_TOKEN:
        print("ERROR: META_PAGE_ACCESS_TOKEN environment variable is not set.")
        sys.exit(1)

    print(f"[*] Initializing Reel upload session for Page: {PAGE_ID}...")
    init_url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/video_reels"
    init_payload = {
        "upload_phase": "start",
        "access_token": ACCESS_TOKEN
    }
    
    res = requests.post(init_url, data=init_payload)
    data = res.json()
    if "video_id" not in data:
        print(f"Failed to start upload session: {data}")
        sys.exit(1)
        
    video_id = data["video_id"]
    upload_url = data["upload_url"]
    print(f"[+] Upload session started. Video ID: {video_id}")
    
    # Upload binary file
    print(f"[*] Uploading binary payload: {video_path}...")
    file_size = os.path.getsize(video_path)
    headers = {
        "Authorization": f"OAuth {ACCESS_TOKEN}",
        "offset": "0",
        "file_size": str(file_size)
    }
    with open(video_path, "rb") as f:
        upload_res = requests.post(upload_url, headers=headers, data=f)
        
    print(f"[+] Upload chunk completed. Response: {upload_res.status_code}")
    
    # Finish and publish
    print("[*] Finalizing and publishing Reel...")
    finish_payload = {
        "upload_phase": "finish",
        "access_token": ACCESS_TOKEN,
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": caption
    }
    finish_res = requests.post(init_url, data=finish_payload)
    finish_data = finish_res.json()
    
    if finish_data.get("success"):
        print(f"[SUCCESS] Reel published successfully to Facebook Page! Video ID: {video_id}")
    else:
        print(f"Finish response: {finish_data}")

if __name__ == "__main__":
    video = "algoedge_fvg_reel.mp4"
    text = (
        "Mechanical discipline eliminates emotional hesitation.\n\n"
        "Our FVG Engine monitors tick data in real time, executing exact invalidation parameters "
        "without fear or FOMO. What session do you trade most?\n\n"
        "#AlgoTrading #MQL5 #ForexPakistan #XAUUSD #MetaTrader5"
    )
    if os.path.exists(video):
        publish_facebook_reel(video, text)
    else:
        print(f"File {video} not found.")
