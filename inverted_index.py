# TODO: make doc map for docs to doc id


# TODO: make inverted index map
    # key: word
    # value: doc id, frequency
    # ex. {cat: [[1, 5], [2, 7]], dog: [1,10]}

# TODO: recursively iterate through directories
    # for each file:
        # add to doc map
        # get alphanumeric tokens
        # stem the token
        # TODO: detect duplicate pages
        # account for important text
        # for each token:
            # if word exists in index -> increase frequency
            # else -> add to index (value = [doc id, 1])
    # if index gets to big -> dump to file

# merge files at the end

# write result to file


# max memory?
    # how many docs per file / memory per file


def main():
    pass


if __name__ == "__main__":
    main()
