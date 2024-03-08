To use this search engine software, begin by creating the index. After the index is created, start the Web GUI search interface and begin performing simple queries. For step by step guidelines, follow the instructions below in the specified order.

How to run the code that creates the index:
1. Run the indexer.py file and wait for the program to finish running. There are five messages printed in the terminal that give updates on the status of the program:
   1. Dumped partial index 1
   2. Dumped partial index 2
   3. Dumped partial index 3
   4. Dumped partial index 4
   5. Merged all partial indices
2. Please note that this may take about an hour to finish running.

How to start the search interface:
1. Type the command “flask run” in your terminal.
2. A message will be generated with a local link. Here is an example: “Running on http://127.0.0.1:5000”
3. Open this url in a browser of your choice. The search interface should appear fully functional as long as you don’t exit or end the “flask run” command in your terminal.

How to perform a simple query:
1. Click on the search bar and type in your query.
2. Either hit enter/return on your keyboard or click the search button.
3. The top five ordered results will quickly appear in less than 100ms below the search bar, along with the time in ms that it took to get these results.
4. You can search for another query by repeating steps 1-3. The results for the new query will replace the existing ones.