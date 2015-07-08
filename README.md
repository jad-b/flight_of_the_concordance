Concordance
===========
Written in `python 3.4.0`

## Design Considerations
Although Python has perfectly good support for classes, I only used one for the Tokenizer.
I believe that unless you need to maintain a state, you're usually better off writing
a library of functions. They tend to be simpler to understand, and thus test.
With that said, a good candidate for a class would've been around the final data
structure for the concordance, in our case an OrderedDict.

## Alternative approaches:
* Don't use generators. Without chunking input, we're not getting much from the
use of generators, as our input file's memory footprint is kept around until
the process has been completed. But, as I said, more fun this way. And it paves
the way for buffered or asynchronous I/O (if we deemed the disk I/O to be the
slow point).
* MapReduce, using multiple processes. I actually originally wrote the solution
this way, but ran out of free time to polish it to my liking (Parallelism's hard,
who knew?). The general approach:
  1. Similar tokenizing step, where you fill a process-safe Queue with parsed sentences.
  2. Your Map step splits the sentences into (word, idx) tuples. These are placed onto
     one of many queues using a hash % modulo. This groups words together for the Reduce,
     allowing it to be executed during the Map phase.
  3. Reduce aggregates the (word, idx) tuples into (word, (count, indices) tuples.
  4. Another process updates a binary tree as results from Reduce come in,
     providing you sorted output as soon as possible.

## To Run
```bash
./concordance.py --text test2.txt -o test2.out
```

## Setup
This script leverages [nltk](http://www.nltk.org/) for parsing English sentences. It does so with middling results
(damn you, `i.e.`. You're not a new sentence!). Installation is simple.
```bash
pip3 install nltk
````
