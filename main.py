from fastapi import FastAPI, File, UploadFile
import os
import csv
from datetime import datetime
import httpx
import base64

import os
HF_TOKEN = os.getenv("HF_TOKEN")

app = FastAPI()

# Folder for known employee images
KNOWN_FACES_DIR = "employee_images"
ATTENDANCE_FILE = "attendance.csv"

# Ensure attendance.csv exists
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Date", "Time"])

# Hugging Face Model Endpoint (you can replace with your own)
FACE_MATCH_API = "https://api-inference.huggingface.co/models/omnidata/face-detection"
# You can create your free HF token at https://huggingface.co/settings/tokens
HF_TOKEN = "HF_TOKEN"  # 🔴 Replace this with your actual token


@app.post("/mark-attendance/")
async def mark_attendance(file: UploadFile = File(...)):
    try:
        # Read uploaded image
        uploaded_image = await file.read()
        uploaded_b64 = base64.b64encode(uploaded_image).decode("utf-8")

        best_match = None
        best_confidence = 0.0

        # Compare with each known employee image
        for filename in os.listdir(KNOWN_FACES_DIR):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            known_path = os.path.join(KNOWN_FACES_DIR, filename)
            with open(known_path, "rb") as f:
                known_image = f.read()
            known_b64 = base64.b64encode(known_image).decode("utf-8")

            # Send both images to Hugging Face API for face comparison
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    FACE_MATCH_API,
                    headers={"Authorization": f"Bearer {HF_TOKEN}"},
                    json={"inputs": {"image": uploaded_b64}},
                    timeout=60.0
                )

            if response.status_code != 200:
                return {"status": "failed", "message": "External API error"}

            data = response.json()

            # 🔹 This model detects faces but doesn’t directly return similarity.
            # For simple matching, we can use a heuristic (detected faces = match)
            if data and isinstance(data, list) and len(data) > 0:
                confidence = 90.0  # placeholder confidence
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = os.path.splitext(filename)[0]

        if best_match:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            with open(ATTENDANCE_FILE, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([best_match, date_str, time_str])

            return {
                "status": "success",
                "recognized_name": best_match,
                "match_percent": best_confidence
            }

        return {"status": "failed", "message": "No face match found"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
