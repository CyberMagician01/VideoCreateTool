from flask import Blueprint, render_template

page_bp = Blueprint("page", __name__)

@page_bp.get("/")
def index():
    return render_template("index.html")

@page_bp.get("/studio")
def studio():
    return render_template("studio.html")

@page_bp.get("/visual")
def visual():
    return render_template("visual.html")

@page_bp.get("/export-center")
def export_center():
    return render_template("export_center.html")

@page_bp.get("/video-lab")
def video_lab():
    return render_template("video_lab.html")