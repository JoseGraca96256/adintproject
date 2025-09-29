import qrcode
from flask import Flask, render_template, request, send_file
import io

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def generate_qr():
    if request.method == "GET":
        return render_template("qrcode.html")
    else:
        # Get user input
        text = request.form["qrText"]

        # Generate QR code
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Send QR code as response
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
