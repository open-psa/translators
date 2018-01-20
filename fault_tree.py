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
"""Fault tree classes and common facilities."""

from collections import deque


class Event(object):
    """Representation of a base class for an event in a fault tree.

    Attributes:
        name: A specific name that identifies this node.
        parents: A set of parents of this node.
    """

    def __init__(self, name):
        """Constructs a new node with a unique name.

        Note that the tracking of parents introduces a cyclic reference.

        Args:
            name: Identifier for the node.
        """
        self.name = name
        self.parents = set()

    def is_common(self):
        """Indicates if this node appears in several places."""
        return len(self.parents) > 1

    def is_orphan(self):
        """Determines if the node has no parents."""
        return not self.parents

    def num_parents(self):
        """Returns the number of unique parents."""
        return len(self.parents)

    def add_parent(self, gate):
        """Adds a gate as a parent of the node.

        Args:
            gate: The gate where this node appears.
        """
        assert gate not in self.parents
        self.parents.add(gate)


class BasicEvent(Event):
    """Representation of a basic event in a fault tree.

    Attributes:
        prob: Probability of failure of this basic event.
    """

    def __init__(self, name, prob):
        """Initializes a basic event node.

        Args:
            name: Identifier of the node.
            prob: Probability of the basic event.
        """
        super(BasicEvent, self).__init__(name)
        self.prob = prob

    def to_xml(self):
        """Produces the Open-PSA MEF XML definition of the basic event."""
        return ("<define-basic-event name=\"" + self.name + "\">\n"
                "<float value=\"" + str(self.prob) + "\"/>\n"
                "</define-basic-event>\n")


class HouseEvent(Event):
    """Representation of a house event in a fault tree.

    Attributes:
        state: State of the house event ("true" or "false").
    """

    def __init__(self, name, state):
        """Initializes a house event node.

        Args:
            name: Identifier of the node.
            state: Boolean state string of the constant.
        """
        super(HouseEvent, self).__init__(name)
        self.state = state

    def to_xml(self):
        """Produces the Open-PSA MEF XML definition of the house event."""
        return ("<define-house-event name=\"" + self.name + "\">\n"
                "<constant value=\"" + self.state + "\"/>\n"
                "</define-house-event>\n")


class Gate(Event):  # pylint: disable=too-many-instance-attributes
    """Representation of a fault tree gate.

    Attributes:
        operator: Logical operator of this formula.
        min_num: Min number for the combination and cardinality operator.
        max_num: Max number for the cardinality operator.
        g_arguments: arguments that are gates.
        b_arguments: arguments that are basic events.
        h_arguments: arguments that are house events.
        u_arguments: arguments that are undefined.
        mark: Marking for various algorithms like toposort.
    """

    def __init__(self, name, operator, min_num=None, max_num=None):
        """Initializes a gate.

        Args:
            name: Identifier of the node.
            operator: Boolean operator of this formula.
            min_num: Min number for the combination and cardinality operators.
            max_num: Max number for the cardinality operator.
        """
        super(Gate, self).__init__(name)
        self.mark = None
        self.operator = operator
        self.min_num = min_num
        self.max_num = max_num
        self.g_arguments = set()
        self.b_arguments = set()
        self.h_arguments = set()
        self.u_arguments = set()
        self.complement_arguments = set()

    def num_arguments(self):
        """Returns the number of arguments."""
        return (len(self.b_arguments) + len(self.h_arguments) +
                len(self.g_arguments) + len(self.u_arguments))

    def add_argument(self, argument, complement=False):
        """Adds argument into a collection of gate arguments.

        Note that this function also updates the parent set of the argument.
        Duplicate arguments are ignored.
        The logic of the Boolean operator is not taken into account
        upon adding arguments to the gate.
        Therefore, no logic checking is performed
        for repeated or complement arguments.

        Args:
            argument: Gate, HouseEvent, BasicEvent, or Event argument.
            complement: Flag to treat the argument as a complement.
        """
        if complement:
            self.complement_arguments.add(argument)
        argument.parents.add(self)
        if isinstance(argument, Gate):
            self.g_arguments.add(argument)
        elif isinstance(argument, BasicEvent):
            self.b_arguments.add(argument)
        elif isinstance(argument, HouseEvent):
            self.h_arguments.add(argument)
        else:
            assert isinstance(argument, Event)
            self.u_arguments.add(argument)

    def to_xml(self, nest=0):
        """Produces the Open-PSA MEF XML definition of the gate.

        Args:
            nest: The level for nesting formulas of argument gates.
        """

        def args_to_xml(type_str, container, gate, converter=None):
            """Produces XML string representation of arguments."""
            mef_xml = ""
            for arg in container:
                complement = arg in gate.complement_arguments
                if complement:
                    mef_xml += "<not>\n"
                if converter:
                    mef_xml += converter(arg)
                else:
                    mef_xml += "<%s name=\"%s\"/>\n" % (type_str, arg.name)
                if complement:
                    mef_xml += "</not>\n"
            return mef_xml

        def convert_formula(gate, nest):
            """Converts the formula of a gate into XML representation."""
            mef_xml = ""
            if gate.operator != "null":
                mef_xml += "<" + gate.operator
                if gate.operator == "atleast":
                    mef_xml += ' min="%s"' % gate.min_num
                elif gate.operator == "cardinality":
                    mef_xml += ' min="%s" max="%s"' % (gate.min_num,
                                                       gate.max_num)
                mef_xml += ">\n"
            mef_xml += args_to_xml("house-event", gate.h_arguments, gate)
            mef_xml += args_to_xml("basic-event", gate.b_arguments, gate)
            mef_xml += args_to_xml("event", gate.u_arguments, gate)

            if nest > 0:
                mef_xml += args_to_xml("gate", gate.g_arguments, gate,
                                       lambda x: convert_formula(x, nest - 1))
            else:
                mef_xml += args_to_xml("gate", gate.g_arguments, gate)

            if gate.operator != "null":
                mef_xml += "</" + gate.operator + ">\n"
            return mef_xml

        mef_xml = "<define-gate name=\"" + self.name + "\">\n"
        mef_xml += convert_formula(self, nest)
        mef_xml += "</define-gate>\n"
        return mef_xml


class FaultTree(object):  # pylint: disable=too-many-instance-attributes
    """Representation of a fault tree for general purposes.

    Attributes:
        name: The name of a fault tree.
        top_gate: The root gate of the fault tree.
        top_gates: Container of top gates. Single one is the default.
        gates: A set of all gates that are created for the fault tree.
        basic_events: A list of all basic events created for the fault tree.
        house_events: A list of all house events created for the fault tree.
    """

    def __init__(self, name=None):
        """Initializes an empty fault tree.

        Args:
            name: The name of the system described by the fault tree container.
        """
        self.name = name
        self.top_gate = None
        self.top_gates = None
        self.gates = []
        self.basic_events = []
        self.house_events = []

    def to_xml(self, nest=0):
        """Produces the Open-PSA MEF XML definition of the fault tree.

        The fault tree is produced breadth-first.
        The output XML representation is not formatted for human readability.
        The fault tree must be valid and well-formed.

        Args:
            nest: A nesting factor for the Boolean formulae.

        Returns:
            XML snippet representing the fault tree container.
        """
        mef_xml = "<opsa-mef>\n"
        mef_xml += "<define-fault-tree name=\"%s\">\n" % self.name

        sorted_gates = toposort_gates(self.top_gates or [self.top_gate],
                                      self.gates)
        for gate in sorted_gates:
            mef_xml += gate.to_xml(nest)

        mef_xml += "</define-fault-tree>\n"

        mef_xml += "<model-data>\n"
        for basic_event in self.basic_events:
            mef_xml += basic_event.to_xml()

        for house_event in self.house_events:
            mef_xml += house_event.to_xml()
        mef_xml += "</model-data>\n"
        mef_xml += "</opsa-mef>\n"
        return mef_xml


def toposort_gates(root_gates, gates):
    """Sorts gates topologically starting from the root gate.

    The gate marks are used for the algorithm.
    After this sorting the marks are reset to None.

    Args:
        root_gates: The root gates of the graph.
        gates: Gates to be sorted.

    Returns:
        A deque of sorted gates.
    """
    for gate in gates:
        gate.mark = ""

    def visit(gate, final_list):
        """Recursively visits the given gate sub-tree to include into the list.

        Args:
            gate: The current gate.
            final_list: A deque of sorted gates.
        """
        assert gate.mark != "temp"
        if not gate.mark:
            gate.mark = "temp"
            for arg in gate.g_arguments:
                visit(arg, final_list)
            gate.mark = "perm"
            final_list.appendleft(gate)

    sorted_gates = deque()
    for root_gate in root_gates:
        visit(root_gate, sorted_gates)
    assert len(sorted_gates) == len(gates)
    for gate in gates:
        gate.mark = None
    return sorted_gates
