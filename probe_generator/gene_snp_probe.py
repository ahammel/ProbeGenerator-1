"""Probe for an SNP mutation based on the index of a nucleotide in a coding
sequence.

"""
import re
import sys

from probe_generator import annotation, transcript
from probe_generator.amino_acid_probe import AminoAcidProbe
from probe_generator.probe import AbstractProbe, InvalidStatement
from probe_generator.sequence import reverse_complement

_STATEMENT_REGEX = re.compile("""
        \s*                # whitespace
        ([a-zA-Z0-9_./-]+) # gene name
        \s*
        :
        \s*
        c\.
        ([0-9]+)           # base number
        \s*
        ([ACGTacgt])       # reference base
        \s*
        >
        \s*
        ([ACGTacgt])       # mutation base
        \s*
        /
        \s*
        ([0-9]+)           # number of base pairs
        \s*
        (--.*|\s*)         # comment
        """, re.VERBOSE)


class GeneSnpProbe(AbstractProbe):
    """Probe for a single nucleotide mutation event at a base pair specified
    relative to the start of a transcript.

    """
    _STATEMENT_SKELETON = ("{gene}:c.{base}{reference}>{mutation}/{bases}_"
                           "{transcript}_{chromosome}:{index}{comment}")

    def get_ranges(self):
        return AminoAcidProbe.get_ranges(self)

    @staticmethod
    def explode(statement, genome_annotation=None):
        """Given a gene SNP probe statement, return all the probes which match
        the specification.

        If more than one probe has identical genomic coordinates, only the
        first is returned.

        """
        probes = []

        if genome_annotation is None:
            genome_annotation = []
        partial_spec = _parse(statement)
        transcripts = annotation.lookup_gene(
            partial_spec["gene"], genome_annotation)
        cached_coordinates = set()
        for txt in transcripts:
            if txt.plus_strand:
                base = partial_spec["base"]
            else:
                base = partial_spec["base"] - 2
                partial_spec["mutation"] = reverse_complement(
                    partial_spec["mutation"])
            try:
                index = txt.nucleotide_index(base)
            except transcript.OutOfRange as error:
                print("{} in statement: {!r}".format(error, statement),
                      file=sys.stderr)
            else:
                chromosome = txt.chromosome
                if not (chromosome, index) in cached_coordinates:
                    cached_coordinates.add((chromosome, index))
                    spec = dict(partial_spec,
                                chromosome=chromosome,
                                transcript=txt.name,
                                index=index)
                    probes.append(GeneSnpProbe(spec))
        return probes


def _parse(statement):
    """Return a partial GeneSnpProbe specification given a probe statement.

    Raises an InvalidStatement exception when fed an invalid gene snp
    statement.

    """
    match = _STATEMENT_REGEX.match(statement)

    if not match:
        raise InvalidStatement
    (gene,
     base,
     reference,
     mutation,
     bases,
     comment) = match.groups()
    return {"gene": gene,
            "base": int(base),
            "reference": reference,
            "mutation": mutation,
            "bases": int(bases),
            "comment": comment}
