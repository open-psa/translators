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

from lxml import etree
import pytest

from aralia import ParsingError, FormatError, FaultTreeError, parse_input, main


def parse_input_file(name, multi_top=False):
    """Calls the input file parser to get the fault tree."""
    with open(name) as aralia_file:
        return parse_input(aralia_file, multi_top)


def test_correct():
    """Tests the valid overall process."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("ValidFaultTree\n\n")
    tmp.write("root := g1 | g2 | g3 | g4 | g7 | g9 | g10 | g11 | e1\n")
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
    tmp.write("g11 := #(2, 4, [e1, e2, e3, e4, g5])\n")
    tmp.write("p(e1) = 0.1\n")
    tmp.write("p(e2) = 0.2\n")
    tmp.write("p(e3) = 0.3\n")
    tmp.write("s(h1) = true\n")
    tmp.write("s(h2) = false\n")
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None
    assert len(fault_tree.gates) == 12
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
    with pytest.raises(FormatError):
        parse_input_file(tmp.name)


@pytest.mark.parametrize("name", [
    "Contains Whitespace Characters", "Peri.od", "EndWithDash-", "Double--Dash",
    "42StartWithNumbers", "__under__", "~Not", "Not~a", "!Not", "&And", "And&"
])
def test_ncname_ft(name):
    """The name of the fault tree must conform to NCNAME format."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("%s\n" % name)
    tmp.flush()
    with pytest.raises(ParsingError):
        parse_input_file(tmp.name)


@pytest.mark.parametrize("name", [
    "Period", "With-Dash", "With_Under", "With__Dunder", "WithNumber42",
    "Correct-Name_42"
])
def test_correct_ncname_ft(name):
    """The name of the fault tree must conform to NCNAME format."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("%s\n" % name)
    tmp.write("g1 := e1 & e2\n")  # dummy gate
    tmp.flush()
    parse_input_file(tmp.name)


def test_no_ft_name():
    """Tests the case where no fault tree name is provided."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := h1 & e1\n")
    tmp.flush()
    with pytest.raises(FormatError):
        parse_input_file(tmp.name)


@pytest.mark.parametrize("definition", [
    "g1 := g2 + e1", "g1 := g2 * e1", "g1 := -e1", "g1 := g2 / e1",
    "g1 = e1 & e2", "g1 : e1 & e2", "g1 := (3 == (e1 + e2 + e3))",
    "g1 := (1, [e1, e2, e3])", "g1 := (2, [])", "g1 := (2, [e1])",
    "g1 := (2, [e1, e2])", "g1 := (-1, [e1, e2, e3])"
])
def test_illegal_format(definition):
    """Test Arithmetic operators."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("%s\n" % definition)
    tmp.flush()
    with pytest.raises(ParsingError):
        parse_input_file(tmp.name)


def test_repeated_argument():
    """Tests the formula with a repeated argument."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := e1 & e1\n")
    tmp.flush()
    with pytest.raises(FaultTreeError):
        parse_input_file(tmp.name)


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


@pytest.mark.parametrize("definition",
                         ["g1 := a | b)", "g1 := (a | b", "g1 := ((a | b)"])
def test_missing_parenthesis(definition):
    """Tests cases with a missing opening or closing parentheses."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("WrongParentheses\n")
    tmp.write("%s\n" % definition)
    tmp.flush()
    with pytest.raises(ParsingError):
        parse_input_file(tmp.name)


def test_nested_parentheses():
    """Tests cases with nested parentheses."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("WrongParentheses\n")
    tmp.write("g1 := ((a | b))")
    tmp.flush()
    with pytest.raises(ParsingError):
        parse_input_file(tmp.name)


@pytest.mark.parametrize(
    "definition",
    [
        "g1 := @(3, [a, b, c])",  # K = N
        "g1 := @(4, [a, b, c])"  # K > N
    ])
def test_atleast_gate_arguments(definition):
    """K/N or Combination gate/operator should have its K < its N."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("%s\n" % definition)  # K = N
    tmp.flush()
    with pytest.raises(FaultTreeError):
        parse_input_file(tmp.name)


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


def test_atleast_gate():
    """Tests if ATLEAST type gates are recognized correctly."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := @(2, [e1, e2, e3, e4, e5])")
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None
    assert len(fault_tree.gates) == 1
    gate = fault_tree.gates[0]
    assert gate.name == "g1"
    assert gate.event_arguments == ["e1", "e2", "e3", "e4", "e5"]
    assert gate.operator == "atleast"
    assert gate.min_num == 2


def test_cardinality_gate():
    """Tests if CARDINALITY type gates are recognized correctly."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := #(2, 4, [e1, e2, e3, e4, e5])")
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
    assert fault_tree is not None
    assert len(fault_tree.gates) == 1
    gate = fault_tree.gates[0]
    assert gate.name == "g1"
    assert gate.event_arguments == ["e1", "e2", "e3", "e4", "e5"]
    assert gate.operator == "cardinality"
    assert gate.min_num == 2
    assert gate.max_num == 4


def test_no_top_event():
    """Detection of cases without top gate definitions.

    Note that this also means that there is a cycle that includes the root.
    """
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := g1 & e1\n")
    tmp.flush()
    with pytest.raises(FaultTreeError):
        parse_input_file(tmp.name)


def test_multi_top():
    """Multiple root events without the flag causes a problem by default."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := e2 & e1\n")
    tmp.write("g2 := h1 & e1\n")
    tmp.flush()
    with pytest.raises(FaultTreeError):
        parse_input_file(tmp.name)
    assert parse_input_file(tmp.name, True) is not None  # with the flag


def test_redefinition():
    """Tests name collision detection of events."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := g2 & e1\n")
    tmp.write("g2 := h1 & e1\n")
    tmp.write("g2 := e2 & e1\n")  # redefining an event
    tmp.flush()
    with pytest.raises(FaultTreeError):
        parse_input_file(tmp.name)


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
    with pytest.raises(FaultTreeError):
        parse_input_file(tmp.name)


def test_detached_gates():
    """Some cycles may get detached from the original fault tree."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := e2 & e1\n")
    tmp.write("g2 := g3 & e1\n")  # detached gate
    tmp.write("g3 := g2 & e1\n")  # cycle
    tmp.flush()
    with pytest.raises(FaultTreeError):
        parse_input_file(tmp.name)


@pytest.mark.parametrize("symbol,operator,custom_gate", [
    ("|", "or", None),
    ("^", "xor", None),
    ("=>", "imply", None),
    ("&", "and", None),
    ("@", "atleast", "g1 := @(2, [e1, ~e2, e3])"),
    ("", "null", "g1 := ~e2"),
    ("", "not", "g1 := ~(~e2)"),
    ("&", "and", "g1 := ~e2 & e2"),
])
def test_complement_arg(symbol, operator, custom_gate):
    """Complement arguments of gates."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    if custom_gate:
        tmp.write(custom_gate)
    else:
        tmp.write("g1 := e1 %s ~e2\n" % symbol)
    tmp.flush()
    fault_tree = parse_input_file(tmp.name)
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


@pytest.mark.parametrize("formula", [
    "e1 | e2 ^ e3", "e1 | e2 & e3", "e1 | @(2, [e2, e3, e4])", "e1 ^ e2 ^ e3",
    "e1 ^ e2 & e3", "~~e1", "~e1~a", "e1 => e2 => e3", "e1 => e2 || e3",
    "e1 <=> e2 <=> e3", "e1 <=> e2 || e3"
])
def test_nested_formula(formula):
    """Nested logical operator tests."""
    tmp = NamedTemporaryFile(mode="w+")
    tmp.write("FT\n")
    tmp.write("g1 := %s\n" % formula)
    tmp.flush()
    with pytest.raises(ParsingError):
        parse_input_file(tmp.name)


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
