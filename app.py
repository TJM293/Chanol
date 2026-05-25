import os
import tempfile
import subprocess
import json
import time
import shutil
from flask import Flask, request, render_template, Response, send_file
import requests

app = Flask(__name__)

# === НАСТРОЙКИ ===
OLLAMA_API_KEY = "ваш ключ"
OLLAMA_URL = "https://ollama.com/v1/chat/completions"
MODEL = "qwen3-coder:480b"
TIMEOUT = 180

def clean_temp_files():
    temp_dir = tempfile.gettempdir()
    now = time.time()
    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        if os.path.isfile(filepath):
            if filename.startswith('output.') or (filename.startswith('tmp') and filename.endswith('.py')):
                try:
                    if now - os.path.getmtime(filepath) > 3600:
                        os.unlink(filepath)
                except:
                    pass

def generate_status_stream(query, file_format):
    clean_temp_files()
    try:
        yield f"data: {json.dumps({'status': 'info', 'message': '⏳ Отправка запроса в AI...'})}\n\n"
        time.sleep(0.3)

        # Улучшенный промпт с примером структуры документа
        prompt = f"""Ты — эксперт по генерации Python кода для создания официальных документов. Запрос пользователя: "{query}".

Твоя задача: написать Python код, который создаст файл 'output.{file_format}' с **полноценным, реалистичным документом**, соответствующим запросу. Документ должен быть детальным, содержать все необходимые поля, таблицы, подписи, даты, суммы (если применимо). НЕ используй слова-заглушки вроде "тестовый документ", "пример", "заполните сами". Сгенерируй правдоподобные данные.

Пример требуемой структуры для документа "Акт передачи квартиры" (адаптируй под свой запрос):

---
АКТ ПРИЕМА-ПЕРЕДАЧИ КВАРТИРЫ

г. Москва                                          "15" мая 2026 г.

Передающая сторона: Иванов Иван Иванович, паспорт 4510 123456, выдан ОВД "Тверской" г. Москвы, зарегистрирован по адресу: г. Москва, ул. Тверская, д. 10, кв. 5.
Принимающая сторона: Петрова Мария Сергеевна, паспорт 4620 654321, выдан ОВД "Арбат" г. Москвы, зарегистрирована по адресу: г. Москва, ул. Арбат, д. 15, кв. 12.

На основании Договора купли-продажи от 10.05.2026 № 123-КП настоящим стороны составили настоящий акт о том, что:
1. Передающая сторона передала, а Принимающая сторона приняла квартиру, расположенную по адресу: г. Москва, ул. Новый Арбат, д. 20, кв. 45.
2. Квартира имеет следующие характеристики:
   - Общая площадь: 65.4 кв. м
   - Жилая площадь: 42.1 кв. м
   - Количество комнат: 2
   - Этаж: 5
   - Состояние: удовлетворительное, требуется косметический ремонт.
3. Квартира передается с мебелью и техникой: холодильник "Indesit", стиральная машина "LG", кухонный гарнитур.
4. Претензий у Принимающей стороны к качеству квартиры нет.

Подписи сторон:
Иванов И.И. (подпись) ______________
Петрова М.С. (подпись) ______________
---

Если формат .docx — используй библиотеку python-docx, создай заголовки, абзацы, таблицы, жирный шрифт для важных полей.
Если .pdf — reportlab, с отступами, шрифтами, возможно рамками.
Если .txt — просто текст, но с соблюдением структуры.
Если .xlsx — openpyxl, создай таблицу с заголовками столбцов и данными.
Если .csv — csv модуль, строки с полями.

Выведи ТОЛЬКО код Python, без пояснений, без markdown-разметки (кроме ```python ... ```, но это будет удалено автоматически). Код должен создавать файл в текущей рабочей директории, быть самодостаточным. Используй реалистичные русские имена, адреса, даты, суммы."""

        headers = {
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 4000,  # увеличено для сложного документа
            "stream": True
        }

        yield f"data: {json.dumps({'status': 'info', 'message': f'🧠 Генерация кода моделью {MODEL} (это может занять до 3 минут)...'})}\n\n"

        retries = 2
        response = None
        for attempt in range(retries):
            try:
                response = requests.post(OLLAMA_URL, json=payload, headers=headers, stream=True, timeout=TIMEOUT)
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    yield f"data: {json.dumps({'status': 'info', 'message': f'⚠️ Таймаут, повторная попытка {attempt+2}...'})}\n\n"
                    time.sleep(2)
                else:
                    raise

        full_content = ""
        for line in response.iter_lines():
            if line:
                line_decoded = line.decode('utf-8')
                if line_decoded.startswith('data: '):
                    data_str = line_decoded[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get('choices', [{}])[0].get('delta', {})
                        content = delta.get('content', '')
                        full_content += content
                    except:
                        continue

        code = full_content.strip()
        if not code:
            yield f"data: {json.dumps({'status': 'error', 'message': 'Модель вернула пустой ответ'})}\n\n"
            return

        yield f"data: {json.dumps({'status': 'info', 'message': '🔧 Код получен, обработка...'})}\n\n"

        if code.startswith('```python'):
            code = code[9:]
        if code.startswith('```'):
            code = code[3:]
        if code.endswith('```'):
            code = code[:-3]
        code = code.strip()

        yield f"data: {json.dumps({'status': 'info', 'message': '⚙️ Выполнение Python скрипта...'})}\n\n"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_script = f.name

        process = subprocess.run(['python', temp_script], capture_output=True, text=True, timeout=60, cwd=tempfile.gettempdir())
        os.unlink(temp_script)

        if process.returncode != 0:
            yield f"data: {json.dumps({'status': 'error', 'message': f'Ошибка выполнения кода: {process.stderr[:300]}'})}\n\n"
            return

        output_file = os.path.join(tempfile.gettempdir(), f'output.{file_format}')
        if not os.path.exists(output_file):
            yield f"data: {json.dumps({'status': 'error', 'message': 'Файл не был создан'})}\n\n"
            return

        file_size = os.path.getsize(output_file)
        yield f"data: {json.dumps({'status': 'ready', 'message': f'✅ Файл готов ({file_size} байт)! Скачивание начнётся автоматически.', 'file_url': f'/download?file={output_file}&format={file_format}'})}\n\n"

        def schedule_deletion():
            time.sleep(120)
            try:
                os.unlink(output_file)
            except:
                pass
        import threading
        threading.Thread(target=schedule_deletion, daemon=True).start()

    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'message': f'Ошибка: {str(e)}'})}\n\n"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-stream', methods=['POST'])
def generate_stream():
    query = request.form['query']
    file_format = request.form['format']
    return Response(generate_status_stream(query, file_format), mimetype='text/event-stream')

@app.route('/download')
def download():
    file_path = request.args.get('file')
    file_format = request.args.get('format')
    if not file_path or not os.path.exists(file_path):
        return "Файл не найден или уже удалён. Попробуйте сгенерировать заново.", 404
    return send_file(file_path, as_attachment=True, download_name=f'generated.{file_format}')

if __name__ == '__main__':
    print("🚀 Сервер с улучшенным промптом на http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
