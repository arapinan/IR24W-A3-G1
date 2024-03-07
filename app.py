from flask import Flask, render_template, request, flash
import indexer

app = Flask(__name__)
app.secret_key = "000"

@app.route("/")
def index():
	return render_template("index.html")

@app.route("/query", methods=['POST', 'GET'])
def getResults():
	queryInput = str(request.form['name_input'])
	#results = indexer.tokenize("DEV/cert_ics_uci_edu/948f66bf8fdd193f5eb74187895b656377f02cf98907582fc065fb81a032aad0.json")
	flash('Showing results for "' + str(request.form['name_input']) + '"')
	results = indexer.stud(queryInput)
	for url in results:
		flash(url)
	return render_template("index.html")
