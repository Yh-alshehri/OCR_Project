from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io
import os
import fitz
import requests
from PIL import Image

app = Flask(__name__)
CORS(app)

OCR_SPACE_API_KEY = 'helloworld'

def ocr_space_bytes(image_bytes, language='ar'):
    """ إرسال مصفوفة الصورة المباشرة للـ API """
    try:
        lang_code = 'arabic' if language == 'ar' else 'eng'
        
        payload = {
            'apikey': OCR_SPACE_API_KEY,
            'language': lang_code,
            'isOverlayRequired': False,
            'OCREngine': 2,
        }
        files = {
            'file': ('image.jpg', image_bytes, 'image/jpeg')
        }
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files=files,
            data=payload,
            timeout=30
        )
        result = response.json()
        
        if result.get("IsErroredOnProcessing"):
            return ""
        
        parsed_results = result.get("ParsedResults", [])
        if parsed_results:
            return parsed_results[0].get("ParsedText", "").strip()
        return ""
    except Exception as e:
        return ""

def extract_from_pdf(file_bytes, language):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = ""

        # 1. المحاولة الأولى: قراءة النص الرقمي المباشر
        for page_num in range(min(len(doc), 5)):
            text = doc[page_num].get_text()
            if text.strip():
                all_text += f"\n📄 صفحة {page_num+1}:\n{text.strip()}\n" + "-"*40 + "\n"

        # 2. إذا كان الملف Scanned (صور)، نحول كل صفحة لصورة ونستخرج نصها عبر الـ OCR
        if not all_text.strip():
            for page_num in range(min(len(doc), 3)): # معالجة أول 3 صفحات لتفادي البطء
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("jpeg")
                
                ocr_text = ocr_space_bytes(img_bytes, language)
                if ocr_text:
                    all_text += f"\n📄 صفحة {page_num+1}:\n{ocr_text}\n" + "-"*40 + "\n"

        return all_text if all_text.strip() else "⚠️ لم يتم العثور على نص واضح في الملف."
    except Exception as e:
        return f"❌ PDF Error: {str(e)}"

def extract_from_image(file_bytes, language):
    text = ocr_space_bytes(file_bytes, language)
    return text if text else "⚠️ لم يتم العثور على نص في الصورة."

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

        lang_input = request.form.get('language', 'ar').lower()
        if 'عرب' in lang_input or lang_input in ['ar', 'ara', 'arabic']:
            language = 'ar'
        else:
            language = 'en'

        file_bytes = file.read()
        filename = file.filename

        if filename.lower().endswith('.pdf'):
            text = extract_from_pdf(file_bytes, language)
        else:
            text = extract_from_image(file_bytes, language)

        return jsonify({'status': 'success', 'text': text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)