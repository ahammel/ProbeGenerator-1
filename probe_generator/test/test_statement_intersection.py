"""Test whether it's possible for a string to match more than one statement
regular expression.

"""
import re
import itertools
import sys

from nose.plugins.skip import SkipTest
from greenery import lego

import probe_generator

PROBE_MODULES = (
    probe_generator.coordinate_probe,
    probe_generator.snp_probe,
    probe_generator.exon_probe,
    probe_generator.amino_acid_probe,
    probe_generator.gene_snp_probe,
    probe_generator.gene_indel_probe,
    )


def deverbosify(regex):
    """Return verbose regular expression string with the comments and
    whitespace stripped out.

    Because of the way greenery deals with escapes (i.e., incorrectly), I
    also escape hyphens in character classes even if they're at the end of the
    class, and un-escape the '#' character (the escape character is required
    in Python verbose regexes for a literal '#').

    """
    sub_strings = []
    for line in regex.split("\n"):
        decommented_line = re.sub(r'[^\\]#.*', '', line)
        whitepace_stripped_line = re.sub(r'\s', '', decommented_line)
        escaped_line = re.sub(r'-]', '\-]', whitepace_stripped_line)
        unescaped_line = re.sub(r'\\#', '#', escaped_line)
        sub_strings.append(unescaped_line)
    return ''.join(sub_strings)


def assert_non_overlapping(fsa1, fsa2):
    """Assert that the intersection of two lego finite state automata is the
    empty FSA.

    """
    if not'--no-skip' in sys.argv:
        raise SkipTest
    assert fsa1 & fsa2 == lego.charclass(), ("Overlapping regex: "
                                             "{}".format(fsa1 & fsa2))

def test_statement_regex_mutual_exclusivity():
    fsa_list = [lego.parse(deverbosify(module._STATEMENT_REGEX.pattern))
                for module in PROBE_MODULES]
    for fsa1, fsa2 in itertools.combinations(fsa_list, 2):
        yield assert_non_overlapping, fsa1, fsa2
