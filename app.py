from flask import Flask, render_template, request, jsonify, session
import os
import io
from datetime import datetime
from chatbot import get_lawbot_response, LANGUAGES

# Optional: Google AI Studio (Gemini) integration
try:
    import google.generativeai as genai
except ImportError:
    genai = None

app = Flask(__name__)
app.secret_key = 'lawbot_secret_key'  # Required for session


# ---------- Pages ----------
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/query')
def query_page():
    return render_template('query.html', languages=LANGUAGES)


@app.route('/complaint')
def complaint_page():
    return render_template('complaint.html')


@app.route('/contact')
def contact_page():
    return render_template('contact.html')


# ---------- APIs ----------
@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(force=True)
    user_input = data.get('message', '')
    selected_lang = data.get('language')

    response = get_lawbot_response(user_input, selected_lang)
    detected_lang = response.get('detected_language', 'en')

    return jsonify({
        'reply': response['text'],
        'detected_language': detected_lang,
        'language_name': LANGUAGES.get(detected_lang, 'English')
    })


@app.route('/ai_ask', methods=['POST'])
def ai_ask():
    """Proxy to Google AI Studio (Gemini). Requires env var GOOGLE_API_KEY."""
    data = request.get_json(force=True)
    prompt = data.get('message', '').strip()
    if not prompt:
        return jsonify({'error': 'Empty prompt'}), 400

    api_key = os.environ.get('GOOGLE_API_KEY')
    if genai is None:
        return jsonify({'error': 'google-generativeai package not installed. Add google-generativeai to requirements.'}), 500
    if not api_key:
        return jsonify({'error': 'Missing GOOGLE_API_KEY environment variable.'}), 500

    try:
        genai.configure(api_key=api_key)
        # Fast, cost-effective default model
        model = genai.GenerativeModel('gemini-1.5-flash')
        system_preamble = (
            "You are LawBot, a helpful legal assistant for India. "
            "Explain legal topics in simple terms and include references to IPC/CrPC when relevant. "
            "Always include a short disclaimer: This is informational and not legal advice."
        )
        full_prompt = f"{system_preamble}\n\nUser query: {prompt}"
        result = model.generate_content(full_prompt)
        text = result.text or "I'm sorry, I couldn't generate a response."
        return jsonify({'reply': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/languages', methods=['GET'])
def get_languages():
    return jsonify(LANGUAGES)


@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    data = request.get_json(force=True)
    # Here you can persist to a DB or send an email/integration
    # For now, just echo back a success
    return jsonify({'status': 'received', 'data': data})


@app.route('/contact_submit', methods=['POST'])
def contact_submit():
    data = request.get_json(force=True)
    # Here you can persist to a DB or send an email/integration
    # For now, just echo back a success
    return jsonify({'status': 'received', 'data': data})


@app.route('/complaint_pdf', methods=['POST'])
def complaint_pdf():
    """Generate a professional PDF draft of the complaint and send as download."""
    try:
        data = request.get_json(force=True)
    except Exception:
        data = {}

    # Prepare fields with defaults
    name = (data.get('name') or '').strip() or '—'
    email = (data.get('email') or '').strip() or '—'
    phone = (data.get('phone') or '').strip() or '—'
    location = (data.get('location') or '').strip() or '—'
    incident_type = (data.get('incident_type') or '').strip() or '—'
    incident_date = (data.get('incident_date') or '').strip() or '—'
    incident_location = (data.get('incident_location') or '').strip() or '—'
    summary = (data.get('summary') or '').strip() or '—'
    parties = (data.get('parties') or '').strip() or '—'
    evidence = (data.get('evidence') or '').strip() or '—'

    # Lazy import ReportLab to avoid hard failure if not installed yet
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        from reportlab.lib import colors
    except ImportError:
        return jsonify({'error': 'ReportLab not installed. Please add reportlab to requirements and install.'}), 500

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Margins
    margin_left = 25 * mm
    margin_right = 25 * mm
    x = margin_left
    y = height - 30 * mm

    # Header
    pdf.setFillColor(colors.HexColor('#3a6186'))
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(x, y, 'Complaint Draft')
    pdf.setFillColor(colors.black)
    pdf.setFont('Helvetica', 10)
    pdf.drawRightString(width - margin_right, y, datetime.now().strftime('%d %b %Y'))
    y -= 8 * mm
    pdf.setStrokeColor(colors.HexColor('#89253e'))
    pdf.setLineWidth(2)
    pdf.line(margin_left, y, width - margin_right, y)
    y -= 10 * mm

    def draw_section(title, lines):
        nonlocal y
        if y < 40 * mm:
            pdf.showPage()
            y = height - 30 * mm
        pdf.setFont('Helvetica-Bold', 12)
        pdf.setFillColor(colors.HexColor('#89253e'))
        pdf.drawString(x, y, title)
        pdf.setFillColor(colors.black)
        y -= 6 * mm
        pdf.setLineWidth(0.5)
        pdf.setStrokeColor(colors.HexColor('#cccccc'))
        pdf.line(margin_left, y, width - margin_right, y)
        y -= 5 * mm
        pdf.setFont('Helvetica', 11)
        for line in lines:
            for wrapped in wrap_text(line, width - margin_left - margin_right, pdf, 'Helvetica', 11):
                if y < 20 * mm:
                    pdf.showPage()
                    y = height - 30 * mm
                    pdf.setFont('Helvetica', 11)
                pdf.drawString(x, y, wrapped)
                y -= 6 * mm
        y -= 4 * mm

    def wrap_text(text, max_width, canv, font_name, font_size):
        canv.setFont(font_name, font_size)
        words = (text or '').split()
        lines, line = [], ''
        for w in words:
            test = (line + ' ' + w).strip()
            if canv.stringWidth(test) <= max_width:
                line = test
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines or ['']

    # Content sections
    draw_section('Complainant Details', [
        f'Name: {name}',
        f'Email: {email}',
        f'Phone: {phone}',
        f'City/State: {location}',
    ])

    draw_section('Incident Details', [
        f'Type of Incident: {incident_type}',
        f'Date: {incident_date}',
        f'Location: {incident_location}',
    ])

    draw_section('Brief Summary', [summary])
    draw_section('Parties Involved', [parties])
    draw_section('Evidence/Attachments', [evidence])

    # Footer note
    if y < 30 * mm:
        pdf.showPage()
        y = height - 30 * mm
    pdf.setFont('Helvetica-Oblique', 9)
    pdf.setFillColor(colors.HexColor('#666666'))
    pdf.drawString(x, 20 * mm, 'This draft is generated by LawBot for information only and is not legal advice.')

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    fname = f"Complaint_Draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return (
        buffer.read(),
        200,
        {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{fname}"'
        }
    )


if __name__ == '__main__':
    app.run(debug=True)
