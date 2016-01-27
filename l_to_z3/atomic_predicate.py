"""
L's atomic predicate: constrains graph-action pairs.

This thing should be an interface implemented by a bunch of different
subclasses; combine those subclasses together to make a predicate, and then
allow the predicate to be executed / checked / model-got / whatever we want by
Z3. This is one abstraction layer higher than the above Z3 definitions are.
Probably the subclasses should only return Z3 formulae, not make any assertions;
then, Predicate can manipulate those formulae into an assertion.

Refer to pg. TODO of the L description.
"""

# pylint: disable=C0103

from z3 import Solver, Datatype, IntSort, Function

from model import Identifier, Pregraph, AtomicAction, Postgraph, Model

DEBUG = False

Variable = Datatype('Variable')
Variable.declare('variable', ('get_varname', IntSort()))
Variable = Variable.create()

# TODO?: Create a better datatype for Variable -- a class
# that both contains this z3 datatype, and that automatically
# does all of the variable naming/numbering things for me.

def z3_accessor(func, item):
    """Apply func and read out the accessed value of a z3 datatype, if the
    value for that accessor was an IntSort().

    Arguments:
        func :: a z3 accessor function
        item :: a z3 datatype instance
    Returns:
        :: long - the accessed value
    """
    return func(item).children()[0].children()[0].as_long()

def ensure_variable(thing):
    """Raise ValueError if thing is not an instance of z3 Variable."""
    try:
        assert thing.sort() == Variable
    except (AttributeError, AssertionError):
        raise ValueError("Arguments must be z3 instances of Variable.")

def ensure_atomic_predicate(thing):
    """Raise ValueError if thing is not an instance of AtomicPredicate."""
    if not isinstance(thing, AtomicPredicate):
        raise ValueError("Arguments must be instances of AtomicPredicate.")

class AtomicPredicate(object):
    """Parent class which all AtomicPredicates will subclass.

    Contains implementations of some z3-related functionality. Subclasses will
    override get_predicate.
    """
    def __init__(self, graphactionpair):
        self.solver = Solver()
        self.graphactionpair = graphactionpair
        self.interpretation = Function('interpretation', Variable, Identifier)
        self._asserted_yet = False
        self._status = None
        self.graphactionpair.initialize(self.solver)

    def get_predicate(self):
        raise NotImplementedError("Implement get_predicate in subclasses.")

    def _assert_over(self):
        self.solver.add(self.get_predicate())
        self._status = self.solver.check()

        self._asserted_yet = True

    def check_sat(self):
        if not self._asserted_yet:
            self._assert_over()
        if DEBUG:
            print self._status
        return self._status

    def get_model(self):
        """Raises Z3Exception if the model is not available."""
        if not self._asserted_yet:
            self._assert_over()
        output = self.solver.model()
        if DEBUG:
            print output
        return output

class Top(AtomicPredicate):
    def get_predicate(self):
        return True

class Bottom(AtomicPredicate):
    def get_predicate(self):
        return False

class Equal(AtomicPredicate):
    """
    ; Equality of variables x and y.
    (declare-const x Variable)
    (declare-const y Variable)
    (assert (= (get-varname x) (get-varname y)))
    """
    def __init__(self, x, y, *args):
        super(Equal, self).__init__(*args)
        ensure_variable(x)
        ensure_variable(y)
        self.x = x
        self.y = y

    def get_predicate(self):
        return (z3_accessor(Variable.get_varname, self.x) ==
                z3_accessor(Variable.get_varname, self.y))

class Labeled(AtomicPredicate):
    """
    ; Variable has specific label.
    (declare-const x Variable)
    (declare-const Label Int)
    (assert (= (get-label (interpretation x)) Label))
    """
    def __init__(self, x, label, *args):
        super(Labeled, self).__init__(*args)
        ensure_variable(x)
        self.label = label
        self.x = x


    def get_predicate(self):
        return (z3_accessor(Identifier.label, self.interpretation(self.x)) ==
                self.label)


class PreParent(AtomicPredicate):
    """
    ; Variable x has child y.
    (declare-const x Variable)
    (declare-const y Variable)
    (assert (graph-parents (interpretation x) (interpretation y)))
    """
    def __init__(self, x, y, *args):
        super(PreParent, self).__init__(*args)
        ensure_variable(x)
        ensure_variable(y)
        self.x = x
        self.y = y

    def get_predicate(self):
        return self.model.pregraph.parents(
            self.interpretation(self.x), self.interpretation(self.y))

class PostParent(AtomicPredicate):
    """
    ; "Bar" of "Variable x has child y", which seems to indicate that x has
    ; child y only in the second graph produced by G combined with A.
    ; This is the postcondition!
    (declare-const x Variable)
    (declare-const y Variable)
    (assert (graph-2-parents (interpretation x) (interpretation y)))
    """
    def __init__(self, x, y, *args):
        super(PostParent, self).__init__(*args)
        ensure_variable(x)
        ensure_variable(y)
        self.x = x
        self.y = y

    def get_predicate(self):
        return self.model.postgraph.parents(
            self.interpretation(self.x), self.interpretation(self.y))

class DoParent(AtomicPredicate):
    """
    ; "Do" of "Variable x has child y".
    (declare-const x Variable)
    (declare-const y Variable)
    (assert (actions-has (parent-action (interpretation x) (interpretation y))))
    """
    def __init__(self, x, y, *args):
        super(DoParent, self).__init__(*args)
        ensure_variable(x)
        ensure_variable(y)
        self.x = x
        self.y = y

    def get_predicate(self):
        return self.model.action.has(
            AtomicAction.parent_action(
                self.interpretation(self.x), self.interpretation(self.y)))

class PreLink(AtomicPredicate):
    """
    ; Variable x links to variable y.
    (declare-const x Variable)
    (declare-const y Variable)
    (assert (graph-links (interpretation x) (interpretation y)))
    """
    def __init__(self, x, y, *args):
        super(PreLink, self).__init__(*args)
        ensure_variable(x)
        ensure_variable(y)
        self.x = x
        self.y = y

    def get_predicate(self):
        return self.model.pregraph.links(
            self.interpretation(self.x), self.interpretation(self.y))

class PostLink(AtomicPredicate):
    """
    ; "Bar" of Variable x links to variable y; Again a postcondition.
    (declare-const x Variable)
    (declare-const y Variable)
    (assert (graph-2-links (interpretation x) (interpretation y)))
    """
    def __init__(self, x, y, *args):
        super(PostLink, self).__init__(*args)
        ensure_variable(x)
        ensure_variable(y)
        self.x = x
        self.y = y

    def get_predicate(self):
        return self.model.postgraph.links(
            self.interpretation(self.x), self.interpretation(self.y))

class DoLink(AtomicPredicate):
    """
    ; "Do" of "Variable x links to variable y".
    (declare-const x Variable)
    (declare-const y Variable)
    (assert (actions-has (link-action (interpretation x) (interpretation y))))
    """
    def __init__(self, x, y, *args):
        super(DoLink, self).__init__(*args)
        ensure_variable(x)
        ensure_variable(y)
        self.x = x
        self.y = y

    def get_predicate(self):
        return self.model.action.has(
            AtomicAction.link_action(
                self.interpretation(self.x), self.interpretation(self.y)))

class DoUnlink(AtomicPredicate):
    """
    ; "Do" of "Variable x unlinks to variable y".
    (declare-const x Variable)
    (declare-const y Variable)
    (assert (actions-has (unlink-action (interpretation x) (interpretation y))))
    """
    def __init__(self, x, y, *args):
        super(DoUnlink, self).__init__(*args)
        ensure_variable(x)
        ensure_variable(y)
        self.x = x
        self.y = y

    def get_predicate(self):
        return self.model.action.has(
            AtomicAction.unlink_action(
                self.interpretation(self.x), self.interpretation(self.y)))

class PreHas(AtomicPredicate):
    """
    ; "Has" of variable x.
    (declare-const x Variable)
    (assert (graph-has (interpretation x)))
    """
    def __init__(self, x, *args):
        super(PreHas, self).__init__(*args)
        ensure_variable(x)
        self.x = x

    def get_predicate(self):
        return self.model.pregraph.has(
            self.interpretation(self.x))

class PostHas(AtomicPredicate):
    """
    ; "Bar" of "Has" of x. Again, a postcondition.
    (declare-const x Variable)
    (assert (graph-2-has (interpretation x)))
    """
    def __init__(self, x, *args):
        super(PostHas, self).__init__(*args)
        ensure_variable(x)
        self.x = x

    def get_predicate(self):
        return self.model.postgraph.has(
            self.interpretation(self.x))


class Add(AtomicPredicate):
    pass # TODO

class Rem(AtomicPredicate):
    pass # TODO
