from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io
import os
import fitz
from PIL import Image
import pytesseract
import numpy as np
import cv2

app = Flask(__name__)
CORS(app)

def preprocess_image(img_np):
    try:
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        return binary
    except:
        return img_np

def extract_from_pdf(file_bytes, language):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = ""
        lang_code = 'ara' if language == 'ar' else 'eng'

        for page_num in range(min(len(doc), 5)):
            pix = doc[page_num].get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_np = np.array(img)
            processed = preprocess_image(img_np)
            
            text = pytesseract.image_to_string(processed, lang=lang_code)
            if text.strip():
                all_text += f"\n📄 Page {page_num+1}:\n{text.strip()}\n" + "-"*40 + "\n"

        return all_text if all_text.strip() else "⚠️ لم يتم العثور على نص واضح"
    except Exception as e:
        return f"❌ PDF Error: {str(e)}"

def extract_from_image(file_bytes, language):
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img_np = np.array(img)
        processed = preprocess_image(img_np)
        lang_code = 'ara' if language == 'ar' else 'eng'
        
        text = pytesseract.image_to_string(processed, lang=lang_code)
        return text.strip() if text.strip() else "⚠️ لم يتم العثور على نص في الصورة"
    except Exception as e:
        return f"❌ Image Error: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract_text():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'File name is empty'}), 400

        language = request.form.get('language', 'ar')
        file_bytes = file.read()

        if file.filename.lower().endswith('.pdf'):
            text = extract_from_pdf(file_bytes, language)
        else:
            text = extract_from_image(file_bytes, language)

        return jsonify({'status': 'success', 'text': text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)