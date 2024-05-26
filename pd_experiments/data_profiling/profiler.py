from collections import Counter
from pprint import pprint
import pandas as pd
from nltk.tokenize import RegexpTokenizer


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


def main():
    # Read csv
    df = pd.read_csv("../data_input/menu.csv")
    target_col = "physical_description"

    # Concatenate rows of values in a sequence 
    # Count word occurance
    res_df = word_occur(df[target_col])


if __name__ == "__main__":
    main()