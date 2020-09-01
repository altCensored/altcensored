from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
    send_from_directory, make_response, session, current_app )
from . import util

bp = Blueprint('playlist', __name__, url_prefix='/playlist')


@bp.route('/')
def index():
    return render_template('playlist/playlist_index.html')
