from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io
import os
import fitz
import requests

app = Flask(__name__)
CORS(app)

# استخدام خدمة OCR مجانية وسريعة للصور والصفحات المصورة بدون استهلاك ذاكرة السيرفر
OCR_SPACE_API_KEY = 'helloworld'  # المفتاح المجاني العام للاختبار

def ocr_space_file(file_bytes, filename, language='ara'):
    """ استخراج النص من الصور أو الـ PDF عبر API مجاني خفيف """
    try:
        lang_code = 'ara' if language == 'ar' else 'eng'
        payload = {
            'apikey': OCR_SPACE_API_KEY,
            'language': lang_code,
            'isOverlayRequired': False,
            'OCREngine': 2, # Engine 2 ممتازة جداً للغة العربية
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
                extracted_text += f"\n📄 Page/Section {i+1}:\n{text}\n" + "-"*40 + "\n"
                
        return extracted_text if extracted_text.strip() else "⚠️ لم يتم العثور على نص واضح."
    except Exception as e:
        return f"❌ OCR API Error: {str(e)}"

def extract_from_pdf(file_bytes, filename, language):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = ""

        # أولاً: المحاولة عبر استخراج النص الرقمي مباشرة (سريع جداً وخفيف)
        for page_num in range(min(len(doc), 10)):
            text = doc[page_num].get_text()
            if text.strip():
                all_text += f"\n📄 Page {page_num+1}:\n{text.strip()}\n" + "-"*40 + "\n"

        # ثانياً: إذا كان الملف عبارة عن صور مسحوبة ضوئياً (Scanned PDF)
        if not all_text.strip():
            print("PDF contains images, routing to OCR Engine...")
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

        language = request.form.get('language', 'ar')
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