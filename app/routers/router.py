from flask import Blueprint, render_template, request, session
from app import socketio
import os
from app.gemini.modelo import responder_pergunta

bp = Blueprint("chat", __name__)

