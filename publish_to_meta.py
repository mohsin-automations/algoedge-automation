import datetime
import io
import json
import os
import subprocess
import sys
import requests

UPLOAD_FOLDER_ID = "17Qgq-26-H_D_ZEjjFN5hP0ckLsRCEVzt"   # AlgoEdge_Ready_For_Upload
ARCHIVE_FOLDER_ID = "1UsGiLRSsekxLPMM5h0t0XHi8Ikx0IGBe"  # AlgoEdge_Archive

CLIENT_ID = os.environ.get("GCP_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("GCP_CLIENT_SECRET", "").strip()
DRIVE_REFRESH_TOKEN = os.environ.get("DRIVE_REFRESH_TOKEN", "").strip()
TOKEN_URI = "https://oauth2.googleapis.com/token"

INPUT_PAGE_ID = os.environ.get("META_PAGE_ID", "").strip()
INPUT_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN", "").strip()

RUN_LOGS = []


def log(msg: str):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    RUN_LOGS.append(line)


def get_drive_service():
    if not CLIENT_ID or not CLIENT_SECRET or not DRIVE_REFRESH_TOKEN:
        log("Notice: Google Drive secrets not set; running local repo scripts directly.")
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None,
            refresh_token=DRIVE_REFRESH_TOKEN,
            token_uri=TOKEN_URI,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )
        creds.refresh(Request())
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        log(f"Notice: Drive API connection skipped ({e}); proceeding with local scripts.")
        return None


def download_drive_file_to_disk(drive_service, file_id: str, local_path: str):
    from googleapiclient.http import MediaIoBaseDownload
    request = drive_service.files().get_media(fileId=file_id)
    with open(local_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def move_drive_file_to_archive(drive_service, file_id: str, original_name: str):
    try:
        ts_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(original_name)
        archived_name = f"{base}_archived_{ts_str}{ext}"
        file_meta = drive_service.files().get(fileId=file_id, fields="parents").execute()
        prev_parents = ",".join(file_meta.get("parents", []))
        drive_service.files().update(
            fileId=file_id,
            addParents=ARCHIVE_FOLDER_ID,
            removeParents=prev_parents,
            body={"name": archived_name},
            fields="id, parents, name"
        ).execute()
        log(f"[+] Moved '{original_name}' -> AlgoEdge_Archive as '{archived_name}'")
    except Exception as e:
        log(f"Warning: Could not move '{original_name}' to archive: {e}")


def sync_staged_code_and_state_from_drive(drive_service) -> bool:
    if not drive_service:
        return False

    updated_any_script = False
    try:
        q_state = f"'{ARCHIVE_FOLDER_ID}' in parents and name = 'AlgoEdge_Queue_State.json' and trashed = false"
        state_files = drive_service.files().list(q=q_state, fields="files(id, name)", orderBy="modifiedTime desc").execute().get("files", [])
        if state_files:
            download_drive_file_to_disk(drive_service, state_files[0]["id"], "AlgoEdge_Queue_State.json")
            log("[+] Restored rotation queue state from AlgoEdge_Archive.")

        q_ready = f"'{UPLOAD_FOLDER_ID}' in parents and trashed = false"
        staged_files = drive_service.files().list(q=q_ready, fields="files(id, name, mimeType)", orderBy="modifiedTime asc").execute().get("files", [])

        for sf in staged_files:
            fname = sf.get("name", "")
            fid = sf.get("id")
            if fname in ["render_algo_reel.py", "publish_to_meta.py"]:
                log(f"[*] Found staged code update in AlgoEdge_Ready_For_Upload: '{fname}' ({fid})")
                download_drive_file_to_disk(drive_service, fid, fname)
                move_drive_file_to_archive(drive_service, fid, fname)
                updated_any_script = True
            elif fname == "publish_reels.yml":
                os.makedirs(".github/workflows", exist_ok=True)
                download_drive_file_to_disk(drive_service, fid, ".github/workflows/publish_reels.yml")
                move_drive_file_to_archive(drive_service, fid, fname)
                updated_any_script = True
    except Exception as e:
        log(f"Notice during Drive sync check: {e}")

    return updated_any_script


def deduplicate_page_posts(page_id: str, page_token: str) -> int:
    """
    Scans up to 50 recent published posts on the Page, keeps ONLY the newest post
    of each unique message signature, and deletes all older duplicate posts via Graph API.
    """
    deleted_count = 0
    try:
        res = requests.get(
            f"https://graph.facebook.com/v21.0/{page_id}/published_posts",
            params={"fields": "id,message,created_time", "limit": 50, "access_token": page_token}
        ).json()
        posts = res.get("data", [])
        seen_signatures = set()
        for post in posts:
            pid = post.get("id")
            msg = (post.get("message") or "").strip()
            if not msg:
                continue
            sig = msg[:70].lower()
            if sig in seen_signatures:
                del_res = requests.delete(
                    f"https://graph.facebook.com/v21.0/{pid}",
                    params={"access_token": page_token}
                )
                if del_res.status_code == 200:
                    deleted_count += 1
                    log(f"[CLEANUP] Deleted duplicate post {pid} ('{msg[:35]}...')")
                else:
                    log(f"[CLEANUP] Could not delete {pid}: {del_res.text}")
            else:
                seen_signatures.add(sig)
    except Exception as e:
        log(f"Notice during Page deduplication: {e}")
    return deleted_count


def ensure_pinned_lead_magnet_published(page_id: str, page_token: str):
    """
    Publishes the dedicated 'FREE MT5 PROP FIRM DRAWDOWN GUARD & LOT CALCULATOR (.EX5)'
    Lead-Magnet post once (if not already present in AlgoEdge_Queue_State.json) and logs its Post ID.
    """
    state_file = "AlgoEdge_Queue_State.json"
    state = {}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    if state.get("leadMagnetPublished"):
        return

    log("[*] Publishing dedicated Pinned Lead-Magnet post (Free MT5 Prop Drawdown Guard .ex5)...")
    subprocess.run([sys.executable, "render_algo_reel.py", "lead_magnet"], check=False)
    caption = ""
    if os.path.exists("post_caption.txt"):
        with open("post_caption.txt", "r", encoding="utf-8") as cf:
            caption = cf.read().strip()

    if os.path.exists("algoedge_post.png") and caption:
        url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
        with open("algoedge_post.png", "rb") as f:
            res = requests.post(url, data={"message": caption, "access_token": page_token}, files={"source": f}).json()
        if "id" in res:
            post_id = res.get("post_id") or res.get("id")
            log(f"[PIN_THIS_POST] Lead-Magnet Post Published! Post ID: {post_id} | Photo URL: https://www.facebook.com/photo/?fbid={res['id']}")
            state["leadMagnetPublished"] = True
            state["leadMagnetPostId"] = str(post_id)
            state["leadMagnetPhotoUrl"] = f"https://www.facebook.com/photo/?fbid={res['id']}"
            with open(state_file, "w", encoding="utf-8") as sf:
                json.dump(state, sf, indent=2)
        else:
            log(f"[!] Lead-Magnet upload returned: {res}")


def save_state_and_telemetry_to_drive(drive_service, page_id: str, page_token: str, replies_sent: int):
    if not drive_service:
        return
    try:
        from googleapiclient.http import MediaFileUpload

        if os.path.exists("AlgoEdge_Queue_State.json"):
            q_s = f"'{ARCHIVE_FOLDER_ID}' in parents and name = 'AlgoEdge_Queue_State.json' and trashed = false"
            ex_s = drive_service.files().list(q=q_s, fields="files(id)").execute().get("files", [])
            media_s = MediaFileUpload("AlgoEdge_Queue_State.json", mimetype="application/json")
            if ex_s:
                drive_service.files().update(fileId=ex_s[0]["id"], media_body=media_s).execute()
            else:
                drive_service.files().create(body={"name": "AlgoEdge_Queue_State.json", "parents": [ARCHIVE_FOLDER_ID]}, media_body=media_s).execute()

        page_info_url = f"https://graph.facebook.com/v21.0/{page_id}"
        p_res = requests.get(page_info_url, params={"fields": "id,name,followers_count,fan_count", "access_token": page_token}).json()
        posts_res = requests.get(f"https://graph.facebook.com/v21.0/{page_id}/published_posts", params={"fields": "id,message,created_time,shares,likes.summary(true),comments.summary(true)", "limit": 15, "access_token": page_token}).json()

        report_data = {
            "generatedAtUtc": datetime.datetime.utcnow().isoformat() + "Z",
            "pageId": page_id,
            "pageName": p_res.get("name", "AlgoEdge Systems"),
            "followersCount": p_res.get("followers_count", 0),
            "likesCount": p_res.get("fan_count", 0),
            "autoRepliesSentThisRun": replies_sent,
            "recentPosts": posts_res.get("data", [])
        }
        with open("AlgoEdge_Page_Report.json", "w", encoding="utf-8") as rf:
            json.dump(report_data, rf, indent=2)

        q_r = f"'{ARCHIVE_FOLDER_ID}' in parents and name = 'AlgoEdge_Page_Report.json' and trashed = false"
        ex_r = drive_service.files().list(q=q_r, fields="files(id)").execute().get("files", [])
        media_r = MediaFileUpload("AlgoEdge_Page_Report.json", mimetype="application/json")
        if ex_r:
            drive_service.files().update(fileId=ex_r[0]["id"], media_body=media_r).execute()
        else:
            drive_service.files().create(body={"name": "AlgoEdge_Page_Report.json", "parents": [ARCHIVE_FOLDER_ID]}, media_body=media_r).execute()

        with open("AlgoEdge_Last_Run_Log.txt", "w", encoding="utf-8") as lf:
            lf.write("\n".join(RUN_LOGS) + "\n")
        q_l = f"'{ARCHIVE_FOLDER_ID}' in parents and name = 'AlgoEdge_Last_Run_Log.txt' and trashed = false"
        ex_l = drive_service.files().list(q=q_l, fields="files(id)").execute().get("files", [])
        media_l = MediaFileUpload("AlgoEdge_Last_Run_Log.txt", mimetype="text/plain")
        if ex_l:
            drive_service.files().update(fileId=ex_l[0]["id"], media_body=media_l).execute()
        else:
            drive_service.files().create(body={"name": "AlgoEdge_Last_Run_Log.txt", "parents": [ARCHIVE_FOLDER_ID]}, media_body=media_l).execute()

        log("[+] Exported live AlgoEdge_Page_Report.json and run logs to AlgoEdge_Archive.")
    except Exception as e:
        log(f"Notice: Could not export telemetry report to Drive: {e}")


def resolve_page_credentials(token, target_id):
    log("[*] Resolving true Graph API Page ID and Access Token...")
    url = f"https://graph.facebook.com/v21.0/me/accounts?access_token={token}"
    try:
        res = requests.get(url)
        data = res.json()
        if "data" in data and len(data["data"]) > 0:
            for page in data["data"]:
                if "algoedge" in page.get("name", "").lower():
                    true_id = str(page.get("id"))
                    page_token = page.get("access_token")
                    log(f"[+] Found AlgoEdge Systems! True Page ID: {true_id}")
                    return true_id, page_token
            for page in data["data"]:
                if str(page.get("id")) == str(target_id):
                    return str(page.get("id")), page.get("access_token")
            first_page = data["data"][0]
            return str(first_page.get("id")), first_page.get("access_token")
    except Exception as e:
        log(f"[*] Note: Could not query /me/accounts ({e})")
    return target_id, token


def publish_video_direct(page_id, page_token, video_path, caption):
    upload_url = f"https://graph-video.facebook.com/v21.0/{page_id}/videos"
    with open(video_path, "rb") as f:
        res = requests.post(upload_url, data={"description": caption, "access_token": page_token}, files={"source": f}).json()
    if "id" in res:
        log(f"[SUCCESS] Video published! Video ID: {res['id']}")
        return True
    log(f"Direct video upload failed: {res}")
    return False


def publish_facebook_reel(page_id, page_token, video_path, caption):
    init_url = f"https://graph.facebook.com/v21.0/{page_id}/video_reels"
    data = requests.post(init_url, data={"upload_phase": "start", "access_token": page_token}).json()
    if "video_id" not in data:
        return publish_video_direct(page_id, page_token, video_path, caption)

    video_id = data["video_id"]
    upload_url = data["upload_url"]
    file_size = os.path.getsize(video_path)
    headers = {"Authorization": f"OAuth {page_token}", "offset": "0", "file_size": str(file_size)}
    with open(video_path, "rb") as f:
        requests.post(upload_url, headers=headers, data=f)

    finish_res = requests.post(init_url, data={
        "upload_phase": "finish",
        "access_token": page_token,
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": caption
    }).json()
    if finish_res.get("success"):
        log(f"[SUCCESS] Reel published! Video ID: {video_id}")
        return True
    return publish_video_direct(page_id, page_token, video_path, caption)


def publish_photo_post(page_id, page_token, image_path, caption):
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    with open(image_path, "rb") as f:
        res = requests.post(url, data={"message": caption, "access_token": page_token}, files={"source": f}).json()
    if "id" in res:
        log(f"[SUCCESS] Photo post published! Post ID: {res['id']}")
        return True
    log(f"[!] Photo upload failed: {res}")
    return False


def publish_text_discussion(page_id, page_token, message_text):
    url = f"https://graph.facebook.com/v21.0/{page_id}/feed"
    res = requests.post(url, data={"message": message_text, "access_token": page_token}).json()
    if "id" in res:
        log(f"[SUCCESS] Discussion post published! Post ID: {res['id']}")
        return True
    log(f"[!] Discussion post failed: {res}")
    return False


def run_comment_auto_responder(page_id, page_token) -> int:
    url = f"https://graph.facebook.com/v21.0/{page_id}/published_posts"
    params = {"fields": "id,comments{id,message,from,comments{from}}", "limit": 10, "access_token": page_token}
    replies_sent = 0
    try:
        posts = requests.get(url, params=params).json().get("data", [])
        for post in posts:
            for comment in post.get("comments", {}).get("data", []):
                c_id = comment.get("id")
                c_msg = (comment.get("message") or "").strip()
                c_upper = c_msg.upper()
                if str(comment.get("from", {}).get("id")) == str(page_id):
                    continue
                sub_comments = comment.get("comments", {}).get("data", [])
                if any(str(sc.get("from", {}).get("id")) == str(page_id) for sc in sub_comments):
                    continue
                if any(k in c_upper for k in ["RISK", "GUARD", "LOT"]):
                    reply_text = (
                        "Thanks for reaching out! Our MT5 Risk & Prop Drawdown Guard (.ex5) is ready for your terminal. "
                        "Please click 'Message' on our Page and send your preferred pair (e.g. XAUUSD / US30) so our desk can send the direct download link and setup guide."
                    )
                elif any(k in c_upper for k in ["SWEEP", "FVG", "TREND", "CODE", "BOT", "EA"]):
                    reply_text = (
                        "Great to connect! We have verified MT5 backtest logs and execution breakdowns ready for this setup. "
                        "Send us a quick DM with the timeframe and session you trade, and our development desk will share the full parameters."
                    )
                else:
                    reply_text = (
                        "Appreciate the feedback! Mechanical execution and strict drawdown protection are the core of what we build at AlgoEdge Systems. "
                        "Feel free to DM our desk anytime if you want to test our turnkey EAs or automate your own strategy rules."
                    )
                rep_res = requests.post(f"https://graph.facebook.com/v21.0/{c_id}/comments", data={"message": reply_text, "access_token": page_token})
                if rep_res.status_code == 200:
                    replies_sent += 1
                    log(f"[+] Auto-replied to comment {c_id}")
    except Exception as e:
        log(f"[*] Note: Comment Auto-Responder notice: {e}")
    return replies_sent


if __name__ == "__main__":
    drive_service = get_drive_service()

    if "--synced" not in sys.argv and drive_service is not None:
        scripts_updated = sync_staged_code_and_state_from_drive(drive_service)
        if scripts_updated:
            log("[*] Staged scripts pulled from Google Drive! Re-running with new code...")
            subprocess.run([sys.executable, "render_algo_reel.py"], check=False)
            res = subprocess.run([sys.executable, "publish_to_meta.py", "--synced"])
            sys.exit(res.returncode)

    if not INPUT_TOKEN:
        log("ERROR: META_PAGE_ACCESS_TOKEN environment variable is not set.")
        sys.exit(1)

    true_page_id, page_token = resolve_page_credentials(INPUT_TOKEN, INPUT_PAGE_ID)

    # 1. Clean up duplicate posts on the Page
    dedup_count = deduplicate_page_posts(true_page_id, page_token)
    log(f"[*] Deduplication check complete. Duplicate posts removed: {dedup_count}")

    # 2. Ensure the dedicated Pinned Lead-Magnet post is published once
    ensure_pinned_lead_magnet_published(true_page_id, page_token)

    # 3. Publish today's scheduled/rotated content pillar
    if not os.path.exists("active_mode.txt"):
        subprocess.run([sys.executable, "render_algo_reel.py"], check=False)

    mode = "reel"
    if os.path.exists("active_mode.txt"):
        with open("active_mode.txt", "r", encoding="utf-8") as mf:
            mode = mf.read().strip().lower()

    caption = ""
    if os.path.exists("post_caption.txt"):
        with open("post_caption.txt", "r", encoding="utf-8") as cf:
            caption = cf.read().strip()

    log(f"[*] Executing Meta Graph API Publisher in mode: {mode.upper()}")

    published_ok = False
    if mode == "reel":
        published_ok = publish_facebook_reel(true_page_id, page_token, "algoedge_fvg_reel.mp4", caption)
    elif mode in ["blueprint", "diagnostics", "lead_magnet"]:
        published_ok = publish_photo_post(true_page_id, page_token, "algoedge_post.png", caption)
    elif mode == "discussion":
        published_ok = publish_text_discussion(true_page_id, page_token, caption)

    replies_count = run_comment_auto_responder(true_page_id, page_token)
    save_state_and_telemetry_to_drive(drive_service, true_page_id, page_token, replies_count)

    if not published_ok:
        sys.exit(1)
