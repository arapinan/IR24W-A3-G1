import os
import json
import re
from nltk.stem import PorterStemmer, SnowballStemmer
from bs4 import BeautifulSoup
import pandas as pd


# define the initial merged index DataFrame
merged_index = pd.DataFrame(columns=["token", "freq"])

# dict where key is the file and the value is the doc id 
file_id_dict = {}

# list of all partial indices
partial_indices = []

# current partial index dict
partial_index = {}

# set for all unique tokens
word_set = set()

# threshold for max tokens per partial index
partial_index_threshold = 8000

# number of files processed
file_count = 0

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
            file_info = json.load(input_file)
         
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

        for token in tokens:
            word_set.add(token)

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
    
        dict_length = len(file_id_dict)
        file_id_dict[file] = dict_length + 1
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
    global word_set
    global merged_index
    global partial_indices
    
    # create a partial index DataFrame
    partial_index_df = pd.DataFrame(partial_index.items(), columns=["token", "freq"])
    
    # merge current partial index with existing merged index df
    merged_index = pd.concat([merged_index, partial_index_df], ignore_index=True)
    
    # clear the partial index dict
    partial_index.clear()

    # write the merged index to disk
    # write_merged_index_to_disk(merged_index)

    # write the partial index to disk
    partial_index_file = f"partial_index_{len(partial_indices)}.json"
    partial_index_df.to_json(partial_index_file, orient="records")
    partial_indices.append(partial_index_file)
    
    # update result file
    write_result_to_file()
    print("dumped")


# def write_merged_index_to_disk(merged_index):
#     """
#     Write the merged index to a JSON file
#     """
#     global output_file
    
#     # group by token and aggregate occurrences
#     merged_index = merged_index.groupby("token")["freq"].sum().reset_index()

#     # write the merged index to a JSON file
#     merged_index.to_json(output_file, orient="records")
    

def merge_partial_indices():
    """
    merge all the partial indices into a single DataFrame.
    """
    global merged_index
    global partial_indices
    
    # # initialize an empty DataFrame for merged index
    # merged_index = pd.DataFrame(columns=["token", "freq"])
    
    # # merge all partial indices
    # for file in partial_indices:
    #     partial_index_df = pd.read_json(file)
    #     merged_index = pd.concat([merged_index, partial_index_df], ignore_index=True)
    #     print("merged file")
    
    # # group by token and combine frequencies
    # merged_index = merged_index.groupby("token")["freq"].sum().reset_index()

    # # write the merged index to a JSON file
    # merged_index.to_json(output_file, orient="records")


    # initialize empty DataFrames for each range of tokens
    tokens_0_f = pd.DataFrame(columns=["token", "freq"])
    tokens_g_p = pd.DataFrame(columns=["token", "freq"])
    tokens_r_z = pd.DataFrame(columns=["token", "freq"])
    
    # group tokens based on the first letter
    for file in partial_indices:
        with open(file, "r") as f:
            data = json.load(f)
            for token_data in data:
                token = token_data["token"]
                freq = token_data["freq"]
                first_letter = token[0].lower()
                if first_letter.isdigit() or first_letter < "g":
                    tokens_0_f = tokens_0_f._append({"token": token, "freq": freq}, ignore_index=True)
                elif first_letter in "ghijklmnop":
                    tokens_g_p = tokens_g_p._append({"token": token, "freq": freq}, ignore_index=True)
                else:
                    tokens_r_z = tokens_r_z._append({"token": token, "freq": freq}, ignore_index=True)
    
    # write DataFrames to JSON files
    tokens_0_f.to_json("0_f.json", orient="records")
    tokens_g_p.to_json("g_p.json", orient="records")
    tokens_r_z.to_json("r_z.json", orient="records")


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
                tokens = process_tokens(file_path)
                process_file(file_path, tokens)

                # check if partial index needs to be dumped
                if len(partial_index) >= partial_index_threshold:
                    dump_partial_index()
    # dump one last time with current partial index
    if (len(partial_index) > 0):
        dump_partial_index()
        # write_merged_index_to_disk(merged_index)


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

     # merge all partial indices into a single DataFrame
    merge_partial_indices()

    # write the final results to a file
    write_result_to_file()
 

if __name__ == "__main__":
    main()

