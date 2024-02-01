import logging, os
from datetime import datetime

from ..parser import wdefs
from .wnamerow import NameRow



class Namedumper(object):
    EMPTY_BANKTYPE = ''

    def __init__(self, wnames, cfg, names, missing, bankpaths):
        # flags
        self._wnames = wnames
        self._cfg = cfg
        self._names = names
        self._missing = missing
        self._bankpaths = bankpaths
        self._bank_mix = self._get_bank_mix()
        

    # true if there are sfx and localized, false if all are from the same type
    def _get_bank_mix(self):
        is_sfx = False
        is_lang = False
        for _, loc in self._bankpaths.keys():
            if loc:
                is_lang = True
            else:
                is_sfx = True

        return is_lang and is_sfx


    # saves loaded hashnames to .txt
    # (useful to check names when loading generic db/lst of names)
    def save_lst(self, basename=None, path=None):

        # setup
        if not basename:
            basename = 'banks'
        else:
            basename = os.path.basename(basename)
        time = datetime.today().strftime('%Y%m%d%H%M%S')
        outname = 'wwnames-%s-%s.txt' % (basename, time)
        if path:
            outname = os.path.join(path, outname)

        logging.info("names: saving %s" % (outname))

        lines = self.get_lines()

        # final output
        with open(outname, 'w', encoding='utf-8') as outfile:
            config_lines = self._cfg.get_config_lines()
            outfile.write('\n'.join(config_lines))

            outfile.write('\n'.join(lines))

    def get_lines(self):
        has_companion_names = False
        names = self._names.values()
        rows = []

        # save valid names
        for row in names:
            # hashnames only, as they can be safely shared between games
            if not row.hashname:
                continue
            # used names only, unless set to save all
            if not self._cfg.save_all and not row.hashname_used:
                continue
            # names not in xml/h/etc only, unless set to save extra
            if not self._cfg.save_companion and row.source != NameRow.NAME_SOURCE_EXTRA:
                has_companion_names = True
                continue

            rows.append(row)
                
        if self._cfg.classify_bank:
            # clasified list: include rows divided into sections
            lines = self._include_classify(rows)
        else:
            # simple list: include rows as-is
            lines = self._include_simple(rows)

        if has_companion_names:
            lines.append("\n### (more names found in companion files)\n")

        return lines

    def _include_simple(self, rows):
        lines = []
        for row in rows:
            self._save_lst_name(row, lines)

        # write IDs that don't should have hashnames but don't
        for hashtype in wdefs.fnv_order:
            if hashtype not in self._missing:
                continue
            banks = self._missing[hashtype]
            for bank in banks:
                self._include_missing(lines, hashtype, bank, header=True)

        return lines

    def _include_classify(self, rows):
        lines = []

        hashtypes_lines = {}

        # save names in temp sublines per bank (ids not in names are in self._missing)
        for row in rows:
            hashtypes = row.hashtypes
            if not hashtypes:
                hashtypes = set()
                hashtypes.add((wdefs.fnv_no, self.EMPTY_BANKTYPE))

            for hashtype, bank in hashtypes:                     
                banks_lines = hashtypes_lines.get(hashtype)
                if not banks_lines:
                    banks_lines = {}
                    hashtypes_lines[hashtype] = banks_lines

                sublines = banks_lines.get(bank)
                if not sublines:
                    sublines = []
                    banks_lines[bank] = sublines

                self._save_lst_name(row, sublines)

        # get banks to write
        banks = [(self.EMPTY_BANKTYPE, False)] #special value for other names
        banks += list(self._bankpaths.keys()) #all bankkeys
         # general names > init > regular-localized > names
        banks.sort(key=lambda x: (x[0] != self.EMPTY_BANKTYPE, x[0].lower() not in ('init.bnk','1355168291.bnk'), x[1], x[0]))

        # may print like: bank > hashtypes (banks_first=True), or hashtypes > banks (mainly a test)
        banks_first = True
        if banks_first:
            for bankkey in banks:
                for hashtype in wdefs.fnv_order:
                    self._include_classify_lines(lines, hashtypes_lines, hashtype, bankkey)
        else:
            for hashtype in wdefs.fnv_order:
                for bankkey in banks:
                    self._include_classify_lines(lines, hashtypes_lines, hashtype, bankkey)

        lines.append('')
        return lines

    def _include_classify_lines(self, lines, types_lines, hashtype, bank):
        save_missing = self._cfg.save_missing
        if hashtype not in types_lines and not save_missing:
            return
        banks = types_lines.get(hashtype)

        if not banks or bank not in banks:
            banks_missing = self._missing.get(hashtype)
            if not banks_missing or bank not in banks_missing:
                return
            sublines = None
        else:
            sublines = banks.get(bank)
        if not sublines and not save_missing:
            return

        lines.append('')
        banktext = self._get_banktext(bank)
        if banktext:
            banktext = " (%s)" % (banktext)
        lines.append('### %s NAMES%s' % (hashtype.upper(), banktext))

        if sublines:
            sublines.sort(key=str.lower)
            for subline in sublines:
                lines.append(subline)

        # include missing ids at bank level (otherwise at the end)
        if save_missing:
            self._include_missing(lines, hashtype, bank)


    def _include_missing(self, lines, hashtype, bank, header=False):
        if self._cfg.skip_hastype(hashtype):
            return

        banks = self._missing.get(hashtype)
        if not banks:
            return
        ids = banks.get(bank)
        if not ids:
            return

        if header:
            lines.append('')
            banktext = self._get_banktext(bank)
            if banktext:
                banktext = " (%s)" % (banktext)
            lines.append('### MISSING %s NAMES%s' % (hashtype.upper(), banktext))

        for id in ids:
            lines.append('# %s' % (id))
        
        # remove so it doesn't get saved twice
        banks[bank] = {}

    def _get_banktext(self, bankkey):
        bankname, bank_loc = bankkey
        basebank, _ = os.path.splitext(bankname)
        if not bankname:
            return ''

        # optional info
        bankpath = ''
        if self._cfg.bank_paths:
            bankpath = self._bankpaths.get(bankkey)
        elif bank_loc is True and self._bank_mix:
            # mark localized banks if there are localized and non-localized banks (as some games may use only localized)
            bankpath = 'langs'

        if bankpath:
            bankpath = bankpath.replace('\\', '/')
            bankname = "%s/%s" % (bankpath, bankname)

        if not basebank.isdigit():
            return bankname

        row = self._wnames.get_namerow(basebank)
        if not row or not row.hashname:
            return bankname

        return "%s: %s" % (bankname, row.hashname)

    def _save_lst_name(self, row, lines):
        #logging.debug("names: using '%s'", row.hashname)
        extended = ''
        if row.extended:
            extended = ' = 0' #allow names with special chars
        lines.append('%s%s' % (row.hashname, extended))

        # log alts too (list should be cleaned up manually)
        for hashname in row.hashnames:
            if extended:
                lines.append('#alt')
                lines.append('%s%s' % (row.hashname, extended))
            else:
                lines.append('%s #alt' % (hashname))
