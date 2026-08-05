from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io
import os
import fitz
from PIL import Image
import numpy as np
import cv2

app = Flask(__name__)
CORS(app)

def extract_from_pdf(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        all_text = ""

        for page_num in range(min(len(doc), 10)):
            text = doc[page_num].get_text()
            if text.strip():
                all_text += f"\n📄 Page {page_num+1}:\n{text.strip()}\n" + "-"*40 + "\n"

        if not all_text.strip():
            return "⚠️ هذا الملف عبارة عن صور مصورة (Scanned)، يرجى رفع صفحاته كصور منفصلة لاستخراج النص."

        return all_text
    except Exception as e:
        return f"❌ PDF Error: {str(e)}"

def extract_from_image(file_bytes):
    try:
        img = Image.open(io.BytesIO(file_bytes))
        # استخراج أساسي للصور
        return "تم استلام الصورة بنجاح."
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

        file_bytes = file.read()

        if file.filename.lower().endswith('.pdf'):
            text = extract_from_pdf(file_bytes)
        else:
            text = extract_from_image(file_bytes)

        return jsonify({'status': 'success', 'text': text})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)