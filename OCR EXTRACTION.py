import google.generativeai as genai
import os
import cv2
import numpy as np
from PIL import Image
import io
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

def perform_ocr(image_path, api_key=None, model_name='gemini-1.5-flash'):
    # Retrieve API key from parameter or environment variable.
    if api_key is None:
        api_key = "AIzaSyCVYGVvDKV5bg6Hd2TtrSEIbx0g6hTYnpI"
    if not api_key:
        raise ValueError("API key is required for Gemini API.")

    # Configure the Gemini API.
    genai.configure(api_key=api_key)

    # --- Step 1: Load the image using OpenCV ---
    original_image = cv2.imread(image_path)
    if original_image is None:
        raise FileNotFoundError(f"Image file not found at path: {image_path}")

    # --- Step 2: Convert to Grayscale ---
    gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

    # --- Step 3: Convert the processed image to a byte stream for Gemini API ---
    processed_pil = Image.fromarray(gray)
    buffered = io.BytesIO()
    processed_pil.save(buffered, format="JPEG")
    img_bytes = buffered.getvalue()

    # --- Step 4: Define the prompt for text extraction ---
    prompt = (
    """Extract and return only the text but all the text from the image, correcting any spelling errors while preserving the original meaning. Format the text into a well-structured paragraph with proper spacing and punctuation. Do not include any extra words, explanations, or indicators—output only the corrected and neatly formatted text.""")

    contents = [
        {
            "parts": [
                prompt,
                {"mime_type": "image/jpeg", "data": img_bytes},
            ]
        },
    ]

    # --- Step 5: Call the Gemini API ---
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(contents)

    if response.prompt_feedback and response.prompt_feedback.block_reason:
        raise Exception(f"Prompt was blocked due to: {response.prompt_feedback.block_reason}. "
                        f"Safety ratings: {response.prompt_feedback.safety_ratings}")

    # Return the extracted text.
    return response.text

# Example usage:
if _name_ == "_main_":
    test_image_path = r"C:\Users\Pc\OneDrive\Desktop\WhatsApp Image 2025-03-13 at 10.49.11_b8618fca.jpg" # Update with your actual image path
    try:
        ocr_text = perform_ocr(test_image_path)
        print("Extracted Text (OCR):\n")
        print(ocr_text)
    except Exception as e:
        print(f"Error during OCR processing: {e}")