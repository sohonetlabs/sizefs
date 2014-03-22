#!/usr/bin/env python

"""
Content Generation Code for SizeFS
"""

__author__ = "Joel Wright, Mark McArdle"

import re
import random
import logging
from string import ascii_uppercase, ascii_lowercase, digits

DEBUG = False

if DEBUG:
    logging.setLevel(logging.DEBUG)


class SizeFSGeneratorType(object):
    ZEROS = 'zeros'
    ONES = 'ones'
    ALPHA_NUM = 'alpha_num'
    REGEX = 'regex'


ONE_K = 1000

FILE_REGEX = re.compile("^(?P<size>[0-9]+(\.[0-9])?)(?P<size_si>[EPTGMKB])"
                        "((?P<operator>[\+|\-])(?P<shift>\d+)"
                        "(?P<shift_si>[EPTGMKB]))?$")


class SizeFSGen(object):
    """
    Generate Zeros
    """

    def __init__(self):
        self.chars = 'X'

    def fill(self, fill):
        if len(self.chars) == 0:
            return self.chars * fill
        else:
            pre_seed_count = 0
            content = []
            pre_seed_len = len(self.chars)
            while fill > pre_seed_len:
                content.append(self.chars)
                fill -= pre_seed_len
                pre_seed_count += 1
            content.append(self.chars[0:fill])
            return ''.join(content)

    def read(self, start, end):
        if start <= end:
            return self.chars * (end-start+1)
        else:
            return ''


class SizeFSZeroGen(SizeFSGen):
    """
    Generate Zeros
    """
    CHARS = '0'

    def __init__(self):
        super(SizeFSZeroGen, self).__init__()
        self.chars = self.CHARS


class SizeFSOneGen(SizeFSGen):
    """
    Generate Ones
    """
    CHARS = '1'

    def __init__(self):
        super(SizeFSOneGen, self).__init__()
        self.chars = self.CHARS


class SizeFSAlphaNumGen(SizeFSGen):
    """
    Generate Alpha Numeric Characters
    """

    CHARS = ascii_uppercase + digits + ascii_lowercase

    def __init__(self):
        super(SizeFSAlphaNumGen, self).__init__()
        self.chars = ''.join(random.choice(
            self.CHARS) for _ in range(64 * 1024))

    def read(self, start, end):
        if start <= end:
            return self.fill(end - start)
        else:
            return ''


class FastRandom(object):
    """
    random itself is too slow for our purposes, so we use random to populate
    a small list of randomly generated numbers that can be used in each call
    to randint()

    A call to randint() just returns the a number from our list and increments
    the list index.

    This is faster and good enough for a "random" filler
    """
    def __init__(self, min, max, len=255):
        # Generate a small list of random numbers
        self.randoms = [random.randint(min, max) for i in range(len)]
        self.index = 0
        self.len = len

    def rand(self):
        value = self.randoms[self.index]
        if self.index < self.len - 1:
            self.index += 1
        else:
            self.index = 0
        return value


class XegerError(Exception):
    """
    Exception type for reporting Xeger generation errors
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class XegerGen(object):
    """
    The generator uses up to 4 regular expressions to generate the contents
    of a file defined below:

     - prefix: fixed start to the file
               defaults to ""
     - suffix: fixed end to the file
               defaults to ""
     - filler: the repeating body of the file (the body of the file always
               amounts to (filler)*
               defaults to 0*
     - padder: if a complex filler pattern generated does not fit within
               the remaining space left in the generated file, padding
               is used to fill the remaining space. This should always be
               as simple as possible (preferably generating individual
               characters).
               defaults to 0*

    The file will be generated as follows: (prefix)(filler)*(padder)*(suffix)

    BNF for acceptable Xeger patterns:

      <Xeger> ::= <Pattern>

      <Pattern> ::= <Expression>
                  | <Expression> <Pattern>

      <Expression> ::= <Char> [<Multiplier>]
                     | "(" <Pattern> ")" [<Multiplier>]
                     | "[" <Set> "]" [<Multiplier>]

      <Multiplier> ::= "*"
                     | "+"
                     | "?"
                     | '{' <Num> '}'

      <Set> ::= <Char>
              | <Char> "-" <Char>
              | <Set> <Set>

    The generator will always produce a string containing the prefix and
    suffix if a string of sufficient size is requested. Following that, the
    generator will fill the remaining space with filler, either ending there
    or filling remaining space using the padder pattern. The padder pattern
    will only be used if a complete filler pattern will not fit in the space
    remaining.

    max_random is used to define the largest random repeat factor of any
    + or * operators.

    Random seeks within a file may produce inconsistent results for general
    file contents, however prefix and suffix will always be consistent with
    the requested pattern.
    """
    reserved_chars = ['[', ']', '{', '}', '*', '+', '?']

    def __init__(self, size, filler=None, prefix=None,
                 suffix=None, padder=None, max_random=10):
        self._size = size
        self._end_last_read = 0
        self._remainder = ""
        self._remainder_length = 0

        if filler == "":
            logging.error("Empty filler pattern supplied,"
                          " using default")
            filler = None
        elif padder == "":
            logging.error("Empty padder pattern supplied,"
                          " using default")
            padder = None
        elif prefix == "":
            logging.error("Empty prefix pattern supplied,"
                          " using default")
            prefix = None
        elif suffix == "":
            logging.error("Empty suffix pattern supplied,"
                          " using default")
            suffix = None

        if filler is not None:
            self._filler = Xeger(filler, max_random)
        else:
            self._filler = Xeger("0", max_random)

        if padder is not None:
            self._padder = Xeger(padder, max_random)
        else:
            self._padder = Xeger("0", max_random)

        if prefix is not None:
            prefix_c = []
            _, prefix_len = Xeger(prefix, max_random).generate(prefix_c, 0)
            self._prefix = "".join(prefix_c)
            self._prefix_length = prefix_len
        else:
            self._prefix = ""
            self._prefix_length = 0

        if suffix is not None:
            suffix_c = []
            _, suffix_len = Xeger(suffix, max_random).generate(suffix_c, 0)
            self._suffix = "".join(suffix_c)
            self._suffix_length = suffix_len
        else:
            self._suffix = ""
            self._suffix_length = 0

        if size < (self._prefix_length + self._suffix_length):
            logging.error("Prefix and suffix combination is longer than"
                          "the requested size of the file. One or both will"
                          "be truncated")

        self._get_filler = self._filler.generate

    def read(self, start, end):
        """
        Return regex content.

        Only fully supports sequential reading, however, any read with start or
        end range within a specified prefix or suffix pattern will produce
        appropriate output (this is necessary for metadata testing functions).
        """
        #return "".zfill(end-start)
        content = []
        content_length = 0

        if end > self._size - 1:
            logging.debug("Read beyond end of generator requested - resetting"
                          "requested end to size of generator")
            end = self._size - 1

        if start < 0:
            logging.error("Can't read before the beginning")
            start = 0

        self._end_last_read = end

        if start < self._prefix_length:
            self._remainder = ""
            self._remainder_length = 0
            content.append(self._prefix[start:])
            content_length += self._prefix_length - start
        else:
            if start == self._end_last_read + 1:
                # If we're reading sequentially, append any remainder
                content.append(self._remainder)
                content_length += self._remainder_length
                self._remainder = ""
                self._remainder_length = 0

        chunk_size = (end + 1) - start

        # Calculate how much content is required
        last_required = False
        if end > (self._size - self._suffix_length):
            # If we're sufficiently close to the end size of the contents
            # requested, then we need to consider padding and suffix
            last_required = True
            last = self._suffix[:self._suffix_length + (end
                                                        - (self._size - 1))]
            still_required = chunk_size - len(last)
        else:
            still_required = chunk_size

        # Grab content
        while content_length < still_required:
            new_items, content_length = \
                self._get_filler(content, content_length)

        # Adjust content and get padding if necessary
        if content_length > still_required:
            overrun = content_length - still_required
            overrun_content = []
            for x in xrange(new_items):
                overrun_content.insert(0, content.pop())
            overrun_content_string = "".join(overrun_content)
            overrun_length = len(overrun_content_string)
            if (end + overrun) > (self._size - 1 - self._suffix_length):
                content_length -= overrun_length
                padding_required = still_required - content_length
                pad, pad_length = self._get_padding(padding_required)
                content.append(pad)
                if last_required:
                    content.append(last)
            else:
                this_time = overrun_length - overrun
                content.append(overrun_content_string[:this_time])
                self._remainder = overrun_content_string[this_time:]
                self._remainder_length = len(self._remainder)
        elif content_length == still_required:
            if last_required:
                content.append(last)

        return "".join(content)

    def _get_padding(self, size):
        pad = []
        pad_length = 0

        while pad_length < size:
            new_items, pad_length = \
                self._padder.generate(pad, pad_length)

        return "".join(pad)[:size], size


class Xeger(object):
    """
    Parses a given regex pattern and yields content on demand.

    regex - a string describing the requested pattern
    max_random - a value passed within the generator describing the maximum
                 number of repeats for * or + operators
    """
    def __init__(self, regex, max_random=10):
        self._pattern = XegerPattern(regex, max_random=max_random)
        if self._pattern.length() == 1:
            self._pattern = self._pattern._expressions[0]

        self.generate = self._pattern.generate


class XegerPattern(object):
    """
    Parses a given pattern into a list of XegerExpressions

    This generates a list of top-level expressions that can be used to generate
    the contents of a file.
    """
    def __init__(self, regex, max_random=10):
        self._max_random = max_random
        self._parse_expressions(regex)

    def _parse_expressions(self, regex):
        self._expressions = []
        regex_list = list(regex)
        while regex_list:
            expression = XegerExpression(regex_list, self._max_random)
            if expression._multiplier is None:
                self._expressions.append(expression._generator)
            else:
                self._expressions.append(expression)

    def length(self):
        return len(self._expressions)

    def generate(self, generated_content, generated_content_length):
        new_item_count = 0
        for expression in self._expressions:
            new_items, generated_content_length = \
                expression.generate(generated_content,
                                    generated_content_length)
            new_item_count += new_items
        return new_item_count, generated_content_length


class XegerExpression(object):
    """
    Parses an Expression from a list of input characters
    """
    def __init__(self, regex_list, max_random=10):
        self._max_random = max_random
        self._get_generator(regex_list)

    def _get_generator(self, regex):
        accum = []

        while regex:
            c = regex.pop(0)
            if c == '(':
                # We've reached what appears to be a nested expression
                if not accum:  # We've not accumulated any content to return
                    accum = self._get_nested_pattern_input(regex)
                    self._generator = XegerPattern(accum, self._max_random)
                    self._multiplier = XegerMultiplier(regex)
                    self._is_constant_multiplier()
                    return
                else:  # There is info in the accumulator, so it much be chars
                    regex.insert(0, c)
                    self._generator = XegerSequence(accum)
                    self._constant_multiplier = None
                    self._multiplier = None
                    return
            elif c == '[':  # We've reached the start of a set
                if not accum:  # If nothing in accumulator, just process set
                    self._generator = XegerSet(regex)
                    self._multiplier = XegerMultiplier(regex)
                    self._is_constant_multiplier()
                    return
                else:
                    # There's already stuff in the accumulator, must be chars
                    regex.insert(0, c)
                    self._generator = XegerSequence(accum)
                    self._constant_multiplier = None
                    self._multiplier = None
                    return
            elif c == '\\':  # Escape the next character
                c = regex.pop(0)
                accum.append(c)
            elif c in ['{', '*', '+', '?']:  # We've reached a multiplier
                if len(accum) == 1:  # just multiply a single character
                    regex.insert(0, c)
                    self._generator = XegerSequence(accum)
                    self._multiplier = XegerMultiplier(regex)
                    self._is_constant_multiplier()
                    return
                elif len(accum) > 1:  # only multiply the last character
                    last_c = accum.pop(-1)
                    regex.insert(0, c)
                    regex.insert(0, last_c)
                    self._generator = XegerSequence(accum)
                    self._constant_multiplier = None
                    self._multiplier = None
                    return
                else:
                    raise XegerError("Multiplier used without expression")
            else:  # just keep collecting boring characters
                accum.append(c)

        if accum:  # If there's anything left in the accumulator, must be chars
            self._generator = XegerSequence(accum)
            self._constant_multiplier = None
            self._multiplier = None

    def _is_constant_multiplier(self):
        if not self._multiplier.is_random:
            if self._multiplier.value() == 1:
                # Special case to avoid range on 1
                self._multiplier = None
                self._constant_multiplier = None
            else:
                self._constant_multiplier = True
                self._multiplier = self._multiplier.value()
        else:
            self._constant_multiplier = False

    def _get_nested_pattern_input(self, regex):
        accum = []

        while regex:
            c = regex.pop(0)
            if c == '(':
                accum.append('(')
                accum += self._get_nested_pattern_input(regex)
                accum.append(')')
            elif c == ')':
                return accum
            else:
                accum.append(c)

        raise XegerError("Incomplete expression")

    def generate(self, generated_content, generated_content_length):
        # self._multiplier & self._constant_multiplier
        # are guaranteed to be set if generate() is called
        new_item_count = 0
        if self._constant_multiplier:
            mult = self._multiplier
            for x in xrange(mult):
                new_items, generated_content_length = \
                    self._generator.generate(generated_content,
                                             generated_content_length)
                new_item_count += new_items
        else:
            mult = self._multiplier.value()
            for x in xrange(mult):
                new_items, generated_content_length = \
                    self._generator.generate(generated_content,
                                             generated_content_length)
                new_item_count += new_items

        return new_item_count, generated_content_length


class XegerMultiplier(object):
    """
    Represents a multiplier
    """
    def __init__(self, regex, max_random=10):
        self._max_random = max_random
        self._get_multiplier(regex)

    def _get_multiplier(self, regex):
        mult = []
        started = False

        while regex:
            c = regex.pop(0)
            if c == '{':
                if mult:
                    raise XegerError("Error in multiplier pattern")
                started = True
            elif c == '}':
                if mult:
                    self.is_random = False
                    try:
                        self._constant = int("".join(mult))
                    except:
                        raise XegerError("Multiplier must be a number")
                    return
                else:
                    raise XegerError("Illegal end of multiplier pattern")
            elif c in ['*', '+', '?']:
                if started:
                    raise XegerError("Error in multiplier pattern")
                else:
                    self.is_random = True
                    if c == '+':
                        self._random = FastRandom(1, self._max_random)
                    elif c == '*':
                        self._random = FastRandom(0, self._max_random)
                    else:
                        self._random = FastRandom(0, 1)
                    return
            else:
                if started:
                    mult.append(c)
                else:
                    regex.insert(0, c)
                    break

        if started:
            raise XegerError("Incomplete multiplier")
        else:
            self.is_random = False
            self._constant = 1

    def value(self):
        if self.is_random:
            return self._random.rand()
        else:
            return self._constant


class XegerSequence(object):
    """
    Simple generator, just returns the sequence on each call to generate
    """
    def __init__(self, character_list):
        self._sequence = "".join(character_list)
        self._sequence_length = len(self._sequence)

    def generate(self, generated_content, generated_content_length):
        generated_content.append(self._sequence)
        generated_content_length += self._sequence_length
        return 1, generated_content_length


class XegerSet(object):
    """
    Set generator, parses an input list for a set and returns a single element
    on each call to generate
    """
    def __init__(self, regex):
        if DEBUG:
            logging.debug("Parsing Set from regex: %s" % "".join(regex))
        self._parse_set(regex)

    def _parse_set(self, regex):
        select_list = []
        ch1 = ''

        while regex:
            c = regex.pop(0)
            if c == ']':
                if not ch1 == '':
                    self._set = select_list
                    self._random = FastRandom(0, len(self._set) - 1)
                    return
                else:
                    raise XegerError("Error in set description")
            elif c == '-':
                if ch1 == '':
                    raise XegerError("Error in set description")
                elif len(regex) == 0:
                    raise XegerError("Incomplete set description")
                else:
                    # Remove the unneeded character from the last loop
                    select_list.pop(-1)
                    ch2 = regex.pop(0)
                    set_extras = self._char_range(ch1, ch2)
                    for extra in set_extras:
                        select_list.append(extra)
            elif c == '\\':  # Escape the next character
                c = regex.pop(0)
                ch1 = c
                select_list.append(c)
            elif c in XegerGen.reserved_chars:
                raise XegerError("Non-escaped special character in set")
            else:
                ch1 = c
                select_list.append(ch1)

        # The range was incomplete because we never reached the closing brace
        raise XegerError("Incomplete set description")

    def _char_range(self, a, b):
        return [chr(c) for c in range(ord(a), ord(b)+1)]

    def generate(self, generated_content, generated_content_length):
        generated_content.append(self._set[self._random.rand()])
        return 1, generated_content_length + 1
