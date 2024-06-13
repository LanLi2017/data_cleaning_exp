from collections import Counter
from pprint import pprint
import re
import pandas as pd
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams


def word_occur(rows: pd.Series):
    filtered_values = rows.dropna()
    values_seq = " ".join(filtered_values)
    print(len(values_seq))
    # Tokenize the text
    # only keep word:
    word_tokenizer = RegexpTokenizer(r'[a-zA-Z]+')
    word_tokens = word_tokenizer.tokenize(values_seq)
    word_counts = Counter(word_tokens)
    
    # only keep digitXdigit:
    # TODO
    dd_tokenizer = RegexpTokenizer(r'\d+(?:[,.]\d+)?\s*[Xx]\s*\d+(?:[,.]\d+)?')
    dd_tokens = dd_tokenizer.tokenize(values_seq)
    dd_counts = Counter(dd_tokens)

    # Convert Counter to dictionary
    word_counts_dict = dict(word_counts + dd_counts)

    # Create DataFrame from dictionary
    df = pd.DataFrame(list(word_counts_dict.items()), 
                      columns=['Occurrance', 'Frequency'])
    df.to_csv("word_occur.csv")
    return values_seq


def preprocess(cell):
    tokens = re.split(r'[;,\s:]+', cell)
    # tokens = [token for token in tokens if not any(char.isdigit() for char in token)]
    tokens = [token for token in tokens if token]
    return ['bos'] + tokens + ['eos']

def phrase_detect(cell_values):
    # Using N-grams to detect the occurrance of "phrase"
    tokenized_cells = [preprocess(cell) for cell in cell_values]
    # Flatten the list of tokenized cells
    flattened_tokens = [token for sublist in tokenized_cells for token in sublist]
    # Generate bigrams
    bigrams = list(ngrams(flattened_tokens, 2))
    filtered_bigrams = [gram for gram in bigrams 
                        if 'bos' not in gram and 'eos' not in gram]
    # Count the frequency of each bigram
    bigram_counts = Counter(filtered_bigrams)
    # Display the most common bigrams
    pprint(bigram_counts)
    # Convert Counter to dictionary
    phrase_counts_dict = dict(bigram_counts)

    # Create DataFrame from dictionary
    df = pd.DataFrame(list(phrase_counts_dict.items()), 
                      columns=['Occurrance', 'Frequency'])
    df.to_csv("phrase_occur.csv")


def main():
    # Read csv
    parent_folder = "history_update_problem"
    df = pd.read_csv(f"{parent_folder}/data.in/menu_sp.csv")
    target_col = "physical_description"

    # Concatenate rows of values in a sequence 
    # Count word occurance
    res_df = word_occur(df[target_col])

    # Count phrase
    phrase_detect(df[target_col].dropna().tolist())


if __name__ == "__main__":
    main()