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
-c
--exclude
    Exclude a list of words (case insensitive; before and after possible
    umlaut rewriting).
-l INT1,INT2, --length INT1,INT2
    Limit length of words to a range from INT1 to INT2 (both inclusive).
    Defaults to 3,7
-n
    Number of words to select.
    Defaults to 7
-r FILE, --randomness FILE
    Source of randomness.
    Defaults to /dev/random
-s FILE, --savelist FILE
    Save generated wordlist to FILE
-u OPT, --umlauts OPT
    where OPT is filter or rewrite.  With 'filter', words with umlauts are
    removed from the list, with 'rewrite' umlauts are rewritten using 'e'.
    Defaults to filter.
-q, --quiet
    Suppress output about entropy and print words in one line separated by
    spaces.

EXAMPLES

    diceware.py -n 4
    diceware.py -s /dev/urandom -c -u rewrite
""".format(sys.argv[0]))

def fatal(msg, printhelp=False):
    print(msg)
    if printhelp:
        print_help()
    sys.exit(1)

umlaut_map = {
    'Ä': 'AE',
    'Ö': 'OE',
    'Ü': 'UE',
    'ä': 'ae',
    'ö': 'oe',
    'ü': 'ue',
    'ß': 'ss'
}

def compile_list(inputfile, length, caps, umlauts):
    """
      Generate a set of words from lines in `inputfile` obeying given
      rules.
    """
    lenfrom, lento = length
    words = set()
    with open(inputfile, 'r') as inputf:
        for word in inputf:
            word = word.strip()
            if lenfrom is not None and len(word) < lenfrom \
              or lento is not None and len(word) > lento:
                continue
            if any([(ord(ch) < 32 or ord(ch) > 126) and
                    (umlauts == 'rewrite' and ch not in umlaut_map
                     or umlauts == 'filter')
                        for ch in word]):
                continue
            if umlauts == 'rewrite':
                for k, v in umlaut_map.items():
                    word = word.replace(k, v)
            if not caps:
                word = word.lower()
            words.add(word)
    return words

def print_entropy_info(words, num):
    """
      Print some information about the word list and a hypothetical password
      of `num` words from that list.
    """
    print("List length: {:d} words".format(len(words)))
    if not len(words):
        sys.ext(1)
    print("Number of words to select: {:d}".format(num))
    epw = math.log2(len(words))
    print("Entropy per word: {:.2f} bits".format(epw))
    print("Entropy of passphrase: {:.1f} bits".format(epw*num))

def select(source, words, num, quiet=True):
    """Select `num` words from `words` using `source` as random number
      generator.  Returns a list of words.
    """
    words = list(words)
    # number of random bits needed per word:
    bits = math.log2(len(words))
    # number of bytes needed for one word
    b = math.ceil(bits / 8)
    if not quiet: print("Drawing {} bits of randomness"
                        "from {}".format(b*num, source))
    with open(source, 'br') as randomness:
        raw = randomness.read(b * num)

    pwd = []
    chunks = list(raw[i:i+b] for i in range(0, len(raw), b))
    for chunk in chunks:
        r = int.from_bytes(chunk, byteorder='little')
        # scale random number to length of list
        # 0 <= r <= 256**b
        # 0 <= x <= len(words)-1
        # len(words)-1+1 is used for math.floor
        x = math.floor(len(words) / 256**b * r)
        pwd.append(words[x])
    return pwd

def main():
    # parse args
    args = sys.argv[1:]
    inputfile = None
    caps = False
    length = (3, 7)
    num = 7
    quiet = False
    source = '/dev/random'
    umlauts = 'filter'
    while args:
        arg = args.pop(0)
        if arg == '-c' or arg == '--capitals':
            caps = True
        elif arg == '-l' or arg == '--length':
            try: l = args.pop(0)
            except IndexError:
                fatal("Expected argument to {}".format(arg), True)
            lenfrom, lento, *rest = l.split(',')
            if rest:
                fatal("Expected argument of format"
                      " 'INT,INT' to {}".format(arg), True)
            lenfrom = int(lenfrom) if lenfrom != '' else None
            lento = int(lento) if lenfrom != '' else None
            length = (lenfrom, lento)
        elif arg == '-n' or arg == '--words':
            num = int(args.pop(0))
        elif arg == '-q' or arg == '--quiet':
            quiet = True
        elif arg == '-s' or arg == '--randomness':
            source = args.pop(0)
        elif arg == '-u' or arg == '--umlauts':
            umlauts = args.pop(0)
        else:
            if inputfile is None:
                inputfile = arg
            else:
                fatal("Unexpected argument: {}".format(arg), True)
    if not inputfile:
        inputfile = '/usr/share/dict/ngerman'

    #TODO OPTIONS -r, -q, --exclude

    with open(inputfile, 'r') as inputf:
        words = compile_list(inputfile, length, caps, umlauts)
        if not quiet: print_entropy_info(words, num)
        pwdlst = select(source, words, num, quiet)

    if quiet:
        print(' '.join(pwdlst))
    else:
        print("== Words ==")
        print('\n'.join(pwdlst))
        print()

if __name__ == '__main__':
    main()
