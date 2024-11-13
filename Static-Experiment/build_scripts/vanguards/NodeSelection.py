#!/usr/bin/env python

import copy
import random

from .logger import plog

class RestrictionError(Exception):
  "Error raised for issues with applying restrictions"
  pass

class NoNodesRemain(RestrictionError):
  "Error raised for issues with applying restrictions"
  pass

class NodeRestriction:
  "Interface for node restriction policies"
  def r_is_ok(self, r):
    "Returns true if Router 'r' is acceptable for this restriction"
    return True

class FlagsRestriction(NodeRestriction):
  "Restriction for mandatory and forbidden router flags"
  def __init__(self, mandatory, forbidden=[]):
    """Constructor. 'mandatory' and 'forbidden' are both lists of router
     flags as strings."""
    self.mandatory = mandatory
    self.forbidden = forbidden

  def r_is_ok(self, router):
    for m in self.mandatory:
      if not m in router.flags: return False
    for f in self.forbidden:
      if f in router.flags: return False
    return True

class MetaNodeRestriction(NodeRestriction):
  """Interface for a NodeRestriction that is an expression consisting of
     multiple other NodeRestrictions"""
  def next_rstr(self): raise NotImplemented()

class NodeRestrictionList(MetaNodeRestriction):
  "Class to manage a list of NodeRestrictions"
  def __init__(self, restrictions):
    "Constructor. 'restrictions' is a list of NodeRestriction instances"
    self.restrictions = restrictions

  def r_is_ok(self, r):
    "Returns true of Router 'r' passes all of the contained restrictions"
    for rs in self.restrictions:
      if not rs.r_is_ok(r): return False
    return True

class NodeGenerator:
  "Interface for node generation"
  def __init__(self, sorted_r, rstr_list):
    """Constructor. Takes a bandwidth-sorted list of Routers 'sorted_r'
    and a NodeRestrictionList 'rstr_list'"""
    self.rstr_list = rstr_list
    self.rebuild(sorted_r)
    self.rewind()

  def rewind(self):
    "Rewind the generator to the 'beginning'"
    self.routers = copy.copy(self.rstr_routers)
    if not self.routers:
      plog("NOTICE", "No routers left after restrictions applied: "+str(self.rstr_list))
      raise NoNodesRemain(str(self.rstr_list))

  def rebuild(self, sorted_r=None):
    """ Extra step to be performed when new routers are added or when
    the restrictions change. """
    if sorted_r != None:
      self.sorted_r = sorted_r
    self.rstr_routers = list(filter(lambda r: self.rstr_list.r_is_ok(r),
                                    self.sorted_r))

    if not self.rstr_routers:
      plog("NOTICE", "No routers left after restrictions applied: "+str(self.rstr_list))
      raise NoNodesRemain(str(self.rstr_list))

  def generate(self):
    "Return a python generator that yields routers according to the policy"
    raise NotImplemented()

class BwWeightedGenerator(NodeGenerator):
  POSITION_GUARD = 'g'
  POSITION_MIDDLE = 'm'
  POSITION_EXIT = 'e'

  def flag_to_weight(self, node):
    if 'Guard' in node.flags and "Exit" in node.flags:
      return self.bw_weights[u'W'+self.position+'d']/self.WEIGHT_SCALE

    if 'Exit' in node.flags:
      return self.bw_weights[u'W'+self.position+'e']/self.WEIGHT_SCALE

    if "Guard" in node.flags:
      return self.bw_weights[u'W'+self.position+'g']/self.WEIGHT_SCALE

    return self.bw_weights[u'Wmm']/self.WEIGHT_SCALE


  # This function handles https://github.com/mikeperry-tor/vanguards/issues/24
  #
  # Exit nodes got their weights set to 0 by the BwWeightedGenerator,
  # because we told it we were selecting for middle. Since they can
  # still be used as RPs in normal client cannibalized circuits,
  # we need to set their upper bound to be their exit selection
  # probability.
  #
  # Note that we deliberately *don't* re-normalize weight_total
  # since we don't want to lower the upper bound of the rest
  # of the nodes due to this madness. But we do want a separate
  # exit_total for use with these Exit nodes (since it gives their
  # selection probability for cannibalized circs).
  def repair_exits(self):
    oldpos = self.position
    self.position = BwWeightedGenerator.POSITION_EXIT
    self.exit_total = 0

    i = 0
    rlen = len(self.rstr_routers)
    while i < rlen:
      r = self.rstr_routers[i]
      if "Exit" in r.flags:
        self.node_weights[i] = r.measured*self.flag_to_weight(r)
        self.exit_total += self.node_weights[i]

      i+=1

    self.position = oldpos

  def rebuild(self, sorted_r=None):
    NodeGenerator.rebuild(self, sorted_r)
    NodeGenerator.rewind(self)
    # TODO: Use consensus param
    self.WEIGHT_SCALE = 10000.0

    self.node_weights = []
    for r in self.rstr_routers:
      self.node_weights.append(r.measured*self.flag_to_weight(r))

    self.weight_total = sum(self.node_weights)

  def __init__(self, sorted_r, rstr_list, bw_weights, position):
    self.position = position
    self.bw_weights = bw_weights
    self.node_weights = []
    NodeGenerator.__init__(self, sorted_r, rstr_list)

  def generate(self):
    while True:
      choice_val = random.uniform(0, self.weight_total)
      choose_total = 0
      choice_idx = 0
      while choose_total < choice_val:
        choose_total += self.node_weights[choice_idx]
        choice_idx += 1
      yield self.rstr_routers[choice_idx-1]

# FIXME: FlagsRestriction: Uptime, capacity (NodeRestriction: always want)
# FIXME: Subnet16Restriction: Set restriction: at least one be different
# FIXME: FamilyRestriction: Set restriction: at least one must be different


