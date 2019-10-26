
import flask

app = flask.Flask(__name__)


@app.route('/')
def index():
    return 'Hello World!'

@app.route('/exif-zapper')
def zapper():
    return flask.render_template('exif-zapper.html')
