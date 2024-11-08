""" Log monitoring for attacks, protocol issues, and debugging """
import stem
import time
import functools

from . import control

from .logger import plog
from .logger import loglevels

# XXX: Off by default for now
LOG_PROTOCOL_WARNS = True

LOG_DUMP_LIMIT = 25

LOG_DUMP_LEVEL = "NOTICE"

class LogGuard:
  def __init__(self, controller):
    self.controller = controller
    self.log_buffer = list()
    self.log_level = LOG_DUMP_LEVEL.lower()
    self.log_limit = LOG_DUMP_LIMIT

    # Upgrade to ProtocolWarns if set. Otherwise, leave whatever torrc set
    if LOG_PROTOCOL_WARNS:
      controller.set_conf("ProtocolWarnings", "1")

    self._init_logbuffer(controller)

  # Register log events depending on log dump level
  def _init_logbuffer(self, controller):
    dump_level = loglevels[LOG_DUMP_LEVEL]

    if dump_level <= loglevels["DEBUG"]:
      controller.add_event_listener(
                   functools.partial(LogGuard.log_all_event, self),
                                     stem.control.EventType.DEBUG)

    if dump_level <= loglevels["INFO"]:
      controller.add_event_listener(
                   functools.partial(LogGuard.log_all_event, self),
                                     stem.control.EventType.INFO)


    if dump_level <= loglevels["NOTICE"]:
      controller.add_event_listener(
                   functools.partial(LogGuard.log_all_event, self),
                                     stem.control.EventType.NOTICE)


    if dump_level <= loglevels["WARN"]:
      controller.add_event_listener(
                   functools.partial(LogGuard.log_all_event, self),
                                     stem.control.EventType.WARN)


    if dump_level <= loglevels["ERROR"]:
      controller.add_event_listener(
                   functools.partial(LogGuard.log_all_event, self),
                                     stem.control.EventType.ERR)


  def log_warn_event(self, event):
    plog("NOTICE", "Tor log warn: "+event.message)

  def log_all_event(self, event):
    self.log_buffer.append(event)

    # XXX: This might not be efficient, idk
    # XXX: This might also be a memleak/memfrag, depending on how list()
    # decides to handle this underneath :/
    while len(self.log_buffer) > self.log_limit:
      self.log_buffer.pop(0)

  # This is called before and after circuit close. The "when" argument is
  # "Pre" before we close a circuit in controller.try_close_circuit(), and "Post" after.
  def dump_log_queue(self, circ_id, when):
    while len(self.log_buffer):
      event = self.log_buffer.pop(0)
      plog("NOTICE", when+"-close CIRC ID="+circ_id+" Tor log: TOR_"+event.runlevel+"["+time.ctime(event.arrived_at)+"]: "+event.message)

  # This lets us emit post-close logs that may be relevant (more ProtocolWarns, etc)
  def circ_event(self, event):
    if (event.status == "CLOSED" or event.status == "FAILED") \
       and event.reason == "REQUESTED":
      self.dump_log_queue(event.id, "Post")

