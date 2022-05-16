from . import bnode_misc
from . import wbuilder_util


# common for all renderer nodes (rnode)
class RN_CAkHircNode(object):
    def __init__(self):
        #no params since changing constructors is a pain, uses init_x below
        pass

    def init_renderer(self, renderer):
        self._renderer = renderer
        self._builder = renderer._builder
        self._filter = renderer._filter

    #--------------------------------------------------------------------------

    # info when generating transitions's musicsegments
    def _register_statechunks(self, txtp, bnode):
        # node defines states that muted sources
        if bnode.config.volume_states:
            txtp.scpaths.add_nstates(bnode.config.volume_states)
        return

    def _register_transitions(self, txtp, rules):
        #if not txtp.gsparams:
        #    return

        txtp.transitions.add(rules)
        return

    def _register_stingers(self, txtp, bstingerlist):
        #if not txtp.gsparams:
        #    return

        txtp.stingers.add(bstingerlist)
        return

    #--------------------------------------------------------------------------

    def _barf(self, text="not implemented"):
        raise ValueError("%s - %s %s" % (text, self.name, self.sid))

    def _render_base(self, bnode, txtp):
        try:
            txtp.info.next(bnode.node, bnode.fields, nsid=bnode.nsid)
            self._render_txtp(bnode, txtp)
            txtp.info.done()
        except Exception: #as e #autochained
            raise ValueError("Error processing TXTP for node %i" % (bnode.sid)) #from e

    def _render_txtp(self, bnode, txtp):
        self._barf("must implement")

    def _render_next_event(self, ntid, txtp):
        self._render_next(ntid, txtp, nbankid=None, idtype=wbuilder_util.IDTYPE_EVENT)

    def _render_next(self, ntid, txtp, nbankid=None, idtype=None):
        tid = ntid.value()
        if tid == 0:
            #this is fairly common in switches, that may define all combos but some nodes don't point to anything
            return

        if nbankid:
            # play actions reference bank by id (plus may save bankname in STID)
            bank_id = nbankid.value()
        else:
            # try same bank as node
            bank_id = ntid.get_root().get_id()

        builder = self._builder
        bnode = builder._get_bnode(bank_id, tid, idtype, sid_info=None, nbankid_info=nbankid) #self.sid
        if not bnode:
            return

        # filter HIRC nodes (for example drop unwanted calls to layered ActionPlay)
        filter = self._filter
        if filter and filter.active:
            generate = filter.allow_inner(bnode.node, bnode.nsid)
            if not generate:
                return

        #logging.debug("next: %s %s > %s", self.node.get_name(), self.sid, tid)
        rnode = self._renderer._get_rnode(bnode)
        rnode._render_base(bnode, txtp)
        return

    #--------------------------------------------------------------------------


    #todo
    def _build_silence(self, node, clip):
        sound = bnode_misc.NodeSound()
        sound.nsrc = node
        sound.silent = True
        sound.clip = clip
        return sound

