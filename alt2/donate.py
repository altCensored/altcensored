from flask import (Blueprint, render_template)
from .models import Crypto
from .cache import cache

bp = Blueprint('donate', __name__, url_prefix='/donate' )

@bp.route('/')
@cache.cached()
def index():
    cryptos = Crypto.query.all()

    return render_template('donate/donate_index.html', cryptos=cryptos)


