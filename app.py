from flask import Flask, render_template, request, send_from_directory, abort, url_for
import subprocess
import os
from datetime import datetime
import uuid

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def scan():
    target_url = request.form.get('target_url', '').strip()
    if not target_url:
        return render_template('index.html', output="Error: Please enter a URL.", target='')

    # create a unique filename for this scan
    scans_dirname = 'REPORTS'  # created by scanner or here
    out_filename = f"scan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.txt"

    try:
        # run scanner with working dir set to where scanner.py is
        scanner_dir = os.path.dirname(os.path.abspath(__file__))
        proc = subprocess.run(
            ['python', 'scanner.py', target_url, out_filename],
            capture_output=True,
            text=True,
            cwd=scanner_dir
        )

        stdout = proc.stdout or ''
        stderr = proc.stderr or ''

        # Choose output to display in page: prefer stdout then stderr
        display = stdout.strip() if stdout.strip() else stderr.strip()

        # Determine saved report path (absolute)
        # scanner wrote to either sibling REPORTS or local REPORTS; try both
        candidate1 = os.path.join(scanner_dir, '..', 'REPORTS', out_filename)
        candidate2 = os.path.join(scanner_dir, 'REPORTS', out_filename)
        if os.path.exists(candidate1):
            report_abs = os.path.abspath(candidate1)
            report_rel = os.path.relpath(report_abs, start=scanner_dir)
        elif os.path.exists(candidate2):
            report_abs = os.path.abspath(candidate2)
            report_rel = os.path.relpath(report_abs, start=scanner_dir)
        else:
            report_rel = None

        # Build a download URL if we found the report
        report_url = None
        if report_rel:
            # we'll serve reports via /reports/<filename>
            report_url = url_for('download_report', filename=os.path.basename(report_rel))

        return render_template('index.html', output=display, target=target_url, report_path=report_url)

    except Exception as e:
        return render_template('index.html', output=f"Exception: {e}", target=target_url)

@app.route('/reports/<path:filename>')
def download_report(filename):
    # serve only from known REPORTS directories
    scanner_dir = os.path.dirname(os.path.abspath(__file__))
    parent_reports = os.path.abspath(os.path.join(scanner_dir, '..', 'REPORTS'))
    local_reports = os.path.abspath(os.path.join(scanner_dir, 'REPORTS'))

    # allow file only if it exists inside one of the reports dirs
    for d in (parent_reports, local_reports):
        candidate = os.path.join(d, filename)
        if os.path.exists(candidate):
            # use send_from_directory for safe serving
            return send_from_directory(d, filename, as_attachment=True)
    # not found
    abort(404)

if __name__ == '__main__':
    app.run(debug=True)
