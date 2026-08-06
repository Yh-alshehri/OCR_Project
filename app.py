from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io
import os
import fitz
import requests

app = Flask(__name__)
CORS(app)

# مفتاح API مجاني لخدمة استخراج النصوص
OCR_SPACE_API_KEY = 'helloworld'

def ocr_space_file(file_bytes, filename, language='ar'):
    """ استخراج النص من الصور والملفات المصورة """
    try:
        # ضبط رمز اللغة العربي المناسب لـ API
        lang_code = 'arabic' if language == 'ar' else 'eng'
        
        payload = {
            'apikey': OCR_SPACE_API_KEY,
            'language': lang_code,
            'isOverlayRequired': False,
            'OCREngine': 2,  # المحرك المخصص والممتاز للغة العربية
        }
        files = {
            'file': (filename, file_bytes)
        }
        response = requests.post(
            'https://api.ocr.space/parse/image',
            files=files,
            data=payload,
            timeout=30
        )
        result = response.json()
        
        if result.get("IsErroredOnProcessing"):
            return f"❌ خطأ في المعالجة: {result.get('ErrorMessage')}"
        
        parsed_results = result.get("ParsedResults", [])
        extracted_text = ""
        for i, page in enumerate(parsed_results):
            text = page.get("ParsedText", "").strip()
            if text:
                extracted_text += f"\n📄 صفحة / جزء {i+1}:\n{text}\n" + "-"*40 + "\n"
                
        return extracted_text if extracted_text.strip() else "⚠️ لم يتم العثور على نص واضح."
    except Exception as e:
        return f"❌ OCR API Error: {str(e)}"

def extract_from_pdf(file_bytes, filename, language):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = ""

        # 1. محاولة استخراج النص المباشر من الـ PDF (إذا كان نصياً وليس صورة)
        for page_num in range(min(len(doc), 10)):
            text = doc[page_num].get_text()
            if text.strip():
                all_text += f"\n📄 صفحة {page_num+1}:\n{text.strip()}\n" + "-"*40 + "\n"

        # 2. إذا كان الـ PDF عبارة عن صور مصورة (Scanned PDF)، يتم توجيهه للـ OCR
        if not all_text.strip():
            all_text = ocr_space_file(file_bytes, filename, language)

        return all_text
    except Exception as e:
        return f"❌ PDF Error: {str(e)}"

def extract_from_image(file_bytes, filename, language):
    return ocr_space_file(file_bytes, filename, language)

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

        # قراءة خيار اللغة من الواجهة وضبطه سواء جاء "ar" أو "العربية"
        lang_input = request.form.get('language', 'ar').lower()
        if 'عرب' in lang_input or lang_input in ['ar', 'ara', 'arabic']:
            language = 'ar'
        else:
            language = 'en'

        file_bytes = file.read()
        filename = file.filename

        if filename.lower().endswith('.pdf'):
            text = extract_from_pdf(file_bytes, filename, language)
        else:
            text = extract_from_image(file_bytes, filename, language)

        return jsonify({'status': 'success', 'text': text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)