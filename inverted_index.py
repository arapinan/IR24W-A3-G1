import os
import json
import re
from nltk.stem import PorterStemmer, SnowballStemmer
from bs4 import BeautifulSoup


# dict where key is the file and the value is the doc id 
file_id_dict = {}

# list of all partial indices
partial_indices = []

# current partial index dict
partial_index = {}

# set for all unique tokens
word_set = set()

# threshold for max tokens per partial index
partial_index_threshold = 14000

# number of files processed
file_count = 0


# TODO: make inverted index map
    # key: word
    # value: doc id, frequency
    # ex. file 1: {cat: [(1, 5), (2, 7)], dog: [(1, 10)]}
    #     file 2: {cat: [(3, 5), (4, 3)], dog: [(4, 9)], cow: [4, 3]}


# TODO: detect duplicate pages
# TODO: account for important text


def tokenize(file: str) -> list:
    """
    Tokenize the text from a specified file.
    """
    try:
        # open the file and read its contents
        with open(file, "r") as input_file:
            file_info = json.load(input_file)

        content = file_info["content"]
        
        # create a bs obj to scrape the content
        soup = BeautifulSoup(content, "html.parser")
        
        # remove extra whitespace
        text = re.sub(r'\s+', ' ', soup.get_text())

        # use regex to split on non-alphanumeric characters
        tokens = re.split(r'[^a-zA-Z0-9]+', text.lower())

        # remove empty strings from token list
        tokens = [token for token in tokens if token]

         
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


# def detect_exact_similarity(tokens: list):
#     """
#     Detect exact similarity using the checksum technique.
#     """


# def detect_near_similarity(tokens: list):
#     """
#     Detect near similiarity using the simhash technique.
#     """


def process_tokens(file):
    # similar_files = False
            
    # add the file to the file_id_dict dictionary for future reference
    if file not in file_id_dict:
        # get the alphanumeric tokens
        tokens = tokenize(file)
        # stem the tokens 
        tokens = stem_tokens(tokens)
        
    #     # detect duplicate pages
    #     exact_similar_files = detect_exact_similarity(tokens)
    #     near_similar_files = detect_near_similarity(tokens)
        
    #     if not exact_similar_files and not near_similar_files:
    #         dict_length = len(file_id_dict)
    #         file_id_dict[file] = dict_length + 1
    #     else:
    #         similar_files = True
    # return similar_files
        dict_length = len(file_id_dict)
        file_id_dict[file] = dict_length + 1
    return tokens


def process_file(file, tokens):
    """
    add tokens to partial index
    """
    # TODO: we need to add more global variables to do this and add extra checks for this...

    # TODO: account for important text
    # TODO: why do we need to do this, and what will do do with this information once we
    # determine which text is important? i think we should move it before
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
    # TODO: if index gets to big -> dump to file
        

def dump_partial_index():
    """
    dump the partial index to a file in JSON format
    """
    partial_index_file = "index" + str(len(partial_indices)) + ".json"
    with open(partial_index_file, "w") as output_file:
        json.dump(partial_index, output_file, indent=4)
     

def merge_partial_indices():
    global word_set

    inverted_index_file = "inverted_index.json"
    with open(inverted_index_file, "a") as inverted_index_report:
        for index_1 in range(len(partial_indices)):
            index_file = "index" + str(index_1) + ".json"
            with open(index_file, "r") as partial_index_file:
                # load the partial index data
                index_data = json.load(partial_index_file)
                # iterate through each token in the file
                for token in index_data:
                    # check if the token was already merged
                    if token not in word_set:
                        token_dict = dict()
                        # initialize an occurences list with all occurences in current file
                        occurences = index_data[token]
                        # iterate through other partial indices to check if they contain this token 
                        for index_2 in range(len(partial_indices)):
                            if index_1 != index_2:
                                # open and load other file's data
                                other_index_file = "index" + str(index_2) + ".json"
                                with open(other_index_file, "r") as other_partial_index_file:
                                    other_index_data = json.load(other_partial_index_file)
                                    # check if the token exists in the other file
                                    if token in other_index_data.keys():
                                        # add all other index's occurences to existing occurences
                                        other_index_occurences = other_index_data[token]
                                        occurences.append(other_index_occurences)
                        token_dict[token] = occurences
                        # add the token to word_set
                        word_set.add(token)
                    # dump this token to final inverted index
                    json.dump(token_dict, inverted_index_report, indent=4)
                    inverted_index_report.write('\n')


def iterateDirectory() -> None:
    """
    Recursively iterate through the DEV folder to process all the files.
    """
    global partial_index 
    global file_count
     
    directory_path = "DEV"

    # iterate through each file of the directory
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file != ".DS_Store":
                if len(partial_index) < partial_index_threshold:
                    # similar_files = process_tokens(file)
                    # if not similar_files:
                    #     process_file(file)
                    file_path = os.path.join(root, file)
                    tokens = process_tokens(file_path)
                    process_file(file_path, tokens)
                else:
                    # dump the partial index to a file
                    dump_partial_index()

                    partial_indices.append(len(partial_indices))

                    # clear the partial index dict
                    partial_index.clear()

                    # process the tokens in this file
                    file_path = os.path.join(root, file)
                    tokens = process_tokens(file_path)
                    process_file(file_path, tokens)
                file_count += 1
         

def write_result_to_file():
    result_file = "results.txt"
    with open(result_file, "w") as output_result_file:
        output_result_file.write("number of documents processed: " + str(file_count) + "\n")
        output_result_file.write("number of unique words: " + str(len(word_set)) + "\n")
        
 
def main():
    iterateDirectory()
    merge_partial_indices()
    write_result_to_file()


if __name__ == "__main__":
    main()
