from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io
import os
import fitz
import requests

app = Flask(__name__)
CORS(app)

# استخدام محرك OCR أونلاين مجاني وسريع للصور والمستندات المصورة
OCR_SPACE_API_KEY = 'helloworld'

def ocr_process_image_bytes(image_bytes, language='ar'):
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
    except Exception:
        return ""

def extract_from_pdf(file_bytes, language):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = ""

        # 1. الممر الأول: استخراج النص الرقمي المباشر (للملفات الرقمية مثل التقارير)
        for page_num in range(min(len(doc), 10)):
            text = doc[page_num].get_text()
            if text.strip():
                all_text += f"\n📄 صفحة {page_num+1}:\n{text.strip()}\n" + "-"*40 + "\n"

        # 2. الممر الثاني: إذا كان PDF مصور (Scanned مثل كتاب غير أفكارك)
        if not all_text.strip():
            for page_num in range(min(len(doc), 3)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("jpeg")
                
                ocr_result = ocr_process_image_bytes(img_bytes, language)
                if ocr_result:
                    all_text += f"\n📄 صفحة {page_num+1}:\n{ocr_result}\n" + "-"*40 + "\n"

        return all_text if all_text.strip() else "⚠️ لم يتم العثور على نص واضح في الملف."
    except Exception as e:
        return f"❌ PDF Error: {str(e)}"

def extract_from_image(file_bytes, language):
    ocr_result = ocr_process_image_bytes(file_bytes, language)
    return ocr_result if ocr_result else "⚠️ لم يتم العثور على نص واضح في الصورة."

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

        # قراءة خيار اللغة والتأكد من توجيهه بشكل صحيح
        raw_lang = str(request.form.get('language', 'ar')).strip().lower()
        if 'عرب' in raw_lang or 'ar' in raw_lang:
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