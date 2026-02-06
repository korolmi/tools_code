import sys
from io import TextIOWrapper

def count_words(filename):
    try:
        word_count = 0
        in_word = False

        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                for ch in line:
                    if isspace(ch):
                        if in_word:
                            in_word = False
                            word_count += 1
                    else:
                        in_word = True

                # Handle the case where the line ends with a word
                if in_word:
                    word_count += 1
                    in_word = False

        return word_count
    except FileNotFoundError:
        print(f"Error: The file {filename} was not found.")
        return None
    except IOError:
        print(f"Error: Could not read the file {filename}.")
        return None

def isspace(ch):
    return ch in ' \t\n\r'

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python wordcount.py filename")
        sys.exit(1)

    filename = sys.argv[1]
    word_count = count_words(filename)

    if word_count is not None:
        print(f"Number of words: {word_count}")