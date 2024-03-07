import time
from flask import Flask, render_template, request, flash
import orjson
import indexer

app = Flask(__name__)
app.secret_key = "000"

@app.route("/")
def index():
	return render_template("index.html")

@app.route("/query", methods=['POST', 'GET'])
def getResults():
	#results = indexer.tokenize("DEV/cert_ics_uci_edu/948f66bf8fdd193f5eb74187895b656377f02cf98907582fc065fb81a032aad0.json")
	# flash('Showing results for "' + str(request.form['name_input']) + '"')
	
	# load the token locations file
	with open("combined_token_locations.json", "r") as token_loc_file:
		loaded_token_loc_dict = orjson.loads(token_loc_file.read())    

	# load the url dict from file
	with open("url_dict.json", "r") as url_dict_file:
		loaded_url_dict = orjson.loads(url_dict_file.read())    
	
	queryInput = str(request.form['name_input'])

	# start the timer in ms
	start_time = time.time_ns() // 1000000   

	url_results, result_query, exact_query = indexer.process_search(queryInput, loaded_token_loc_dict, loaded_url_dict)
	
	# print the results
	if url_results == []:
		flash('No results for "' + queryInput + '"')
	else:
		if not exact_query:
			flash('No results for "' + queryInput + '".' + "\n" + 'Showing results for "' + result_query + '"')
			for num, url in enumerate(url_results):
				flash(str(num + 1) + ". " + url)
		else:
			flash('Showing results for "' + result_query + '"')
			for num, url in enumerate(url_results):
				flash(str(num + 1) + ". " + url)

	# end timer
	end_time = time.time_ns() // 1000000

	# calculate execution time
	execution_time = end_time - start_time
	flash("Search time: " + str(execution_time) + " ms")

	# for url in results:
	# 	flash(url)
	return render_template("index.html")
