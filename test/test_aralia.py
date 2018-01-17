# Copyright (C) 2014-2018 Olzhas Rakhimov
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Tests for the Aralia-to-XML converter."""

from __future__ import absolute_import

import os
from tempfile import NamedTemporaryFile
from unittest import TestCase

from lxml import etree
from nose.tools import assert_raises

from aralia import ParsingError, FormatError, FaultTreeError, parse_input, main


def parse_input_file(name, multi_top=False):
    """Calls the input file parser to get the fault tree."""
    with open(name) as aralia_file:
        return parse_input(aralia_file, multi_top)


def test_correct():
    """Tests the valid overall process."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("ValidFaultTree\n\n")
    tmp.write("root := g1 | g2 | g3 | g4 | g7 | g9 | g10 | e1\n")
    tmp.write("g1 := e2 & g3 & g5\n")
    tmp.write("g2 := h1 & g6\n")
    tmp.write("g3 := (g6 ^ e2)\n")
    tmp.write("g4 := @(2, [g5, e3, e4])\n")
    tmp.write("g5 := ~(e3)\n")
    tmp.write("g6 := (e3 | e4)\n\n")
    tmp.write("g7 := g8\n\n")
    tmp.write("g8 := ~e2 & ~e3\n\n")
    tmp.write("g9 := (g8 => g2)\n")
    tmp.write("g10 := e1 <=> e2\n")
    tmp.write("p(e1) = 0.1\n")
    tmp.write("p(e2) = 0.2\n")
    tmp.write("p(e3) = 0.3\n")
    tmp.write("s(h1) = true\n")
    tmp.write("s(h2) = false\n")
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None
    assert len(fault_tree.gates) == 11
    assert len(fault_tree.basic_events) == 3
    assert len(fault_tree.house_events) == 2
    assert len(fault_tree.undefined_events()) == 1
    out = NamedTemporaryFile(mode="w+")
    out.write("<?xml version=\"1.0\"?>\n")
    out.write(fault_tree.to_xml())
    out.flush()
    relaxng_doc = etree.parse("schemas/2.0d/mef.rng")
    relaxng = etree.RelaxNG(relaxng_doc)
    with open(out.name, "r") as test_file:
        doc = etree.parse(test_file)
        assert relaxng.validate(doc)


def test_ft_name_redefinition():
    """Tests the redefinition of the fault tree name."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FaultTreeName\n")
    tmp.write("AnotherFaultTree\n")
    tmp.write("g1 := e1\n")
    tmp.flush()
    assert_raises(FormatError, parse_input_file, tmp.name)


def test_ncname_ft():
    """The name of the fault tree must conform to NCNAME format."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("Contains Whitespace Characters\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("Peri.od\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("EndWithDash-\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("Double--Dash\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("42StartWithNumbers\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("Correct-Name_42\n")
    tmp.write("g1 := e1 & e2\n")  # dummy gate
    tmp.flush()
    parse_input_file(tmp.name)


def test_no_ft_name():
    """Tests the case where no fault tree name is provided."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := h1 & e1\n")
    tmp.flush()
    assert_raises(FormatError, parse_input_file, tmp.name)


def test_illegal_format():
    """Test Arithmetic operators."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 + e1\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 * e1\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := -e1\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 / e1\n")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)


def test_repeated_argument():
    """Tests the formula with a repeated argument."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := e1 & e1\n")
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)


def test_case_sensitive():
    """Tests the formula with a case-sensitive argument."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & G2\n")  # considered repeated arg w/o case-sensitive.
    tmp.write("g2 := E1 & e1\n")
    tmp.write("G2 := E1 & e1\n")  # considered repeated def w/o case-sensitive.
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None


def test_missing_parenthesis():
    """Tests cases with a missing opening or closing parentheses."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("WrongParentheses\n")
    tmp.write("g1 := a | b)")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("WrongParentheses\n")
    tmp.write("g1 := (a | b")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)


def test_nested_parentheses():
    """Tests cases with nested parentheses."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("WrongParentheses\n")
    tmp.write("g1 := ((a | b))")
    tmp.flush()
    assert_raises(ParsingError, parse_input_file, tmp.name)


def test_vote_gate_arguments():
    """K/N or Combination gate/operator should have its K < its N."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := @(3, [a, b, c])")  # K = N
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := @(4, [a, b, c])")  # K > N
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)


def test_null_gate():
    """Tests if NULL type gates are recognized correctly."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := a")
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None
    assert len(fault_tree.gates) == 1
    assert fault_tree.gates[0].name == "g1"
    assert "a" in fault_tree.gates[0].event_arguments
    assert fault_tree.gates[0].operator == "null"


def test_not_gate():
    """Tests if NOT type gates are recognized correctly."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := ~(a)")
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None
    assert len(fault_tree.gates) == 1
    assert fault_tree.gates[0].name == "g1"
    assert "a" in fault_tree.gates[0].event_arguments
    assert fault_tree.gates[0].operator == "not"


def test_imply_gate():
    """Tests if IMPLY type gates are recognized correctly."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := (a => b)")
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None
    assert len(fault_tree.gates) == 1
    assert fault_tree.gates[0].name == "g1"
    assert fault_tree.gates[0].event_arguments == ["a", "b"]
    assert fault_tree.gates[0].operator == "imply"


def test_iff_gate():
    """Tests if IFF type gates are recognized correctly."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := (a <=> b)")
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None
    assert len(fault_tree.gates) == 1
    assert fault_tree.gates[0].name == "g1"
    assert fault_tree.gates[0].event_arguments == ["a", "b"]
    assert fault_tree.gates[0].operator == "iff"


def test_no_top_event():
    """Detection of cases without top gate definitions.

    Note that this also means that there is a cycle that includes the root.
    """
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := g1 & e1\n")
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)


def test_multi_top():
    """Multiple root events without the flag causes a problem by default."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := e2 & e1\n")
    tmp.write("g2 := h1 & e1\n")
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)
    assert parse_input_file(tmp.name, True) is not None  # with the flag


def test_redefinition():
    """Tests name collision detection of events."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := h1 & e1\n")
    tmp.write("g2 := e2 & e1\n")  # redefining an event
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)


def test_orphan_events():
    """Tests cases with orphan house and basic event events."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := h1 & e1\n")
    tmp.write("p(e1) = 0.5\n")
    tmp.write("s(h1) = false\n")
    tmp.flush()
    assert parse_input_file(tmp.name) is not None
    tmp.write("p(e2) = 0.1\n")  # orphan basic event
    tmp.flush()
    assert parse_input_file(tmp.name) is not None
    tmp.write("s(h2) = true\n")  # orphan house event
    tmp.flush()
    assert parse_input_file(tmp.name) is not None


def test_cycle_detection():
    """Tests cycles in the fault tree."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := g3 & e1\n")
    tmp.write("g3 := g2 & e1\n")  # cycle
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := u1 & g2 & e1\n")
    tmp.write("g2 := u2 & g3 & e1\n")  # nested formula cycle
    tmp.write("g3 := u3 & g2 & e1\n")  # cycle
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)


def test_detached_gates():
    """Some cycles may get detached from the original fault tree."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := e2 & e1\n")
    tmp.write("g2 := g3 & e1\n")  # detached gate
    tmp.write("g3 := g2 & e1\n")  # cycle
    tmp.flush()
    assert_raises(FaultTreeError, parse_input_file, tmp.name)


class ComplementArgTestCase(TestCase):
    """Complement arguments of gates."""

    def setUp(self):
        """Launches a temporary file."""
        self.tmp = NamedTemporaryFile(mode="w+")
        self.tmp.write("FT\n")

    def check_gate(self, symbol, operator, custom_gate=None):
        """Default g1 gate test with e2 as a complement argument."""
        if custom_gate:
            self.tmp.write(custom_gate)
        else:
            self.tmp.write("g1 := e1 %s ~e2\n" % symbol)
        self.tmp.flush()
        fault_tree = parse_input_file(self.tmp.name)
        assert fault_tree is not None
        assert len(fault_tree.gates) == 1
        gate = fault_tree.gates[0]
        assert gate.name == "g1"
        assert gate.operator == operator
        if not custom_gate:
            assert "e1" in gate.event_arguments
        assert "~e2" in gate.event_arguments
        assert len(gate.complement_arguments) == 1
        assert [x.name for x in gate.complement_arguments][0] == "e2"

    def test_or(self):
        """OR formula with complement arguments."""
        self.check_gate("|", "or")

    def test_xor(self):
        """XOR formula with complement arguments."""
        self.check_gate("^", "xor")

    def test_imply(self):
        """IMPLY formula with complement arguments."""
        self.check_gate("=>", "imply")

    def test_and(self):
        """AND Formula with complement arguments."""
        self.check_gate("&", "and")

    def test_vote(self):
        """Combination with complement arguments."""
        self.check_gate("@", "atleast", "g1 := @(2, [e1, ~e2, e3])")

    def test_null(self):
        """NULL with a single complement argument."""
        self.check_gate("", "null", "g1 := ~e2")

    def test_not(self):
        """NOT of a complement argument."""
        self.check_gate("", "not", "g1 := ~(~e2)")

    def test_cancellation(self):
        """Supplies argument and its complement."""
        self.check_gate("&", "and", "g1 := ~e2 & e2")


class NestedFormulaTestCase(TestCase):
    """Nested logical operator tests."""

    def setUp(self):
        """Launches a temporary file."""
        self.tmp = NamedTemporaryFile(mode="w+")
        self.tmp.write("FT\n")

    def test_or_xor(self):
        """Formula with OR and XOR operators."""
        self.tmp.write("g1 := e1 | e2 ^ e3\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)

    def test_or_and(self):
        """Formula with OR and AND operators."""
        self.tmp.write("g1 := e1 | e2 & e3\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)

    def test_or_vote(self):
        """Formula with OR and K/N operators."""
        self.tmp.write("g1 := e1 | @(2, [e2, e3, e4])\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)

    def test_xor_xor(self):
        """Formula with XOR and XOR operators.

        Note that this is a special case
        because most analysis restricts XOR operator to two arguments,
        so nested formula of XOR operators must be created.
        """
        self.tmp.write("g1 := e1 ^ e2 ^ e3\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)

    def test_xor_and(self):
        """Formula with XOR and AND operators."""
        self.tmp.write("g1 := e1 ^ e2 & e3\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)

    def test_not_not(self):
        """Formula with NOT and NOT operators.

        This is a special case. It is considered an error without parentheses.
        """
        self.tmp.write("g1 := ~~e1\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)
        tmp = NamedTemporaryFile(mode="w+")
        tmp.write("FT\n")
        tmp.write("g1 := ~e1~a\n")
        tmp.flush()
        assert_raises(ParsingError, parse_input_file, tmp.name)

    def test_imply_imply(self):
        """Formula with IMPLY and IMPLY operators."""
        self.tmp.write("g1 := e1 => e2 => e3\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)

    def test_imply_or(self):
        """Formula with IMPLY and OR operators."""
        self.tmp.write("g1 := e1 => e2 || e3\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)

    def test_iff_iff(self):
        """Formula with IFF and IFF operators."""
        self.tmp.write("g1 := e1 <=> e2 <=> e3\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)

    def test_iff_or(self):
        """Formula with IFF and OR operators."""
        self.tmp.write("g1 := e1 <=> e2 || e3\n")
        self.tmp.flush()
        assert_raises(ParsingError, parse_input_file, self.tmp.name)


def test_main():
    """Tests the main function."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := g3 & e1\n")
    tmp.write("g3 := e2 & e1\n")
    tmp.flush()
    main([tmp.name])
    out = os.path.basename(tmp.name)
    out = os.path.splitext(out)[0] + ".xml"
    assert os.path.exists(out)
    os.remove(out)
