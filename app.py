from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()

ROLES = ["super_admin", "kepala_sekolah", "wakil_kepala_sekolah", "staff"]
TEMPLATES = [
    "surat_keputusan",
    "surat_keterangan",
    "surat_tugas",
    "surat_pernyataan",
]


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(40), nullable=False)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)


class IncomingLetter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(64), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    sender = db.Column(db.String(128), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    disposition_to = db.Column(db.String(128), nullable=True)
    disposition_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    category = db.relationship("Category")


class OutgoingLetter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(64), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    recipient = db.Column(db.String(128), nullable=False)
    template_type = db.Column(db.String(64), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    @app.context_processor
    def inject_user():
        user = None
        if session.get("user_id"):
            user = db.session.get(User, session["user_id"])
        return {"current_user": user}

    def require_login():
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return None

    @app.route("/")
    def index():
        return redirect(url_for("dashboard"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                session["user_id"] = user.id
                flash("Login berhasil", "success")
                return redirect(url_for("dashboard"))
            flash("Username/password salah", "danger")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    def dashboard():
        guard = require_login()
        if guard:
            return guard

        incoming_count = IncomingLetter.query.count()
        outgoing_count = OutgoingLetter.query.count()
        role_count = Counter([u.role for u in User.query.all()])

        monthly = defaultdict(int)
        for letter in IncomingLetter.query.all():
            monthly[letter.created_at.strftime("%Y-%m")] += 1

        return render_template(
            "dashboard.html",
            incoming_count=incoming_count,
            outgoing_count=outgoing_count,
            role_count=role_count,
            labels=list(monthly.keys()),
            values=list(monthly.values()),
        )

    @app.route("/categories", methods=["GET", "POST"])
    def categories():
        guard = require_login()
        if guard:
            return guard

        if request.method == "POST":
            name = request.form["name"]
            if not Category.query.filter_by(name=name).first():
                db.session.add(Category(name=name))
                db.session.commit()
        return render_template("categories.html", categories=Category.query.order_by(Category.name).all())

    @app.route("/incoming", methods=["GET", "POST"])
    def incoming():
        guard = require_login()
        if guard:
            return guard

        categories = Category.query.order_by(Category.name).all()
        if request.method == "POST":
            db.session.add(
                IncomingLetter(
                    number=request.form["number"],
                    subject=request.form["subject"],
                    sender=request.form["sender"],
                    category_id=int(request.form["category_id"]),
                )
            )
            db.session.commit()
            return redirect(url_for("incoming"))
        letters = IncomingLetter.query.order_by(IncomingLetter.created_at.desc()).all()
        return render_template("incoming.html", letters=letters, categories=categories, roles=ROLES)

    @app.route("/incoming/<int:letter_id>/disposition", methods=["POST"])
    def disposition(letter_id: int):
        guard = require_login()
        if guard:
            return guard

        letter = db.session.get(IncomingLetter, letter_id)
        letter.disposition_to = request.form["disposition_to"]
        letter.disposition_note = request.form["disposition_note"]
        db.session.commit()
        return redirect(url_for("incoming"))

    @app.route("/outgoing", methods=["GET", "POST"])
    def outgoing():
        guard = require_login()
        if guard:
            return guard

        if request.method == "POST":
            db.session.add(
                OutgoingLetter(
                    number=request.form["number"],
                    subject=request.form["subject"],
                    recipient=request.form["recipient"],
                    template_type=request.form["template_type"],
                    content=request.form["content"],
                )
            )
            db.session.commit()
            return redirect(url_for("outgoing"))

        letters = OutgoingLetter.query.order_by(OutgoingLetter.created_at.desc()).all()
        return render_template("outgoing.html", letters=letters, templates=TEMPLATES)

    @app.route("/reports/recap.pdf")
    def report_pdf():
        guard = require_login()
        if guard:
            return guard

        buf = BytesIO()
        pdf = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        y = height - 40

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, y, "Rekap Laporan Surat")
        y -= 25
        pdf.setFont("Helvetica", 10)
        pdf.drawString(40, y, f"Tanggal cetak: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
        y -= 25

        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(40, y, "Surat Masuk")
        y -= 18
        pdf.setFont("Helvetica", 10)
        for item in IncomingLetter.query.order_by(IncomingLetter.created_at.desc()).limit(20):
            pdf.drawString(45, y, f"{item.number} | {item.subject} | {item.sender} | {item.category.name}")
            y -= 14
            if y < 80:
                pdf.showPage()
                y = height - 40

        y -= 10
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(40, y, "Surat Keluar")
        y -= 18
        pdf.setFont("Helvetica", 10)
        for item in OutgoingLetter.query.order_by(OutgoingLetter.created_at.desc()).limit(20):
            pdf.drawString(45, y, f"{item.number} | {item.subject} | {item.recipient} | {item.template_type}")
            y -= 14
            if y < 80:
                pdf.showPage()
                y = height - 40

        pdf.save()
        data = buf.getvalue()
        buf.close()
        return Response(
            data,
            mimetype="application/pdf",
            headers={"Content-Disposition": "inline; filename=rekap-laporan-surat.pdf"},
        )

    return app


def seed_data(app: Flask):
    with app.app_context():
        db.create_all()

        if not User.query.first():
            users = [
                ("superadmin", "admin123", "super_admin"),
                ("kepsek", "admin123", "kepala_sekolah"),
                ("wakasek", "admin123", "wakil_kepala_sekolah"),
                ("staff", "admin123", "staff"),
            ]
            for username, password, role in users:
                db.session.add(
                    User(username=username, password_hash=generate_password_hash(password), role=role)
                )

        default_categories = ["Umum", "Kepegawaian", "Kesiswaan", "Keuangan"]
        for category in default_categories:
            if not Category.query.filter_by(name=category).first():
                db.session.add(Category(name=category))

        db.session.commit()
