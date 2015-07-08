#!/usr/bin/env python3
import unittest
import string
from unittest import TestCase

from concordance import Tokenizer, split_sentences


test_file = "test1.txt"
with open(test_file) as fp:
    test_paragraph = fp.read()
test_sentences = [
    'As Mr. Smith walked towards the edge of the cliff, he recalled what his father had said to him.',
    '"Boy,", his father had started, "I must tell you this next thing before I go."',
    'But Mr. Smith had never gotten to hear what his father had to say, as at that moment his father had fallen over the side of the cliff.',
    'The very same cliff, Mr. Smith mused, that he himself was walking towards this very moment.',
    '"How Ms. Smith would laugh," he thought to himself, "if she were reading an account of his present actions."'
]


class TestTokenizer(TestCase):

    def setUp(self):
        self.tokenizer = Tokenizer()

    def test_from_file(self):
        tokens = self.tokenizer.from_file(test_file)
        self.assertListEqual(test_sentences, tokens)

    def test_from_text(self):
        tokens = self.tokenizer.from_text(test_paragraph)
        self.assertListEqual(test_sentences, tokens)

    def test_stream_tokens(self):
        stream = self.tokenizer.stream_tokens(test_paragraph)
        for i, token in enumerate(stream):
            self.assertEqual(token, test_sentences[i])


class TestSplittingSentences(TestCase):

    def test_split_sentences(self):
        # Split the entire paragraph at once. These indices will be by-word
        # instead of by-sentence.
        exp = [(w.strip(string.punctuation).lower(), i) for i, w in enumerate(test_paragraph.split())]

        sentence_stream = (s for s in test_sentences)
        # Enumerate over our word tokens
        for i, word_tuple in enumerate(split_sentences(sentence_stream)):
            with self.subTest(i=i, word=word_tuple):
                # Assert the words are returned in the right order
                self.assertEqual(exp[i][0], word_tuple[0])



if __name__ == "__main__":
    unittest.main()
