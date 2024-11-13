""" This code monitors the circuit build timeout. It is non-essential """
from .logger import plog

class CircuitStat:
  def __init__(self, circ_id, is_hs):
    self.circ_id = circ_id
    self.is_hs = is_hs

class TimeoutStats:
  def __init__(self):
    self.circuits = {}
    self.zero_fields()
    self.record_timeouts = True

  def zero_fields(self):
    self.all_launched = 0
    self.all_built = 0
    self.all_timeout = 0
    self.hs_launched = 0
    self.hs_built = 0
    self.hs_timeout = 0

  def circ_event(self, event):
    is_hs = event.hs_state or event.purpose[0:2] == "HS"

    if is_hs and event.id in self.circuits and \
      self.circuits[event.id].is_hs != is_hs:
      plog("ERROR", "Circuit "+event.id+" just changed from non-HS to HS: "\
                   +event.raw_content())

    # Do not record circuits built while we have no timeout
    # (ie: after reset but before computed)
    if not self.record_timeouts:
      return

    # Stages of circuits:
    # LAUNCHED -> BUILT
    #             BUILT -> EXTENDED -> FINISHED
    #             BUILT -> EXTENDED -> FAILED
    #             BUILT -> EXTENDED -> TIMEOUT
    # LAUNCHED -> TIMEOUT
    #             TIMEOUT -> MEASURED
    #                        MEASURED -> FINSHED
    #                        MEASURED -> EXPIRED
    # LAUNCHED -> FAILED
    # LAUNCHED -> CLOSED
    #             FAILED -> CLOSED
    #             TIMEOUT -> CLOSED
    if event.status == "LAUNCHED":
      self.add_circuit(event.id, is_hs)
    elif event.status == "BUILT":
      self.built_circuit(event.id)
    elif event.reason == "TIMEOUT":
      self.timeout_circuit(event.id)
    elif event.purpose != "MEASURE_TIMEOUT" and \
         (event.status == "CLOSED" or event.status == "FAILED"):
      self.closed_circuit(event.id)

  def cbt_event(self, event):
    # TODO: Check if this is too high...
    plog("INFO", "CBT Timeout rate: "+str(event.timeout_rate)+"; Our measured timeout rate: "+str(self.timeout_rate_all())+"; Hidden service timeout rate: "+str(self.timeout_rate_hs()))
    plog("INFO", event.raw_content())
    if event.set_type == "COMPUTED":
      plog("INFO", "CBT Timeout computed: "+event.raw_content())
      self.record_timeouts = True
    if event.set_type == "RESET":
      plog("INFO", "CBT Timeout reset")
      self.record_timeouts = False
      self.zero_fields()


  def add_circuit(self, circ_id, is_hs):
    if circ_id in self.circuits:
      plog("ERROR", "Circuit "+circ_id+" already exists in map!")
    self.circuits[circ_id] = CircuitStat(circ_id, is_hs)
    self.all_launched += 1
    if is_hs: self.hs_launched += 1

  def built_circuit(self, circ_id):
    if circ_id in self.circuits:
      self.all_built += 1
      if self.circuits[circ_id].is_hs:
        self.hs_built += 1
      del self.circuits[circ_id]

  def closed_circuit(self, circ_id):
    # If we are closed but still in circuits, then we closed
    # before being built or timing out. Don't count as a launched circ
    if circ_id in self.circuits:
      self.all_launched -= 1
      if self.circuits[circ_id].is_hs:
        self.hs_launched -= 1
      del self.circuits[circ_id]

  def timeout_circuit(self, circ_id):
    if circ_id in self.circuits:
      self.all_timeout += 1
      if self.circuits[circ_id].is_hs:
        self.hs_timeout += 1
      del self.circuits[circ_id]

  def timeout_rate_all(self):
    if self.all_launched:
      return float(self.all_timeout)/(self.all_launched)
    else: return 0.0

  def timeout_rate_hs(self):
    if self.hs_launched:
      return float(self.hs_timeout)/(self.hs_launched)
    else: return 0.0



