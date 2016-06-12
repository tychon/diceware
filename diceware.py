#!/usr/bin/python3

import sys
import os
import math
import struct

def print_help():
    """Print help message"""
    print("""
Usage: {:s} [OPTIONS] [INPUTFILE]

OPTIONS
-d DELIM, --delimiter DELIM
    Print DELIM between words.
    Defaults to newline
--dice
    You will be asked to input results of die rolls as random source.
    Specifying this option overwrites --source option.
-n, --words
    Number of words to select.
    Defaults to 7
-s FILE, --source FILE
    Source of randomness as file / device name.  Specifying this option
    overwrites --dice option.
    Defaults to /dev/random
-q, --quiet
    Suppress any output except password.
    Does not suppress input dialog for dice rolls.

EXAMPLES

    diceware.py --delimiter ' ' -n 4
    diceware.py -s /dev/urandom
""".format(sys.argv[0]))

def fatal(msg, printhelp=False):
    print(msg)
    if printhelp:
        print_help()
    sys.exit(1)

def load_words(filename, quiet=True):
    """Read all non-empty lines into a list of strings."""
    if not quiet:
        print("Reading words from {}".format(filename))
    words = []
    with open(filename, 'r') as f:
        for l, line in enumerate(f):
            word = line.strip()
            if len(word) is 0:
                continue
            #if word in words:
            #    print("WARNING: Words in list not unique!"
            #          " Word {} repeats in line {}"
            #          "".format(words.index(word)+1, l+1))
            words.append(word)
    if not quiet:
        print("List length: {:d} words".format(len(words)))
    return words

def print_entropy_info(words, num):
    """
      Print some information about the word list and a hypothetical password
      of `num` words from that list.
    """
    print("Number of words to select: {:d}".format(num))
    epw = math.log2(len(words))
    print("Entropy per word: {:.2f} bits".format(epw))
    print("Entropy of passphrase: {:.1f} bits".format(epw*num))


def get_one_index(N, M, entropy):
    """
      If `entropy` is a callback function (called without any arguments)
      returning an integer randomly distributed in [0, M-1], then this
      function returns an integer randomly distributed in [0, N-1].

      Idea for algorithm: http://math.stackexchange.com/a/1244365

      Algorithm:
      0. let M = a * N + b where b is positive and less than N
      1. generate random number r uniformly distributed
         in 0 <= r <= M-1
      2. go to step (1) if r is larger or equal to a*N
         now 0 <= r <= a*N-1 is uniformly distributed
      3. x = r mod N
         now 0 <= x <= N-1 is uniformly distributed
    """
    assert M >= N
    aN = M - M % N
    while True:
        r = entropy()
        assert 0 <= r <= M-1
        if r >= aN:
            continue
        else:
            return r % N

def get_cast_of_dice(wordnum, num):
    sides = input("Enter the number of sides on your die (6): ")
    if not sides.strip():
        sides = 6
    else:
        sides = int(sides)
    # throws per word
    throws = math.ceil(math.log(wordnum)/math.log(sides))
    print("You have to throw your die {} times per word.".format(throws))
    print("Enter the results seperated by spaces.")
    xs = []
    for i in range(num):
        def entropy():
            return _get_throw(i, sides, throws)
        x = get_one_index(wordnum, sides**throws, entropy)
        xs.append(x)
    print(xs)
    return xs

def _get_throw(wordidx, sides, throws):
    """
      Ask the user to input results of `throws` dice rolls of a die with
      `sides` sides.  Returns an integer in range 0 (inclusive) to
      sides**throws (exclusive).
    """
    while True:
        throw = input("Word {}: ".format(wordidx+1))
        try:
            rs = list(map(int, throw.split()))
        except ValueError as e:
            print("Invalid integer input:")
            print(e)
            continue
        if len(rs) != throws:
            print("You have to enter exactly {} numbers.".format(throws))
            continue
        outofrange = list(r < 1 or r > sides for r in rs)
        if any(outofrange):
            print("Number {} out of range (1 to {})"
                  "".format(outofrange.index(True)+1, sides))
            continue
        break
    # converting rs to one integer is equivalent to converting the
    # integer represented by rs in the base of sides of the die to
    # decimal/binary
    res = 0
    for i, r in enumerate(rs):
        res += sides**i * (r-1)
    return res

def get_random_numbers(source, wordnum, num, quiet=True):
    """
      Select `num` indices using `source` as random number generator.
      Returns a list of integers.

      We draw full bytes from the random source.  The discrete number r
      they represent has to be rescaled to be uniformly distributed over
      the length of the word list.
    """
    xs = []
    # number of bytes needed per word
    nbytes = math.ceil(math.log2(wordnum) / 8)
    if not quiet:
        print("Drawing at least {} bytes of randomness"
              " from {}".format(nbytes*num, source))

    with open(source, 'br') as randomness:
        def entropy():
            if quiet:
                raw = randomness.read(nbytes)
            else:
                # print a dot for every byte read since
                # /dev/random is blocking when there is no entropy
                # available
                raw = b''
                sys.stdout.flush()
                for j in range(nbytes):
                    raw += randomness.read(1)
                    sys.stdout.write('.')
                    sys.stdout.flush()
            # convert bytes to integer r
            # 0 <= r <= 256**b-1
            r = int.from_bytes(raw, byteorder='little',
                               signed=False)
            return r
        for i in range(num):
            x = get_one_index(wordnum, 256**nbytes, entropy)
            xs.append(x)
        if not quiet:
            # print newline after dots
            print()
    return xs


def main():
    # parse args
    args = sys.argv[1:]
    inputfile = None
    delimiter = '\n'
    num = 7
    source = '/dev/random' # None for --dice
    quiet = False
    while args:
        arg = args.pop(0)
        if arg == '-d' or arg == '--delimiter':
            delimiter = args.pop(0)
        elif arg == '--dice':
            source = None
        elif arg == '-n' or arg == '--words':
            num = int(args.pop(0))
        elif arg == '-s' or arg == '--randomness':
            source = args.pop(0)
        elif arg == '-q' or arg == '--quiet':
            quiet = True
        else:
            if inputfile is None:
                inputfile = arg
            else:
                fatal("Unexpected argument: {}".format(arg), True)
    if not inputfile:
        fatal("No wordlist given.", True)

    words = load_words(inputfile, quiet)
    if not words:
        fatal("Empty wordlist.")
    if not quiet:
        print_entropy_info(words, num)

    if source is None:
        indices = get_cast_of_dice(len(words), num)
    else:
        indices = get_random_numbers(source, len(words), num, quiet)

    pwdlst = list(words[i] for i in indices)
    pwd = delimiter.join(pwdlst)

    if quiet:
        print(pwd)
    else:
        print()
        print(pwd)
        print()

if __name__ == '__main__':
    main()
