"""Get the sequence range for a probe.

Provides the `sequence_range` function, which returns a dictionary specifying
the genomic location of a probe sequence, given a row of a UCSC gene table and
a fully-realized specification (one without wild-card characters).

"""
import sys

from probe_generator import annotation

WARNING_MESSAGE = (
        "WARNING: probes generated using the '->' syntax may not have the \n"
        "expected value when the end of the first exon is not joined to the \n"
        "start of the second.\n\n"
        "Double-check that your probe statments are specified correctly.\n")


def sequence_range(specification, row_1, row_2):
    """Return the range of base pairs to be extracted from the genome.

    `specification` is a probe specification, such as is returned by
    `probe_statement.parse`. The `specification` must be fully-realized (i.e.,
    no globs except in the 'bases' field). `row_1` and `row_2` are rows from a
    UCSC annotation table.

    Returns a dict in the same format as a coordinate statement.

    Raises an `InterfaceError` if the `specification` or either of the `rows`
    are improperly formatted.

    Raises a `NoFeatureError` if the `specification` asks for a feature outside
    of the range of the `row`.

    """
    if specification.get('separator') == '/':
        return _positional_sequence_range(
                specification, row_1, row_2)
    elif specification.get('separator') == '->':
        return _read_through_sequence_range(
                specification, row_1, row_2)
    else:
        raise InterfaceError


def _read_through_sequence_range(specification, row_1, row_2):
    """Return the sequence range for a 'read through' probe specification.

    This strategy returns a sequence range for a fusion that is oriented such
    that the two exons form a single transcriptional unit that can potentially
    be transcribed and translated.

    In practice, this is similar to the positional strategy indicated by the
    '/' operator, but with two differences:

        1. The start and end operators are less relevant, as a read-through
           event only makes sense when it covers the end of the first gene and
           the beginning of the second gene.

        2. The two sequences are rearranged such that the end of the first
           gene touches the start of the second.

    For example:
                                                BAR
                                               |=========>
            ..............................................
            ..............................................
            <-------|
                 FOO


            FOO-/BAR+
                    <----====|
            FOO->BAR
                    ====|<----
    """
    _check_read_through_spec(specification)
    if row_1.get('strand') == '+':
        return _positional_sequence_range(
                specification,
                row_1,
                row_2)
    elif row_1.get('strand') == '-':
        return _positional_sequence_range(
                _flip_specification(specification),
                row_2,
                row_1)
    else:
        raise InterfaceError


def _flip_specification(specification):
    """Return the specification with all of the fields ending in '1' replaced
    with the corresponding field ending in '2' and vice-versa.

    """
    try:
        return dict(
                specification,
                gene1=specification['gene2'],
                gene2=specification['gene1'],
                feature1=specification['feature2'],
                feature2=specification['feature1'],
                side1=specification['side2'],
                side2=specification['side1'],
                bases1=specification['bases2'],
                bases2=specification['bases1'])
    except KeyError as error:
        raise InterfaceError(error)


def _check_read_through_spec(specification):
    """Raises a warning message if the sides of the specification don't make
    sense.

    This is only an issue for probes specified using the read-through syntax.
    In fact, I may make it illegal to specify sides at all for read-through
    statements in a future version.

    """
    try:
        sides_ok = (specification['side1'] == 'end' and
                    specification['side2'] == 'start')
    except KeyError:
        raise InterfaceError
    if not sides_ok:
        print(WARNING_MESSAGE, file=sys.stderr, end="")


def _positional_sequence_range(specification, row_1, row_2):
    """Return the sequence range for a positional probe specification.

    This strategy returns a sequence range based on the sides of the exons
    specified in the probe statement.

    """
    left_chromosome, right_chromosome = _get_chromosomes(row_1, row_2)
    (left_start,
     left_end,
     right_start,
     right_end) = _get_base_positions(specification, row_1, row_2)

    rc_left, rc_right = _get_rev_comp_flags(
            specification, row_1, row_2)

    return {'chromosome1': left_chromosome,
            'start1':      left_start,
            'end1':        left_end,
            'chromosome2': right_chromosome,
            'start2':      right_start,
            'end2':        right_end,
            'rc_side_1':   rc_left,
            'rc_side_2':   rc_right}


def _get_chromosomes(*rows):
    """Return the chromosomes of the rows with the 'chr' prefix removed if it
    exists.

    """
    return (row['chrom'].lstrip('chr') for row in rows)


def _get_base_positions(specification, row_1, row_2):
    """Return a 4-tuple of the start and end positions of row_1 and row_2.

    """
    try:
        (first_feature,
         first_bases,
         first_side,
         second_feature,
         second_bases,
         second_side) = (specification['feature1'],
                         specification['bases1'],
                         specification['side1'],
                         specification['feature2'],
                         specification['bases2'],
                         specification['side2'])
    except KeyError as error:
        raise InterfaceError(str(error))
    start_1, end_1 = _get_base_position_per_row(
            first_feature, first_bases, first_side, row_1)
    start_2, end_2 = _get_base_position_per_row(
            second_feature, second_bases, second_side, row_2)
    return start_1, end_1, start_2, end_2


def _get_base_position_per_row(feature, bases, side, row):
    """Return the start and end positions of a probe, given a feature, the
    side of the feature, the number of bases required (may be a glob) and the
    related row of a UCSC gene annotation table.

    """
    _, which_exon = feature
    try:
        strand = row['strand']
    except KeyError as error:
        raise InterfaceError(str(error))
    exon_positions = annotation.exons(row)

    exon_start, exon_end = _get_exon(exon_positions, which_exon)

    if bases == '*':
        return exon_start, exon_end
    else:
        return _get_base_pair_range(bases, exon_start, exon_end, side, strand)


def _get_base_pair_range(bases, start, end, side, strand):
    """Return the desired sub-range of a genomic feature, given its range, the
    number of base-pairs required, the side from which the sub-range is to be
    extracted, and the strand of the feature.

    """
    if _is_leftmost_side(side, strand):
        return start + 1, (start + bases)
    else:
        return (end - bases + 1), end


def _is_leftmost_side(side, strand):
    """Is the side of the exon we're asking for closest to base 1 of the
    chromosome?

    The _leftmost_ base pair of an exon (i.e., the one with the lowest index)
    is the _start_ of an exon on the plus strand, on the _end_ of an exon on
    the minus strand:

                    start |                end |
                          --------------------->
          1 + ...................................................
            - ...................................................
                          <---------------------
                          ^ end                ^ start

    In UCSC genome files, the starting base pairs of exons are given from left
    to right across the '+' strand of the chromosome, regardless of the
    orientation of the gene. The locations of the start and the stop codons of an
    exon are switched for a gene on the minus strand.

    The coordinates of the exons are given in left-exclusive-right-inclusive
    format---(n,m] in interval notation---meaning that for a gene on the plus
    strand, the 'A' of the 'ATG' codon which starts the exon is actually one
    base _after_ the exon starts value:

    {exonStarts: 100,
     exonEnds:   200,
     strand:     +}:
                          --------->
                    100 101 102 103 ...
                      N   A   T   G ...
             non-exon }   { exon    ...

    """
    return (side == 'start') == (strand == '+')


def _get_exon(positions, index):
    """Return the exon at the (1-based) `index` in the `positions` list.

    """
    try:
        return positions[index-1] # zero-indexed list
    except IndexError:
        raise NoFeatureError(
                "specification requires feature 'exon'[{number!s}], "
                "but row specifies only {length} 'exon'(s)".format(
                    number=index,
                    length=len(positions)))


def _get_rev_comp_flags(specification, row_1, row_2):
    """Determine whether the specification represents an inversion event.

    Take a probe specification and two lines from a UCSC genome annotation.

    We reverse-complement the first set of base pairs if it's the start of an
    exon on the plus strand, or the end of an exon on the minus strand. The
    second set of base-pairs is rc'd if it's the start of an exon on the minus
    strand or the end of an exon on the plus strand. If this rule is followed,
    the intended breakpoint is always in the middle of the probe.

    [Understand? Good, explain it to me. --Alex]

    """
    side1, side2 = specification['side1'], specification['side2']
    strand1, strand2 = row_1['strand'], row_2['strand']
    return ((side1, strand1) in (('start', '+'), ('end', '-')),
            (side2, strand2) in (('start', '-'), ('end', '+')))


class InterfaceError(Exception):
    """Raised when an object from another module does not provide the expected
    interface.

    """


class NoFeatureError(Exception):
    """Raised when a specification asks for a feature outside of the range of a
    UCSC table row.

    """
