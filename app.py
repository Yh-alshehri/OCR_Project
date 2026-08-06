from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io
import os
import fitz
from PIL import Image
import easyocr
import numpy as np
import cv2
import re
import gc

app = Flask(__name__)
CORS(app)

# تحميل النماذج مرة واحدة فقط في الذاكرة لتفادي بطء التشغيل
print("Loading EasyOCR Models...")
reader_ar = easyocr.Reader(['ar', 'en'], gpu=False)
reader_en = easyocr.Reader(['en'], gpu=False)
print("Models Loaded Successfully!")

def preprocess_image_arabic(img_np):
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
        pages_done = 0

        reader = reader_ar if language == "ar" else reader_en

        for page_num in range(len(doc)):
            if pages_done >= 3:
                break

            mat = fitz.Matrix(1.5, 1.5)
            pix = doc[page_num].get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_np = np.array(img)

            if language == "ar":
                processed_img = preprocess_image_arabic(img_np)
                result = reader.readtext(processed_img, detail=1, paragraph=False)
                result.sort(key=lambda x: (x[0][0][1], -x[0][0][0]))
                text = " ".join([r[1] for r in result])
                text = re.sub(r'[^\w\s\u0600-\u06FF\u0750-\u077F0-9\.،؟]', ' ', text)
            else:
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                enhanced = cv2.equalizeHist(gray)
                result = reader.readtext(enhanced, paragraph=True)
                text = " ".join([r[1] for r in result])
                text = re.sub(r'[^\w\s\.،]', ' ', text)

            text = re.sub(r'\s+', ' ', text).strip()

            if text and len(text) > 5:
                pages_done += 1
                all_text += f"\n📄 Page {page_num+1}:\n{text}\n"
                all_text += "-" * 40 + "\n"

        gc.collect() # تنظيف الذاكرة
        return all_text if all_text.strip() else "⚠️ لم يتم العثور على نص واضح"

    except Exception as e:
        return f"❌ PDF Error: {str(e)}"

def extract_from_image(file_bytes, language):
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img_np = np.array(img)

        if language == "ar":
            reader = reader_ar
            processed_img = preprocess_image_arabic(img_np)
            result = reader.readtext(processed_img, detail=1, paragraph=False)
            result.sort(key=lambda x: (x[0][0][1], -x[0][0][0]))
            text = " ".join([r[1] for r in result])
            text = re.sub(r'[^\w\s\u0600-\u06FF\u0750-\u077F0-9\.،؟]', ' ', text)
        else:
            reader = reader_en
            if len(img_np.shape) == 3:
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_np
            enhanced = cv2.equalizeHist(gray)
            result = reader.readtext(enhanced, paragraph=True)
            text = " ".join([r[1] for r in result])
            text = re.sub(r'[^\w\s\.،]', ' ', text)

        text = re.sub(r'\s+', ' ', text).strip()
        gc.collect() # تنظيف الذاكرة
        return text if text else "⚠️ لم يتم العثور على نص في الصورة"

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

        # الالتقاط الدقيق للغة سواء كانت "العربية" أو "ar" أو "Arabic"
        raw_lang = str(request.form.get('language', 'ar')).strip().lower()
        if 'ar' in raw_lang or 'عرب' in raw_lang:
            language = 'ar'
        else:
            language = 'en'

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