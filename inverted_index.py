import os


# reference the file with its corresponding id when needed
# key: filename
# value: id (starting at 1)
file_to_id = {}


# inverted index map
# key: word/token
# value: file id, frequency
# ex. {cat: [[1, 5], [2, 7]], dog: [1, 10]}
inverted_index = {}


def tokenize(file: str) -> list:
    """
    Tokenize the text from a specified file.
    """


def porter_stemmer(tokens: list) -> list:
    """
    Using the porter stemming technique to derive the root of words.
    """


def detect_exact_similarity(tokens: list):
    """
    Detect exact similarity using the checksum technique.
    """


def detect_near_similarity(tokens: list):
    """
    Detect near similiarity using the simhash technique.
    """


def iterateDirectory() -> None:
    """
    Recursively iterate through the DEV folder to process all the files.
    """

    directory_path = "DEV"

    # iterate through each file of the directory
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            # add the file to the file_to_id dictionary for future reference
            if file not in file_to_id:
                dict_length = len(file_to_id)
                file_to_id[file] = dict_length + 1
            # get the alphanumeric tokens
            tokens = tokenize(file)
            # stem the tokens, if necessary
            stemmed_tokens = porter_stemmer(tokens)
            # detect duplicate pages
            # TODO: do we want to detect duplicate pages after stemming?
            # TODO: we need to add more global variables to do this and add extra checks for this...
            # TODO: what do we do if we detect similarity?
            detect_exact_similarity(stemmed_tokens)
            detect_near_similarity(stemmed_tokens)
            # TODO: account for important text
            # TODO: why do we need to do this, and what will do do with this information once we
            # determine which text is important? i think we should move it before
            for token in stemmed_tokens:
                # if word exists in inverted_index -> increase frequency
                if token in inverted_index:
                    occurences = inverted_index[token]
                    found = False
                    for occurence in occurences:
                        if occurence[0] == file_to_id[file]:
                            occurence[1] += 1
                            found = True
                            break
                    if found == False:
                        occurences.append([file_to_id[file], 1])
                # if not -> add to inverted_index (value = [[id, 1]])
                else:
                    inverted_index[token] = [[file_to_id[file], 1]]
            # TODO: if index gets to big -> dump to file
            # TODO: not sure how to approach this... i'm confused


# TODO: merge files at the end


# TODO: write result to file


# TODO: max memory?
    # how many docs per file / memory per file


if __name__ == "__main__":
    iterateDirectory()
