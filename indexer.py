import os
import time
import orjson
import re
from nltk.stem import PorterStemmer, SnowballStemmer
from bs4 import BeautifulSoup
import pandas as pd
import math

# dict where key is the file and the value is the doc id 
file_id_dict = {}

# keep track the length of each document
file_wordcount_dict = {}

# list of all partial indices
partial_indices = []

# current partial index dict
partial_index = {}

# set for all unique tokens
word_set = set()

# threshold for max tokens per partial index
partial_index_threshold = 90000

# number of files processed
file_count = 0

max_file_size = 20 * 1024 * 1024

token_locs = {}

combined_token_locs = {}

# final file for inverted index
output_file = "inverted_index.json"


def tokenize(file: str) -> list:
    global file_count
    """
    Tokenize the text from a specified file.
    """
    try:
        # open the file and read its contents
        with open(file, "r") as input_file:
            file_info = orjson.loads(input_file.read())
         
        # check if the content is in HTML format
        if "</html>" not in file_info["content"].lower():
            # skip non-HTML content
            return []
        
        # increment file count
        file_count += 1

        content = file_info["content"]
        
        # create a bs obj to scrape the content
        soup = BeautifulSoup(content, "html.parser")
        
        # remove extra whitespace
        text = re.sub(r'\s+', ' ', soup.get_text())

        # use regex to split on non-alphanumeric characters
        tokens = re.split(r'[^a-zA-Z0-9]+', text.lower())

        # remove empty strings and single chars from token list
        tokens = [token for token in tokens if token and len(token) > 1]

        # sort the tokens
        tokens = sorted(tokens)

        return tokens
    except FileNotFoundError as e:
        return []


def stem_tokens(tokens: list) -> list:
    """
    Using the porter stemming technique to derive the root of words.
    """ 
    # stem plurals to singles
    plural_stemmer = PorterStemmer()
    tokens = [plural_stemmer.stem(token) for token in tokens]

    # stem roots
    snowball_stemmer = SnowballStemmer("english")
    tokens = [snowball_stemmer.stem(token) for token in tokens]
    return tokens


def process_tokens(file):
    # similar_files = False
            
    # add the file to the file_id_dict dictionary for future reference
    if file not in file_id_dict:
        # get the alphanumeric tokens
        tokens = tokenize(file)
        # stem the tokens 
        tokens = stem_tokens(tokens)

        for token in tokens:
            word_set.add(token)
    
        dict_length = len(file_id_dict)
        doc_id = dict_length + 1
        file_id_dict[file] = doc_id

        # update the word count
        file_wordcount_dict[doc_id] = len(tokens)
    return tokens


def process_file(file, tokens):
    """
    add tokens to partial index
    """
    for token in tokens:
        # if word exists in inverted_index -> increase frequency
        if token in partial_index:
            occurences = partial_index[token]
            word_found_in_file = False
            for occurence in occurences:
                if occurence[0] == file_id_dict[file]:
                    occurence[1] += 1
                    word_found_in_file = True
                    break
            if word_found_in_file == False:
                occurences.append([file_id_dict[file], 1])
        # if not -> add to inverted_index (value = [(id, 1)])
        else:
            partial_index[token] = [[file_id_dict[file], 1]]
        

def dump_partial_index():
    """
    Dump the partial index to a file in JSON format and merge with the existing merged index.
    """
    global partial_index

    token_loc_dict = {}

    # write partial index to a JSON file
    with open(f"{len(partial_indices)}.json", "w") as partial_index_file:
        for token, freq in partial_index.items():
            loc = partial_index_file.tell()
            token_loc_dict[token] = loc
            json_data = {token: freq}
            partial_index_file.write(orjson.dumps(json_data).decode())
            # add a newline to separate records
            partial_index_file.write('\n')  

    token_locs[f"{len(partial_indices)}.json"] = token_loc_dict

    # clear the partial index dict
    partial_index.clear()

    # add the partial index to partial_indices
    partial_indices.append(f"{len(partial_indices)}.json")

    # update result file
    write_result_to_file()
    print("dumped partial index", len(partial_indices))


def merge_partial_indices():
    """
    merge all partial indices
    """
    global partial_indices

    with open(output_file, "w") as inverted_index_file:
        # iterate through all words in the wordset
        for token in word_set:
            token_frequencies = []
            
            # iterate through each partial index
            for partial_index_file in partial_indices:
                # check if the token exists in the partial index
                if token in token_locs[partial_index_file]:
                    token_loc = token_locs[partial_index_file][token]
                    with open(partial_index_file, "rb") as partial_file:
                        partial_file.seek(token_loc)
                        token_line = partial_file.readline()
                        data = orjson.loads(token_line.decode())
                        # extract the frequency
                        token_frequencies.extend(data[token])

            # write the combined frequencies to final inverted index
            file_loc = inverted_index_file.tell()
            combined_token_locs[token] = file_loc
            json_data = {token: token_frequencies}
            inverted_index_file.write(orjson.dumps(json_data).decode())
            # add a newline to separate records
            inverted_index_file.write('\n')  
    
    print("merged all partial indices")


def iterateDirectory() -> None:
    """
    Recursively iterate through the DEV folder to process all the files.
    """
    global partial_index 
     
    directory_path = "DEV"

    # iterate through each file of the directory
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file != ".DS_Store":
                # similar_files = process_tokens(file)
                # if not similar_files:
                #     process_file(file)
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                # check file size
                if file_size < max_file_size:
                    tokens = process_tokens(file_path)
                    process_file(file_path, tokens)

                    # check if partial index needs to be dumped
                    if len(partial_index) >= partial_index_threshold:
                        dump_partial_index()
    # dump one last time with current partial index
    if (len(partial_index) > 0):
        dump_partial_index()


def get_common_docs(nested_lists, query_word_count):
    # create a dictionary to store frequencies for each element
    freq_dict = {}
    
    # iterate over each sublist in the nested list
    for lst in nested_lists:
        for doc in lst:
            doc_id = doc[0]
            if doc_id in freq_dict:
                freq_count = freq_dict[doc_id][0] + 1
                score = freq_dict[doc_id][1] + doc[2]
                freq_dict[doc_id] = [freq_count, score]
            else:
                freq_count = 1
                score = doc[2] 
                freq_dict[doc_id] = [freq_count, score]
    
    common_docs_dict = {key: value for key, value in freq_dict.items() if value[0] == query_word_count}
    return common_docs_dict


def process_user_query(query):
    """
    process the user's query and return a list of documents that include the user's query words
    """ 
    # tokenize the query:
    query_tokens = re.split(r'[^a-zA-Z0-9]+', query.lower())
    query_tokens = [token for token in query_tokens if token and len(token) > 1]
    query_tokens = sorted(query_tokens)

    # stem the query:
    query_tokens = stem_tokens(query_tokens)

    # access the scores for each token in the query
    query_freqs_list = []

    for word in query_tokens:
        all_word_freqs = []
        file_prefix = get_file_prefix(word)
        with open(f"{file_prefix}.json", "rb") as f:
            tokens = orjson.loads(f.read())
            for i in range(len(tokens)):
                if tokens[i]["token"] == word:
                    found_word = True
                    token_freqs = tokens[i]["freq"]
                    all_word_freqs.extend(token_freqs)
                      
        query_freqs_list.append(all_word_freqs)

        common_docs_dict = get_common_docs(query_freqs_list, len(query_tokens))

        common_docs_dict = dict(sorted(common_docs_dict.items(), key=lambda x: x[1][1], reverse=True))

    return common_docs_dict

    
def write_result_to_file():
    """
    write the results to a file
    """
    result_file = "results.txt"
    with open(result_file, "w") as output_result_file:
        output_result_file.write("number of documents processed: " + str(file_count) + "\n")
        output_result_file.write("number of unique words: " + str(len(word_set)) + "\n")
        


def main():
    # iterate through the files and process the tokens
    iterateDirectory()

    # merge the partial indices
    merge_partial_indices()

    # # write the final results to a file
    # write_result_to_file()


    # write the token locations to a file
    with open("token_locations.json", "w") as f:
        f.write(orjson.dumps(token_locs).decode())

    # write the combined token locations to a file
    with open("combined_token_locations.json", "w") as f:
        f.write(orjson.dumps(combined_token_locs).decode())

    # write the file id dict to a file
    with open("file_id.json", "w") as f:
        f.write(orjson.dumps(file_id_dict).decode())


    # loc = combined_token_locs["toward"]
    # with open(output_file, "rb") as file:

    #     file.seek(loc)
    #     token_line = file.readline()
    #     data = orjson.loads(token_line.decode())
    #     # extract the frequency
    #     print(data)

        


    # # prompt the user for a search query
    # query = input("Search: ")
    
    # # start the timer in ms
    # start_time = time.time_ns() // 1000000   

    # # get the top docs
    # common_docs_dict = process_user_query(query)

    # # take top 5 documents
    # top_5_docs = dict(list(common_docs_dict.items())[:5])

    # top_5_doc_ids = list(top_5_docs.keys())

    # print("documents:", top_5_doc_ids)
    # print("file id dict size:", len(file_id_dict))
    
    
    # # end timer
    # end_time = time.time_ns() // 1000000
    # execution_time = end_time - start_time
    # print("time:", execution_time, "ms")


if __name__ == "__main__":
    main()