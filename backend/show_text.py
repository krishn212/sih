import sys
import os
from PIL import Image
from dotenv import load_dotenv
from google import genai

# Ensure Windows PowerShell handles Unicode like Rupee symbol
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
    sys.exit(1)

client = genai.Client(api_key=api_key)

image_path = sys.argv[1] if len(sys.argv) > 1 else "WIN_20260906_21_57_19_Pro.jpg"

if not os.path.exists(image_path):
    print(f"Error: File '{image_path}' not found.")
    sys.exit(1)

print(f"\nScanning image: {image_path} with Gemini Vision...\n" + "=" * 60 + "\n")
img = Image.open(image_path)

from google.genai import types

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        img,
        """Strictly transcribe all visible text on this product label.
RULES:
1. Do NOT guess, deduce, or calculate missing information (e.g. do not calculate expiry date from best before).
2. Transcribe numbers, dates, and volumes character-by-character exactly as printed on the bottle (e.g. read exact volume in ml, do not round to 200 ml).
3. If a field or line is not physically inked on the label, do not include it.
4. Output literal text only."""
    ],
    config=types.GenerateContentConfig(
        temperature=0.0,
    )
)

print(response.text)
print("\n" + "=" * 60)
