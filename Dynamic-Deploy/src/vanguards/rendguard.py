from . import control

from .logger import plog

############## Rendguard options #####################

# Minimum number of hops we have to see before applying use stat checks
REND_USE_GLOBAL_START_COUNT = 1000

# Number of hops to scale counts down by two at
REND_USE_SCALE_AT_COUNT = 20000

# Minimum number of times a relay has to be used before we check it for
# overuse
REND_USE_RELAY_START_COUNT = 100

# How many times more than its bandwidth must a relay be used?
REND_USE_MAX_USE_TO_BW_RATIO = 5.0

# What is percent of the network weight is not in the consensus right now?
# Put another way, the max number of rend requests not in the consensus is
# REND_USE_MAX_USE_TO_BW_RATIO times this churn rate.
REND_USE_MAX_CONSENSUS_WEIGHT_CHURN = 1.0

# Should we close circuits on rend point overuse?
REND_USE_CLOSE_CIRCUITS_ON_OVERUSE = True

_NOT_IN_CONSENSUS_ID = "NOT_IN_CONSENSUS"

class RendUseCount:
  def __init__(self, idhex, weight):
    self.idhex = idhex
    self.used = 0
    self.weight = weight

class RendGuard:
  def __init__(self):
    self.use_counts = {}
    self.total_use_counts = 0.0
    self.pickle_revision = 1.0

  def valid_rend_use(self, r):
    r_name = r
    if r not in self.use_counts:
      plog("INFO", "Relay "+r+" is not in our consensus.")
      r_name = r+" (not in-consensus)"
      r = _NOT_IN_CONSENSUS_ID
      if r not in self.use_counts:
        self.use_counts[r] = RendUseCount(r, 0)

    self.use_counts[r].used += 1.0
    self.total_use_counts += 1.0
    plog("DEBUG", "Relay "+r_name+" used %d times out of %d, "+\
                   "for a use rate of %f%%. It has a consensus "
                   "weight of %f%%", int(self.use_counts[r].used),
                   int(self.total_use_counts),
                   (100.0*self.use_counts[r].used)/self.total_use_counts,
                   100.0*self.use_counts[r].weight)

    # TODO: Can we base this check on statistical confidence intervals?
    if self.total_use_counts >= REND_USE_GLOBAL_START_COUNT and \
       self.use_counts[r].used >= REND_USE_RELAY_START_COUNT and \
       self.use_counts[r].used/self.total_use_counts > \
         self.use_counts[r].weight*REND_USE_MAX_USE_TO_BW_RATIO:

        # Let's warn if they disable ciruit closing.
        if REND_USE_CLOSE_CIRCUITS_ON_OVERUSE:
          loglevel = "NOTICE"
        else:
          loglevel = "WARN"
        plog(loglevel, "Relay "+r_name+" used %d times out of %d, "+\
                     "for a use rate of %f%%. This is above its consensus "
                     "weight of %f%%", int(self.use_counts[r].used),
                     int(self.total_use_counts),
                     (100.0*self.use_counts[r].used)/self.total_use_counts,
                     100.0*self.use_counts[r].weight)
        return 0
    return 1

  def xfer_use_counts(self, node_gen):
    old_counts = self.use_counts
    self.use_counts = {}
    for r in node_gen.sorted_r:
       self.use_counts[r.fingerprint] = RendUseCount(r.fingerprint, 0)

    if _NOT_IN_CONSENSUS_ID not in old_counts:
      old_counts[_NOT_IN_CONSENSUS_ID] = \
        RendUseCount(_NOT_IN_CONSENSUS_ID,
                     REND_USE_MAX_CONSENSUS_WEIGHT_CHURN/100.0)

    self.use_counts[_NOT_IN_CONSENSUS_ID] = \
      RendUseCount(_NOT_IN_CONSENSUS_ID,
                   REND_USE_MAX_CONSENSUS_WEIGHT_CHURN/100.0)

    i = 0
    rlen = len(node_gen.rstr_routers)
    while i < rlen:
      r = node_gen.rstr_routers[i]

      if "Exit" in r.flags:
        self.use_counts[r.fingerprint].weight = \
           node_gen.node_weights[i]/node_gen.exit_total
      else:
        self.use_counts[r.fingerprint].weight = \
           node_gen.node_weights[i]/node_gen.weight_total
      i+=1

    if self.total_use_counts >= REND_USE_SCALE_AT_COUNT:
      plog("INFO", "Total use counts %d reached the scale count %d. Scaling.",
           self.total_use_counts, REND_USE_SCALE_AT_COUNT)

    # Periodically we divide counts by two, to avoid overcounting
    # high-uptime relays vs old ones
    for r in old_counts:
      if r != _NOT_IN_CONSENSUS_ID and r not in self.use_counts:
        continue
      if self.total_use_counts >= REND_USE_SCALE_AT_COUNT:
        self.use_counts[r].used = old_counts[r].used/2.0
      else:
        self.use_counts[r].used = old_counts[r].used


    self.total_use_counts = sum(map(lambda x: self.use_counts[x].used,
                                    self.use_counts))
    self.total_use_counts = float(self.total_use_counts)

  def circ_event(self, controller, event):
    if event.status == "BUILT" and \
       event.purpose == "HS_SERVICE_REND" and \
       event.hs_state == "HSSR_CONNECTING":
      if not self.valid_rend_use(event.path[-1][0]):
        if REND_USE_CLOSE_CIRCUITS_ON_OVERUSE:
           control.try_close_circuit(controller, event.id)

    plog("DEBUG", event.raw_content())
