import os
import sys
import time
import orjson
import re
from nltk.stem import PorterStemmer, SnowballStemmer
from bs4 import BeautifulSoup
import pandas as pd
import math

# dict where key is the file and the value is the doc id 
file_id_dict = {}

# dict where key is doc id and value is url
url_dict = {}

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
# partial_index_threshold = 6000

# number of files processed
file_count = 0

max_file_size = 20 * 1024 * 1024
min_file_size = 1000

large_files = []
small_files = []

token_locs = {}

combined_token_locs = {}

# variables to check for exact/near similarity
checksum_set = set()
fingerprint_set = set()


def checksum(tokens):
    """
    Calculate the checksum of each page
    """
    sum = 0
    for token in tokens:
        for char in token:
            sum += ord(char)
    return sum


def hash_word(word):
    hash_value = 0
    for char in word:
        hash_value += ord(char)

    hash_value %= 65536

    bin_hash = bin(hash_value)[2:].zfill(16)
    return bin_hash


def simhash(page_dict: dict):
    """
    Detect similar documents. page_dict is every single word on a page with its frequency.
    """
    # Hash each word in the page_dict
    word_hashes = {word: hash_word(word) for word in page_dict.keys()}
    # Initialize fingerprint with 16 bits set to 0
    fingerprint = [0] * 16   

    # Combine hashes using XOR
    for word, hash_value in word_hashes.items():
        for i in range(16):  # Iterate over each bit position
            # Extract i-th bit from the hash value
            bit = (int(hash_value) // (2 ** i)) % 2
            # Update fingerprint using XOR
            fingerprint[i] ^= bit * page_dict[word]

    # Convert fingerprint to binary string
    fingerprint_str = ''.join(map(str, fingerprint))

    return fingerprint_str


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

        # get tokens
        content = file_info["content"]
        
        # create a bs obj to scrape the content
        soup = BeautifulSoup(content, "html.parser")
        
        # remove extra whitespace
        text = re.sub(r'\s+', ' ', soup.get_text())

        # use regex to split on non-alphanumeric characters
        tokens = re.split(r'[^a-zA-Z0-9]+', text.lower())

        # remove empty strings and single chars from token list
        tokens = [token for token in tokens if token and len(token) > 1]

        # Find all bolded (<b>, <strong>) tags
        bold_tags = soup.find_all(['b', 'strong'])
        for tag in bold_tags:
            text = re.sub(r'\s+', ' ', tag.get_text())
            temps = re.split(r'[^a-zA-Z0-9]+', text.lower())
            temps = [temp for temp in temps if temp and len(temp) > 1]
            for temp in temps:
                if temp in tokens:
                    #print(tag.get_text().strip().lower())
                    #tokens.append(tag.get_text().strip().lower())
                    tokens.append(temp)

        # Find all heading tags (<h1>, <h2>, <h3>), title, and anchors
        title_header_anchor_tags = soup.find_all(['a', 'b', 'strong', 'h1', 'h2', 'h3'])
        for tag in title_header_anchor_tags:
            text = re.sub(r'\s+', ' ', tag.get_text())
            temps = re.split(r'[^a-zA-Z0-9]+', text.lower())
            temps = [temp for temp in temps if temp and len(temp) > 1]
            for temp in temps:
                if temp in tokens:
                    #print(tag.get_text().strip().lower())
                    #tokens.append(tag.get_text().strip().lower())
                    tokens.append(temp)
                    tokens.append(temp)

        # dont process files with too little content
        if len(tokens) < 100:
            small_files.append(file)
            return []

        # dont process files with exact similarity
        sum = checksum(tokens)
        if sum in checksum_set:
            return []
        checksum_set.add(sum)

        # create the doc's page_dict (key: token, value: freq) for simhash
        page_dict = {}
        for token in tokens:
            if token in page_dict:  # if the key exists, increment its frequency
                page_dict[token] += 1
            else:  # if the key doesn't exist, add it to the dictionary and update its frequency
                page_dict[token] = 1

        # dont process files with near similarity
        fingerprint = simhash(page_dict)
        near_duplicate = False
        if (fingerprint not in fingerprint_set):
            for i in range(16):
                # make a copy of the original fingerprint
                new_fingerprint = list(fingerprint)
                # flip 1 bit at a time to detect near similarity
                if new_fingerprint[i] == "1":
                    new_fingerprint[i] = "0"
                else:
                     new_fingerprint[i] = "1"
                if "".join(new_fingerprint) in fingerprint_set:
                    fingerprint_set.add(fingerprint)
                    near_duplicate = True
                    break
  
        # check if fingerprint already exists to detect exact similarity or if there is near similarity
        if (fingerprint not in fingerprint_set) and not near_duplicate:        
            # update variables
            # increment file count
            file_count += 1

            # add the doc id and file to file_id dict
            dict_length = len(file_id_dict)
            doc_id = str(dict_length + 1)
            file_id_dict[file] = doc_id

            # add the url to the url dict
            url = file_info["url"]
            url_dict[doc_id] = url

            # update the word count
            file_wordcount_dict[doc_id] = len(tokens)

            # add fingerprint to the set
            fingerprint_set.add(fingerprint)
            return tokens
        return []
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

    with open("final_index.json", "w") as inverted_index_file:
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
            
            # create a new list for token frequencies with scores
            token_frequencies_scores = []

            # iterate through the token's frequencies and add the tf-idf score for each doc
            for token_freq in token_frequencies:
                doc_id = token_freq[0]
                file_freq = token_freq[1]
                file_wordcount = file_wordcount_dict[str(doc_id)]
                tf = file_freq / file_wordcount
                idf = math.log(file_count / len(token_frequencies))
                tf_idf = round(tf * idf, 5)
                token_frequencies_scores.append([doc_id, file_freq, tf_idf])

            # write the combined frequencies to final inverted index
            file_loc = inverted_index_file.tell()
            combined_token_locs[token] = file_loc
            json_data = {token: token_frequencies_scores}
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
                # dont process too big or too small files
                if file_size > max_file_size:
                    large_files.append(file_path)
                elif file_size < min_file_size:
                    small_files.append(file_path)
                else:
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


def process_user_query(query, token_loc_dict):
    """
    process the user's query and return a list of documents that include the user's query words
    """ 
    # set the exact query bool to true
    exact_query = True

    # tokenize the query:
    search_tokens = re.split(r'[^a-zA-Z0-9]+', query.lower())
    search_tokens = [token for token in search_tokens if token and len(token) > 1]

    # stem the query:
    query_tokens = stem_tokens(search_tokens)

    query_tokens_dict = {k: v for k, v in zip(query_tokens, search_tokens)}

    # access the scores for each token in the query
    query_tokens_lines = []

    accepted_query_tokens = []

    # check if the word exists in inverted index
    for word in query_tokens:
        try:
            word_loc = token_loc_dict[word]
            accepted_query_tokens.append(word)
        except KeyError:
            # set exact query to false
            exact_query = False
    
    # return empty result if no query tokens exist
    if len(accepted_query_tokens) == 0:
        return [], "", False
    
    # offer alternative search for nonnexistent words
    result_words = [query_tokens_dict[word] for word in accepted_query_tokens if word in accepted_query_tokens]
    result_query = " ".join(result_words)
    
    # get all postings of tokens in the accepted query tokens
    for word in accepted_query_tokens:
        with open("final_index.json", "rb") as index_file:
            word_loc = token_loc_dict[word]
            index_file.seek(word_loc)
            token_line = index_file.readline()
            token_data = orjson.loads(token_line.decode())
            query_tokens_lines.append(token_data)

    # extract the common documents that have all the words
    all_doc_ids = [set([item[0] for item in list(line.values())[0]]) for line in query_tokens_lines]
    common_doc_ids = set.intersection(*all_doc_ids)

    # dict to store the total sum of third values for each common document
    common_docs_scores = {}

    # iterate through the lines and sum up the third values for common documents    
    for line in query_tokens_lines:
        for word, postings in line.items():
            for item in postings:
                doc_id = item[0]
                if doc_id in common_doc_ids:
                    common_docs_scores.setdefault(doc_id, 0)
                    common_docs_scores[doc_id] += item[2]
    
    # sort the elements based on scores descending
    sorted_doc_sum = sorted(common_docs_scores.items(), key=lambda x: x[1], reverse=True)

    # return the top doc ids
    common_doc_ids_list = [item[0] for item in sorted_doc_sum] if sorted_doc_sum else []
    
    # return common docs sorted
    return common_doc_ids_list, result_query, exact_query

    
def write_result_to_file():
    """
    write the results to a file
    """
    result_file = "results.txt"
    with open(result_file, "w") as output_result_file:
        output_result_file.write("number of documents processed: " + str(file_count) + "\n")
        output_result_file.write("number of unique words: " + str(len(word_set)) + "\n")
        output_result_file.write("number of files too large: " + str(len(large_files)) + "\n")
        output_result_file.write("number of files too small: " + str(len(small_files)) + "\n")


def create_inverted_index():
    # iterate through the files and process the tokens
    iterateDirectory()

    # merge the partial indices
    merge_partial_indices()

    # write results to files
    # write the final results to a file
    write_result_to_file()

    # write the token locations to a file
    with open("token_locations.json", "w") as f:
        f.write(orjson.dumps(token_locs).decode())

    # write the combined token locations to a file
    with open("combined_token_locations.json", "w") as f:
        f.write(orjson.dumps(combined_token_locs).decode())

    # write the file id dict to a file
    with open("file_id.json", "w") as f:
        f.write(orjson.dumps(file_id_dict).decode())

    with open("url_dict.json", "w") as f:
        f.write(orjson.dumps(url_dict).decode())   

    with open("small_files.json", "w") as f:
        f.write(orjson.dumps(small_files).decode())   

    with open("large_files.json", "w") as f:
        f.write(orjson.dumps(large_files).decode())   

 

def process_search(query, loaded_token_loc_dict, loaded_url_dict):    
    # start the timer in ms
    start_time = time.time_ns() // 1000000   

    # get the top 5 docs
    common_docs, result_query, exact_query = process_user_query(query, loaded_token_loc_dict)

    urls_list = []

    if common_docs == [] or not exact_query:
        print('No results for "' + query + '"')
    if common_docs != []:
        urls_list = []

        # remove the fragments from common docs
        while (len(urls_list) < 5 and len(common_docs) > 0):
            # print the urls in the common docs
            common_doc = common_docs[0]
            doc_url = loaded_url_dict[common_doc]
            url_without_fragment = doc_url.split("#")[0]
            if url_without_fragment not in urls_list:
                urls_list.append(url_without_fragment)
            common_docs = common_docs[1:]

        # print the results
        print('Showing results for "' + result_query + '"')
        for num, url in enumerate(urls_list):
            print(str(num + 1), url)
    
    # end timer
    end_time = time.time_ns() // 1000000

    # calculate execution time
    execution_time = end_time - start_time
    print("Search time:", execution_time, "ms")

    return urls_list, result_query, exact_query


def main():
    # create inverted index
    # create_inverted_index()

    # # load the token locations file
    # with open("combined_token_locations.json", "r") as token_loc_file:
    #     loaded_token_loc_dict = orjson.loads(token_loc_file.read())    

    # # load the url dict from file
    # with open("url_dict.json", "r") as url_dict_file:
    #     loaded_url_dict = orjson.loads(url_dict_file.read())    

    # # prompt the user for a search query
    # query = input("Search: ")

    # # process search queries
    # process_search(query, loaded_token_loc_dict, loaded_url_dict)


if __name__ == "__main__":
    main()
