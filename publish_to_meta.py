import os
import requests
import json
import sys

INPUT_PAGE_ID = os.environ.get("META_PAGE_ID", "").strip()
INPUT_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN", "").strip()

def resolve_page_credentials(token, target_id):
    print("[*] Resolving true Graph API Page ID and Access Token...")
    url = f"https://graph.facebook.com/v21.0/me/accounts?access_token={token}"
    try:
        res = requests.get(url)
        data = res.json()
        if "data" in data and len(data["data"]) > 0:
            for page in data["data"]:
                if "algoedge" in page.get("name", "").lower():
                    true_id = str(page.get("id"))
                    page_token = page.get("access_token")
                    print(f"[+] Found AlgoEdge Systems! True Page ID: {true_id}")
                    return true_id, page_token
            for page in data["data"]:
                if str(page.get("id")) == str(target_id):
                    return str(page.get("id")), page.get("access_token")
            first_page = data["data"][0]
            true_id = str(first_page.get("id"))
            page_token = first_page.get("access_token")
            print(f"[+] Using Page '{first_page.get('name')}' with true Page ID: {true_id}")
            return true_id, page_token
    except Exception as e:
        print(f"[*] Note: Could not query /me/accounts ({e})")
    
    return target_id, token

def publish_video_direct(page_id, page_token, video_path, caption):
    print(f"[*] Publishing video directly to https://graph-video.facebook.com/v21.0/{page_id}/videos...")
    upload_url = f"https://graph-video.facebook.com/v21.0/{page_id}/videos"
    
    with open(video_path, "rb") as f:
        files = {
            "source": f
        }
        data = {
            "description": caption,
            "access_token": page_token
        }
        res = requests.post(upload_url, data=data, files=files)
        res_data = res.json()
        
    if "id" in res_data:
        print(f"[SUCCESS] Video successfully published as a Reel to Facebook Page! Video ID: {res_data['id']}")
        return True
    else:
        print(f"Direct video upload failed: {res_data}")
        return False

def publish_facebook_reel(video_path, caption):
    if not INPUT_TOKEN:
        print("ERROR: META_PAGE_ACCESS_TOKEN environment variable is not set.")
        sys.exit(1)

    true_page_id, page_token = resolve_page_credentials(INPUT_TOKEN, INPUT_PAGE_ID)

    print(f"[*] Initializing Reel upload session for Page: {true_page_id}...")
    init_url = f"https://graph.facebook.com/v21.0/{true_page_id}/video_reels"
    init_payload = {
        "upload_phase": "start",
        "access_token": page_token
    }
    
    res = requests.post(init_url, data=init_payload)
    data = res.json()
    
    if "video_id" not in data:
        print(f"Reel API response: {data}")
        print("[*] Falling back to direct video publishing endpoint...")
        success = publish_video_direct(true_page_id, page_token, video_path, caption)
        if not success:
            sys.exit(1)
        return
        
    video_id = data["video_id"]
    upload_url = data["upload_url"]
    print(f"[+] Reel upload session started. Video ID: {video_id}")
    
    print(f"[*] Uploading binary payload: {video_path}...")
    file_size = os.path.getsize(video_path)
    headers = {
        "Authorization": f"OAuth {page_token}",
        "offset": "0",
        "file_size": str(file_size)
    }
    with open(video_path, "rb") as f:
        upload_res = requests.post(upload_url, headers=headers, data=f)
        
    print(f"[+] Upload chunk completed. Response: {upload_res.status_code}")
    
    print("[*] Finalizing and publishing Reel...")
    finish_payload = {
        "upload_phase": "finish",
        "access_token": page_token,
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
        print("[*] Attempting direct upload fallback...")
        success = publish_video_direct(true_page_id, page_token, video_path, caption)
        if not success:
            sys.exit(1)

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
