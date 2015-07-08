#!/usr/bin/env python3
# coding: utf-8
"""
concordance
===========
We'll recreate a real-time streaming system, a la Apache Storm, using Python's
generators. Why? Because it's more interesting this way.

## Quick terminology:
 Stream: Data input.
 Spout: Stream creator.
 Bolt: Stream processor. Outputs a modified stream.


## Design Considerations
Although Python has perfectly good support for classes, I only used one for the Tokenizer.
I believe that unless you need to maintain a state, you're usually better off writing
a library of functions. They tend to be simpler to understand, and thus test.
With that said, a good candidate for a class would've been around the final data
structure for the concordance, in our case an OrderedDict. It has state (the
concordance) with several good helper functions for output.


## Alternative approaches:
- Don't use generators. Without chunking input, we're not getting much from the
use of generators, as our input file's memory footprint is kept around until
the process has been completed. But, as I said, more fun this way. And it paves
the way for buffered or asynchronous I/O (if we deemed the disk I/O to be the
slow point).
- MapReduce, using multiple processes. I actually originally wrote the solution
this way, but ran out of free time to polish it to my liking (Parallelism's hard,
who knew?). The general approach:
  1. Similar tokenizing step, where you fill a process-safe Queue with parsed sentences.
  2. Your Map step splits the sentences into (word, idx) tuples. These are placed onto
     one of many queues using a hash % modulo. This groups words together for the Reduce,
     allowing it to be executed during the Map phase.
  3. Reduce aggregates the (word, idx) tuples into (word, (count, indices) tuples.
  4. Another process updates a binary tree as results from Reduce come in,
     providing you sorted output as soon as possible.

Requirements:
  1. Install nltk via `pip3 install nltk`
"""
from collections import defaultdict, OrderedDict
import argparse
import logging
import os
import string

import nltk.data


# Logging
LOGGER = logging.getLogger('WordCount')
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())
LOGGER.propagate = False


def nltk_setup():
    nltk_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
    if not os.path.isdir(nltk_dir):
        import nltk
        nltk.download('punkt')
    return nltk_dir


class Tokenizer:
    """Tokenizers convert file streams into streams of delimited values.

    Parsing an English sentence is a bit tricky. We can attempt to write a very
    complete regex, or we can leverage more powerful tooling.  Nltk
    (natural language processing toolkit) satisfies the latter. Oddly enough,
    it fails to recognize 'i.e.' as a not being the start of a new sentence.
    """

    def __init__(self):
        nltk_data_dir = nltk_setup()
        english_tokens = os.path.join(nltk_data_dir,
            'tokenizers/punkt/english.pickle')
        try:
            self.nl_tokenizer = nltk.data.load(english_tokens)
        except:
            LOGGER.exception('Failed to load tokenizer data from %s',
                             english_tokens)
            raise

    def from_file(self, filename):
        """Convert the file to sentence tokens.

        This is dangerous if the file is very large. If memory was a bottlneck,
        we'd need to be trickier about reading in chunks, checking for valid
        sentences, and resetting the file pointer to the last found sentence.
        """
        with open(filename, 'r') as data:
            return self.from_text(data.read())

    def stream_from_file(self, filename):
        for token in self.from_file(filename):
            yield token

    def from_text(self, text):
        """Convert string into tokens."""
        return self.nl_tokenizer.tokenize(text)

    def stream_tokens(self, text):
        """Yield sentences from the already-parsed list.

        Why not just return the list? Because we're working with a theme
        of streams of data. Plus, see the comment about memory usage in
        `from_file`, where a generator would be ideal for keeping memory
        usage down.
        """
        for token in self.from_text(text):
            yield token


def split_sentences(stream):
    """Split sentences into word tokens, bereft of punctuation and lowercase."""
    for idx, s in enumerate(stream):
        LOGGER.debug("split_bolt: %s", s)
        words = (w.strip(string.punctuation).lower() for w in s.split())
        for word in words:
            LOGGER.debug("split_bolt: Yielding %s, %d", word, idx)
            yield (word, idx)


def tally_words(stream, table):
    """Associate words with sentence indices and tally their appearances."""
    for word, idx in stream:
        table[word].append(idx)
        LOGGER.debug("tally_bolt: Yielding %s, %d, %s", word, idx, table[word])
        yield word, len(table[word]), table[word]


def count_words(stream):
    """Archive word counts from previous stream.

    To continue the theme of stream processing, I could've had this itself
    be a stream, maintaining an organized data structure of words. The output
    would be the most recently updated (word, count, sentence indices) tuple.
    We'd need to implement a data structure with good lookup and ordered insertions
    times, such as a binary tree. The `bisect` library provides a working example
    for doing so.
    """
    table = {}
    for word, count, indices in stream:
        LOGGER.debug("count_words: Updating %s => %d, %s", word, count, indices)
        table[word] = (count, indices)
    return table


def pretty_streamer(word_hash):
    """Convert 'word: (count, indices)' => 'word: count [indices]'"""
    for word, val in word_hash.items():
        yield '{}: {} [{}]'.format(word,
                                   val[0],
                                   ', '.join([str(x) for x in val[1]]))


def write_to_file(inputs, filename):
    with open(filename, 'w') as fp:
        fp.write('word: count [sentence indices]\n')
        for line in inputs:
            fp.write(line + '\n')


def generate_concordance(istream):
    """Generate a list of words, their appearance counts, and the sentences they belong to."""
    # First bolt: Convert sentences into (word, sentence #)
    split_bolt = split_sentences(istream)
    # Second bolt: Tally words up
    tally_hash = defaultdict(list)
    tally_bolt = tally_words(split_bolt, tally_hash)
    # Terminal: Maintain a structure of words and their counts
    word_count = count_words(tally_bolt)
    # Sort for output
    ordered_count = OrderedDict(sorted(word_count.items(), key=lambda x: x[0]))
    return ordered_count


def main():
    # Argument parsing
    parser = argparse.ArgumentParser(description='Generate a concordance.')
    parser.add_argument('--text', dest='text', type=str, required=True,
                       help='file to generate concordance from')
    parser.add_argument('-o', dest='output', type=str,
                        help='save output to filename')
    parser.add_argument('--debug', dest='test', action='store_true',
                        help='enable debug logging')
    args = parser.parse_args()
    if args.test:
        LOGGER.setLevel(logging.DEBUG)

    tokenizer = Tokenizer()
    token_stream = tokenizer.stream_from_file(args.text)
    concordance = generate_concordance(token_stream)
    text_stream = pretty_streamer(concordance)
    if args.output:
        write_to_file(text_stream, args.output)
    else:
       print('\n'.join([line for line in text_stream]))


if __name__ == '__main__':
    main()
