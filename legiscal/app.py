import json
import urllib
from flask import Flask, request, Response, render_template
from legiscal.cal import gen_ical, fetch_bodies

app = Flask(__name__)
BASEURL = 'https://webapi.legistar.com/v1/'


@app.route('/')
def root():
    return 'hello'


@app.route('/b/<namespace>')
def bodies(namespace):
    return render_template(
        'bodies.html',
        namespace=namespace,
        bodies=fetch_bodies(namespace)
    )


@app.route('/c/<namespace>')
def cal(namespace):
    body_list = request.args.getlist('b')
    nscal = gen_ical(namespace, bodies=body_list)
    calbin = nscal.to_ical()
    resp = Response(calbin, mimetype='text/calendar')
    return resp
