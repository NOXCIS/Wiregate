""" Simple checks against bandwidth side channels """
import stem

from . import control

from .logger import plog

_ROUTELEN_FOR_PURPOSE = {
                         "HS_VANGUARDS"     : 4,
                         "HS_CLIENT_HSDIR"  : 5,
                         "HS_CLIENT_INTRO"  : 5,
                         "HS_CLIENT_REND"   : 4,
                         "HS_SERVICE_HSDIR" : 4,
                         "HS_SERVICE_INTRO" : 4,
                         "HS_SERVICE_REND"  : 5
                        }

# XXX: Hrmm
_ROUTELEN_FOR_PURPOSE_LITE = {
                         "HS_VANGUARDS"     : 3,
                         "HS_CLIENT_HSDIR"  : 4,
                         "HS_CLIENT_INTRO"  : 4,
                         "HS_CLIENT_REND"   : 3,
                         "HS_SERVICE_HSDIR" : 4,
                         "HS_SERVICE_INTRO" : 4,
                         "HS_SERVICE_REND"  : 4
                        }

class Layer1Stats:
  def __init__(self):
    self.use_count = 0
    self.conn_count = 1

class Layer1Guards:
  def __init__(self, num_layer1):
    self.guards = {}
    self.num_layer1 = num_layer1

  def add_conn(self, guard_fp):
    if guard_fp in self.guards:
      self.guards[guard_fp].conn_count += 1
    else:
      self.guards[guard_fp] = Layer1Stats()

  def del_conn(self, guard_fp):
    if guard_fp in self.guards:
      if self.guards[guard_fp].conn_count > 1:
        self.guards[guard_fp].conn_count -= 1
      else:
        del self.guards[guard_fp]

  # Returns -1 when fewer than expected, 0 when correct, +1 when too many
  # (Retval used only by tests)
  def check_conn_counts(self):
    ret = 0

    if len(self.guards) < self.num_layer1:
      plog("NOTICE", "Fewer guard connections than configured. Connected to: "+ \
           str(self.guards.keys()))
      ret = -1
    elif len(self.guards) > self.num_layer1:
      plog("NOTICE", "More guard connections than configured. Connected to: "+ \
           str(self.guards.keys()))
      ret = 1

    for g in self.guards.keys():
      if self.guards[g].conn_count > 1:
       plog("NOTICE", "Extra connections to guard "+g+": "+\
            str(self.guards[g].conn_count))
       ret = 1
    return ret

  def add_use_count(self, guard_fp):
    if not guard_fp in self.guards:
      plog("WARN", "Guard "+guard_fp+" not in "+ \
           str(self.guards.keys()))
    else:
      self.guards[guard_fp].use_count += 1

  # Returns -1 when fewer than expected, 0 when correct, +1 when too many
  # (Retval used only by tests)
  def check_use_counts(self):
    ret = 0
    layer1_in_use = list(filter(lambda x: self.guards[x].use_count,
                                self.guards.keys()))
    layer1_counts = list(map(lambda x:
                          x+": "+str(self.guards[x].use_count),
                        layer1_in_use))

    if len(layer1_in_use) > self.num_layer1:
      plog("WARN", "Circuits are being used on more guards " + \
             "than configured. Current guard use: "+str(layer1_counts))
      ret = 1
    elif len(layer1_in_use) < self.num_layer1:
      plog("NOTICE", "Circuits are being used on fewer guards " + \
             "than configured. Current guard use: "+str(layer1_counts))
      ret = -1
    return ret

class PathVerify:
  def __init__(self, controller, full_vanguards, num_layer1, num_layer2, num_layer3):
    self.controller = controller
    self.full_vanguards = full_vanguards
    self.layer2 = set()
    self.layer3 = set()
    self.num_layer1 = num_layer1
    self.num_layer2 = num_layer2
    self.num_layer3 = num_layer3
    self._layers_init(controller)
    self.layer1 = Layer1Guards(self.num_layer1)
    self._orconn_init(controller)

  def _orconn_init(self, controller):
    for l in controller.get_info("orconn-status").split("\n"):
      if len(l):
        guard_fp = l.split("~")[0][1:]
        self.layer1.add_conn(guard_fp)

    self.layer1.check_conn_counts()

  def _layers_init(self, controller):
    layer2 = controller.get_conf("HSLayer2Nodes", None)
    layer3 = controller.get_conf("HSLayer3Nodes", None)

    # These may be empty at startup
    if layer2:
      self.layer2 = set(layer2.split(","))
      self.full_vanguards = True

    if layer3:
      self.layer3 = set(layer3.split(","))
      self.full_vanguards = True

    # If they are empty, and vanguards is disabled by the addon,
    # then we're just verifying vg-lite in C-Tor.
    if not layer2 and not layer3 and not self.full_vanguards:
      plog("NOTICE", "Monitoring vanguards-lite with pathverify.")
      # Update our num layer params because they now depend on vg-lite
      self.num_layer1 = 1
      self.num_layer2 = 4
      self.num_layer3 = 0
    else:
      plog("NOTICE", "Monitoring vanguards with pathverify.")

    self._check_layer_counts()

  def conf_changed_event(self, event):
    if "HSLayer2Nodes" in event.changed:
      self.layer2 = set(event.changed["HSLayer2Nodes"][0].split(","))
      self.full_vanguards = True

    if "HSLayer3Nodes" in event.changed:
      self.layer3 = set(event.changed["HSLayer3Nodes"][0].split(","))
      self.full_vanguards = True

    self._check_layer_counts()

    plog("DEBUG", event.raw_content())

  # Returns True when right number, False otherwise
  def _check_layer_counts(self):
    ret = False
    # These can become empty briefly on sighup and startup. Aka set([''])
    if len(self.layer2) > 1:
      if len(self.layer2) != self.num_layer2:
        plog("NOTICE", "Wrong number of layer2 guards. " + \
            str(self.num_layer2)+" vs: "+str(self.layer2))
        ret = False
      else:
        ret = True

    if len(self.layer3) > 1:
      if len(self.layer3) != self.num_layer3:
        plog("NOTICE", "Wrong number of layer3 guards. " + \
             str(self.num_layer3)+" vs: "+str(self.layer3))
        ret = False
      else:
        ret = True
    return ret

  def orconn_event(self, event):
    if event.status == "CONNECTED":
      self.layer1.add_conn(event.endpoint_fingerprint)
    elif event.status == "CLOSED" or event.status == "FAILED":
      self.layer1.del_conn(event.endpoint_fingerprint)

    self.layer1.check_conn_counts()

  def guard_event(self, event):
    if event.status == "GOOD_L2":
      self.layer2.add(event.endpoint_fingerprint)
    elif event.status == "BAD_L2":
      self.layer2.discard(event.endpoint_fingerprint)

    plog("DEBUG", event.raw_content())

  def routelen_for_purpose(self, purpose):
    if self.full_vanguards:
      return _ROUTELEN_FOR_PURPOSE[purpose]
    else:
      return _ROUTELEN_FOR_PURPOSE_LITE[purpose]

  def circ_event(self, event):
    if event.purpose[0:3] == "HS_" and (event.status == stem.CircStatus.BUILT or \
       event.status == "GUARD_WAIT"):
      if len(event.path) != self.routelen_for_purpose(event.purpose):
        if (event.purpose == "HS_SERVICE_HSDIR" and \
            event.hs_state == "HSSI_CONNECTING") or \
           (event.purpose == "HS_CLIENT_INTRO" and \
            event.hs_state == "HSCI_CONNECTING"):
          # This can happen when HS_VANGUARDS are cannibalized..
          # XXX: Is that a bug?
          # It can also happen if client intros fail and are retried with a
          # new hop. That case is not a bug.
          plog("INFO", "Tor made a "+str(len(event.path))+ "-hop path, but I wanted a " + \
               str(self.routelen_for_purpose(event.purpose))+ "-hop path for purpose " + \
               event.purpose +":"+str(event.hs_state)+" + " + \
               event.raw_content())
        else:
          plog("NOTICE", "Tor made a "+str(len(event.path))+ "-hop path, but I wanted a " + \
               str(self.routelen_for_purpose(event.purpose))+ "-hop path for purpose " + \
               event.purpose +":"+str(event.hs_state)+" + " + \
               event.raw_content())

      self.layer1.add_use_count(event.path[0][0])
      self.layer1.check_use_counts()

      if not event.path[1][0] in self.layer2:
         plog("WARN", "Layer2 "+event.path[1][0]+" not in "+ \
             str(self.layer2))

      if self.num_layer3 and not event.path[2][0] in self.layer3:
         plog("WARN", "Layer3 "+event.path[1][0]+" not in "+ \
             str(self.layer3))

      if len(self.layer2) != self.num_layer2:
        plog("WARN", "Circuit built with different number of layer2 nodes " + \
             "than configured. Currently using: " + str(self.layer2))

      if len(self.layer3) != self.num_layer3:
        plog("WARN", "Circuit built with different number of layer3 nodes " + \
             "than configured. Currently using: " + str(self.layer3))

  def circ_minor_event(self, event):
    if event.purpose[0:3] == "HS_" and event.old_purpose[0:3] != "HS_":
      plog("WARN", "Purpose switched from non-hs to hs: "+ \
           str(event.raw_content()))
    elif event.purpose[0:3] != "HS_" and event.old_purpose[0:3] == "HS_":
      if event.purpose != "CIRCUIT_PADDING" and \
         event.purpose != "MEASURE_TIMEOUT" and \
         event.purpose != "PATH_BIAS_TESTING":
        plog("WARN", "Purpose switched from hs to non-hs: "+ \
             str(event.raw_content()))

    if event.purpose[0:3] == "HS_" or event.old_purpose[0:3] == "HS_":
      if not event.path[0][0] in self.layer1.guards:
        plog("WARN", "Guard "+event.path[0][0]+" not in "+ \
             str(self.layer1.guards.keys()))
      if len(event.path) > 1 and not event.path[1][0] in self.layer2:
         plog("WARN", "Layer2 "+event.path[1][0]+" not in "+ \
             str(self.layer2))
      if self.num_layer3 and len(event.path) > 2 and not event.path[2][0] in self.layer3:
         plog("WARN", "Layer3 "+event.path[1][0]+" not in "+ \
             str(self.layer3))

