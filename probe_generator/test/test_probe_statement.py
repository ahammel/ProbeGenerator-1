import unittest

import probe_generator.probe_statement as statement


class AbstractProbeStatementTestCase(unittest.TestCase):
    """Provides setUp function for testcases in the `probe_statement` module.

    """
    def setUp(self):
        self.probe_statement = "ABC#exon[1] -20 / DEF#intron[3] +30"
        self.probe_specification = {
                    'gene1':    'ABC',
                    'feature1': ('exon', 1),
                    'side1':    'end',
                    'bases1':   20,
                    'gene2':    'DEF',
                    'feature2': ('intron', 3),
                    'side2':    'start',
                    'bases2':   30,
                }


class TestProbeStatement(AbstractProbeStatementTestCase):
    """Test cases for probe language parsing functionality

    """
    def setUp(self):
        super(TestProbeStatement, self).setUp()

    def test_parse_basic_probe_statement(self):
        self.assertEqual(
                statement.parse(self.probe_statement),
                self.probe_specification)

    def test_nonsense_probe_statement_raises_exception(self):
        with self.assertRaisesRegex(statement.InvalidStatement, "banana"):
            statement.parse("banana")

    def test_partial_probe_statement_raises_InvalidStatement(self):
        with self.assertRaises(statement.InvalidStatement):
            statement.parse(self.probe_statement[:10])

    def test_probe_statements_are_whitespace_insensitive(self):
        self.assertEqual(
                statement.parse(
                    "ABC#exon[1] -20 / DEF#intron[3] +30"),
                statement.parse(
                    "\tABC # exon[\n1\n] -    20/DEF#intron[3]+30")
                )

    # In the names of the following tests, elements of a statement are
    # 'globbable' if they can be replaced by the '*' character.
    def test_probe_statement_genes_are_not_globbable(self):
        with self.assertRaises(statement.InvalidStatement):
            statement.parse("*#exon[1] -20 / DEF#intron[3] +30")
        with self.assertRaises(statement.InvalidStatement):
            statement.parse("ABC#exon[1] -20 / *#intron[3] +30")

    def test_probe_statement_features_are_globbable(self):
        self.probe_specification['feature1'] = ('*', 1)
        self.probe_specification['feature2'] = ('*', 3)
        self.assertEqual(
                statement.parse("ABC#*[1] -20 / DEF#*[3] +30"),
                self.probe_specification)

    def test_probe_statement_feature_numbers_are_globbable(self):
        self.probe_specification['feature1'] = ('exon', '*')
        self.probe_specification['feature2'] = ('intron', '*')
        self.assertEqual(
                statement.parse("ABC#exon[*] -20 / DEF#intron[*] +30"),
                self.probe_specification)

    def test_probe_statement_sides_are_globbable(self):
        self.probe_specification['side1'] = '*'
        self.probe_specification['side2'] = '*'
        self.assertEqual(
                statement.parse("ABC#exon[1] *20 / DEF#intron[3] *30"),
                self.probe_specification)

    def test_probe_statement_bases_are_globbable(self):
        self.probe_specification['bases1'] = '*'
        self.probe_specification['bases2'] = '*'
        self.assertEqual(
                statement.parse("ABC#exon[1] -* / DEF#intron[3] +*"),
                self.probe_specification)

    def test_probe_statement_glob_eveything(self):
        """
        A test where everything that can be globbed is globbed.

        """
        self.probe_specification['feature1'] = ('*', '*')
        self.probe_specification['feature2'] = ('*', '*')
        self.probe_specification['side1'] = '*'
        self.probe_specification['side2'] = '*'
        self.probe_specification['bases1'] = '*'
        self.probe_specification['bases2'] = '*'
        self.assertEqual(
                statement.parse("ABC#*[*] ** / DEF#*[*] **"),
                self.probe_specification)


class TestExpand(AbstractProbeStatementTestCase):
    """Test case for the `probe_statement.expand` function.

    """
    def setUp(self):
        super(TestExpand, self).setUp()

    def test_expand_returns_one_statement_for_fully_realized_statement(self):
        self.assertEqual(
                list(statement.expand(self.probe_specification)),
                [self.probe_specification])

    def test_expand_one_side(self):
        self.probe_specification['side1'] = '*'
        self.assertCountEqual(
                [spec['side1']
                 for spec in statement.expand(self.probe_specification)],
                ['start', 'end'])

    def test_expand_both_sides(self):
        self.probe_specification['side1'] = '*'
        self.probe_specification['side2'] = '*'
        self.assertCountEqual(
                [(spec['side1'], spec['side2'])
                 for spec in statement.expand(self.probe_specification)],
                [('start', 'start'), ('start', 'end'),
                 ('end', 'start'),   ('end', 'end')])

    def test_expand_exon_numbers(self):
        self.probe_specification['feature1'] = ('exon', '*')
        self.probe_specification['feature2'] = ('exon', '*')
        self.assertCountEqual(
                [(spec['feature1'], spec['feature2'])
                  for spec in statement.expand(
                      self.probe_specification, 2, 3)],
                 [(('exon', 1), ('exon', 1)),
                  (('exon', 1), ('exon', 2)),
                  (('exon', 1), ('exon', 3)),
                  (('exon', 2), ('exon', 1)),
                  (('exon', 2), ('exon', 2)),
                  (('exon', 2), ('exon', 3))])

    def test_glob_expanision_does_not_change_value_of_spec(self):
        spec = statement.parse("ABC#exon[*] ** / DEF#exon[*] **")
        value_before = spec.copy()
        for _ in statement.expand(spec, 1, 2):
            pass
        self.assertEqual(spec, value_before)

    def test_expand_raises_ExpandError_when_number_of_features_needed(self):
        """
        The `left_features` must be specified when the number of features in
        'feature1' is a glob. Same with `right_features` and 'feature2'.

        """
        message = ("number of features must be specified when "
                   "feature number is globbed")
        with self.assertRaisesRegex(statement.ExpandError, message):
            self.probe_specification['feature1'] = ('exon', '*')
            for _ in statement.expand(self.probe_specification):
                pass