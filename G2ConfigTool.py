#! /usr/bin/env python3

import argparse
import cmd
import glob
import json
import os
import pathlib
import platform
import re
import sys
import textwrap
import traceback
from collections import OrderedDict
from contextlib import suppress
import subprocess

try:
    import prettytable
except (ImportError, ModuleNotFoundError):
    prettytable = None

import G2Paths
from G2IniParams import G2IniParams

try:
    from senzing import G2Config, G2ConfigMgr, G2Exception, G2ModuleGenericException
except Exception:
    pass

try:
    import readline
    import atexit
except ImportError:
    readline = None

try:
    from pygments import highlight, lexers, formatters
except ImportError:
    pass

# ===== supporting classes =====

class Colors:

    @classmethod
    def apply(cls, in_string, color_list=None):
        ''' apply list of colors to a string '''
        if color_list:
            prefix = ''.join([getattr(cls, i.strip().upper()) for i in color_list.split(',')])
            suffix = cls.RESET
            return f'{prefix}{in_string}{suffix}'
        return in_string

    @classmethod
    def set_theme(cls, theme):
        # best for dark backgrounds
        if theme.upper() == 'DEFAULT':
            cls.TABLE_TITLE = cls.FG_GREY42
            cls.ROW_TITLE = cls.FG_GREY42
            cls.COLUMN_HEADER = cls.FG_GREY42
            cls.ENTITY_COLOR = cls.FG_MEDIUMORCHID1
            cls.DSRC_COLOR = cls.FG_ORANGERED1
            cls.ATTR_COLOR = cls.FG_CORNFLOWERBLUE
            cls.GOOD = cls.FG_CHARTREUSE3
            cls.BAD = cls.FG_RED3
            cls.CAUTION = cls.FG_GOLD3
            cls.HIGHLIGHT1 = cls.FG_DEEPPINK4
            cls.HIGHLIGHT2 = cls.FG_DEEPSKYBLUE1
        elif theme.upper() == 'LIGHT':
            cls.TABLE_TITLE = cls.FG_LIGHTBLACK
            cls.ROW_TITLE = cls.FG_LIGHTBLACK
            cls.COLUMN_HEADER = cls.FG_LIGHTBLACK  # + cls.ITALICS
            cls.ENTITY_COLOR = cls.FG_LIGHTMAGENTA + cls.BOLD
            cls.DSRC_COLOR = cls.FG_LIGHTYELLOW + cls.BOLD
            cls.ATTR_COLOR = cls.FG_LIGHTCYAN + cls.BOLD
            cls.GOOD = cls.FG_LIGHTGREEN
            cls.BAD = cls.FG_LIGHTRED
            cls.CAUTION = cls.FG_LIGHTYELLOW
            cls.HIGHLIGHT1 = cls.FG_LIGHTMAGENTA
            cls.HIGHLIGHT2 = cls.FG_LIGHTCYAN
        elif theme.upper() == 'DARK':
            cls.TABLE_TITLE = cls.FG_LIGHTBLACK
            cls.ROW_TITLE = cls.FG_LIGHTBLACK
            cls.COLUMN_HEADER = cls.FG_LIGHTBLACK  # + cls.ITALICS
            cls.ENTITY_COLOR = cls.FG_MAGENTA + cls.BOLD
            cls.DSRC_COLOR = cls.FG_YELLOW + cls.BOLD
            cls.ATTR_COLOR = cls.FG_CYAN + cls.BOLD
            cls.GOOD = cls.FG_GREEN
            cls.BAD = cls.FG_RED
            cls.CAUTION = cls.FG_YELLOW
            cls.HIGHLIGHT1 = cls.FG_MAGENTA
            cls.HIGHLIGHT2 = cls.FG_CYAN

    # styles
    RESET = '\033[0m'
    BOLD = '\033[01m'
    DIM = '\033[02m'
    ITALICS = '\033[03m'
    UNDERLINE = '\033[04m'
    BLINK = '\033[05m'
    REVERSE = '\033[07m'
    STRIKETHROUGH = '\033[09m'
    INVISIBLE = '\033[08m'
    # foregrounds
    FG_BLACK = '\033[30m'
    FG_WHITE = '\033[97m'
    FG_BLUE = '\033[34m'
    FG_MAGENTA = '\033[35m'
    FG_CYAN = '\033[36m'
    FG_YELLOW = '\033[33m'
    FG_GREEN = '\033[32m'
    FG_RED = '\033[31m'
    FG_LIGHTBLACK = '\033[90m'
    FG_LIGHTWHITE = '\033[37m'
    FG_LIGHTBLUE = '\033[94m'
    FG_LIGHTMAGENTA = '\033[95m'
    FG_LIGHTCYAN = '\033[96m'
    FG_LIGHTYELLOW = '\033[93m'
    FG_LIGHTGREEN = '\033[92m'
    FG_LIGHTRED = '\033[91m'
    # backgrounds
    BG_BLACK = '\033[40m'
    BG_WHITE = '\033[107m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_YELLOW = '\033[43m'
    BG_GREEN = '\033[42m'
    BG_RED = '\033[41m'
    BG_LIGHTBLACK = '\033[100m'
    BG_LIGHTWHITE = '\033[47m'
    BG_LIGHTBLUE = '\033[104m'
    BG_LIGHTMAGENTA = '\033[105m'
    BG_LIGHTCYAN = '\033[106m'
    BG_LIGHTYELLOW = '\033[103m'
    BG_LIGHTGREEN = '\033[102m'
    BG_LIGHTRED = '\033[101m'
    # extended
    FG_DARKORANGE = '\033[38;5;208m'
    FG_SYSTEMBLUE = '\033[38;5;12m'  # darker
    FG_DODGERBLUE2 = '\033[38;5;27m'  # lighter
    FG_PURPLE = '\033[38;5;93m'
    FG_DARKVIOLET = '\033[38;5;128m'
    FG_MAGENTA3 = '\033[38;5;164m'
    FG_GOLD3 = '\033[38;5;178m'
    FG_YELLOW1 = '\033[38;5;226m'
    FG_SKYBLUE1 = '\033[38;5;117m'
    FG_SKYBLUE2 = '\033[38;5;111m'
    FG_ROYALBLUE1 = '\033[38;5;63m'
    FG_CORNFLOWERBLUE = '\033[38;5;69m'
    FG_HOTPINK = '\033[38;5;206m'
    FG_DEEPPINK4 = '\033[38;5;89m'
    FG_MAGENTA3 = '\033[38;5;164m'
    FG_SALMON = '\033[38;5;209m'
    FG_MEDIUMORCHID1 = '\033[38;5;207m'
    FG_NAVAJOWHITE3 = '\033[38;5;144m'
    FG_DARKGOLDENROD = '\033[38;5;136m'
    FG_STEELBLUE1 = '\033[38;5;81m'
    FG_GREY42 = '\033[38;5;242m'
    FG_INDIANRED = '\033[38;5;131m'
    FG_DEEPSKYBLUE1 = '\033[38;5;39m'
    FG_ORANGE3 = '\033[38;5;172m'
    FG_RED3 = '\033[38;5;124m'
    FG_SEAGREEN2 = '\033[38;5;83m'
    FG_YELLOW3 = '\033[38;5;184m'
    FG_CYAN3 = '\033[38;5;43m'
    FG_CHARTREUSE3 = '\033[38;5;70m'
    FG_ORANGERED1 = '\033[38;5;202m'

def colorize(in_string, color_list='None'):
    return Colors.apply(in_string, color_list)

def colorize_msg(msg_text, msg_type_or_color = ''):
    if msg_type_or_color.upper() == 'ERROR':
        msg_color = 'bad'
    elif msg_type_or_color.upper() == 'WARNING':
        msg_color = 'caution'
    elif msg_type_or_color.upper() == 'INFO':
        msg_color = 'highlight2'
    elif msg_type_or_color.upper() == 'SUCCESS':
        msg_color = 'good'
    else:
        msg_color = msg_type_or_color
    print(f"\n{Colors.apply(msg_text, msg_color)}\n")

def colorize_json(json_str):
    for token in set(re.findall(r'"(.*?)"', json_str)):
        tag = f'"{token}":'
        if tag in json_str:
            json_str = json_str.replace(tag, colorize(tag, 'attr_color'))
        else:
            tag = f'"{token}"'
            if tag in json_str:
                json_str = json_str.replace(tag, colorize(tag, 'dim'))
    return json_str

# ===== main class =====

class G2CmdShell(cmd.Cmd, object):

    def __init__(self, g2module_params, hist_disable, force_mode, file_to_process, debug):
        cmd.Cmd.__init__(self)

        # Cmd Module settings
        self.intro = ''
        self.prompt = '(g2cfg) '
        self.ruler = '-'
        self.doc_header = 'Configuration Command List'
        self.misc_header = 'Help Topics (help <topic>)'
        self.undoc_header = 'Misc Commands'
        self.__hidden_methods = ('do_EOF', 'do_help',
                                 'do_addEntityClass', 'do_deleteEntityClass', 'do_listEntityClasses',
                                 'do_addEntityType', 'do_deleteEntityType', 'do_listEntityTypes',
                                 'do_addConfigSection', 'do_addConfigSectionField')

        self.g2_configmgr = G2ConfigMgr()
        self.g2_config = G2Config()

        # Set flag to know if running an interactive command shell or reading from file
        self.isInteractive = True

        # Windows command history
        if platform.system() == 'Windows':
            self.use_rawinput = False

        # Config variables and setup
        self.configUpdated = False
        self.g2_module_params = g2module_params

        # Processing input file
        self.forceMode = force_mode
        self.fileToProcess = file_to_process

        self.attributeClassList = ('NAME', 'ATTRIBUTE', 'IDENTIFIER', 'ADDRESS', 'PHONE', 'RELATIONSHIP', 'OTHER')
        self.lockedFeatureList = ('NAME', 'ADDRESS', 'PHONE', 'DOB', 'REL_LINK', 'REL_ANCHOR', 'REL_POINTER')
        self.valid_behavior_codes = ['NAME','A1','A1E','A1ES','F1','F1E','F1ES','FF','FFE','FFES','FM','FME','FMES','FVM','FVME','FVMES']

        self.doDebug = debug

        # Setup for pretty printing
        self.pygmentsInstalled = True if 'pygments' in sys.modules else False
        self.current_get_format = 'json'
        self.current_list_format = 'table' if prettytable else 'jsonl'

        # Readline and history
        self.readlineAvail = True if 'readline' in sys.modules else False
        self.histDisable = hist_disable
        self.histCheck()

        self.parser = argparse.ArgumentParser(prog='', add_help=False)
        self.subparsers = self.parser.add_subparsers()

        getConfig_parser = self.subparsers.add_parser('getConfig', usage=argparse.SUPPRESS)
        getConfig_parser.add_argument('configID', type=int)

        Colors.set_theme('DEFAULT')

# ===== custom help section =====

    def do_help(self, *args):
        if not args[0]:
            self.help_overview()
        else:
            func_name = args[0]
            if func_name not in self.get_names():
                func_name = 'do_' + func_name
            if func_name in self.get_names():
                if getattr(self, func_name).__doc__:
                    help_lines = textwrap.dedent(getattr(self, func_name).__doc__).split('\n')
                    help_text = ''
                    headers = ['Syntax:', 'Examples:', 'Example:', 'Notes:', 'Caution:']
                    current_section = ''
                    for line in help_lines:
                        line_color = ''
                        if line in headers:
                            current_section = line
                            if current_section == 'Caution:':
                                line_color = 'caution'
                            else:
                                line_color = 'highlight2'
                        elif line:
                            if current_section == 'Caution:':
                                line_color = 'caution'
                            elif current_section not in ('Syntax:', 'Examples:', 'Example:'):
                                line_color = 'dim'
                        help_text += colorize(line, line_color) + '\n'
                    print(help_text)
                else:
                    colorize_msg(f'No help text found for {func_name}', 'warning')
            else:
                cmd.Cmd.do_help(self, *args)

    def help_all(self):
        args = ('',)
        cmd.Cmd.do_help(self, *args)

    def help_overview(self):
        print(textwrap.dedent(f'''
        {colorize('This utility allows you to configure a Senzing instance!', 'dim')}

        {colorize('Senzing compares records within and across data sources.  Records consist of features and features have attributes.', 'dim')}
        {colorize('For instance, the NAME feature has attributes such as NAME_FIRST and NAME_LAST for a person and NAME_ORG for an', 'dim')}
        {colorize('organization.', 'dim')}

        {colorize('Features are standardized and expressed in various ways to create candidate keys, and when candidates are found all', 'dim')}
        {colorize('of their features are compared to the incoming record''s features to see how close they actually are.', 'dim')}

        {colorize('Finally, a set of rules or "principles" are applied to each candidate record''s feature scores to see if the incoming', 'dim')}
        {colorize('record should resolve to an existing entity or become a new one. In either case, the rules are also used to create', 'dim')}
        {colorize('relationships between entities.', 'dim')}

        {colorize('Additional help:', 'highlight2')}
            help basic      {colorize('<- for commonly used commands', 'dim')}
            help features   {colorize('<- to be used only with the guidance of Senzing support', 'dim')}
            help principles {colorize('<- to be used only with the guidance of Senzing support', 'dim')}
            help all        {colorize('<- to show all configuration commands', 'dim')}

        {colorize('To understand more about configuring Senzing, please review:', 'dim')}
            {colorize('https://senzing.com/wp-content/uploads/Entity-Resolution-Processes-021320.pdf', 'highlight1, underline')}
            {colorize('https://senzing.com/wp-content/uploads/Principle-Based-Entity-Resolution-092519.pdf', 'highlight1, underline')}
            {colorize('https://senzing.zendesk.com/hc/en-us/articles/231925448-Generic-Entity-Specification-JSON-CSV-Mapping', 'highlight1, underline')}

        '''))

    def help_basic(self):
        print(textwrap.dedent(f'''
        {colorize('Senzing comes pre-configured with all the settings needed to resolve persons and organizations.  Usually all that is required', 'dim')}
        {colorize('is for you to register your data sources and start loading data based on the Generic Entity Specification.', 'dim')}

        {colorize('Data source commands:', 'highlight2')}
            addDataSource           {colorize('<- to register a new data source', 'dim')}
            deleteDataSource        {colorize('<- to remove a data source created by error', 'dim')}
            listDataSources         {colorize('<- to see all the registered data sources', 'dim')}

        {colorize('When you see a how or a why screen output in Senzing, you see the actual entity counts and scores of a match. The list functions', 'dim,italics')}
        {colorize('below show you what those thresholds and scores are currently configured to.', 'dim,italics')}

        {colorize('Features and attribute settings:', 'highlight2')}
            listFeatures            {colorize('<- to see all features, whether they are used for candidates, and how they are scored', 'dim')}
            listAttributes          {colorize('<- to see all the attributes you can map to', 'dim')}

        {colorize('Principles (rules, scores, and thresholds):', 'highlight2')}
            listFunctions           {colorize('<- to see all the standardization, expression and comparison functions possible', 'dim')}
            listGenericThresholds   {colorize('<- to see all the thresholds for when feature values go generic for candidates or scoring', 'dim')}
            listRules               {colorize('<- to see all the principles in the order they are evaluated', 'dim')}
            listFragments           {colorize('<- to see all the fragments of rules are configured, such as what is considered close_name', 'dim')}

        {colorize('CAUTION:', 'caution')}
            {colorize('While adding or updating features, expressions, scoring thresholds and rules are discouraged without the guidance of Senzing support,', 'caution')}
            {colorize('knowing how they are configured and what their thresholds are can help you understand why records resolved or not, leading to the', 'caution')}
            {colorize('proper course of action when working with Senzing Support.', 'caution')}

        '''))

    def help_features(self):
        print(textwrap.dedent(f'''
        {colorize('New features and their attributes are rarely needed.  But when they are they are usually industry specific', 'dim')}
        {colorize('identifiers (F1s) like medicare_provider_id or swift_code for a bank.  If you want some other kind of attribute like a grouping (FF)', 'dim')}
        {colorize('or a physical attribute (FME, FMES), it is best to clone an existing feature by doing a getFeature, then modifying the json payload to', 'dim')}
        {colorize('use it in an addFeature.', 'dim')}

        {colorize('Commands to add or update features:', 'highlight2')}
            listFeatures            {colorize('<- to list all the features in the system', 'dim')}
            getFeature              {colorize('<- get the json configuration for an existing feature', 'dim')}
            addFeature              {colorize('<- add a new feature from a json configuration', 'dim')}
            setFeature              {colorize('<- to change a setting on an existing feature', 'dim')}
            deleteFeature           {colorize('<- to delete a feature added by mistake', 'dim')}

        {colorize('Attributes are what you map your source data to.  If you add a new feature, you will also need to add attributes for it. Be sure to', 'dim')}
        {colorize('use a unique ID for attributes and to classify them as either an ATTRIBUTE or an IDENTIFIER.', 'dim')}

        {colorize('Commands to add or update attributes:', 'highlight2')}
            listAttributes          {colorize('<- to see all the attributes you can map to', 'dim')}
            getAttribute            {colorize('<- get the json configuration for an existing attribute', 'dim')}
            addAttribute            {colorize('<- add a new attribute from a json configuration', 'dim')}
            deleteAttribute         {colorize('<- to delete an attribute added by mistake', 'dim')}

        {colorize('Some templates have been created to help you add new identifiers if needed. A template adds a feature and its required', 'dim')}
        {colorize('attributes with one command.', 'dim')}

        {colorize('Commands for using templates:', 'highlight2')}
            templateAdd             {colorize('<- add an identifier (F1) feature and attributes based on a template', 'dim')}
            templateAdd list        {colorize('<- to see the list of available templates', 'dim')}
        '''))

    def help_principles(self):
        print(textwrap.dedent(f'''
        {colorize('Before the principles are applied, the features and expressions created for incoming records are used to find candidates.', 'dim')}
        {colorize('An example of an expression is name and DOB and there is an expression call on the feature "name" to automatically create it', 'dim')}
        {colorize('if both a name and DOB are present on the incoming record.  Features and expressions used for candidates are also referred', 'dim')}
        {colorize('to as candidate builders or candidate keys.', 'dim')}

        {colorize('Commands that help with configuring candidate keys:', 'highlight2')}
            listFeatures            {colorize('<- to see what features are used for candidates', 'dim')}
            setFeature              {colorize('<- to toggle whether or not a feature is used for candidates', 'dim')}
            listExpressionCalls     {colorize('<- to see what expressions are currently being created', 'dim')}
            addToNamehash           {colorize('<- to add an element from another feature to the list of composite name keys', 'dim')}
            addExpressionCall       {colorize('<- to add a new expression call, aka candidate key', 'dim')}
            listGenericThresholds   {colorize('<- to see when candidate keys will become generic and are no longer used to find candidates', 'dim')}
            setGenericThreshold     {colorize('<- to change when features with certain behaviors become generic', 'dim')}

        {colorize('CAUTION:', 'caution')}
            {colorize('The cost of raising generic thresholds is speed. It is always best to keep generic thresholds low and to add new', 'caution')}
            {colorize('new expressions instead.  You can extend composite key expressions with the addToNameHash command above, or add ', 'caution')}
            {colorize('new expressions by using the addExpressionCall command above.', 'caution')}

        {colorize('Once the candidate matches have been found, scoring and rule evaluation takes place.  Scores are rolled up by behavior.', 'dim')}
        {colorize('For instance, both addresses and phones have the behavior FF (Frequency Few). If they both score above their scoring', 'dim')}
        {colorize('function''s close threshold, there would be two CLOSE_FFs (a fragment) which can be used in a rule such as NAME+CLOSE_FF.', 'dim')}

        {colorize('Commands that help with configuring principles (rules) and scoring:', 'highlight2')}
            listRules               {colorize('<- these are the principles that are applied top down', 'dim')}
            listFragments           {colorize('<- rules are combinations of fragments like close_name or same_name', 'dim')}
            listFunctions           {colorize('<- the comparison functions show you what is considered same, close, likely, etc.', 'dim')}
            setRule                 {colorize('<- to change whether an existing rule resolves or relates', 'dim')}
        '''))

    def help_support(self):
        print(textwrap.dedent(f'''
        {colorize('Senzing Knowledge Center:', 'dim')} {colorize('https://senzing.zendesk.com/hc/en-us', 'highlight1,underline')}

        {colorize('Senzing Support Request:', 'dim')} {colorize('https://senzing.zendesk.com/hc/en-us/requests/new', 'highlight1,underline')}
        '''))

# ===== Auto completion section =====

    def get_names(self):
        """Hide functions from available list of Commands. Separate help sections for some"""
        return [n for n in dir(self.__class__)] # if n not in self.__hidden_methods]

    def completenames(self, text, *ignored):
        """Override function from cmd module to make command completion case insensitive"""
        dotext = 'do_' + text
        return [a[3:] for a in self.get_names() if a.lower().startswith(dotext.lower())]

    def complete_exportToFile(self, text, line, begidx, endidx):
        if re.match("exportToFile +", line):
            return self.pathCompletes(text, line, begidx, endidx, 'exportToFile')

    def complete_importFromFile(self, text, line, begidx, endidx):
        if re.match("importFromFile +", line):
            return self.pathCompletes(text, line, begidx, endidx, 'importFromFile')

    def pathCompletes(self, text, line, begidx, endidx, callingcmd):
        """ Auto complete paths for commands that have a complete_ function """

        completes = []

        pathComp = line[len(callingcmd) + 1:endidx]
        fixed = line[len(callingcmd) + 1:begidx]

        for path in glob.glob(f'{pathComp}*'):
            path = path + os.sep if path and os.path.isdir(path) and path[-1] != os.sep else path
            completes.append(path.replace(fixed, '', 1))

        return completes

    def complete_getAttribute(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_ATTR', 'ATTR_CODE', text)

    def complete_getFeature(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_FTYPE', 'FTYPE_CODE', text)

    def complete_getElement(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_FELEM', 'FELEM_CODE', text)

    def complete_getFragment(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_ERFRAG', 'ERFRAG_CODE', text)

    def complete_getRule(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_ERRULE', 'ERRULE_CODE', text)

    def complete_deleteAttribute(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_ATTR', 'ATTR_CODE', text)

    def complete_deleteDataSource(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_DSRC', 'DSRC_CODE', text)

    def complete_deleteElement(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_FELEM', 'FELEM_CODE', text)

    def complete_deleteEntityType(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_ETYPE', 'ETYPE_CODE', text)

    def complete_deleteFeature(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_FTYPE', 'FTYPE_CODE', text)

    def complete_deleteFeatureComparison(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_FTYPE', 'FTYPE_CODE', text)

    def complete_deleteFeatureDistinctCall(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_FTYPE', 'FTYPE_CODE', text)

    def complete_deleteFragment(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_ERFRAG', 'ERFRAG_CODE', text)

    def complete_deleteRule(self, text, line, begidx, endidx):
        return self.codes_completes('CFG_ERRULE', 'ERRULE_CODE', text)

    def codes_completes(self, table, field, arg):
        # Build list each time to have latest even after an add*, delete*
        return [code for code in self.getRecordCodes(table, field) if code.lower().startswith(arg.lower())]

    def getRecordCodes(self, table, field):
        code_list = []
        for i in range(len(self.cfgData['G2_CONFIG'][table])):
            code_list.append(self.cfgData["G2_CONFIG"][table][i][field])
        return code_list

    def complete_getConfigSection(self, text, line, begidx, endidx):
        return [section for section in self.cfgData["G2_CONFIG"].keys() if section.lower().startswith(text.lower())]


# ===== command history section =====

    def histCheck(self):

        self.histFileName = None
        self.histFileError = None
        self.histAvail = False

        if not self.histDisable:

            if readline:
                tmpHist = '.' + os.path.basename(sys.argv[0].lower().replace('.py', '_history'))
                self.histFileName = os.path.join(os.path.expanduser('~'), tmpHist)

                # Try and open history in users home first for longevity
                try:
                    open(self.histFileName, 'a').close()
                except IOError as e:
                    self.histFileError = f'{e} - Couldn\'t use home, trying /tmp/...'

                # Can't use users home, try using /tmp/ for history useful at least in the session
                if self.histFileError:

                    self.histFileName = f'/tmp/{tmpHist}'
                    try:
                        open(self.histFileName, 'a').close()
                    except IOError as e:
                        self.histFileError = f'{e} - User home dir and /tmp/ failed!'
                        return

                hist_size = 2000
                readline.read_history_file(self.histFileName)
                readline.set_history_length(hist_size)
                atexit.register(readline.set_history_length, hist_size)
                atexit.register(readline.write_history_file, self.histFileName)

                self.histFileName = self.histFileName
                self.histFileError = None
                self.histAvail = True

    def do_histDedupe(self, arg):
        """
        Deduplicates the command history

        Syntax:
            histDedupe
        """
        if self.histAvail:
            if input('\nAre you sure you want to de-duplicate the session history? (y/n) ').upper().startwith('Y'):

                with open(self.histFileName) as hf:
                    linesIn = (line.rstrip() for line in hf)
                    uniqLines = OrderedDict.fromkeys(line for line in linesIn if line)

                    readline.clear_history()
                    for ul in uniqLines:
                        readline.add_history(ul)

                colorize_msg('Session history and history file both deduplicated!', 'success')
            else:
                print()
        else:
            colorize_msg('History is not available in this session.', 'warning')

    def do_histClear(self, arg):
        """
        Clears the command history

        Syntax:
            histClear
        """
        if self.histAvail:
            if input('\nAre you sure you want to clear the session history? (y/n) ').upper().startwith('Y'):
                readline.clear_history()
                readline.write_history_file(self.histFileName)
                colorize_msg('Session history and history file both cleared!', 'success')
            else:
                print()
        else:
            colorize_msg('History is not available in this session.', 'warning')

    def do_history(self, arg):
        """
        Displays the command history

        Syntax:
            history
        """
        if self.histAvail:
            print()
            for i in range(readline.get_current_history_length()):
                print(readline.get_history_item(i + 1))
            print()
        else:
            colorize_msg('History is not available in this session.', 'warning')


# ===== command loop section =====

    def initEngines(self, init_msg=False):

        if init_msg:
            colorize_msg('Initializing Senzing engines ...')

        try:
            self.g2_configmgr.init('pyG2ConfigMgr', self.g2_module_params, False)
            self.g2_config.init('pyG2Config', self.g2_module_params, False)
        except G2Exception as err:
            colorize_msg(err, 'error')
            self.destroyEngines()
            sys.exit(1)

        # Re-read config after a save
        if self.configUpdated:
            self.loadConfig()

    def destroyEngines(self):

        with suppress(Exception):
            self.g2_configmgr.destroy()
            self.g2_config.destroy()

    def loadConfig(self, defaultConfigID = None):

        # Get the current configuration from the Senzing database
        if not defaultConfigID:
            defaultConfigID = bytearray()
            self.g2_configmgr.getDefaultConfigID(defaultConfigID)

        # If a default config isn't found, create a new default configuration
        if not defaultConfigID:

            colorize_msg('Adding default config to new database!', 'warning')

            config_handle = self.g2_config.create()

            config_default = bytearray()
            self.g2_config.save(config_handle, config_default)
            config_string = config_default.decode()

            # Persist new default config to Senzing Repository
            try:
                addconfig_id = bytearray()
                self.g2_configmgr.addConfig(config_string, 'New default configuration added by G2ConfigTool.',
                                            addconfig_id)
                self.g2_configmgr.setDefaultConfigID(addconfig_id)
            except G2ModuleGenericException:
                raise

            colorize_msg('Default config added!', 'success')
            self.destroyEngines()
            self.initEngines(init_msg=(True if self.isInteractive else False))
            defaultConfigID = bytearray()
            self.g2_configmgr.getDefaultConfigID(defaultConfigID)

        config_current = bytearray()
        self.g2_configmgr.getConfig(defaultConfigID, config_current)
        self.cfgData = json.loads(config_current.decode())
        self.configUpdated = False

    def preloop(self):

        self.initEngines()
        self.loadConfig()

        colorize_msg('Welcome to the Senzing configuration tool! Type help or ? to list commands', 'highlight2')

    def cmdloop(self):

        while True:
            try:
                cmd.Cmd.cmdloop(self)
                break
            except KeyboardInterrupt:
                if self.configUpdated:
                    if input('\n\nThere are unsaved changes, would you like to save first? (y/n) ').upper().startswith('Y'):
                        self.do_save(self)
                        break

                if input('\nAre you sure you want to exit? (y/n) ').upper().startswith('Y'):
                    break
                else:
                    print()

            except TypeError as err:
                colorize_msg(err, 'error')
                type_, value_, traceback_ = sys.exc_info()
                for item in traceback.format_tb(traceback_):
                    print(item)

    def postloop(self):
        self.destroyEngines()

    def emptyline(self):
        return

    def default(self, line):
        colorize_msg('Unknown command, type help to list available commands', 'warning')
        return

    def fileloop(self):

        # Get initial config
        self.initEngines(init_msg=False)
        self.loadConfig()

        # Set flag to know running an interactive command shell or not
        self.isInteractive = False

        save_detected = False

        with open(self.fileToProcess) as data_in:
            for line in data_in:
                line = line.strip()
                if len(line) > 0 and line[0:1] not in ('#', '-', '/'):
                    # *args allows for empty list if there are no args
                    (read_cmd, *args) = line.split()
                    process_cmd = f'do_{read_cmd}'
                    print(colorize(f'----- {read_cmd} -----', 'dim'))
                    print(line)

                    if process_cmd == 'do_save' and not save_detected:
                        save_detected = True

                    if process_cmd not in dir(self):
                        colorize_msg(f'Command {read_cmd} not found', 'error')
                    else:
                        exec_cmd = f"self.{process_cmd}('{' '.join(args)}')"
                        exec(exec_cmd)

                    if not self.forceMode:
                        if input('\nPress enter to continue or (Q)uit... ').upper().startswith('Q'):
                            break

        if not save_detected and self.configUpdated:
            if not self.forceMode:
                if input('\nNo save command was issued would you like to save now? (y/n) ').upper().startswith('Y'):
                    self.do_save(self)
                    print()
                    return

            colorize_msg('Configuration changes were not saved!', 'warning')

    def do_quit(self, arg):
        if self.configUpdated:
            if input('\nThere are unsaved changes, would you like to save first? (y/n) ').upper().startswith('Y'):
                self.do_save(self)
            else:
                colorize_msg('Configuration changes were not saved!', 'warning')
        print()
        return True

    def do_exit(self, arg):
        self.do_quit(self)
        return True

    def do_save(self, args):
        if self.configUpdated:

            # If not accepting file commands without prompts and not using older style config file
            if not self.forceMode:
                if not input('\nAre you certain you wish to proceed and save changes? (y/n) ').upper().startswith('Y'):
                    colorize_msg('Configuration changes have not been saved!', 'warning')
                    return

            try:
                newConfigId = bytearray()
                self.g2_configmgr.addConfig(json.dumps(self.cfgData), 'Updated by G2ConfigTool', newConfigId)
                self.g2_configmgr.setDefaultConfigID(newConfigId)

            except G2ModuleGenericException as err:
                colorize_msg(err, 'error')
            else:
                colorize_msg('Configuration changes saved!', 'success')
                # Reinit engines to pick up changes. This is good practice and will be needed when rewritten to fully use cfg APIs
                # Don't display init msg if not interactive (fileloop)
                if sys._getframe().f_back.f_code.co_name == 'onecmd':
                    self.destroyEngines()
                    self.initEngines(init_msg=(True if self.isInteractive else False))
                    self.configUpdated = False

        else:
            colorize_msg('There were no changes to save', 'warning')

    def do_shell(self, line):
        output = os.popen(line).read()
        print(f'\n{output}\n')


# ===== whole configuration =====

    def do_getDefaultConfigID(self, arg):
        """
        Returns the the current configuration ID

        Syntax:
            getDefaultConfigID
        """
        response = bytearray()
        try:
            self.g2_configmgr.getDefaultConfigID(response)
            colorize_msg(f"The default config ID is: {response.decode()}")
        except G2Exception as err:
            colorize_msg(err, 'error')

    def do_getConfigList(self, arg):
        """
        Returns the list of all known configurations

        Syntax:
            getConfigList [optional_output_format]
        """
        arg = self.check_arg_for_get_format(arg)
        try:
            response = bytearray()
            self.g2_configmgr.getConfigList(response)
            self.print_json_record(response.decode())
        except G2Exception as err:
            colorize_msg(err, 'error')

    def do_getConfigTable(self, arg):
        """
        Returns the json configuration for a specific desired configuration table

        Syntax:
            getConfigTable [table name]

        Examples:
            getConfigTable CFG_CFUNC

        Caution:
            These listings will only be understood by Senzing engineers
        """
        arg = self.check_arg_for_list_format(arg) # checking for list here even though a get as it
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        if self.cfgData["G2_CONFIG"].get(arg):
            self.print_json_lines(self.cfgData["G2_CONFIG"][arg])
        else:
            colorize_msg(f'Config table {arg} not found!', 'error')

    def do_reloadConfig(self, arg):
        """
        Reload the configuration, abandoning any changes

        Syntax:
            configReload
        """
        if self.configUpdated:
            if not input('\nYou have unsaved changes, are you sure you want to discard them? (y/n) ').upper().startswith('Y'):
                colorize_msg('Your changes have not been overwritten', 'info')
                return
            self.loadConfig()
            self.configUpdated = False
            colorize_msg('Config has been reloaded', 'success')
        else:
            colorize_msg('Config has not been updated', 'warning')

    def do_exportToFile(self, arg):
        """
        Export the current configuration data to a file

        Examples:
            exportToFile [fileName] [optional_config_id]

        Notes:
            You can export any prior config_id from the getConfigList command by specifying it after the fileName
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        arg_list = arg.split()
        fileName = arg_list[0]

        if len(arg_list) == 1:
            json_data = self.cfgData
        else:
            config_id = arg_list[1]
            try:
                response = bytearray()
                self.g2_configmgr.getConfig(config_id, response)
                json_data = json.loads(response.decode())
            except G2Exception as err:
                colorize_msg(err, 'error')
                return
        try:
            with open(fileName, 'w') as fp:
                json.dump(json_data, fp, indent=4, sort_keys=True)
        except OSError as err:
            colorize_msg(err, 'error')
        else:
            colorize_msg('Successfully exported!', 'success')

    def do_importFromFile(self, arg):
        """
        Import the config from a file

        Examples:
            importFromFile [fileName]
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        if self.configUpdated:
            if not input('\nYou have unsaved changes, are you sure you want to discard them? (y/n) ').upper().startswith('Y'):
                return
        try:
            self.cfgData = json.load(open(arg, encoding="utf-8"))
        except ValueError as err:
            colorize_msg(err, 'error')
        else:
            colorize_msg('Successfully imported!', 'success')


# ===== settings section =====

    def do_setGetFormat(self, arg):
        """
        Syntax:
            setGetFormat [json/jsonl]
        """
        if not arg:
            colorize_msg(f'current format is {self.current_get_format}', 'info')
            return
        if arg.lower() not in ('json', 'jsonl'):
            colorize_msg(f'format must be json (tall json) or jsonl! (json lines)', 'error')
        else:
            self.current_get_format = arg.lower()
            print()

    def do_setListFormat(self, arg):
        """
        Syntax:
            setListFormat [table/jsonl/json]
        """
        if not arg:
            colorize_msg(f'current format is {self.current_list_format}', 'info')
            return
        if arg.lower() not in ('table', 'json', 'jsonl'):
            colorize_msg(f'format must be table, json (tall json) or jsonl (json lines)', 'error')
        else:
            self.current_list_format = arg.lower()
            print()

    def check_arg_for_get_format(self, arg):
        if not arg:
            return arg
        new_arg = []
        for token in arg.split():
            if token.lower() in ('json', 'jsonl'):
                self.current_get_format = token.lower()
            else:
                new_arg.append(token)
        return ' '.join(new_arg)

    def check_arg_for_list_format(self, arg):
        if not arg:
            return arg
        new_arg = []
        for token in arg.split():
            if token.lower() in ('table', 'json', 'jsonl'):
                self.current_list_format = token.lower()
                arg = arg.replace(token, '')
            else:
                new_arg.append(token)
        return ' '.join(new_arg)


# ===== code lookups and validations =====

    def getRecord(self, table, field, value):
        for i in range(len(self.cfgData['G2_CONFIG'][table])):
            if type(field) == list:
                matched = True
                for ii in range(len(field)):
                    if self.cfgData['G2_CONFIG'][table][i][field[ii]] != value[ii]:
                        matched = False
                        break
            else:
                matched = self.cfgData['G2_CONFIG'][table][i][field] == value

            if matched:
                return self.cfgData['G2_CONFIG'][table][i]
        return None

    def getRecordList(self, table, field=None, value=None):
        recordList = []
        for i in range(len(self.cfgData['G2_CONFIG'][table])):
            if field and value:
                if self.cfgData['G2_CONFIG'][table][i][field] == value:
                    recordList.append(self.cfgData['G2_CONFIG'][table][i])
            else:
                recordList.append(self.cfgData['G2_CONFIG'][table][i])
        return recordList

    def getNextRecordId(self, table, field, value):
        id_taken = False
        last_id = 1000
        for i in range(len(self.cfgData['G2_CONFIG'][table])):
            if value and self.cfgData['G2_CONFIG'][table][i][field] == value:
                id_taken = True
            if self.cfgData['G2_CONFIG'][table][i][field] > last_id:
                last_id = self.cfgData['G2_CONFIG'][table][i][field]
        return value if value > 0 and not id_taken else last_id + 1

    def lookupDatasource(self, dataSource):
        dsrcRecord = self.getRecord('CFG_DSRC', 'DSRC_CODE', dataSource)
        if dsrcRecord:
            return dsrcRecord, f'Data source "{dataSource}" already exists!'
        return None, f'Data source "{dataSource}" does not exist!'

    def lookupFeature(self, feature):
        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', feature)
        if ftypeRecord:
            return ftypeRecord, f'Feature "{feature}" already exists!'
        return None, f'Feature "{feature}" does not exist!'

    def lookupElement(self, element):
        felemRecord = self.getRecord('CFG_FELEM', 'ELEM_CODE', element)
        if felemRecord:
            return felemRecord, f'Element "{element}" already exists!'
        return None, f'Element "{element}" does not exist!'

    def lookupFeatureElement(self, feature, element):
        ftypeRecord, error_text = self.lookupFeature(feature)
        if not ftypeRecord:
            return None, error_text
        else:
            felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', element)
            if felemRecord:
                fbomRecord = self.getRecord('CFG_FBOM', ['FTYPE_ID', 'FELEM_ID'], [ftypeRecord['FTYPE_ID'], felemRecord['FELEM_ID']])
                if fbomRecord:
                    return fbomRecord, None
            return None, f'{element} is not a valid feature element! use command "getFeature {feature}" to see its elements'

    def lookupFeatureClass(self, featureClass):
        fclassRecord = self.getRecord('CFG_FCLASS', 'FCLASS_CODE', featureClass)
        if fclassRecord:
            return fclassRecord, f'Feature class "{featureClass}" is valid!"'
        else:
            return False, f'Feature class "{featureClass}" is not valid! use command "listReferenceCodes featureClass" to see the list'

    def lookupBehaviorCode(self, behaviorCode):
        if behaviorCode in self.valid_behavior_codes:
            return parseFeatureBehavior(behaviorCode), f'Behavior code "{behaviorCode}" is valid!"'
        else:
            return False, f'Behavior code "{behaviorCode}" is not valid! use command "listReferenceCodes behaviorCodes" to see the list'

    def lookupStandardizeFunction(self, standardizeFunction):
        funcRecord = self.getRecord('CFG_SFUNC', 'SFUNC_CODE', standardizeFunction)
        if funcRecord:
            return funcRecord, f'Standardize function "{standardizeFunction}" is valid!"'
        else:
            return False, f'Standardize function "{standardizeFunction}" is not valid! use command "listStandardizeFunctions" to see the list'

    def lookupExpressionFunction(self, expressionFunction):
        funcRecord = self.getRecord('CFG_EFUNC', 'EFUNC_CODE', expressionFunction)
        if funcRecord:
            return funcRecord, f'Expression function "{expressionFunction}" is valid!"'
        else:
            return False, f'Expression function "{expressionFunction}" is not valid! use command "listExpressionFunctions" to see the list'

    def lookupComparisonFunction(self, comparisonFunction):
        funcRecord = self.getRecord('CFG_CFUNC', 'CFUNC_CODE', comparisonFunction)
        if funcRecord:
            return funcRecord, f'Comparison function "{comparisonFunction}" is valid!"'
        else:
            return False, f'Comparison function "{comparisonFunction}" is not valid! use command "listComparisonFunctions" to see the list'

    def validateDomain(self, attr, value, domain_list):
        if value in domain_list:
            return True, f'{attr} value is valid!'
        else:
            return False, f'{attr} value must be in {json.dumps(domain_list)}'

# ===== data Source commands =====

    def do_listDataSources(self, arg):
        """
        Returns the list of registered data sources

        Syntax:
            listDataSources [optional_search_filter]
        """
        arg = self.check_arg_for_list_format(arg)
        json_lines = []
        for dsrcRecord in sorted(self.getRecordList('CFG_DSRC'), key=lambda k: k['DSRC_ID']):
            if arg and arg.lower() not in str(dsrcRecord).lower():
                continue
            json_lines.append({"id": dsrcRecord['DSRC_ID'], "dataSource": dsrcRecord['DSRC_CODE']})
        self.print_json_lines(json_lines)

    def do_addDataSource(self, arg):
        """
        Register a new data source

        Syntax:
            addDataSource [dataSourceCode]

        Examples:
            addDataSource CUSTOMER

        Caution:
            dataSource codes will automatically be converted to upper case
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"DATASOURCE": arg}
            parmData['ID'] = int(parmData.get('ID', 0))
            parmData['DATASOURCE'] = parmData['DATASOURCE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        dsrcRecord, message = self.lookupDatasource(parmData['DATASOURCE'])
        if dsrcRecord:
            colorize_msg(message, 'warning')
            return

        next_id = self.getNextRecordId('CFG_DSRC', 'DSRC_ID', parmData['ID'])
        if next_id != parmData['ID']:
            colorize_msg('The specified ID is already taken! Remove it to assign the next available', 'error')
            return
        else:
            parmData['ID'] = next_id

        newRecord = {}
        newRecord['DSRC_ID'] = parmData['ID']
        newRecord['DSRC_CODE'] = parmData['DATASOURCE']
        newRecord['DSRC_DESC'] = parmData['DATASOURCE']
        newRecord['DSRC_RELY'] = 1
        newRecord['RETENTION_LEVEL'] = "Remember"
        newRecord['CONVERSATIONAL'] = 'No'
        self.cfgData['G2_CONFIG']['CFG_DSRC'].append(newRecord)
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')
        if self.doDebug:
            debug(newRecord)

    def do_deleteDataSource(self, arg):
        """
        Delete an existing data source

        Syntax:
            deleteDataSource [dataSourceCode]

        Examples:
            deleteDataSource CUSTOMER

        Caution:
            Deleting a data source does not delete its data and you will be prevented from saving if it has data loaded!
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"DATASOURCE": arg}
            parmData['DATASOURCE'] = parmData['DATASOURCE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        if parmData['DATASOURCE'] == 'SEARCH':
            colorize_msg('Cannot delete the SEARCH data source', 'error')
            return

        dsrcRecord, message = self.lookupDatasource(parmData['DATASOURCE'])
        if not dsrcRecord:
            colorize_msg(message, 'warning')

        self.cfgData['G2_CONFIG']['CFG_DSRC'].remove(dsrcRecord)
        colorize_msg(f'Successfully deleted!', 'success')
        self.configUpdated = True

# ===== feature commands =====

    def getFeatureJson(self, ftypeRecord):

        fclassRecord = self.getRecord('CFG_FCLASS', 'FCLASS_ID', ftypeRecord['FCLASS_ID'])

        sfcallRecord = self.getRecord('CFG_SFCALL', 'FTYPE_ID', ftypeRecord['FTYPE_ID'])
        efcallRecord = self.getRecord('CFG_EFCALL', 'FTYPE_ID', ftypeRecord['FTYPE_ID'])
        cfcallRecord = self.getRecord('CFG_CFCALL', 'FTYPE_ID', ftypeRecord['FTYPE_ID'])
        sfuncRecord = self.getRecord('CFG_SFUNC', 'SFUNC_ID', sfcallRecord['SFUNC_ID']) if sfcallRecord else None
        efuncRecord = self.getRecord('CFG_EFUNC', 'EFUNC_ID', efcallRecord['EFUNC_ID']) if efcallRecord else None
        cfuncRecord = self.getRecord('CFG_CFUNC', 'CFUNC_ID', cfcallRecord['CFUNC_ID']) if cfcallRecord else None

        jsonString = '{'
        jsonString += '"id": %s' % ftypeRecord['FTYPE_ID']
        jsonString += ', "feature": "%s"' % ftypeRecord['FTYPE_CODE']
        jsonString += ', "class": "%s"' % fclassRecord['FCLASS_CODE'] if fclassRecord else 'OTHER'
        jsonString += ', "behavior": "%s"' % getFeatureBehavior(ftypeRecord)
        jsonString += ', "anonymize": "%s"' % ('Yes' if ftypeRecord['ANONYMIZE'].upper() == 'YES' else 'No')
        jsonString += ', "candidates": "%s"' % ('Yes' if ftypeRecord['USED_FOR_CAND'].upper() == 'YES' else 'No')
        jsonString += ', "standardize": "%s"' % (sfuncRecord['SFUNC_CODE'] if sfuncRecord else '')
        jsonString += ', "expression": "%s"' % (efuncRecord['EFUNC_CODE'] if efuncRecord else '')
        jsonString += ', "comparison": "%s"' % (cfuncRecord['CFUNC_CODE'] if cfuncRecord else '')
        jsonString += ', "matchKey": "%s"' % ftypeRecord['SHOW_IN_MATCH_KEY']

        elementList = []
        fbomRecordList = self.getRecordList('CFG_FBOM', 'FTYPE_ID', ftypeRecord['FTYPE_ID'])
        for fbomRecord in fbomRecordList:
            felemRecord = self.getRecord('CFG_FELEM', 'FELEM_ID', fbomRecord['FELEM_ID'])
            if not felemRecord:
                elementList.append('ERROR: FELEM_ID %s' % fbomRecord['FELEM_ID'])
                break
            else:
                if efcallRecord or cfcallRecord:
                    efbomRecord = efcallRecord and self.getRecord('CFG_EFBOM', ['EFCALL_ID', 'FTYPE_ID','FELEM_ID'],
                        [efcallRecord['EFCALL_ID'], fbomRecord['FTYPE_ID'],fbomRecord['FELEM_ID']])
                    cfbomRecord = cfcallRecord and self.getRecord('CFG_CFBOM', ['CFCALL_ID', 'FTYPE_ID', 'FELEM_ID'],
                        [cfcallRecord['CFCALL_ID'],fbomRecord['FTYPE_ID'],fbomRecord['FELEM_ID']])
                    elementRecord = {}
                    elementRecord['element'] = felemRecord['FELEM_CODE']
                    elementRecord['expressed'] = 'No' if not efcallRecord or not efbomRecord else 'Yes'
                    elementRecord['compared'] = 'No' if not cfcallRecord or not cfbomRecord else 'Yes'
                    elementRecord['display'] = 'No' if fbomRecord['DISPLAY_LEVEL'] == 0 else 'Yes'
                    elementList.append(elementRecord)
                else:
                    elementList.append(felemRecord['FELEM_CODE'])

        jsonString += ', "elementList": %s' % json.dumps(elementList)
        jsonString += '}'

        return json.loads(jsonString)

    def do_listFeatures(self, arg):
        """
        Returns the list of registered features

        Syntax:
            listFeatures [optional_search_filter]
        """
        arg = self.check_arg_for_list_format(arg)
        json_lines = []
        for ftypeRecord in sorted(self.getRecordList('CFG_FTYPE'), key=lambda k: k['FTYPE_ID']):
            featureJson = self.getFeatureJson(ftypeRecord)
            if arg and arg.lower() not in str(featureJson.lower()):
                continue
            json_lines.append(featureJson)
        self.print_json_lines(json_lines)

    def do_getFeature(self, arg):
        """
        Returns a specific feature's json configuration

        Syntax:
            getFeature [feature]

        Example:
            getFeature NAME
        """
        arg = self.check_arg_for_get_format(arg)
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"FEATURE": arg}
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        ftypeRecord, errorText = self.lookupFeature(parmData['FEATURE'])
        if ftypeRecord:
            self.print_json_record(self.getFeatureJson(ftypeRecord))
        else:
            colorize_msg(errorText, 'error')

    def do_addFeature(self, arg):
        """
        Add an new feature to be used for resolution

        Syntax:
            addFeature [json configuration]

        Examples:
            see listFeatures or getFeature [feature] for examples

        Notes:
            The best way to add a feature is via templateAdd as it adds both the feature and its attributes.
            If you add a feature manually, you will also have to manually add attributes for it!
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['ID'] = int(parmData.get('ID', 0))
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            if 'ELEMENTLIST' not in parmData or len(parmData['ELEMENTLIST']) == 0:
                raise ValueError('An element list is required!')
            if type(parmData['ELEMENTLIST']) is not list:
                raise ValueError('Element must be enclosed in brackets ["element1", "element2"]')
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if already exists
        ftypeRecord, message = self.lookupFeature(parmData['FEATURE'])
        if ftypeRecord:
            colorize_msg(message, 'warning')
            return

        next_id = self.getNextRecordId('CFG_FTYPE', 'FTYPE_ID', parmData['ID'])
        if next_id != parmData['ID']:
            colorize_msg('The specified ID is already taken! Remove it to assign the next available', 'error')
            return
        else:
            parmData['ID'] = next_id

        ftypeID = parmData['ID']
        parmData['ID'] = ftypeID
        parmData['CLASS'] = parmData.get('CLASS', 'OTHER').upper()
        parmData['BEHAVIOR'] = parmData.get('BEHAVIOR', 'FM').upper()

        parmData['CANDIDATES'], message = self.validateDomain('Candidates', parmData.get('CANDIDATES', 'No'), ['Yes', 'No'])
        if not parmData['CANDIDATES']:
            colorize_msg(message, 'error')
            return

        parmData['ANONYMIZE'], message = self.validateDomain('Anonymize', parmData.get('ANONYMIZE', 'No'), ['Yes', 'No'])
        if not parmData['ANONYMIZE']:
            colorize_msg(message, 'error')
            return

        parmData['DERIVED'], message = self.validateDomain('Derived', parmData.get('DERIVED', 'No'), ['Yes', 'No'])
        if not parmData['DERIVED']:
            colorize_msg(message, 'error')
            return

        parmData['HISTORY'], message = self.validateDomain('History', parmData.get('HISTORY', 'Yes'), ['Yes', 'No'])
        if not parmData['HISTORY']:
            colorize_msg(message, 'error')
            return

        matchKeyDefault = 'Yes' if parmData.get('COMPARISON') else 'No'
        parmData['MATCHKEY'], message = self.validateDomain('MatchKey', parmData.get('MATCHKEY', matchKeyDefault), ['Yes', 'No', 'Confirm', 'Denial'])
        if not parmData['MATCHKEY']:
            colorize_msg(message, 'error')
            return

        behaviorData, message = self.lookupBehaviorCode(parmData['BEHAVIOR'])
        if not behaviorData:
            colorize_msg(message, 'error')
            return

        fclassRecord, message = self.lookupFeatureClass(parmData['CLASS'])
        if not fclassRecord:
            colorize_msg(message, 'error')
            return
        fclassID = fclassRecord['FCLASS_ID']

        sfuncID = 0
        if parmData.get('STANDARDIZE'):
            sfuncRecord, message = self.lookupStandardizeFunction(parmData['STANDARDIZE'])
            if not sfuncRecord:
                colorize_msg(message, 'error')
                return
        sfuncID = sfuncRecord['SFUNC_ID']

        efuncID = 0
        if parmData.get('EXPRESSION'):
            efuncRecord, message = self.lookupExpressionFunction(parmData['EXPRESSION'])
            if not efuncRecord:
                colorize_msg(message, 'error')
                return
        efuncID = efuncRecord['EFUNC_ID']

        cfuncID = 0
        if parmData.get('COMPARISON'):
            cfuncRecord, message = self.lookupComparisonFunction(parmData['COMPARISON'])
            if not cfuncRecord:
                colorize_msg(message, 'error')
                return
        cfuncID = cfuncRecord['CFUNC_ID']

        # ensure elements going to express or compare routines
        if efuncID > 0 or cfuncID > 0:
            expressedCnt = comparedCnt = 0
            for element in parmData['ELEMENTLIST']:
                if type(element) == dict:
                    element = dictKeysUpper(element)
                    if 'EXPRESSED' in element and element['EXPRESSED'].upper() == 'YES':
                        expressedCnt += 1
                    if 'COMPARED' in element and element['COMPARED'].upper() == 'YES':
                        comparedCnt += 1
            if efuncID > 0 and expressedCnt == 0:
                colorize_msg('No elements marked "expressed" for expression routine', 'error')
                return
            if cfuncID > 0 and comparedCnt == 0:
                colorize_msg('No elements marked "compared" for comparison routine', 'error')
                return

        # insert the feature
        newRecord = {}
        newRecord['FTYPE_ID'] = int(ftypeID)
        newRecord['FTYPE_CODE'] = parmData['FEATURE']
        newRecord['FTYPE_DESC'] = parmData['FEATURE']
        newRecord['FCLASS_ID'] = fclassID
        newRecord['FTYPE_FREQ'] = behaviorData['FREQUENCY']
        newRecord['FTYPE_EXCL'] = behaviorData['EXCLUSIVITY']
        newRecord['FTYPE_STAB'] = behaviorData['STABILITY']
        newRecord['ANONYMIZE'] = parmData['ANONYMIZE']
        newRecord['DERIVED'] = parmData['DERIVED']
        newRecord['USED_FOR_CAND'] = parmData['CANDIDATES']
        newRecord['SHOW_IN_MATCH_KEY'] = parmData.get('MATCHKEY', 'Yes')
        # somewhat hidden fields in case an engineer wants to specify them
        newRecord['PERSIST_HISTORY'] = parmData.get('HISTORY', 'Yes')
        newRecord['DERIVATION'] = parmData.get('DERIVATION')
        newRecord['VERSION'] = parmData.get('VERSION', 1)
        newRecord['RTYPE_ID'] = parmData.get('RTYPE_ID', 0)

        self.cfgData['G2_CONFIG']['CFG_FTYPE'].append(newRecord)
        if self.doDebug:
            debug(newRecord, 'Feature build')

        # add the standardization call
        sfcallID = 0
        if sfuncID > 0:
            sfcallID = self.getNextRecordId('CFG_SFCALL', 'SFCALL_ID', 0)
            newRecord = {}
            newRecord['SFCALL_ID'] = sfcallID
            newRecord['SFUNC_ID'] = sfuncID
            newRecord['EXEC_ORDER'] = 1
            newRecord['FTYPE_ID'] = ftypeID
            newRecord['FELEM_ID'] = -1
            self.cfgData['G2_CONFIG']['CFG_SFCALL'].append(newRecord)
            if self.doDebug:
                debug(newRecord, 'SFCALL build')

        # add the distinct value call (not supported through here yet)
        dfcallID = 0
        dfuncID = 0
        if dfuncID > 0:
            dfcallID = self.getNextRecordId('CFG_DFCALL', 'DFCALL_ID', 0)
            newRecord = {}
            newRecord['DFCALL_ID'] = dfcallID
            newRecord['DFUNC_ID'] = dfuncID
            newRecord['EXEC_ORDER'] = 1
            newRecord['FTYPE_ID'] = ftypeID
            self.cfgData['G2_CONFIG']['CFG_DFCALL'].append(newRecord)
            if self.doDebug:
                debug(newRecord, 'DFCALL build')

        # add the expression call
        efcallID = 0
        if efuncID > 0:
            efcallID = self.getNextRecordId('CFG_EFCALL', 'EFCALL_ID', 0)
            newRecord = {}
            newRecord['EFCALL_ID'] = efcallID
            newRecord['EFUNC_ID'] = efuncID
            newRecord['EXEC_ORDER'] = 1
            newRecord['FTYPE_ID'] = ftypeID
            newRecord['FELEM_ID'] = -1
            newRecord['EFEAT_FTYPE_ID'] = -1
            newRecord['IS_VIRTUAL'] = 'No'
            self.cfgData['G2_CONFIG']['CFG_EFCALL'].append(newRecord)
            if self.doDebug:
                debug(newRecord, 'EFCALL build')

        # add the comparison call
        cfcallID = 0
        if cfuncID > 0:
            cfcallID = self.getNextRecordId('CFG_CFCALL', 'CFCALL_ID', 0)
            newRecord = {}
            newRecord['CFCALL_ID'] = cfcallID
            newRecord['CFUNC_ID'] = cfuncID
            newRecord['EXEC_ORDER'] = 1
            newRecord['FTYPE_ID'] = ftypeID
            self.cfgData['G2_CONFIG']['CFG_CFCALL'].append(newRecord)
            if self.doDebug:
                debug(newRecord, 'CFCALL build')

        # add elements if not found
        fbomOrder = 0
        for element in parmData['ELEMENTLIST']:
            fbomOrder += 1

            if type(element) == dict:
                elementRecord = dictKeysUpper(element)
                elementRecord['ELEMENT'] = elementRecord['ELEMENT'].upper()
            else:
                elementRecord = {}
                elementRecord['ELEMENT'] = element.upper()
            if 'EXPRESSED' not in elementRecord:
                elementRecord['EXPRESSED'] = 'No'
            if 'COMPARED' not in elementRecord:
                elementRecord['COMPARED'] = 'No'

            felemRecord, message = self.lookupElement(elementRecord['ELEMENT'])
            if felemRecord:
                felemID = felemRecord['FELEM_ID']
            else:
                felemID = self.getNextRecordId('CFG_FELEM', 'FELEM_ID', 0)
                newRecord = {}
                newRecord['FELEM_ID'] = felemID
                newRecord['FELEM_CODE'] = elementRecord['ELEMENT']
                newRecord['FELEM_DESC'] = elementRecord['ELEMENT']
                newRecord['DATA_TYPE'] = 'string'
                newRecord['TOKENIZE'] = 'No'
                self.cfgData['G2_CONFIG']['CFG_FELEM'].append(newRecord)
                if self.doDebug:
                    debug(newRecord, 'FELEM build')

            # add all elements to distinct bom if specified
            if dfcallID > 0:
                newRecord = {}
                newRecord['DFCALL_ID'] = dfcallID
                newRecord['EXEC_ORDER'] = fbomOrder
                newRecord['FTYPE_ID'] = ftypeID
                newRecord['FELEM_ID'] = felemID
                self.cfgData['G2_CONFIG']['CFG_DFBOM'].append(newRecord)
                if self.doDebug:
                    debug(newRecord, 'DFBOM build')

            # add to expression bom if directed to
            if efcallID > 0 and elementRecord['EXPRESSED'].upper() == 'YES':
                newRecord = {}
                newRecord['EFCALL_ID'] = efcallID
                newRecord['EXEC_ORDER'] = fbomOrder
                newRecord['FTYPE_ID'] = ftypeID
                newRecord['FELEM_ID'] = felemID
                newRecord['FELEM_REQ'] = 'Yes'
                self.cfgData['G2_CONFIG']['CFG_EFBOM'].append(newRecord)
                if self.doDebug:
                    debug(newRecord, 'EFBOM build')

            # add to comparison bom if directed to
            if cfcallID > 0 and elementRecord['COMPARED'].upper() == 'YES':
                newRecord = {}
                newRecord['CFCALL_ID'] = cfcallID
                newRecord['EXEC_ORDER'] = fbomOrder
                newRecord['FTYPE_ID'] = ftypeID
                newRecord['FELEM_ID'] = felemID
                self.cfgData['G2_CONFIG']['CFG_CFBOM'].append(newRecord)
                if self.doDebug:
                    debug(newRecord, 'CFBOM build')

            # standardize display_level to just display while maintaining backwards compatibility
            if 'DISPLAY' in elementRecord:
                elementRecord['DISPLAY_LEVEL'] = 1 if elementRecord['DISPLAY'].upper() == 'YES' else 0

            # add to feature bom always
            newRecord = {}
            newRecord['FTYPE_ID'] = ftypeID
            newRecord['FELEM_ID'] = felemID
            newRecord['EXEC_ORDER'] = fbomOrder
            newRecord['DISPLAY_LEVEL'] = elementRecord['DISPLAY_LEVEL'] if 'DISPLAY_LEVEL' in elementRecord else 1
            newRecord['DISPLAY_DELIM'] = elementRecord['DISPLAY_DELIM'] if 'DISPLAY_DELIM' in elementRecord else ''
            newRecord['DERIVED'] = elementRecord['DERIVED'] if 'DERIVED' in elementRecord else 'No'

            self.cfgData['G2_CONFIG']['CFG_FBOM'].append(newRecord)
            if self.doDebug:
                debug(newRecord, 'FBOM build')

        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')

    def do_deleteFeature(self, arg):
        """
        Deletes a feature and its attributes

        Syntax:
            deleteFeature [feature]

        Example:
            deleteFeature PHONE

        Caution:
            Deleting a feature does not delete its data and you will be prevented from saving if it has data loaded!
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"FEATURE": arg}
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(err, 'error')
            return

        if parmData['FEATURE'] in self.lockedFeatureList:
            colorize_msg(f"{parmData['FEATURE']} is a locked feature", 'error')
            return

        ftypeRecord, message = self.lookupFeature(parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg(message, 'warning')
            return

        # also delete all supporting tables
        for fbomRecord in self.getRecordList('CFG_FBOM', 'FTYPE_ID', ftypeRecord['FTYPE_ID']):
            self.cfgData['G2_CONFIG']['CFG_FBOM'].remove(fbomRecord)

        for attrRecord in self.getRecordList('CFG_ATTR', 'FTYPE_CODE', ftypeRecord['FTYPE_CODE']):
            self.cfgData['G2_CONFIG']['CFG_ATTR'].remove(attrRecord)

        for sfcallRecord in self.getRecordList('CFG_SFCALL', 'FTYPE_ID', ftypeRecord['FTYPE_ID']):
            self.cfgData['G2_CONFIG']['CFG_SFCALL'].remove(sfcallRecord)

        for efcallRecord in self.getRecordList('CFG_EFCALL', 'FTYPE_ID', ftypeRecord['FTYPE_ID']):
            for efbomRecord in self.getRecordList('CFG_EFBOM', 'EFCALL_ID', efcallRecord['EFCALL_ID']):
                self.cfgData['G2_CONFIG']['CFG_EFBOM'].remove(efbomRecord)

        for cfcallRecord in self.getRecordList('CFG_CFCALL', 'FTYPE_ID', ftypeRecord['FTYPE_ID']):
            for cfbomRecord in self.getRecordList('CFG_CFBOM', 'CFCALL_ID', cfcallRecord['CFCALL_ID']):
                self.cfgData['G2_CONFIG']['CFG_CFBOM'].remove(cfbomRecord)

        for dfcallRecord in self.getRecordList('CFG_DFCALL', 'FTYPE_ID', ftypeRecord['FTYPE_ID']):
            for dfbomRecord in self.getRecordList('CFG_DFBOM', 'DFCALL_ID', cfcallRecord['DFCALL_ID']):
                self.cfgData['G2_CONFIG']['CFG_DFBOM'].remove(dfbomRecord)
        self.cfgData['G2_CONFIG']['CFG_FTYPE'].remove(ftypeRecord)
        colorize_msg(f'Successfully deleted!', 'success')
        self.configUpdated = True

    def do_setFeature(self, arg):
        """
        Sets configuration parameters for an exiting feature

        Syntax:
            setFeature [partial_json_configuration]

        Examples:
            setFeature {"feature": "NAME", "candidates": "Yes"}
            setFeature {"feature": "MEDICARE_PROVIDER_ID", "behavior": "F1E"}

        Notes:
            You must at least specify the "feature" you want to edit.  Then you can change the following settings
                - candidates
                - behavior
                - anonymize

        Caution:
            Changing anything else requires a delete and re-add of the feature.
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"FEATURE": arg}
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if doesn't exist
        old_ftypeRecord, message = self.lookupFeature(parmData['FEATURE'])
        if not old_ftypeRecord:
            colorize_msg(message, 'warning')
            return

        ftypeRecord = old_ftypeRecord

        # make the updates
        error_cnt = 0
        for parmCode in parmData:
            if parmCode == 'FEATURE':
                continue

            elif parmCode == 'CANDIDATES':
                parmData['CANDIDATES'], message = self.validateDomain('Candidates', parmData.get('CANDIDATES', 'No'), ['Yes', 'No'])
                if not parmData['CANDIDATES']:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['USED_FOR_CAND'] = parmData['CANDIDATES']

            elif parmCode == 'ANONYMIZE':
                parmData['ANONYMIZE'], message = self.validateDomain('Anonymize', parmData.get('ANONYMIZE', 'No'), ['Yes', 'No'])
                if not parmData['ANONYMIZE']:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['ANONYMIZE'] = parmData['ANONYMIZE']

            elif parmCode == 'DERIVED':
                parmData['DERIVED'], message = self.validateDomain('Derived', parmData.get('DERIVED', 'No'), ['Yes', 'No'])
                if not parmData['DERIVED']:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['DERIVED'] = parmData['DERIVED']

            elif parmCode == 'HISTORY':
                parmData['HISTORY'], message = self.validateDomain('History', parmData.get('HISTORY', 'Yes'), ['Yes', 'No'])
                if not parmData['HISTORY']:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['HISTORY'] = parmData['HISTORY']

            elif parmCode == 'MATCHKEY':
                matchKeyDefault = 'Yes' if parmData.get('COMPARISON') else 'No'
                parmData['MATCHKEY'], message = self.validateDomain('MatchKey', parmData.get('MATCHKEY', matchKeyDefault), ['Yes', 'No', 'Confirm', 'Denial'])
                if not parmData['MATCHKEY']:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['MATCHKEY'] = parmData['MATCHKEY']

            elif parmCode == 'BEHAVIOR':
                behaviorData, message = self.lookupBehaviorCode(parmData['BEHAVIOR'])
                if not behaviorData:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['BEHAVIOR'] = parmData['BEHAVIOR']

            elif parmCode == 'CLASS':
                fclassRecord, message = self.lookupFeatureClass(parmData['CLASS'])
                if not fclassRecord:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['FCLASS_ID'] = fclassRecord['FCLASS_ID']

            elif parmCode == 'STANDARDIZE':
                sfuncRecord, message = self.lookupStandardizeFunction(parmData['STANDARDIZE'])
                if not sfuncRecord:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['SFUNC_ID'] = funcRecord['SFUNC_ID']

            elif parmCode == 'EXPRESSION':
                efuncRecord, message = self.lookupExpressionFunction(parmData['EXPRESSION'])
                if not efuncRecord:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                elif not old_ftypeRecord['EFUNC_ID']:
                    colorize_msg('Expression function cannot be added here! use command "addExpressionCall" instead', 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['EFUNC_ID'] = funcRecord['EFUNC_ID']

            elif parmCode == 'COMPARISON':
                cfuncRecord, message = self.lookupComparisonFunction(parmData['COMPARISON'])
                if not cfuncRecord:
                    colorize_msg(message, 'error')
                    error_cnt += 1
                elif not old_ftypeRecord['CFUNC_ID']:
                    colorize_msg('Comparison function cannot be added here! use command "addComparisonCall" instead', 'error')
                    error_cnt += 1
                else:
                    ftypeRecord['CFUNC_ID'] = funcRecord['CFUNC_ID']

            else:
                colorize_msg(f'Cannot set {parmCode} on features!', 'error')

        if error_cnt > 0:
            colorize_msg(f'Errors encountered, feature not updated!', 'warning')
        else:
            self.cfgData['G2_CONFIG']['CFG_FTYPE'].remove(old_ftypeRecord)
            self.cfgData['G2_CONFIG']['CFG_FTYPE'].append(ftypeRecord)
            colorize_msg(f'Successfully updated!', 'success')
            self.configUpdated = True




    def do_addToNamehash(self, arg):
        """
        Add a new feature element to the list composite name keys

        Syntax:
            addToNamehash {"feature": "<feature>", "element": "<element>"}

        Example:
            addToNamehash {"feature": "ADDRESS", "element": "STR_NUM"}

        Notes:
            This command appends an attribute from another feature to the name hash.  In the example above, the street number
            computed by the address parser will be added to the list of composite keys created from name.
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"FEATURE": arg}
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        try:
            nameHasher_efuncID = self.getRecord('CFG_EFUNC', 'EFUNC_CODE', 'NAME_HASHER')['EFUNC_ID']
            nameHasher_efcallID = self.getRecord('CFG_EFCALL', 'EFUNC_ID', nameHasher_efuncID)['EFCALL_ID']
        except Exception:
            nameHasher_efcallID = 0
        if not nameHasher_efcallID:
            colorize_msg('Name hasher function call not found!', 'error')
            return
        ftypeID = -1
        if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0:
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
            if not ftypeRecord:
                colorize_msg('Feature not found!', 'error')
                return
            ftypeID = ftypeRecord['FTYPE_ID']

        felemID = -1
        if 'ELEMENT' in parmData and len(parmData['ELEMENT']) != 0:
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
            felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
            if not felemRecord:
                colorize_msg('Feature element not found!', 'error')
                return
            felemID = felemRecord['FELEM_ID']
        else:
            colorize_msg('A feature element value is required', 'error')
            return

        if ftypeID != -1:
            if not self.getRecord('CFG_FBOM', ['FTYPE_ID', 'FELEM_ID'], [ftypeID, felemID]):
                colorize_msg(f"{parmData['ELEMENT']} is not an element of feature {parmData['FEATURE']}", 'error')
                return

        nameHasher_execOrder = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_EFBOM'])):
            if self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['EFCALL_ID'] == nameHasher_efcallID and \
                    self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['EXEC_ORDER'] > nameHasher_execOrder:
                nameHasher_execOrder = self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['EXEC_ORDER']
            if self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['EFCALL_ID'] == nameHasher_efcallID and \
                    self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['FTYPE_ID'] == ftypeID and \
                    self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['FELEM_ID'] == felemID:
                colorize_msg('Already added to name hash!', 'warning')
                return

        # add record
        newRecord = {}
        newRecord['EFCALL_ID'] = nameHasher_efcallID
        newRecord['EXEC_ORDER'] = nameHasher_execOrder + 1
        newRecord['FTYPE_ID'] = ftypeID
        newRecord['FELEM_ID'] = felemID
        newRecord['FELEM_REQ'] = 'No'
        self.cfgData['G2_CONFIG']['CFG_EFBOM'].append(newRecord)
        if self.doDebug:
            debug(newRecord, 'EFBOM build')

        self.configUpdated = True
        colorize_msg('Successfully added', 'success')

    def do_deleteFromNamehash(self, arg):
        """
        Delete a feature element from the list composite name keys

        Syntax:
            deleteFromNamehash {"feature": "<feature>", "element": "<element>"}

        Example:
            deleteFromNamehash {"feature": "ADDRESS", "element": "STR_NUM"}
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"FEATURE": arg}
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        try:
            nameHasher_efuncID = self.getRecord('CFG_EFUNC', 'EFUNC_CODE', 'NAME_HASHER')['EFUNC_ID']
            nameHasher_efcallID = self.getRecord('CFG_EFCALL', 'EFUNC_ID', nameHasher_efuncID)['EFCALL_ID']
        except Exception:
            nameHasher_efcallID = 0
        if not nameHasher_efcallID:
            colorize_msg('Name hasher function not found!', 'error')
            return

        ftypeID = -1
        if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0:
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
            if not ftypeRecord:
                colorize_msg('Feature not found!', 'error')
                return
            ftypeID = ftypeRecord['FTYPE_ID']

        felemID = -1
        if 'ELEMENT' in parmData and len(parmData['ELEMENT']) != 0:
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
            felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
            if not felemRecord:
                colorize_msg('Feature element not found!', 'error')
                return
            felemID = felemRecord['FELEM_ID']

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_EFBOM']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['EFCALL_ID'] == nameHasher_efcallID and \
                    self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['FTYPE_ID'] == ftypeID and \
                    self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]['FELEM_ID'] == felemID:
                del self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]
                deleteCnt += 1
                self.configUpdated = True
        if deleteCnt == 0:
            colorize_msg('Record not found!', 'warning')
        else:
            colorize_msg('Successfully deleted', 'success')


# ===== attributes section =====

    def getAttributeJson(self, attributeRecord):

        if 'ADVANCED' not in attributeRecord:
            attributeRecord['ADVANCED'] = 'No'
        if 'INTERNAL' not in attributeRecord:
            attributeRecord['INTERNAL'] = 'No'

        jsonString = '{'
        jsonString += '"id": "%s"' % attributeRecord['ATTR_ID']
        jsonString += ', "attribute": "%s"' % attributeRecord['ATTR_CODE']
        jsonString += ', "class": "%s"' % attributeRecord['ATTR_CLASS']
        jsonString += ', "feature": "%s"' % attributeRecord['FTYPE_CODE']
        jsonString += ', "element": "%s"' % attributeRecord['FELEM_CODE']
        jsonString += ', "required": "%s"' % attributeRecord['FELEM_REQ'].title()
        jsonString += ', "default": "%s"' % (attributeRecord['DEFAULT_VALUE'] if attributeRecord['DEFAULT_VALUE'] else "")
        jsonString += ', "advanced": "%s"' % attributeRecord['ADVANCED']
        jsonString += ', "internal": "%s"' % attributeRecord['INTERNAL']
        jsonString += '}'

        return json.loads(jsonString)

    def do_listAttributes(self, arg):
        """
        Returns the list of registered attributes

        Syntax:
            listAttributes [optional_search_filter] [optional_output_format]
        """
        arg = self.check_arg_for_list_format(arg)
        json_lines = []
        for attrRecord in sorted(self.getRecordList('CFG_ATTR'), key=lambda k: k['ATTR_ID']):
            if arg and arg.lower() not in str(attrRecord).lower():
                continue
            json_lines.append(self.getAttributeJson(attrRecord))
        self.print_json_lines(json_lines)

    def do_getAttribute(self, arg):
        """
        Returns a specific attribute's json configuration

        Syntax:
            getAttribute [attribute] [optional_output_format]

        Example:
            getAttribute NAME_FULL json

        Notes:
            If you specify a valid feature, all of its attributes will be displayed
                try: getAttribute PASSPORT jsonl
        """

        # hack to determine if they specified an attribute or a feature so we can potentially set the correct output format
        if arg and len(arg.split()) > 1:
            attrRecords = self.getRecordList('CFG_ATTR', 'ATTR_CODE', arg.split()[0])
            if attrRecords:
                arg = self.check_arg_for_get_format(arg)
            else:
                attrRecords = self.getRecordList('CFG_ATTR', 'FTYPE_CODE', arg.split()[0])
                if attr_records:
                    arg = self.check_arg_for_list_format(arg)
        # end of hack

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"ATTRIBUTE": arg}
            parmData['ATTRIBUTE'] = parmData['ATTRIBUTE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        attrRecords = self.getRecordList('CFG_ATTR', 'ATTR_CODE', parmData['ATTRIBUTE'])
        if not attrRecords: # see if they entered a feature name
            attrRecords = self.getRecordList('CFG_ATTR', 'FTYPE_CODE', parmData['ATTRIBUTE'])
        if not attrRecords:
            colorize_msg('Attribute not found', 'error')
        elif len(attrRecords) == 1:
            self.print_json_record(self.getAttributeJson(attrRecords[0]))
        else:
            json_lines = []
            for attrRecord in sorted(attrRecords, key=lambda k: k['ATTR_ID']):
                json_lines.append(self.getAttributeJson(attrRecord))
            self.print_json_lines(json_lines)

    def do_addAttribute(self, arg):
        """
        Adds a new attribute and maps it to a feature element

        Syntax:
            addAttribute [json configuration]

        Examples:
            see listAttributes or getAttribute [attribute] for examples

        Notes:
            - The best way to add an attribute is via templateAdd as it adds both the feature and its attributes.
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"ATTRIBUTE": arg}
            parmData['ATTRIBUTE'] = parmData['ATTRIBUTE'].upper()
        except (ValueError, KeyError) as e:
            print('\nError with argument(s) or parsing JSON - %s \n' % e)
        else:
            if 'CLASS' in parmData and len(parmData['CLASS']) != 0:
                parmData['CLASS'] = parmData['CLASS'].upper()
                if parmData['CLASS'] not in self.attributeClassList:
                    colorize_msg('Invalid attribute class, type listClasses to see a list of valid attribute classes', 'error')
                    return
            else:
                parmData['CLASS'] = 'OTHER'

            if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0:
                parmData['FEATURE'] = parmData['FEATURE'].upper()
                ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
                if not ftypeRecord:
                    colorize_msg('Feature does not exist', 'error')
                    return
            else:
                parmData['FEATURE'] = None
                ftypeRecord = None

            if 'ELEMENT' in parmData and len(parmData['ELEMENT']) != 0:
                parmData['ELEMENT'] = parmData['ELEMENT'].upper()
                if parmData['ELEMENT'] in ('<PREHASHED>', 'USED_FROM_DT', 'USED_THRU_DT', 'USAGE_TYPE'):
                    felemRecord = parmData['ELEMENT']
                else:
                    felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
                    if not felemRecord:
                        colorize_msg('Element does not exist', 'error')
                        return
                    else:
                        if not self.getRecord('CFG_FBOM', ['FTYPE_ID', 'FELEM_ID'], [ftypeRecord['FTYPE_ID'], felemRecord['FELEM_ID']]):
                            colorize_msg(f"{parmData['ELEMENT']} is not an element of feature {parmData['FEATURE']}", 'error')
                            return
            else:
                parmData['ELEMENT'] = None
                felemRecord = None

            if (ftypeRecord and not felemRecord) or (felemRecord and not ftypeRecord):
                colorize_msg('Must have both a feature and an element if either are supplied', 'error')
                return

            if 'REQUIRED' not in parmData or len(parmData['REQUIRED'].strip()) == 0:
                parmData['REQUIRED'] = 'No'
            else:
                if parmData['REQUIRED'].upper() not in ('YES', 'NO', 'ANY', 'DESIRED'):
                    colorize_msg('required value must be "Yes", "No", "Any" or "Desired"', 'error')
                    return

            if 'DEFAULT' not in parmData:
                parmData['DEFAULT'] = None
            if 'ADVANCED' not in parmData:
                parmData['ADVANCED'] = 'No'
            if 'INTERNAL' not in parmData:
                parmData['INTERNAL'] = 'No'

            maxID = 0
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_ATTR'])):
                if self.cfgData['G2_CONFIG']['CFG_ATTR'][i]['ATTR_CODE'] == parmData['ATTRIBUTE']:
                    colorize_msg('Attribute already exists!', 'warning')
                    return
                if 'ID' in parmData and int(self.cfgData['G2_CONFIG']['CFG_ATTR'][i]['ATTR_ID']) == int(parmData['ID']):
                    colorize_msg('Attribute ID already exists!', 'error')
                    return
                if self.cfgData['G2_CONFIG']['CFG_ATTR'][i]['ATTR_ID'] > maxID:
                    maxID = self.cfgData['G2_CONFIG']['CFG_ATTR'][i]['ATTR_ID']

            if 'ID' not in parmData:
                parmData['ID'] = maxID + 1 if maxID >= 2000 else 2000

            newRecord = {}
            newRecord['ATTR_ID'] = int(parmData['ID'])
            newRecord['ATTR_CODE'] = parmData['ATTRIBUTE']
            newRecord['ATTR_CLASS'] = parmData['CLASS']
            newRecord['FTYPE_CODE'] = parmData['FEATURE']
            newRecord['FELEM_CODE'] = parmData['ELEMENT']
            newRecord['FELEM_REQ'] = parmData['REQUIRED']
            newRecord['DEFAULT_VALUE'] = parmData['DEFAULT']
            newRecord['ADVANCED'] = 'Yes' if parmData['ADVANCED'].upper() == 'YES' else 'No'
            newRecord['INTERNAL'] = 'Yes' if parmData['INTERNAL'].upper() == 'YES' else 'No'
            self.cfgData['G2_CONFIG']['CFG_ATTR'].append(newRecord)
            self.configUpdated = True
            colorize_msg('Successfully added!', 'success')
            if self.doDebug:
                debug(newRecord)

    def do_deleteAttribute(self, arg):
        """
        Deletes an attribute

        Syntax:
            deleteAttribute [attribute]

        Example:
            deleteAttribute PHONE_NUMBER
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"ATTRIBUTE": arg}
            parmData['ATTRIBUTE'] = parmData['ATTRIBUTE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_ATTR']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_ATTR'][i]['ATTR_CODE'] == parmData['ATTRIBUTE']:
                del self.cfgData['G2_CONFIG']['CFG_ATTR'][i]
                deleteCnt += 1
                self.configUpdated = True
        if deleteCnt == 0:
            colorize_msg('Attribute not found!', 'warning')
        else:
            colorize_msg('Successfully deleted', 'success')


# ===== template section =====

    def do_templateAdd(self, arg):
        """
        Adds a feature and its attributes based on a template

        Syntax:
            templateAdd {"feature": "<name>", "template": "<template>", "behavior": "<optional-override>", "comparison": "<optional-override>}

        Examples:
            templateAdd {"feature": "customer_number", "template": "global_id"}
            templateAdd {"feature": "customer_number", "template": "global_id", "behavior": "F1E"}
            templateAdd {"feature": "customer_number", "template": "global_id", "behavior": "F1E", "comparison": "exact_comp"}

        Notes:
            Type "templateAdd List" to get a list of valid templates.\n
        """
        validTemplates = {}
        validTemplates['GLOBAL_ID'] = {'DESCRIPTION': 'globally unique identifier (like an ssn, a credit card, or a medicare_id)',
                                       'BEHAVIOR': ['F1', 'F1E', 'F1ES', 'A1', 'A1E', 'A1ES'],
                                       'CANDIDATES': ['No'],
                                       'STANDARDIZE': ['PARSE_ID'],
                                       'EXPRESSION': ['EXPRESS_ID'],
                                       'COMPARISON': ['ID_COMP', 'EXACT_COMP'],
                                       'FEATURE_CLASS': 'ISSUED_ID',
                                       'ATTRIBUTE_CLASS': 'IDENTIFIER',
                                       'ELEMENTS': [{'element': 'ID_NUM', 'expressed': 'No', 'compared': 'no', 'display': 'Yes'},
                                                    {'element': 'ID_NUM_STD', 'expressed': 'Yes', 'compared': 'yes', 'display': 'No'}],
                                       'ATTRIBUTES': [{'attribute': '<feature>', 'element': 'ID_NUM', 'required': 'Yes'}]}

        validTemplates['STATE_ID'] = {'DESCRIPTION': 'state issued identifier (like a drivers license)',
                                      'BEHAVIOR': ['F1', 'F1E', 'F1ES', 'A1', 'A1E', 'A1ES'],
                                      'CANDIDATES': ['No'],
                                      'STANDARDIZE': ['PARSE_ID'],
                                      'EXPRESSION': ['EXPRESS_ID'],
                                      'COMPARISON': ['ID_COMP'],
                                      'FEATURE_CLASS': 'ISSUED_ID',
                                      'ATTRIBUTE_CLASS': 'IDENTIFIER',
                                      'ELEMENTS': [{'element': 'ID_NUM', 'expressed': 'No', 'compared': 'no', 'display': 'Yes'},
                                                   {'element': 'STATE', 'expressed': 'No', 'compared': 'yes', 'display': 'Yes'},
                                                   {'element': 'ID_NUM_STD', 'expressed': 'Yes', 'compared': 'yes', 'display': 'No'}],
                                      'ATTRIBUTES': [{'attribute': '<feature>_NUMBER', 'element': 'ID_NUM', 'required': 'Yes'},
                                                     {'attribute': '<feature>_STATE', 'element': 'STATE', 'required': 'No'}]}

        validTemplates['COUNTRY_ID'] = {'DESCRIPTION': 'country issued identifier (like a passport)',
                                        'BEHAVIOR': ['F1', 'F1E', 'F1ES', 'A1', 'A1E', 'A1ES'],
                                        'CANDIDATES': ['No'],
                                        'STANDARDIZE': ['PARSE_ID'],
                                        'EXPRESSION': ['EXPRESS_ID'],
                                        'COMPARISON': ['ID_COMP'],
                                        'FEATURE_CLASS': 'ISSUED_ID',
                                        'ATTRIBUTE_CLASS': 'IDENTIFIER',
                                        'ELEMENTS': [{'element': 'ID_NUM', 'expressed': 'No', 'compared': 'no', 'display': 'Yes'},
                                                     {'element': 'COUNTRY', 'expressed': 'No', 'compared': 'yes', 'display': 'Yes'},
                                                     {'element': 'ID_NUM_STD', 'expressed': 'Yes', 'compared': 'yes', 'display': 'No'}],
                                        'ATTRIBUTES': [{'attribute': '<feature>_NUMBER', 'element': 'ID_NUM', 'required': 'Yes'},
                                                       {'attribute': '<feature>_COUNTRY', 'element': 'COUNTRY', 'required': 'No'}]}

        if arg and arg.upper() == 'LIST':
            print()
            for template in validTemplates:
                print('\t', template, '-', validTemplates[template]['DESCRIPTION'])
                print('\t\tbehaviors:', validTemplates[template]['BEHAVIOR'])
                print('\t\tcomparisons:', validTemplates[template]['COMPARISON'])
                print()
            return

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg))
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        feature = parmData['FEATURE'].upper() if 'FEATURE' in parmData else None
        template = parmData['TEMPLATE'].upper() if 'TEMPLATE' in parmData else None
        behavior = parmData['BEHAVIOR'].upper() if 'BEHAVIOR' in parmData else None
        comparison = parmData['COMPARISON'].upper() if 'COMPARISON' in parmData else None

        standardize = parmData['STANDARDIZE'].upper() if 'STANDARDIZE' in parmData else None
        expression = parmData['EXPRESSION'].upper() if 'EXPRESSION' in parmData else None
        candidates = parmData['CANDIDATES'].upper() if 'CANDIDATES' in parmData else None

        if not feature:
            colorize_msg('A new feature name is required', 'error')
            return
        if self.getRecord('CFG_FTYPE', 'FTYPE_CODE', feature):
            colorize_msg('Feature already exists!', 'warning')
            return

        if not template:
            colorize_msg('A valid template name is required', 'error')
            return
        if template not in validTemplates:
            colorize_msg('template name supplied is not valid', 'error')
            return

        if not behavior:
            behavior = validTemplates[template]['BEHAVIOR'][0]
        if behavior not in validTemplates[template]['BEHAVIOR']:
            colorize_msg('behavior code supplied is not valid for template', 'error')
            return

        if not comparison:
            comparison = validTemplates[template]['COMPARISON'][0]
        if comparison not in validTemplates[template]['COMPARISON']:
            colorize_msg('comparison code supplied is not valid for template', 'error')
            return

        if not standardize:
            standardize = validTemplates[template]['STANDARDIZE'][0]
        if standardize not in validTemplates[template]['STANDARDIZE']:
            colorize_msg('standardize code supplied is not valid for template', 'error')
            return

        if not expression:
            expression = validTemplates[template]['EXPRESSION'][0]
        if expression not in validTemplates[template]['EXPRESSION']:
            colorize_msg('expression code supplied is not valid for template', 'error')
            return

        if not candidates:
            candidates = validTemplates[template]['CANDIDATES'][0]
        if candidates not in validTemplates[template]['CANDIDATES']:
            colorize_msg('candidates setting supplied is not valid for template', 'error')
            return

        # values that can't be overridden
        featureClass = validTemplates[template]['FEATURE_CLASS']
        attributeClass = validTemplates[template]['ATTRIBUTE_CLASS']

        # exact comp corrections
        if comparison == 'EXACT_COMP':
            standardize = ''
            expression = ''
            candidates = 'Yes'

        # build the feature
        featureData = {'feature': feature,
                       'behavior': behavior,
                       'class': featureClass,
                       'candidates': candidates,
                       'standardize': standardize,
                       'expression': expression,
                       'comparison': comparison,
                       'elementList': []}
        for elementDict in validTemplates[template]['ELEMENTS']:
            if not expression:
                elementDict['expressed'] = 'No'
            if not standardize:
                if elementDict['display'] == 'Yes':
                    elementDict['compared'] = 'Yes'
                else:
                    elementDict['compared'] = 'No'
            featureData['elementList'].append(elementDict)

        featureParm = json.dumps(featureData)
        colorize_msg(f'addFeature {featureParm}', 'dim')
        self.do_addFeature(featureParm)

        # build the attributes
        for attributeDict in validTemplates[template]['ATTRIBUTES']:
            attributeDict['attribute'] = attributeDict['attribute'].replace('<feature>', feature)

            attributeData = {'attribute': attributeDict['attribute'].upper(),
                             'class': attributeClass,
                             'feature': feature,
                             'element': attributeDict['element'].upper(),
                             'required': attributeDict['required']}

            attributeParm = json.dumps(attributeData)
            colorize_msg(f'addAttribute {attributeParm}', 'dim')
            self.do_addAttribute(attributeParm)

        return


# ===== supporting codes =====

    def do_referenceCodes(self, arg):
        """
        Returns the list of internal reference codes

        Syntax:
            referenceCodes [optional_code_type]

        Notes:
            reference code types include:
                matchLevels
                behaviorCodes
                featureClasses
                attributeClasses
        """
        arg = self.check_arg_for_list_format(arg)
        if arg:
            arg = arg.upper()

        if not arg or arg in 'MATCHLEVELS':
            json_lines = []
            for rtypeRecord in sorted(self.getRecordList('CFG_RTYPE'), key=lambda k: k['RTYPE_ID']):
                if arg and arg.lower() not in str(rtypeRecord).lower():
                    continue
                json_lines.append({"level": rtypeRecord["RTYPE_ID"], "code": rtypeRecord["RTYPE_CODE"],
                                   "class": self.getRecord("CFG_RCLASS", "RCLASS_ID", rtypeRecord["RCLASS_ID"])[
                                       "RCLASS_DESC"]})
            self.print_json_lines(json_lines, 'Match Levels')


        if not arg or arg in 'BEHAVIORCODES':
            json_lines = []
            for code in self.valid_behavior_codes:
                if code.startswith('NAME'):
                    desc = 'Controlled behavior used only for names'
                else:
                    if code.startswith('A1'):
                        desc = 'Absolutely 1'
                    elif code.startswith('F1'):
                        desc = 'Frequency 1'
                    elif code.startswith('FF'):
                        desc = 'Frequency 1'
                    elif code.startswith('FM'):
                        desc = 'Frequency many'
                    elif code.startswith('FVM'):
                        desc = 'Frequency very many'
                    else:
                        desc = 'unknown'
                    if 'E' in code:
                        desc += ', exclusive'
                    if 'S' in code:
                        desc += ' and stable'
                json_lines.append({"behaviorCode": code, "behaviorDescription": desc})
            self.print_json_lines(json_lines, 'Behavior Codes')

        if not arg or arg in 'FEATURECLASS':
            json_lines = []
            for fclassRecord in sorted(self.getRecordList('CFG_FCLASS'), key=lambda k: k['FCLASS_ID']):
                json_lines.append({"class": fclassRecord['FCLASS_CODE'], "id": fclassRecord['FCLASS_ID']})
            self.print_json_lines(json_lines, 'Feature Classes')

        if not arg or arg in 'ATTRIBUTECLASS':
            json_lines = []
            for attrClass in self.attributeClassList:
                json_lines.append({"attributeClass": attrClass})
            self.print_json_lines(json_lines, 'Attribute Classes')

    def do_listStandarizeFunctions(self, arg):
        """
        Returns the list of standardization functions

        Syntax:
            listStandarizeFunctions [optional_search_filter] [optional_output_format]
        """
        arg = self.check_arg_for_list_format(arg)
        json_lines = []
        for funcRecord in sorted(self.getRecordList('CFG_SFUNC'), key=lambda k: k['SFUNC_ID']):
            if arg and arg.lower() not in str(funcRecord).lower():
                continue
            json_lines.append({"id": funcRecord["SFUNC_ID"], "function": funcRecord["SFUNC_CODE"], \
                "connectStr": funcRecord["CONNECT_STR"]})
        if json_lines:
            self.print_json_lines(json_lines)

    def do_listExpressionFunctions(self, arg):
        """
        Returns the list of expression functions

        Syntax:
            listExpressionFuncstions [optional_search_filter] [optional_output_format]
        """
        arg = self.check_arg_for_list_format(arg)
        json_lines = []
        for funcRecord in sorted(self.getRecordList('CFG_EFUNC'), key=lambda k: k['EFUNC_ID']):
            if arg and arg.lower() not in str(funcRecord).lower():
                continue
            json_lines.append({"id": funcRecord["EFUNC_ID"], "function": funcRecord["EFUNC_CODE"], \
                "connectStr": funcRecord["CONNECT_STR"]})
        if json_lines:
            self.print_json_lines(json_lines)

        return

    def do_listComparisonFunctions(self, arg):
        """
        Returns the list of comparison functions

        Syntax:
            listComparisonFunctions [optional_search_filter] [optional_output_format]
        """
        arg = self.check_arg_for_list_format(arg)
        json_lines = []
        for funcRecord in sorted(self.getRecordList('CFG_CFUNC'), key=lambda k: k['CFUNC_ID']):
            if arg and arg.lower() not in str(funcRecord).lower():
                continue
            json_lines.append({"id": funcRecord["CFUNC_ID"], "function": funcRecord["CFUNC_CODE"], \
                "connectStr": funcRecord["CONNECT_STR"],\
                "anonSupport": funcRecord["ANON_SUPPORT"],\
                "language": funcRecord["LANGUAGE"],\
                "javaClassName": funcRecord["JAVA_CLASS_NAME"]})
        if json_lines:
            self.print_json_lines(json_lines)

        return

    def do_listComparisonThresholds(self, arg):
        """
        Returns the list of thresholds by comparison function return value

        Syntax:
            listComparisonThresholds [optional_search_filter] [optional_output_format]
        """
        arg = self.check_arg_for_list_format(arg)
        json_lines = []
        for funcRecord in sorted(self.getRecordList('CFG_CFUNC'), key=lambda k: k['CFUNC_ID']):
            if arg and arg.lower() not in str(funcRecord).lower():
                continue
            for cfrtnRecord in sorted(self.getRecordList('CFG_CFRTN', 'CFUNC_ID', funcRecord['CFUNC_ID']),
                                      key=lambda k: (k['CFUNC_ID'], k['FTYPE_ID'], k['CFRTN_ID'])):

                if cfrtnRecord.get("FTYPE_ID", 0) != 0:
                    ftypeCode = self.getRecord("CFG_FTYPE", "FTYPE_ID", cfrtnRecord["FTYPE_ID"])["FTYPE_CODE"]
                else:
                    ftypeCode = 'all'

                json_lines.append({"id": cfrtnRecord["CFRTN_ID"],
                                   "function": funcRecord["CFUNC_CODE"],
                                   "scoreName": cfrtnRecord["CFUNC_RTNVAL"],
                                   "feature": ftypeCode,
                                   "sameScore": cfrtnRecord["SAME_SCORE"],
                                   "closeScore": cfrtnRecord["CLOSE_SCORE"],
                                   "likelyScore": cfrtnRecord["LIKELY_SCORE"],
                                   "plausibleScore": cfrtnRecord["PLAUSIBLE_SCORE"],
                                   "unlikelyScore": cfrtnRecord["UN_LIKELY_SCORE"]})
        if json_lines:
            self.print_json_lines(json_lines)
        print()

    def do_addStandardizeFunction(self, arg):
        """
        Adds a new standardization function

        Syntax:
            addStandardizeFunc {"function":"<function_name>", "connectStr":"<plugin_base_name>"}

        Example:
            addStandardizeFunc {"function":"STANDARDIZE_COUNTRY", "connectStr":"g2StdCountry"}

        Caution:
            Added a new function requires a plugin to be programmed!
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FUNCTION'] = parmData['FUNCTION'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        if self.getRecord('CFG_SFUNC', 'SFUNC_CODE', parmData['FUNCTION']):
            colorize_msg('Function already exists!', 'warning')
            return

        if not parmData.get('FUNCLIB'):
            parmData['FUNCLIB'] = 'g2func_lib'
        if not parmData.get('VERSION'):
            parmData['VERSION'] = '1'
        if not parmData.get('CONNECTSTR'):
            colorize_msg('ConnectStr must be specified.', 'error')
            return

        maxID = []
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_SFUNC'])):
            maxID.append(self.cfgData['G2_CONFIG']['CFG_SFUNC'][i]['SFUNC_ID'])

        sfuncID = 0
        if 'ID' in parmData:
            sfuncID = int(parmData['ID'])
        else:
            sfuncID = max(maxID) + 1 if max(maxID) >= 1000 else 1000

        newRecord = {}
        newRecord['SFUNC_ID'] = sfuncID
        newRecord['SFUNC_CODE'] = parmData['FUNCTION']
        newRecord['SFUNC_DESC'] = parmData['FUNCTION']
        newRecord['FUNC_LIB'] = parmData['FUNCLIB']
        newRecord['FUNC_VER'] = parmData['VERSION']
        newRecord['CONNECT_STR'] = parmData['CONNECTSTR']
        self.cfgData['G2_CONFIG']['CFG_SFUNC'].append(newRecord)
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')
        if self.doDebug:
            debug(newRecord)

    def do_addExpressionFunction(self, arg):
        """
        Adds a new expression function

        Syntax:
            addExpressionFunc {"function":"<function_name>", "connectStr":"<plugin_base_name>"}

        Example:
            addExpressionFunc {"function":"FEAT_BUILDER", "connectStr":"g2FeatBuilder"}

        Caution:
            Adding a new function requires a plugin to be programmed!
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FUNCTION'] = parmData['FUNCTION'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        if self.getRecord('CFG_EFUNC', 'EFUNC_CODE', parmData['FUNCTION']):
            colorize_msg('Function already exists!', 'warning')
            return

        if not parmData.get('FUNCLIB'):
            parmData['FUNCLIB'] = 'g2func_lib'
        if not parmData.get('VERSION'):
            parmData['VERSION'] = '1'
        if not parmData.get('CONNECTSTR'):
            colorize_msg('ConnectStr must be specified.', 'error')
            return

        maxID = []
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_EFUNC'])):
            maxID.append(self.cfgData['G2_CONFIG']['CFG_EFUNC'][i]['EFUNC_ID'])

        efuncID = 0
        if 'ID' in parmData:
            efuncID = int(parmData['ID'])
        else:
            efuncID = max(maxID) + 1 if max(maxID) >= 1000 else 1000

        newRecord = {}
        newRecord['EFUNC_ID'] = efuncID
        newRecord['EFUNC_CODE'] = parmData['FUNCTION']
        newRecord['EFUNC_DESC'] = parmData['FUNCTION']
        newRecord['FUNC_LIB'] = parmData['FUNCLIB']
        newRecord['FUNC_VER'] = parmData['VERSION']
        newRecord['CONNECT_STR'] = parmData['CONNECTSTR']
        self.cfgData['G2_CONFIG']['CFG_EFUNC'].append(newRecord)
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')
        if self.doDebug:
            debug(newRecord)

    def do_addComparisonFunction(self, arg):
        """
        Adds a new comparison function

        Syntax:
            addComparisonFunc {"function":"<function_name>", "connectStr":"<plugin_base_name>"}

        Example:
            addComparisonFunc {"function":"EMAIL_COMP", "connectStr":"g2EmailComp"}

        Caution:
            Adding a new function requires a plugin to be programmed!
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FUNCTION'] = parmData['FUNCTION'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        if self.getRecord('CFG_CFUNC', 'CFUNC_CODE', parmData['FUNCTION']):
            colorize_msg('Function already exists!', 'warning')
            return

        if not parmData.get('FUNCLIB'):
            parmData['FUNCLIB'] = 'g2func_lib'
        if not parmData.get('VERSION'):
            parmData['VERSION'] = '1'
        if not parmData.get('CONNECTSTR'):
            colorize_msg('ConnectStr must be specified.', 'error')
            return
        if not parmData.get('ANONSUPPORT'):
            parmData['ANONSUPPORT'] = 'No'
        if not parmData.get('LANGUAGE'):
            parmData['LANGUAGE'] = ''
        if not parmData.get('JAVACLASSNAME'):
            parmData['JAVACLASSNAME'] = ''

        maxID = []
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFUNC'])):
            maxID.append(self.cfgData['G2_CONFIG']['CFG_CFUNC'][i]['CFUNC_ID'])

        cfuncID = 0
        if 'ID' in parmData:
            cfuncID = int(parmData['ID'])
        else:
            cfuncID = max(maxID) + 1 if max(maxID) >= 1000 else 1000

        newRecord = {}
        newRecord['CFUNC_ID'] = cfuncID
        newRecord['CFUNC_CODE'] = parmData['FUNCTION']
        newRecord['CFUNC_DESC'] = parmData['FUNCTION']
        newRecord['FUNC_LIB'] = parmData['FUNCLIB']
        newRecord['FUNC_VER'] = parmData['VERSION']
        newRecord['CONNECT_STR'] = parmData['CONNECTSTR']
        newRecord['ANON_SUPPORT'] = parmData['ANONSUPPORT']
        newRecord['LANGUAGE'] = parmData['LANGUAGE']
        newRecord['JAVA_CLASS_NAME'] = parmData['JAVACLASSNAME']
        self.cfgData['G2_CONFIG']['CFG_CFUNC'].append(newRecord)
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')
        if self.doDebug:
            debug(newRecord)

    def do_addComparisonThreshold(self, arg):
        """
        Adds a new comparison function threshold setting

        Syntax:
            addComparisonThreshold [json configuration]

        Notes:
            - You can listComparisonThresholds to see what the json configuration is.
            - The best way to change one is to capture it's json from the list, then delete and re-add it.
            - You can override the thresholds for specific features by specifying the specific feature instead of all.
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FUNCTION'] = parmData['FUNCTION'].upper()
            parmData['SCORENAME'] = parmData['SCORENAME'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        cfuncRecord = self.getRecord('CFG_CFUNC', 'CFUNC_CODE', parmData['FUNCTION'])
        if not cfuncRecord:
            colorize_msg('Function does not exist!', 'error')
            return
        cfuncID = cfuncRecord['CFUNC_ID']

        ftypeID = 0
        if 'FEATURE' in parmData and parmData['FEATURE'].upper() != 'ALL':
            ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
            if not ftypeRecord:
                colorize_msg('Feature does not exist!', 'error')
                return
            ftypeID = ftypeRecord['FTYPE_ID']

        #  check for duplicated return codes
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFRTN']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['CFUNC_ID'] == cfuncID and \
                    self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['FTYPE_ID'] == ftypeID and \
                    self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['CFUNC_RTNVAL'] == parmData['SCORENAME']:
                colorize_msg('Comparison function return value for feature already exists!', 'warning')
                return

            # just remove the id if duplicated.  They likely just cut and pasted it.
            if self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['CFRTN_ID'] == parmData.get('ID', 0):
                parmData['ID'] = 0

        maxID = []
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFRTN'])):
            maxID.append(self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['CFRTN_ID'])

        cfrtnID = 0
        if parmData.get('ID', 0) != 0:
            cfrtnID = int(parmData['ID'])
        else:
            cfrtnID = max(maxID) + 1 if max(maxID) >= 1000 else 1000

        execOrder = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFRTN'])):
            if self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['CFUNC_ID'] == cfuncID and self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['FTYPE_ID'] == ftypeID:
                if self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['EXEC_ORDER'] > execOrder:
                    execOrder = self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['EXEC_ORDER']
        execOrder = execOrder + 1

        sameScore = 100
        closeScore = 90
        likelyScore = 80
        plausibleScore = 70
        unlikelyScore = 60

        if 'SAMESCORE' in parmData:
            sameScore = int(parmData['SAMESCORE'])
        if 'CLOSESCORE' in parmData:
            closeScore = int(parmData['CLOSESCORE'])
        if 'LIKELYSCORE' in parmData:
            likelyScore = int(parmData['LIKELYSCORE'])
        if 'PLAUSIBLESCORE' in parmData:
            plausibleScore = int(parmData['PLAUSIBLESCORE'])
        if 'UNLIKELYSCORE' in parmData:
            unlikelyScore = int(parmData['UNLIKELYSCORE'])

        newRecord = {}
        newRecord['CFRTN_ID'] = cfrtnID
        newRecord['CFUNC_ID'] = cfuncID
        newRecord['FTYPE_ID'] = ftypeID
        newRecord['CFUNC_RTNVAL'] = parmData['SCORENAME']
        newRecord['EXEC_ORDER'] = execOrder
        newRecord['SAME_SCORE'] = sameScore
        newRecord['CLOSE_SCORE'] = closeScore
        newRecord['LIKELY_SCORE'] = likelyScore
        newRecord['PLAUSIBLE_SCORE'] = plausibleScore
        newRecord['UN_LIKELY_SCORE'] = unlikelyScore
        self.cfgData['G2_CONFIG']['CFG_CFRTN'].append(newRecord)
        self.configUpdated = True
        colorize_msg('Comparison threshold Successfully added!', 'success')
        if self.doDebug:
            debug(newRecord)

    def do_deleteComparisonThreshold(self, arg):
        """
        Deletes a comparision threshold

        Syntax:
           deleteComparisonThreshold [id]
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"ID": int(arg)}
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFRTN']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]['CFRTN_ID'] == parmData['ID']:
                del self.cfgData['G2_CONFIG']['CFG_CFRTN'][i]
                deleteCnt += 1
                self.configUpdated = True
        if deleteCnt == 0:
            colorize_msg('Record not found', 'caution')
        else:
            colorize_msg('Successfully deleted!', 'success')


# ===== element commands =====

    def getElementJson(self, elementRecord):
        jsonString = '{'
        jsonString += '"id": "%s"' % elementRecord['FELEM_ID']
        jsonString += ', "id": "%s"' % elementRecord['FELEM_CODE']
        jsonString += ', "datatype": "%s"' % elementRecord['DATA_TYPE']
        jsonString += ', "tokenize": "%s"' % elementRecord['TOKENIZE']
        jsonString += '}'

        return json.loads(jsonString)


    def do_listElements(self, arg):
        """
        Returns the list of feature elements

        Syntax:
            listElements [optional_search_filter] [optional_output_format]
        """
        arg = self.check_arg_for_list_format(arg)
        json_lines = []
        for felemRecord in sorted(self.getRecordList('CFG_FELEM'), key=lambda k: k['FELEM_ID']):
            if arg and arg.lower() not in str(felemRecord).lower():
                continue
            json_lines.append(self.getElementJson(felemRecord))
        self.print_json_lines(json_lines)

    def do_getElement(self, arg):
        """\ngetElement [element_name]\n"""

        arg = self.check_arg_for_get_format(arg)
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"ELEMENT": arg}
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
        if not felemRecord:
            colorize_msg('Element not found!', 'error')
        else:
            self.print_json_record(self.getElementJson(felemRecord))

    def do_addElement(self, arg):
        """
        \n\taddElement {"element": "<element_name>"}
        \n\n\taddElement {"element": "<element_name>", "tokenize": "no", "datatype": "no"}
        \n\n\tFor additional example structures, use getFeature or listFeatures\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"ELEMENT": arg}
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        if self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT']):
            colorize_msg('Element already exists!', 'error')
            return
        else:

            # default for missing values
            if 'DATATYPE' not in parmData or len(parmData['DATATYPE'].strip()) == 0:
                parmData['DATATYPE'] = 'string'
            else:
                if parmData['DATATYPE'].upper() not in ('DATE', 'DATETIME', 'JSON', 'NUMBER', 'STRING'):
                    colorize_msg('dataType must be DATE, DATETIME, JSON, NUMBER, or STRING', 'error')
                    return
                parmData['DATATYPE'] = parmData['DATATYPE'].lower()

            if 'TOKENIZE' not in parmData or len(parmData['TOKENIZE'].strip()) == 0:
                parmData['TOKENIZE'] = 'No'
            else:
                if parmData['TOKENIZE'] not in ('0', '1', 'No', 'Yes'):
                    colorize_msg('tokenize value must be Yes or No', 'error')
                    return

            maxID = []
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_FELEM'])):
                maxID.append(self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_ID'])

            if 'ID' in parmData:
                felemID = int(parmData['ID'])
            else:
                felemID = max(maxID) + 1 if max(maxID) >= 1000 else 1000

            newRecord = {}
            newRecord['FELEM_ID'] = felemID
            newRecord['FELEM_CODE'] = parmData['ELEMENT']
            newRecord['FELEM_DESC'] = parmData['ELEMENT']
            newRecord['TOKENIZE'] = parmData['TOKENIZE']
            newRecord['DATA_TYPE'] = parmData['DATATYPE']
            self.cfgData['G2_CONFIG']['CFG_FELEM'].append(newRecord)
            self.configUpdated = True
            colorize_msg('Successfully added!', 'success')
            if self.doDebug:
                debug(newRecord)

    def do_deleteElement(self, arg):
        """\ndeleteElement {"feature": "<feature_name>", "element": "<element_name>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"ELEMENT": arg}
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
        if not felemRecord:
            colorize_msg('Element does not exist: %s. Use listElements to see valid elements.' % parmData['ELEMENT'],
                              'B')
            return

        usedIn = []
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_FBOM'])):
            if int(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FELEM_ID']) == felemRecord['FELEM_ID']:
                for j in range(len(self.cfgData['G2_CONFIG']['CFG_FTYPE'])):
                    if int(self.cfgData['G2_CONFIG']['CFG_FTYPE'][j]['FTYPE_ID']) == \
                            self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FTYPE_ID']:
                        usedIn.append(self.cfgData['G2_CONFIG']['CFG_FTYPE'][j]['FTYPE_CODE'])
        if usedIn:
            colorize_msg(
                'Can\'t delete %s, it is used in these feature(s): %s' % (parmData['ELEMENT'], usedIn), 'B')
            return
        else:
            deleteCnt = 0
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_FELEM'])):
                if int(self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_ID']) == felemRecord['FELEM_ID']:
                    del self.cfgData['G2_CONFIG']['CFG_FELEM'][i]
                    deleteCnt = 1
                    self.configUpdated = True
                    break

            if deleteCnt == 0:
                print('\nRecord not found!\n')
            else:
                colorize_msg('Successfully deleted!', 'success')


    # Compatibility version commands

    def do_verifyCompatibilityVersion(self, arg):
        """
        Verify if the current configuration is compatible with a specific version number

        Examples:
            verifyCompatibilityVersion {"expectedVersion": "2"}
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg))
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        this_version = self.cfgData['G2_CONFIG']['CONFIG_BASE_VERSION']['COMPATIBILITY_VERSION']['CONFIG_VERSION']
        if this_version != parmData['EXPECTEDVERSION']:
            colorize_msg(f"Incompatible! This is version {this_version}", 'error')
            if self.isInteractive is False:
                raise Exception('Incorrect compatibility version.')
        else:
            colorize_msg(f"This version is compatible", 'success')

    def do_updateCompatibilityVersion(self, arg):
        """
        Update the compatiblilty version of this configuration

        Examples:
            updateCompatibilityVersion {"fromVersion": "1", "toVersion": "2"}
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = dictKeysUpper(json.loads(arg))
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        this_version = self.cfgData['G2_CONFIG']['CONFIG_BASE_VERSION']['COMPATIBILITY_VERSION']['CONFIG_VERSION']
        if this_version != parmData['FROMVERSION']:
            colorize_msg(f"From version mismatch. This is version {this_version}", 'error')
            return

        self.cfgData['G2_CONFIG']['CONFIG_BASE_VERSION']['COMPATIBILITY_VERSION']['CONFIG_VERSION'] = parmData['TOVERSION']
        self.configUpdated = True
        colorize_msg('Compatibility version successfully changed!', 'success')

    def do_getCompatibilityVersion(self, arg):
        """
        Retrive the compatiblity version of this configuration

        Syntax:
            getCompatibilityVersion
        """
        try:
            this_version = self.cfgData['G2_CONFIG']['CONFIG_BASE_VERSION']['COMPATIBILITY_VERSION']['CONFIG_VERSION']
            colorize_msg(f'Compatibility version is {this_version}', 'success')
        except KeyError:
            colorize_msg('Could not retrieve compatibility version', 'error')


# ===== to be deprecated =====

    def do_addStandardizeFunc(self, arg):
        self.do_addStandardizeFunction(arg)

    def do_addExpressionFunc(self, arg):
        self.do_addExpressionFunction(arg)

    def do_addComparisonFunc(self, arg):
        self.do_addComparisonFunction(arg)

    def do_addFeatureComparisonElement(self, arg):
        """\naddFeatureComparisonElement {"feature": "<feature_name>", "element": "<element_name>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if it doesn't exist
        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg('Feature not found!', 'error')
            return
        ftypeID = ftypeRecord['FTYPE_ID']

        # lookup element and error if it doesn't exist
        felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
        if not felemRecord:
            colorize_msg('Element not found!', 'error')
            return
        felemID = felemRecord['FELEM_ID']

        # find the comparison function call
        cfcallRecord = self.getRecord('CFG_CFCALL', 'FTYPE_ID', ftypeID)
        if not cfcallRecord:
            colorize_msg('Comparison function for feature not found!', 'error')
            return
        cfcallID = cfcallRecord['CFCALL_ID']

        # check to see if the element is already in the feature
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFBOM']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_CFBOM'][i]['CFCALL_ID'] == cfcallID and \
                    self.cfgData['G2_CONFIG']['CFG_CFBOM'][i]['FELEM_ID'] == felemID:
                colorize_msg('Comparison function for feature already contains element!', 'error')
                return

        # add the feature element
        cfbomExecOrder = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFBOM'])):
            if self.cfgData['G2_CONFIG']['CFG_CFBOM'][i]['CFCALL_ID'] == cfcallID:
                if self.cfgData['G2_CONFIG']['CFG_CFBOM'][i]['EXEC_ORDER'] > cfbomExecOrder:
                    cfbomExecOrder = self.cfgData['G2_CONFIG']['CFG_CFBOM'][i]['EXEC_ORDER']
        cfbomExecOrder = cfbomExecOrder + 1
        newRecord = {}
        newRecord['CFCALL_ID'] = cfcallID
        newRecord['EXEC_ORDER'] = cfbomExecOrder
        newRecord['FTYPE_ID'] = ftypeID
        newRecord['FELEM_ID'] = felemID
        self.cfgData['G2_CONFIG']['CFG_CFBOM'].append(newRecord)
        if self.doDebug:
            debug(newRecord, 'CFBOM build')

        # we made it!
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')

    def do_addFeatureDistinctCallElement(self, arg):
        """\naddFeatureDistinctCallElement {"feature": "<feature_name>", "element": "<element_name>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if it doesn't exist
        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg('Feature not found!', 'error')
            return
        ftypeID = ftypeRecord['FTYPE_ID']

        # lookup element and error if it doesn't exist
        felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
        if not felemRecord:
            colorize_msg('Element not found!', 'error')
            return
        felemID = felemRecord['FELEM_ID']

        # find the distinct function call
        dfcallRecord = self.getRecord('CFG_DFCALL', 'FTYPE_ID', ftypeID)
        if not dfcallRecord:
            colorize_msg('Distinct function for feature not found!', 'error')
            return
        dfcallID = dfcallRecord['DFCALL_ID']

        # check to see if the element is already in the feature
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_DFBOM']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_DFBOM'][i]['DFCALL_ID'] == dfcallID and \
                    self.cfgData['G2_CONFIG']['CFG_DFBOM'][i]['FELEM_ID'] == felemID:
                colorize_msg('Distinct function call already contains element!', 'warning')
                return

        # add the feature element
        dfbomExecOrder = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_DFBOM'])):
            if self.cfgData['G2_CONFIG']['CFG_DFBOM'][i]['DFCALL_ID'] == dfcallID:
                if self.cfgData['G2_CONFIG']['CFG_DFBOM'][i]['EXEC_ORDER'] > dfbomExecOrder:
                    dfbomExecOrder = self.cfgData['G2_CONFIG']['CFG_DFBOM'][i]['EXEC_ORDER']
        dfbomExecOrder = dfbomExecOrder + 1
        newRecord = {}
        newRecord['DFCALL_ID'] = dfcallID
        newRecord['EXEC_ORDER'] = dfbomExecOrder
        newRecord['FTYPE_ID'] = ftypeID
        newRecord['FELEM_ID'] = felemID
        self.cfgData['G2_CONFIG']['CFG_DFBOM'].append(newRecord)
        if self.doDebug:
            debug(newRecord, 'DFBOM build')

        # we made it!
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')

    def do_addFeatureComparison(self, arg):
        """
        \n\taddFeatureComparison {"feature": "<feature_name>", "comparison": "<comparison_function>", "elementList": ["<element_detail(s)"]}
        '\n\n\taddFeatureComparison {"feature":"testFeat", "comparison":"exact_comp", "elementlist": [{"element": "test"}]}\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            if 'ELEMENTLIST' not in parmData or len(parmData['ELEMENTLIST']) == 0:
                raise ValueError('Element list is required!')
            if type(parmData['ELEMENTLIST']) is not list:
                raise ValueError(
                    'Element list should be specified as: "elementlist": ["<values>"]\n\n\tNote the [ and ]')
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if it doesn't exist
        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg('Feature not found!', 'error')
            return
        ftypeID = ftypeRecord['FTYPE_ID']

        cfuncID = 0  # comparison function
        if 'COMPARISON' not in parmData or len(parmData['COMPARISON']) == 0:
            colorize_msg('Comparison function not specified!', 'error')
            return
        parmData['COMPARISON'] = parmData['COMPARISON'].upper()
        cfuncRecord = self.getRecord('CFG_CFUNC', 'CFUNC_CODE', parmData['COMPARISON'])
        if cfuncRecord:
            cfuncID = cfuncRecord['CFUNC_ID']
        else:
            colorize_msg('Invalid comparison function code', 'error')
            return

        # ensure we have elements
        elementCount = 0
        for element in parmData['ELEMENTLIST']:
            elementCount += 1
            elementRecord = dictKeysUpper(element)
            elementRecord['ELEMENT'] = elementRecord['ELEMENT'].upper()
            felemID = 0
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_FELEM'])):
                if self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_CODE'] == elementRecord['ELEMENT']:
                    felemID = self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_ID']
                    break
            if felemID == 0:
                colorize_msg(f"Element does not exist: {elementRecord['ELEMENT']}", 'error')
                return
        if elementCount == 0:
            colorize_msg('No elements specified for comparison', 'error')
            return

        # add the comparison call
        cfcallID = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFCALL'])):
            if self.cfgData['G2_CONFIG']['CFG_CFCALL'][i]['CFCALL_ID'] > cfcallID:
                cfcallID = self.cfgData['G2_CONFIG']['CFG_CFCALL'][i]['CFCALL_ID']
        cfcallID = cfcallID + 1 if cfcallID >= 1000 else 1000
        newRecord = {}
        newRecord['CFCALL_ID'] = cfcallID
        newRecord['CFUNC_ID'] = cfuncID
        newRecord['EXEC_ORDER'] = 1
        newRecord['FTYPE_ID'] = ftypeID
        self.cfgData['G2_CONFIG']['CFG_CFCALL'].append(newRecord)
        if self.doDebug:
            debug(newRecord, 'CFCALL build')

        # add elements
        cfbomOrder = 0
        for element in parmData['ELEMENTLIST']:
            cfbomOrder += 1
            elementRecord = dictKeysUpper(element)

            # lookup
            elementRecord['ELEMENT'] = elementRecord['ELEMENT'].upper()
            felemID = 0
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_FELEM'])):
                if self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_CODE'] == elementRecord['ELEMENT']:
                    felemID = self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_ID']
                    break

            # add to comparison bom if any
            newRecord = {}
            newRecord['CFCALL_ID'] = cfcallID
            newRecord['EXEC_ORDER'] = cfbomOrder
            newRecord['FTYPE_ID'] = ftypeID
            newRecord['FELEM_ID'] = felemID
            self.cfgData['G2_CONFIG']['CFG_CFBOM'].append(newRecord)
            if self.doDebug:
                debug(newRecord, 'CFBOM build')

        # we made it!
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')

    def do_setFeatureComparison(self, arg):
        """\nsetFeatureComparison {"feature": "<feature_name>", "comparison": "<comparison_function>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if it doesn't exist
        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg('Feature not found!', 'error')
            return
        ftypeID = ftypeRecord['FTYPE_ID']

        cfuncID = 0  # comparison function
        if 'COMPARISON' not in parmData or len(parmData['COMPARISON']) == 0:
            colorize_msg('Comparison function not specified!', 'error')
            return
        parmData['COMPARISON'] = parmData['COMPARISON'].upper()
        cfuncRecord = self.getRecord('CFG_CFUNC', 'CFUNC_CODE', parmData['COMPARISON'])
        if cfuncRecord:
            cfuncID = cfuncRecord['CFUNC_ID']
        else:
            colorize_msg('Invalid comparison function code', 'error')
            return

        # set the comparison call
        modificationMade = False
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_CFCALL'])):
            if self.cfgData['G2_CONFIG']['CFG_CFCALL'][i]['FTYPE_ID'] == ftypeID:
                self.cfgData['G2_CONFIG']['CFG_CFCALL'][i]['CFUNC_ID'] = cfuncID
                modificationMade = True
        if not modificationMade:
            colorize_msg('No previous comparison method set.  Use addFeatureComparison instead.', 'error')
            return

        # we made it!
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')

    def do_deleteFeatureComparisonElement(self, arg):
        """\ndeleteFeatureComparisonElement {"feature": "<feature_name>", "element": "<element_name>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if it doesn't exist
        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg('Feature not found!', 'error')
            return

        # lookup element and error if it doesn't exist
        felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
        if not felemRecord:
            colorize_msg('Element not found!', 'error')
            return

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_FTYPE']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_FTYPE'][i]['FTYPE_CODE'] == parmData['FEATURE']:
                for i1 in range(len(self.cfgData['G2_CONFIG']['CFG_CFCALL']) - 1, -1, -1):
                    if self.cfgData['G2_CONFIG']['CFG_CFCALL'][i1]['FTYPE_ID'] == ftypeRecord['FTYPE_ID']:
                        for i2 in range(len(self.cfgData['G2_CONFIG']['CFG_CFBOM']) - 1, -1, -1):
                            if self.cfgData['G2_CONFIG']['CFG_CFBOM'][i2]['CFCALL_ID'] == \
                                    self.cfgData['G2_CONFIG']['CFG_CFCALL'][i1]['CFCALL_ID'] and \
                                    self.cfgData['G2_CONFIG']['CFG_CFBOM'][i2]['FTYPE_ID'] == ftypeRecord[
                                'FTYPE_ID'] and self.cfgData['G2_CONFIG']['CFG_CFBOM'][i2]['FELEM_ID'] == \
                                    felemRecord['FELEM_ID']:
                                del self.cfgData['G2_CONFIG']['CFG_CFBOM'][i2]
                                deleteCnt += 1
                                self.configUpdated = True

        if deleteCnt == 0:
            colorize_msg('Record not found!', 'warning')
        else:
            colorize_msg('Successfully deleted!', 'success')

    def do_deleteFeatureComparison(self, arg):
        """\ndeleteFeatureComparison {"feature": "<feature_name>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"FEATURE": arg}
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if it doesn't exist
        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg('Feature not found!', 'error')
            return

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_FTYPE']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_FTYPE'][i]['FTYPE_CODE'] == parmData['FEATURE']:

                # delete any comparison calls and boms  (must loop through backwards when deleting)
                for i1 in range(len(self.cfgData['G2_CONFIG']['CFG_CFCALL']) - 1, -1, -1):
                    if self.cfgData['G2_CONFIG']['CFG_CFCALL'][i1]['FTYPE_ID'] == \
                            self.cfgData['G2_CONFIG']['CFG_FTYPE'][i]['FTYPE_ID']:
                        for i2 in range(len(self.cfgData['G2_CONFIG']['CFG_CFBOM']) - 1, -1, -1):
                            if self.cfgData['G2_CONFIG']['CFG_CFBOM'][i2]['CFCALL_ID'] == \
                                    self.cfgData['G2_CONFIG']['CFG_CFCALL'][i1]['CFCALL_ID']:
                                del self.cfgData['G2_CONFIG']['CFG_CFBOM'][i2]
                                deleteCnt += 1
                        del self.cfgData['G2_CONFIG']['CFG_CFCALL'][i1]
                        deleteCnt += 1
                        self.configUpdated = True

        if deleteCnt == 0:
            colorize_msg('Record not found!', 'warning')
        else:
            colorize_msg('Successfully deleted!', 'success')

    def do_deleteFeatureDistinctCall(self, arg):
        """\ndeleteFeatureDistinctCall {"feature": "<feature_name>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"FEATURE": arg}
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # lookup feature and error if it doesn't exist
        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg('Feature not found!', 'error')
            return

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_FTYPE']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_FTYPE'][i]['FTYPE_CODE'] == parmData['FEATURE']:

                # delete any distinct-func calls and boms  (must loop through backwards when deleting)
                for i1 in range(len(self.cfgData['G2_CONFIG']['CFG_DFCALL']) - 1, -1, -1):
                    if self.cfgData['G2_CONFIG']['CFG_DFCALL'][i1]['FTYPE_ID'] == \
                            self.cfgData['G2_CONFIG']['CFG_FTYPE'][i]['FTYPE_ID']:
                        for i2 in range(len(self.cfgData['G2_CONFIG']['CFG_DFBOM']) - 1, -1, -1):
                            if self.cfgData['G2_CONFIG']['CFG_DFBOM'][i2]['DFCALL_ID'] == \
                                    self.cfgData['G2_CONFIG']['CFG_DFCALL'][i1]['DFCALL_ID']:
                                del self.cfgData['G2_CONFIG']['CFG_DFBOM'][i2]
                                deleteCnt += 1
                        del self.cfgData['G2_CONFIG']['CFG_DFCALL'][i1]
                        deleteCnt += 1
                        self.configUpdated = True

        if deleteCnt == 0:
            colorize_msg('Record not found!', 'warning')
        else:
            colorize_msg('Successfully deleted!', 'success')

# ===== function and calls section =====

    def do_addStandardizeCall(self, arg):
        """
        \n\taddStandardizeCall {"element":"<element_name>", "function":"<function_name>", "execOrder":<exec_order>}
        \n\n\taddStandardizeCall {"element":"COUNTRY", "function":"STANDARDIZE_COUNTRY", "execOrder":100}\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        featureIsSpecified = False
        ftypeID = -1
        if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0:
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
            if not ftypeRecord:
                colorize_msg('Feature does not exist!', 'error')
                return
            featureIsSpecified = True
            ftypeID = ftypeRecord['FTYPE_ID']

        elementIsSpecified = False
        felemID = -1
        if 'ELEMENT' in parmData and len(parmData['ELEMENT']) != 0:
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
            felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
            if not felemRecord:
                colorize_msg('Element does not exist!', 'error')
                return
            elementIsSpecified = True
            felemID = felemRecord['FELEM_ID']

        if featureIsSpecified is False and elementIsSpecified is False:
            colorize_msg('No feature or element specified.', 'error')
            return

        if featureIsSpecified is True and elementIsSpecified is True:
            colorize_msg('Both feature and element specified.  Must only use one, not both.', 'error')
            return

        sfuncID = -1
        if 'FUNCTION' not in parmData or len(parmData['FUNCTION'].strip()) == 0:
            colorize_msg('Function is required', 'error')
            return
        parmData['FUNCTION'] = parmData['FUNCTION'].upper()
        sfuncRecord = self.getRecord('CFG_SFUNC', 'SFUNC_CODE', parmData['FUNCTION'])
        if not sfuncRecord:
            colorize_msg('Function does not exist', 'error')
            return
        sfuncID = sfuncRecord['SFUNC_ID']

        if 'EXECORDER' not in parmData:
            colorize_msg('Exec order not specified.', 'error')
            return

        maxID = []
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_SFCALL'])):
            maxID.append(self.cfgData['G2_CONFIG']['CFG_SFCALL'][i]['SFCALL_ID'])

        sfcallID = 0
        if 'ID' in parmData:
            sfcallID = int(parmData['ID'])
        else:
            sfcallID = max(maxID) + 1 if max(maxID) >= 1000 else 1000

        newRecord = {}
        newRecord['SFCALL_ID'] = sfcallID
        newRecord['FTYPE_ID'] = ftypeID
        newRecord['FELEM_ID'] = felemID
        newRecord['SFUNC_ID'] = sfuncID
        newRecord['EXEC_ORDER'] = parmData['EXECORDER']
        self.cfgData['G2_CONFIG']['CFG_SFCALL'].append(newRecord)
        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')
        if self.doDebug:
            debug(newRecord)

    def do_updateFeatureVersion(self, arg):
        """\nupdateFeatureVersion {"feature":"<feature_name>", "version":<version_number>}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            if 'FEATURE' not in parmData or len(parmData['FEATURE']) == 0:
                raise ValueError('Feature name is required!')
            if 'VERSION' not in parmData:
                raise ValueError('Version is required!')
            parmData['FEATURE'] = parmData['FEATURE'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
        if not ftypeRecord:
            colorize_msg('Feature does not exist!' 'error')
            return
        else:
            ftypeRecord['VERSION'] = parmData['VERSION']
            self.configUpdated = True
            colorize_msg('Successfully updated!', 'B')
            if self.doDebug:
                debug(ftypeRecord)

    def do_updateAttributeAdvanced(self, arg):
        """\nupdateAttributeAdvanced {"attribute":"<attribute_name>", "advanced":"Yes"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            if 'ATTRIBUTE' not in parmData or len(parmData['ATTRIBUTE']) == 0:
                raise ValueError('Attribute name is required!')
            if 'ADVANCED' not in parmData:
                raise ValueError('Advanced value is required!')
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        attrRecord = self.getRecord('CFG_ATTR', 'ATTR_CODE', parmData['ATTRIBUTE'])
        if not attrRecord:
            colorize_msg('Attribute does not exist!', 'error')
            return
        else:
            attrRecord['ADVANCED'] = parmData['ADVANCED']
            self.configUpdated = True
            colorize_msg('Successfully updated!', 'success')
            if self.doDebug:
                debug(attrRecord)

    def do_updateExpressionFuncVersion(self, arg):
        """\nupdateExpressionFuncVersion {"function":"<function_name>", "version":"<version_number>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            if 'FUNCTION' not in parmData or len(parmData['FUNCTION']) == 0:
                raise ValueError('Function is required!')
            if 'VERSION' not in parmData or len(parmData['VERSION']) == 0:
                raise ValueError('Version is required!')
            parmData['FUNCTION'] = parmData['FUNCTION'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        funcRecord = self.getRecord('CFG_EFUNC', 'EFUNC_CODE', parmData['FUNCTION'])
        if not funcRecord:
            colorize_msg('Function does not exist!', 'error')
            return
        else:
            funcRecord['FUNC_VER'] = parmData['VERSION']
            self.configUpdated = True
            colorize_msg('Successfully updated!', 'success')

            if self.doDebug:
                debug(funcRecord)

    def do_addExpressionCall(self, arg):
        """
        \n\taddExpressionCall {"element":"<element_name>", "function":"<function_name>", "execOrder":<exec_order>, "expressionFeature":<feature_name>, "virtual":"No","elementList": ["<element_detail(s)"]}
        \n\n\taddExpressionCall {"element":"COUNTRY_CODE", "function":"FEAT_BUILDER", "execOrder":100, "expressionFeature":"COUNTRY_OF_ASSOCIATION", "virtual":"No","elementList": [{"element":"COUNTRY", "featureLink":"parent", "required":"No"}]}
        \n\n\taddExpressionCall {"element":"COUNTRY_CODE", "function":"FEAT_BUILDER", "execOrder":100, "expressionFeature":"COUNTRY_OF_ASSOCIATION", "virtual":"No","elementList": [{"element":"COUNTRY", "feature":"ADDRESS", "required":"No"}]}\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            if 'ELEMENTLIST' not in parmData or len(parmData['ELEMENTLIST']) == 0:
                raise ValueError('Element list is required!')
            if type(parmData['ELEMENTLIST']) is not list:
                raise ValueError(
                    'Element list should be specified as: "elementlist": ["<values>"]\n\n\tNote the [ and ]')
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        featureIsSpecified = False
        ftypeID = -1
        if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0:
            parmData['FEATURE'] = parmData['FEATURE'].upper()
            ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
            if not ftypeRecord:
                colorize_msg('Feature does not exist', 'error')
                return
            featureIsSpecified = True
            ftypeID = ftypeRecord['FTYPE_ID']

        elementIsSpecified = False
        felemID = -1
        if 'ELEMENT' in parmData and len(parmData['ELEMENT']) != 0:
            parmData['ELEMENT'] = parmData['ELEMENT'].upper()
            felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
            if not felemRecord:
                colorize_msg('Element does not exist', 'error')
                return
            elementIsSpecified = True
            felemID = felemRecord['FELEM_ID']

        if featureIsSpecified is False and elementIsSpecified is False:
            colorize_msg('No feature or element specified.', 'error')
            return

        if featureIsSpecified is True and elementIsSpecified is True:
            colorize_msg('Both feature and element specified.  Must only use one, not both.', 'error')
            return

        efuncID = -1
        if 'FUNCTION' not in parmData or len(parmData['FUNCTION'].strip()) == 0:
            colorize_msg('Function is required', 'error')
            return
        parmData['FUNCTION'] = parmData['FUNCTION'].upper()
        efuncRecord = self.getRecord('CFG_EFUNC', 'EFUNC_CODE', parmData['FUNCTION'])
        if not efuncRecord:
            colorize_msg('Function does not exist', 'error')
            return
        efuncID = efuncRecord['EFUNC_ID']

        if 'EXECORDER' not in parmData:
            colorize_msg('An execOrder for the call must be specified.', 'error')
            return

        callExists = False
        efcallID = int(parmData['ID']) if 'ID' in parmData else 0
        maxID = []
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_EFCALL'])):
            maxID.append(self.cfgData['G2_CONFIG']['CFG_EFCALL'][i]['EFCALL_ID'])
            if self.cfgData['G2_CONFIG']['CFG_EFCALL'][i]['EFCALL_ID'] == efcallID:
                colorize_msg('The supplied ID already exists.', 'error')
                callExists = True
                break
            elif self.cfgData['G2_CONFIG']['CFG_EFCALL'][i]['FTYPE_ID'] == ftypeID and \
                    self.cfgData['G2_CONFIG']['CFG_EFCALL'][i]['EXEC_ORDER'] == parmData['EXECORDER']:
                colorize_msg('A call for that feature and execOrder already exists.', 'warning')
                callExists = True
                break
        if callExists:
            return

        if 'ID' in parmData:
            efcallID = int(parmData['ID'])
        else:
            efcallID = max(maxID) + 1 if max(maxID) >= 1000 else 1000

        isVirtual = parmData['VIRTUAL'] if 'VIRTUAL' in parmData else 'No'

        efeatFTypeID = -1
        if 'EXPRESSIONFEATURE' in parmData and len(parmData['EXPRESSIONFEATURE']) != 0:
            parmData['EXPRESSIONFEATURE'] = parmData['EXPRESSIONFEATURE'].upper()
            expressionFTypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['EXPRESSIONFEATURE'])
            if not expressionFTypeRecord:
                colorize_msg('Expression feature does not exist', 'error')
                return
            efeatFTypeID = expressionFTypeRecord['FTYPE_ID']

        # ensure we have valid elements
        elementCount = 0
        for element in parmData['ELEMENTLIST']:
            elementCount += 1
            elementRecord = dictKeysUpper(element)

            bomFTypeIsSpecified = False
            bomFTypeID = -1
            if 'FEATURE' in elementRecord and len(elementRecord['FEATURE']) != 0:
                elementRecord['FEATURE'] = elementRecord['FEATURE'].upper()
                bomFTypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', elementRecord['FEATURE'])
                if not bomFTypeRecord:
                    colorize_msg('Referenced feature does not exist', 'error')
                    return
                bomFTypeIsSpecified = True
                bomFTypeID = bomFTypeRecord['FTYPE_ID']

            bomFElemIsSpecified = False
            bomFElemID = -1
            if 'ELEMENT' in elementRecord and len(elementRecord['ELEMENT']) != 0:
                elementRecord['ELEMENT'] = elementRecord['ELEMENT'].upper()
                bomFElemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', elementRecord['ELEMENT'])
                if not bomFElemRecord:
                    colorize_msg('Referenced element does not exist!', 'error')
                    return
                bomFElemIsSpecified = True
                bomFElemID = bomFElemRecord['FELEM_ID']

            if bomFElemIsSpecified is False:
                colorize_msg('Referenced element is missing!', 'error')
                return

            bomFTypeFeatureLinkIsSpecified = False
            if 'FEATURELINK' in elementRecord and len(elementRecord['FEATURELINK']) != 0:
                elementRecord['FEATURELINK'] = elementRecord['FEATURELINK'].upper()
                if elementRecord['FEATURELINK'] != 'PARENT':
                    colorize_msg('featureLink must be "PARENT" if feature not specifiied', 'error')
                    return
                bomFTypeFeatureLinkIsSpecified = True
                bomFTypeID = 0

            if bomFTypeIsSpecified is True and bomFTypeFeatureLinkIsSpecified is True:
                colorize_msg('Cannot specify both feature and featureLink on single function BOM entry.', 'error')
                return

        if elementCount == 0:
            colorize_msg('No elements specified.', 'error')
            return

        # add the expression call
        newRecord = {}
        newRecord['EFCALL_ID'] = efcallID
        newRecord['FTYPE_ID'] = ftypeID
        newRecord['FELEM_ID'] = felemID
        newRecord['EFUNC_ID'] = efuncID
        newRecord['EXEC_ORDER'] = parmData['EXECORDER']
        newRecord['EFEAT_FTYPE_ID'] = efeatFTypeID
        newRecord['IS_VIRTUAL'] = isVirtual
        self.cfgData['G2_CONFIG']['CFG_EFCALL'].append(newRecord)
        if self.doDebug:
            debug(newRecord)

        # add elements
        efbomOrder = 0
        for element in parmData['ELEMENTLIST']:
            efbomOrder += 1
            elementRecord = dictKeysUpper(element)

            bomFTypeID = -1
            if 'FEATURE' in elementRecord and len(elementRecord['FEATURE']) != 0:
                bomFTypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', elementRecord['FEATURE'])
                bomFTypeID = bomFTypeRecord['FTYPE_ID']

            bomFElemID = -1
            if 'ELEMENT' in elementRecord and len(elementRecord['ELEMENT']) != 0:
                bomFElemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', elementRecord['ELEMENT'])
                bomFElemID = bomFElemRecord['FELEM_ID']

            if 'FEATURELINK' in elementRecord and len(elementRecord['FEATURELINK']) != 0:
                elementRecord['FEATURELINK'] = elementRecord['FEATURELINK'].upper()
                bomFTypeID = 0

            felemRequired = elementRecord['REQUIRED'] if 'REQUIRED' in elementRecord else 'No'

            # add to expression bom if any
            newRecord = {}
            newRecord['EFCALL_ID'] = efcallID
            newRecord['EXEC_ORDER'] = efbomOrder
            newRecord['FTYPE_ID'] = bomFTypeID
            newRecord['FELEM_ID'] = bomFElemID
            newRecord['FELEM_REQ'] = felemRequired
            self.cfgData['G2_CONFIG']['CFG_EFBOM'].append(newRecord)
            if self.doDebug:
                debug(newRecord, 'EFBOM build')

        self.configUpdated = True
        colorize_msg('Successfully added!', 'success')

    def do_deleteExpressionCall(self, arg):
        """\ndeleteExpressionCall {"id": "<id>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg)) if arg.startswith('{') else {"ID": arg}
            if 'ID' not in parmData or not parmData['ID'].isnumeric():
                raise ValueError(arg)
            else:
                searchField = 'EFCALL_ID'
                searchValue = int(parmData['ID'])
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_EFCALL']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_EFCALL'][i][searchField] == searchValue:
                del self.cfgData['G2_CONFIG']['CFG_EFCALL'][i]
                deleteCnt += 1
                self.configUpdated = True
        if deleteCnt == 0:
            colorize_msg('Record not found', 'warning')
        else:
            colorize_msg('Successfully deleted!', 'success')

        # delete the efboms too
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_EFBOM']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_EFBOM'][i][searchField] == searchValue:
                del self.cfgData['G2_CONFIG']['CFG_EFBOM'][i]

    def do_addElementToFeature(self, arg):
        """
        \n\taddElementToFeature {"feature": "<feature_name>", "element": "<element_name>"}
        \n\n\taddElementToFeature {"feature": "<feature_name>", "element": "<element_name>", "compared": "no", "expressed": "no"}
        \n\n\tFor additional example structures, use getFeature or listFeatures\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
        except (ValueError, KeyError) as e:
            print('\nError with argument(s) or parsing JSON - %s \n' % e)
        else:

            if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0 and 'ELEMENT' in parmData and len(
                    parmData['ELEMENT']) != 0:

                parmData['FEATURE'] = parmData['FEATURE'].upper()
                ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
                if not ftypeRecord:
                    colorize_msg('Feature does not exist!', 'error')
                    return

                parmData['ELEMENT'] = parmData['ELEMENT'].upper()
                felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])

            else:
                colorize_msg('Both a feature and element must be specified!', 'error')
                return

            # default for missing values

            if 'COMPARED' not in parmData or len(parmData['COMPARED'].strip()) == 0:
                parmData['COMPARED'] = 'No'
            else:
                if parmData['COMPARED'].upper() not in ('YES', 'NO'):
                    colorize_msg('"compared" value must be "Yes" or "No"', 'error')
                    return

            if 'EXPRESSED' not in parmData or len(parmData['EXPRESSED'].strip()) == 0:
                parmData['EXPRESSED'] = 'No'
            else:
                if parmData['EXPRESSED'].upper() not in ('YES', 'NO'):
                    colorize_msg('"expressed" value must be "Yes" or "No"', 'error')
                    return

            if 'DATATYPE' not in parmData or len(parmData['DATATYPE'].strip()) == 0:
                parmData['DATATYPE'] = 'string'
            else:
                if parmData['DATATYPE'].upper() not in ('DATE', 'DATETIME', 'JSON', 'NUMBER', 'STRING'):
                    colorize_msg('"dataType" must be "DATE", "DATETIME", "JSON", "NUMBER", or "STRING"', 'error')
                    return
                parmData['DATATYPE'] = parmData['DATATYPE'].lower()

            if 'TOKENIZE' not in parmData or len(parmData['TOKENIZE'].strip()) == 0:
                parmData['TOKENIZE'] = 'No'
            else:
                if parmData['TOKENIZE'] not in ('0', '1', 'No', 'Yes'):
                    colorize_msg('"tokenize" value must be "Yes" or "No"', 'error')
                    return

            if 'DERIVED' not in parmData:
                parmData['DERIVED'] = 'No'
            else:
                if parmData['DERIVED'] not in ('0', '1', 'No', 'Yes'):
                    colorize_msg('"derived" value must be "Yes" or "No"', 'error')
                    return

            if 'DISPLAY_DELIM' not in parmData:
                parmData['DISPLAY_DELIM'] = None

            if 'DISPLAY_LEVEL' not in parmData:
                parmData['DISPLAY_LEVEL'] = 0

            # does the element exist already and has conflicting parms to what was requested?
            if felemRecord:
                felemID = felemRecord['FELEM_ID']
                if (
                        (parmData['DATATYPE'] and len(parmData['DATATYPE'].strip()) > 0 and parmData['DATATYPE'] !=
                         felemRecord['DATA_TYPE']) or
                        (parmData['TOKENIZE'] and len(parmData['TOKENIZE'].strip()) > 0 and parmData['TOKENIZE'] !=
                         felemRecord['TOKENIZE'])
                ):
                    colorize_msg('Element already exists with conflicting parameters', 'error')
                    return
            else:
                # If no element already add it first
                if not felemRecord:
                    maxID = 0
                    for i in range(len(self.cfgData['G2_CONFIG']['CFG_FELEM'])):
                        if 'ID' in parmData and int(self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_ID']) == int(
                                parmData['ID']):
                            colorize_msg('Element id already exists!', 'error')
                            return
                        if self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_ID'] > maxID:
                            maxID = self.cfgData['G2_CONFIG']['CFG_FELEM'][i]['FELEM_ID']

                    if 'ID' in parmData:
                        felemID = int(parmData['ID'])
                    else:
                        felemID = maxID + 1 if maxID >= 1000 else 1000

                    newRecord = {}
                    newRecord['FELEM_ID'] = felemID
                    newRecord['FELEM_CODE'] = parmData['ELEMENT']
                    newRecord['FELEM_DESC'] = parmData['ELEMENT']
                    newRecord['DATA_TYPE'] = parmData['DATATYPE']
                    newRecord['TOKENIZE'] = parmData['TOKENIZE']
                    self.cfgData['G2_CONFIG']['CFG_FELEM'].append(newRecord)
                    self.configUpdated = True
                    colorize_msg('Successfully added the element!', 'success')
                    if self.doDebug:
                        debug(newRecord)

            # add the fbom, if it does not already exist
            alreadyExists = False
            maxExec = [0]
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_FBOM'])):
                if int(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FTYPE_ID']) == ftypeRecord['FTYPE_ID']:
                    maxExec.append(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['EXEC_ORDER'])
                    if int(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FELEM_ID']) == felemID:
                        alreadyExists = True
                        break

            if alreadyExists:
                colorize_msg('Element already exists for feature!', 'error')
            else:
                newRecord = {}
                newRecord['FTYPE_ID'] = ftypeRecord['FTYPE_ID']
                newRecord['FELEM_ID'] = felemID
                newRecord['EXEC_ORDER'] = max(maxExec) + 1
                newRecord['DISPLAY_DELIM'] = parmData['DISPLAY_DELIM']
                newRecord['DISPLAY_LEVEL'] = parmData['DISPLAY_LEVEL']
                newRecord['DERIVED'] = parmData['DERIVED']
                self.cfgData['G2_CONFIG']['CFG_FBOM'].append(newRecord)
                self.configUpdated = True
                colorize_msg('Successfully added to feature!', 'success')
                if self.doDebug:
                    debug(newRecord)

    def xx_setFeatureElementDisplayLevel(self, arg):
        """\nsetFeatureElementDisplayLevel {"feature": "<feature_name>", "element": "<element_name>", "display_level": <display_level>}\n"""
        # DELETE AND RE-ADD INSTEAD
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
        except (ValueError, KeyError) as e:
            print('\nError with argument(s) or parsing JSON - %s \n' % e)
        else:

            if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0 and 'ELEMENT' in parmData and len(
                    parmData['ELEMENT']) != 0:

                parmData['FEATURE'] = parmData['FEATURE'].upper()
                ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
                if not ftypeRecord:
                    colorize_msg('Feature does not exist', 'error')
                    return

                parmData['ELEMENT'] = parmData['ELEMENT'].upper()
                felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
                if not felemRecord:
                    colorize_msg('Element does not exist', 'error')
                    return

            else:
                colorize_msg('Both a feature and element must be specified!', 'error')
                return

            if 'DISPLAY_LEVEL' in parmData:
                displayLevel = int(parmData['DISPLAY_LEVEL'])
            else:
                colorize_msg('Display level must be specified!', 'error')
                return

            for i in range(len(self.cfgData['G2_CONFIG']['CFG_FBOM'])):
                if int(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FTYPE_ID']) == ftypeRecord['FTYPE_ID']:
                    if int(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FELEM_ID']) == felemRecord['FELEM_ID']:
                        self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['DISPLAY_LEVEL'] = displayLevel
                        self.configUpdated = True
                        colorize_msg('Feature element display level updated!', 'success')
                        if self.doDebug:
                            debug(self.cfgData['G2_CONFIG']['CFG_FBOM'][i])

    def xx_setFeatureElementDerived(self, arg):
        """\nsetFeatureElementDerived {"feature": "<feature_name>", "element": "<element_name>", "derived": <display_level>}\n"""
        # DELETE AND RE-ADD INSTEAD

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
        except (ValueError, KeyError) as e:
            print('\nError with argument(s) or parsing JSON - %s \n' % e)
        else:

            if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0 and 'ELEMENT' in parmData and len(
                    parmData['ELEMENT']) != 0:

                parmData['FEATURE'] = parmData['FEATURE'].upper()
                ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
                if not ftypeRecord:
                    colorize_msg(
                        'Feature does not exist: %s. Use listFeatures to see valid features.' % parmData['FEATURE'], 'B')
                    return

                parmData['ELEMENT'] = parmData['ELEMENT'].upper()
                felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
                if not felemRecord:
                    colorize_msg('Feature does not exist element: %s.' % parmData['ELEMENT'], 'B')
                    return

            else:
                colorize_msg('Both a feature and element must be specified!', 'B')
                return

            if 'DERIVED' in parmData:
                derived = parmData['DERIVED']
            else:
                colorize_msg('Derived status must be specified!', 'B')
                return

            for i in range(len(self.cfgData['G2_CONFIG']['CFG_FBOM'])):
                if int(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FTYPE_ID']) == ftypeRecord['FTYPE_ID']:
                    if int(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FELEM_ID']) == felemRecord['FELEM_ID']:
                        self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['DERIVED'] = derived
                        self.configUpdated = True
                        colorize_msg('Feature element derived status updated!', 'B')
                        if self.doDebug:
                            debug(self.cfgData['G2_CONFIG']['CFG_FBOM'][i])

    def do_deleteElementFromFeature(self, arg):
        """\ndeleteElementFromFeature {"feature": "<feature_name>", "element": "<element_name>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
        except (ValueError, KeyError) as e:
            print('\nError with argument(s) or parsing JSON - %s \n' % e)
        else:

            if 'FEATURE' in parmData and len(parmData['FEATURE']) != 0 and 'ELEMENT' in parmData and len(
                    parmData['ELEMENT']) != 0:

                parmData['FEATURE'] = parmData['FEATURE'].upper()
                ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
                if not ftypeRecord:
                    colorize_msg(
                        'Feature does not exist: %s. Use listFeatures to see valid features.' % parmData['FEATURE'], 'B')
                    return

                parmData['ELEMENT'] = parmData['ELEMENT'].upper()
                felemRecord = self.getRecord('CFG_FELEM', 'FELEM_CODE', parmData['ELEMENT'])
                if not felemRecord:
                    colorize_msg(
                        'Element does not exist: %s. Use listElements to see valid elements.' % parmData['ELEMENT'], 'B')
                    return

            else:
                colorize_msg('Both a feature and element must be specified!', 'B')
                return

            deleteCnt = 0
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_FBOM']) - 1, -1, -1):
                if int(self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FTYPE_ID']) == ftypeRecord['FTYPE_ID'] and int(
                        self.cfgData['G2_CONFIG']['CFG_FBOM'][i]['FELEM_ID']) == felemRecord['FELEM_ID']:
                    del self.cfgData['G2_CONFIG']['CFG_FBOM'][i]
                    deleteCnt = 1
                    self.configUpdated = True

            if deleteCnt == 0:
                print('\nRecord not found!\n')
            else:
                colorize_msg('Successfully deleted!', 'success')

    def do_listExpressionCalls(self, arg):
        """\nlistExpressionCalls [search_filter]\n"""

        json_lines = []
        for efcallRecord in sorted(self.cfgData['G2_CONFIG']['CFG_EFCALL'],
                                   key=lambda k: (k['FTYPE_ID'], k['EXEC_ORDER'])):
            efuncRecord = self.getRecord('CFG_EFUNC', 'EFUNC_ID', efcallRecord['EFUNC_ID'])
            ftypeRecord1 = self.getRecord('CFG_FTYPE', 'FTYPE_ID', efcallRecord['FTYPE_ID'])
            ftypeRecord2 = self.getRecord('CFG_FTYPE', 'FTYPE_ID', efcallRecord['EFEAT_FTYPE_ID'])
            felemRecord2 = self.getRecord('CFG_FELEM', 'FELEM_ID', efcallRecord['FELEM_ID'])

            efcallDict = {}
            efcallDict['id'] = efcallRecord['EFCALL_ID']
            if ftypeRecord1:
                efcallDict['feature'] = ftypeRecord1['FTYPE_CODE']
            elif self.current_list_format == 'table':
                efcallDict['feature'] = 'n/a'
            if felemRecord2:
                efcallDict['element'] = felemRecord2['FELEM_CODE']
            elif self.current_list_format == 'table':
                efcallDict['element'] = 'n/a'
            efcallDict['execOrder'] = efcallRecord['EXEC_ORDER']
            efcallDict['function'] = efuncRecord['EFUNC_CODE']
            efcallDict['is_virtual'] = efcallRecord['IS_VIRTUAL']
            if ftypeRecord2:
                efcallDict['expressionFeature'] = ftypeRecord2['FTYPE_CODE']
            elif self.current_list_format == 'table':
                efcallDict['expressionFeature'] = 'n/a'

            efbomList = []
            for efbomRecord in [record for record in self.cfgData['G2_CONFIG']['CFG_EFBOM'] if
                                record['EFCALL_ID'] == efcallRecord['EFCALL_ID']]:
                ftypeRecord3 = self.getRecord('CFG_FTYPE', 'FTYPE_ID', efbomRecord['FTYPE_ID'])
                felemRecord3 = self.getRecord('CFG_FELEM', 'FELEM_ID', efbomRecord['FELEM_ID'])

                efbomDict = {}
                if efbomRecord['FTYPE_ID'] == 0:
                    efbomDict['featureLink'] = 'parent'
                elif ftypeRecord3:
                    efbomDict['feature'] = ftypeRecord3['FTYPE_CODE']
                if felemRecord3:
                    efbomDict['element'] = felemRecord3['FELEM_CODE']
                else:
                    efbomDict['element'] = str(efbomRecord['FELEM_ID'])
                efbomDict['required'] = efbomRecord['FELEM_REQ']
                efbomList.append(efbomDict)
            efcallDict['elementList'] = efbomList

            json_lines.append(efcallDict)
        self.print_json_lines(json_lines)

    # ===== misc commands =====

    def do_setDistinct(self, arg):
        """
        \n\tDistinct processing only compares the most complete feature values for an entity. You may want to turn this off for watch list checking.
        \n\n\tSyntax:
        \n\t\tsetDistinct on
        \n\t\tsetDistinct off\n
        """

        if not arg:
            colorize_msg(
                'Distinct is currently %s' % ('ON' if len(self.cfgData['G2_CONFIG']['CFG_DFCALL']) != 0 else 'OFF'),
                'B')
            return

        if arg.upper() not in ('ON', 'OFF'):
            colorize_msg('invalid distinct setting %s' % arg, 'B')
            return

        newSetting = arg.upper()

        if len(self.cfgData['G2_CONFIG']['CFG_DFCALL']) == 0 and newSetting == 'OFF':
            colorize_msg('distinct is already off!', 'B')
            return

        if len(self.cfgData['G2_CONFIG']['CFG_DFCALL']) != 0 and newSetting == 'ON':
            colorize_msg('distinct is already on!', 'B')
            return

        if newSetting == 'OFF':
            self.cfgData['G2_CONFIG']['XXX_DFCALL'] = self.cfgData['G2_CONFIG']['CFG_DFCALL']
            self.cfgData['G2_CONFIG']['XXX_DFBOM'] = self.cfgData['G2_CONFIG']['CFG_DFBOM']
            self.cfgData['G2_CONFIG']['CFG_DFCALL'] = []
            self.cfgData['G2_CONFIG']['CFG_DFBOM'] = []
        else:
            if 'XXX_DFCALL' not in self.cfgData['G2_CONFIG']:
                colorize_msg('distinct settings cannot be restored, backup could not be found!', 'B')
                return

            self.cfgData['G2_CONFIG']['CFG_DFCALL'] = self.cfgData['G2_CONFIG']['XXX_DFCALL']
            self.cfgData['G2_CONFIG']['CFG_DFBOM'] = self.cfgData['G2_CONFIG']['XXX_DFBOM']
            del (self.cfgData['G2_CONFIG']['XXX_DFCALL'])
            del (self.cfgData['G2_CONFIG']['XXX_DFBOM'])

        colorize_msg('distinct is now %s!' % newSetting, 'B')

        self.configUpdated = True

        return

    def do_listGenericThresholds(self, arg):
        """\nlistGenericThresholds [search_filter]\n"""

        planCode = {}
        planCode[1] = 'load'
        planCode[2] = 'search'

        recordList = self.getRecordList('CFG_GENERIC_THRESHOLD')
        for i in range(len(recordList)):
            try:
                recordList[i]['BEHAVIOR_ORDER'] = self.valid_behavior_codes.index(recordList[i]['BEHAVIOR'])
            except:
                recordList[i]['BEHAVIOR_ORDER'] = 99

        json_lines = []
        for thisRecord in sorted(recordList, key=lambda k: (k['GPLAN_ID'], k['BEHAVIOR_ORDER'])):
            if arg and arg.lower() not in str(thisRecord).lower():
                continue

            if thisRecord.get("FTYPE_ID", 0) != 0:
                ftypeCode = self.getRecord("CFG_FTYPE", "FTYPE_ID", thisRecord["FTYPE_ID"])["FTYPE_CODE"]
            else:
                ftypeCode = 'all'
            json_lines.append({"plan": planCode[thisRecord['GPLAN_ID']],
                               "behavior": thisRecord['BEHAVIOR'],
                               "feature": ftypeCode,
                               "candidateCap": thisRecord['CANDIDATE_CAP'],
                               "scoringCap": thisRecord['SCORING_CAP'],
                               "sendToRedo": thisRecord['SEND_TO_REDO']})
        self.print_json_lines(json_lines)

    def do_addGenericThreshold(self, arg):
        """
        \n\taddGenericThreshold {"plan": "load", "behavior": "<behavior_type>", "feature": "<feature>", "scoringCap": 99, "candidateCap": 99, "sendToRedo": "Yes"}
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['PLAN'] = parmData['PLAN'].upper()
            parmData['BEHAVIOR'] = parmData['BEHAVIOR'].upper()
            parmData['SCORINGCAP'] = int(parmData['SCORINGCAP'])
            parmData['CANDIDATECAP'] = int(parmData['CANDIDATECAP'])
            parmData['SENDTOREDO'] = parmData.get('SENDTOREDO', 'Yes').upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        if parmData['PLAN'] not in ('LOAD', 'SEARCH'):
            print('\nPlan must either be "LOAD" or "SEARCH"\n')
            return
        gplan_id = 1 if parmData['PLAN'] == 'LOAD' else 2

        behaviorData = parseFeatureBehavior(parmData['BEHAVIOR'])
        if not behaviorData:
            print(f"\n{parmData['BEHAVIOR']} is not a valid feature behavior\n")
            return

        if 'FEATURE' in parmData:
            ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
            if not ftypeRecord:
                print(f"\n{parmData['FEATURE']} is not a valid feature\n")
                return
            elif getFeatureBehavior(ftypeRecord) != parmData['BEHAVIOR']:
                print(f"\nFeature behavior is {getFeatureBehavior(ftypeRecord)} and does not match threshold behavior {parmData['BEHAVIOR']}\n")
                return
            ftypeID = ftypeRecord['FTYPE_ID']
        else:
            ftypeID = 0

        if parmData['SENDTOREDO'] not in ('YES', 'NO'):
            print('\nSendToRedo must be "Yes" or "No"\n')
            return

        listID = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'])):
            if self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][i]['GPLAN_ID'] == gplan_id and \
               self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][i]['BEHAVIOR'] == parmData['BEHAVIOR'] and \
               self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][i]['FTYPE_ID'] == ftypeID:
                listID = i
        if listID:
            print('\nGeneric threshold already exists.  Use setGenericThreshold to update it.\n')
            return

        newRecord = {}
        newRecord['GPLAN_ID'] = gplan_id
        newRecord['BEHAVIOR'] = parmData['BEHAVIOR']
        newRecord['FTYPE_ID'] = ftypeID
        newRecord['CANDIDATE_CAP'] = parmData['CANDIDATECAP']
        newRecord['SCORING_CAP'] = parmData['SCORINGCAP']
        newRecord['SEND_TO_REDO'] = 'Yes' if parmData['SENDTOREDO'].upper() == 'YES' else 'No'
        self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'].append(newRecord)
        self.configUpdated = True
        print('\nSuccessfully added!\n')
        if self.doDebug:
            debug(newRecord)

    def do_setGenericThreshold(self, arg):
        """
        \n\tsetGenericThreshold {"plan": "load", "behavior": "<behavior_type>", "scoringCap": 99}
        \n\tsetGenericThreshold {"plan": "search", "behavior": "<behavior_type>", "candidateCap": 99}\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['PLAN'] = {'LOAD': 1, 'SEARCH': 2}[parmData['PLAN'].upper()]
            parmData['BEHAVIOR'] = parmData['BEHAVIOR'].upper()
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        print()

        if 'FEATURE' in parmData:
            ftypeRecord = self.getRecord('CFG_FTYPE', 'FTYPE_CODE', parmData['FEATURE'])
            if not ftypeRecord:
                print(f"\n{parmData['FEATURE']} is not a valid feature\n")
                return
            ftypeID = ftypeRecord['FTYPE_ID']
        else:
            ftypeID = 0

        if parmData.get('SENDTOREDO') and parmData.get('SENDTOREDO').upper() not in ('YES', 'NO'):
            print('\nSendToRedo must be "Yes" or "No"\n')
            return

        listID = -1
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'])):
            if self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][i]['GPLAN_ID'] == parmData['PLAN'] and \
               self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][i]['BEHAVIOR'] == parmData['BEHAVIOR'] and \
               self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][i]['FTYPE_ID'] == ftypeID:
                listID = i
        if listID == -1:
            colorize_msg('Threshold does not exist!')
            return

        # make the updates
        if 'CANDIDATECAP' in parmData:
            self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][listID]['CANDIDATE_CAP'] = int(
                parmData['CANDIDATECAP'])
            colorize_msg('Candidate cap updated!')
            self.configUpdated = True
        if 'SCORINGCAP' in parmData:
            self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][listID]['SCORING_CAP'] = int(parmData['SCORINGCAP'])
            colorize_msg('Scoring cap updated!')
            self.configUpdated = True

        if 'SENDTOREDO' in parmData:
            self.cfgData['G2_CONFIG']['CFG_GENERIC_THRESHOLD'][listID]['SEND_TO_REDO'] = 'Yes' if parmData['SENDTOREDO'].upper() == 'YES' else 'No'
            colorize_msg('Send to redo updated!')
            self.configUpdated = True

        print()

    # ===== fragment commands =====

    def getFragmentJson(self, record):

        return {"id": record["ERFRAG_ID"],
                "fragment": record["ERFRAG_CODE"],
                "source": record["ERFRAG_SOURCE"],
                "depends": record["ERFRAG_DEPENDS"]}

    def do_listFragments(self, arg):
        """\nlistFragments [search_filter]\n"""

        json_lines = []
        for thisRecord in sorted(self.getRecordList('CFG_ERFRAG'), key=lambda k: k['ERFRAG_ID']):
            if arg and arg.lower() not in str(thisRecord).lower():
                continue
            json_lines.append(self.getFragmentJson(thisRecord))
        self.print_json_lines(json_lines)

    def do_getFragment(self, arg):
        """\ngetFragment [id]\ngetFragment [fragment_name]\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            if arg.startswith('{'):
                parmData = dictKeysUpper(json.loads(arg))
            elif arg.isdigit():
                parmData = {"ID": arg}
            else:
                parmData = {"FRAGMENT": arg}
            if 'FRAGMENT' in parmData and len(parmData['FRAGMENT'].strip()) != 0:
                searchField = 'ERFRAG_CODE'
                searchValue = parmData['FRAGMENT'].upper()
            elif 'ID' in parmData and len(parmData['ID'].strip()) != 0:
                searchField = 'ERFRAG_ID'
                searchValue = int(parmData['ID'])
            else:
                raise ValueError(arg)
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        foundRecords = self.getRecordList('CFG_ERFRAG', searchField, searchValue)
        if not foundRecords:
            print('\nRecord not found!\n')
        else:
            print()
            for thisRecord in sorted(foundRecords, key=lambda k: k['ERFRAG_ID']):
                self.print_json_record(self.getFragmentJson(thisRecord))
            print()

    def do_deleteFragment(self, arg):
        """
        \n\tdeleteFragment {"id": "<fragment_id>"}
        \n\tdeleteFragment {"fragment": "<fragment_code>"}\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            if arg.startswith('{'):
                parmData = dictKeysUpper(json.loads(arg))
            elif arg.isdigit():
                parmData = {"ID": arg}
            else:
                parmData = {"FRAGMENT": arg}
            if 'FRAGMENT' in parmData and len(parmData['FRAGMENT'].strip()) != 0:
                searchField = 'ERFRAG_CODE'
                searchValue = parmData['FRAGMENT'].upper()
            elif 'ID' in parmData and len(parmData['ID'].strip()) != 0:
                searchField = 'ERFRAG_ID'
                searchValue = int(parmData['ID'])
            else:
                raise ValueError(arg)
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_ERFRAG']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i][searchField] == searchValue:
                del self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]
                deleteCnt += 1
                self.configUpdated = True
        if deleteCnt == 0:
            print('\nRecord not found!\n')
        colorize_msg('Successfully deleted!', 'success')

    def do_setFragment(self, arg):
        """\nsetFragment {"id": "<fragment_id>", "fragment": "<fragment_code>", "source": "<fragment_source>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            if arg.startswith('{'):
                parmData = dictKeysUpper(json.loads(arg))
            elif arg.isdigit():
                parmData = {"ID": arg}
            else:
                parmData = {"FRAGMENT": arg}
            if 'FRAGMENT' in parmData and len(parmData['FRAGMENT'].strip()) != 0:
                searchField = 'ERFRAG_CODE'
                searchValue = parmData['FRAGMENT'].upper()
            elif 'ID' in parmData and len(parmData['ID'].strip()) != 0:
                searchField = 'ERFRAG_ID'
                searchValue = int(parmData['ID'])
            else:
                raise ValueError(arg)
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        print()

        # lookup fragment and error if doesn't exist
        listID = -1
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_ERFRAG']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i][searchField] == searchValue:
                listID = i
        if listID == -1:
            colorize_msg('Fragment does not exist!')
            return

        # make the updates
        for parmCode in parmData:
            if parmCode == 'ID':
                pass

            elif parmCode == 'SOURCE':
                # compute dependencies from source
                # example: './FRAGMENT[./SAME_NAME>0 and ./SAME_STAB>0] or ./FRAGMENT[./SAME_NAME1>0 and ./SAME_STAB1>0]'
                dependencyList = []
                sourceString = parmData['SOURCE']
                startPos = sourceString.find('FRAGMENT[')
                while startPos > 0:
                    fragmentString = sourceString[startPos:sourceString.find(']', startPos) + 1]
                    sourceString = sourceString.replace(fragmentString, '')
                    # parse the fragment string
                    currentFrag = 'eof'
                    fragmentChars = list(fragmentString)
                    potentialErrorString = ''
                    for thisChar in fragmentChars:
                        potentialErrorString += thisChar
                        if thisChar == '/':
                            currentFrag = ''
                        elif currentFrag != 'eof':
                            if thisChar in '| =><)':
                                # lookup the fragment code
                                fragRecord = self.getRecord('CFG_ERFRAG', 'ERFRAG_CODE', currentFrag)
                                if not fragRecord:
                                    colorize_msg('Invalid fragment reference: %s' % currentFrag, 'B')
                                    return
                                else:
                                    dependencyList.append(str(fragRecord['ERFRAG_ID']))
                                currentFrag = 'eof'
                            else:
                                currentFrag += thisChar
                    # next list of fragments
                    startPos = sourceString.find('FRAGMENT[')

        self.cfgData['G2_CONFIG']['CFG_ERFRAG'][listID]['ERFRAG_SOURCE'] = parmData['SOURCE']
        self.cfgData['G2_CONFIG']['CFG_ERFRAG'][listID]['ERFRAG_DEPENDS'] = ','.join(dependencyList)
        colorize_msg('Fragment source updated!')
        self.configUpdated = True

        print()

    def do_addFragment(self, arg):
        """
        \n\taddFragment {"id": "<fragment_id>", "fragment": "<fragment_code>", "source": "<fragment_source>"}
        \n\n\tFor additional example structures, use getFragment or listFragments\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['FRAGMENT'] = parmData['FRAGMENT'].upper()
        except (ValueError, KeyError) as e:
            print('\nError with argument(s) or parsing JSON - %s \n' % e)
        else:

            maxID = 0
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_ERFRAG'])):
                if self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_CODE'] == parmData['FRAGMENT']:
                    colorize_msg('Fragment %s already exists!' % parmData['FRAGMENT'], 'B')
                    return
                if 'ID' in parmData and int(self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_ID']) == int(
                        parmData['ID']):
                    colorize_msg('Fragment ID %s already exists!' % parmData['ID'], 'B')
                    return
                if self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_ID'] > maxID:
                    maxID = self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_ID']

            if 'ID' not in parmData:
                parmData['ID'] = maxID + 1 if maxID >= 1000 else 1000

            # must have a source field
            if 'SOURCE' not in parmData:
                colorize_msg('A fragment source field is required!', 'B')
                return

            # compute dependencies from source
            # example: './FRAGMENT[./SAME_NAME>0 and ./SAME_STAB>0] or ./FRAGMENT[./SAME_NAME1>0 and ./SAME_STAB1>0]'
            dependencyList = []
            sourceString = parmData['SOURCE']
            startPos = sourceString.find('FRAGMENT[')
            while startPos > 0:
                fragmentString = sourceString[startPos:sourceString.find(']', startPos) + 1]
                sourceString = sourceString.replace(fragmentString, '')
                # parse the fragment string
                currentFrag = 'eof'
                fragmentChars = list(fragmentString)
                potentialErrorString = ''
                for thisChar in fragmentChars:
                    potentialErrorString += thisChar
                    if thisChar == '/':
                        currentFrag = ''
                    elif currentFrag != 'eof':
                        if thisChar in '| =><)':
                            # lookup the fragment code
                            fragRecord = self.getRecord('CFG_ERFRAG', 'ERFRAG_CODE', currentFrag)
                            if not fragRecord:
                                colorize_msg('Invalid fragment reference: %s' % currentFrag, 'B')
                                return
                            else:
                                dependencyList.append(str(fragRecord['ERFRAG_ID']))
                            currentFrag = 'eof'
                        else:
                            currentFrag += thisChar
                # next list of fragments
                startPos = sourceString.find('FRAGMENT[')

            newRecord = {}
            newRecord['ERFRAG_ID'] = int(parmData['ID'])
            newRecord['ERFRAG_CODE'] = parmData['FRAGMENT']
            newRecord['ERFRAG_DESC'] = parmData['FRAGMENT']
            newRecord['ERFRAG_SOURCE'] = parmData['SOURCE']
            newRecord['ERFRAG_DEPENDS'] = ','.join(dependencyList)
            self.cfgData['G2_CONFIG']['CFG_ERFRAG'].append(newRecord)
            self.configUpdated = True
            colorize_msg('Successfully added!', 'success')
            if self.doDebug:
                debug(newRecord)

    def do_copyFragment(self, arg):
        """\ncopyFragment {"currentFragment": "<fragment_code>", "newID": "<fragment_id>", "newFragment": "<fragment_code>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['CURRENTFRAGMENT'] = parmData['CURRENTFRAGMENT'].upper()
            parmData['NEWFRAGMENT'] = parmData['NEWFRAGMENT'].upper()
        except (ValueError, KeyError) as e:
            print('\nError with argument(s) or parsing JSON - %s \n' % e)
        else:

            # lookup fragment and error if doesn't exist
            currentFragmentID = -1
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_ERFRAG']) - 1, -1, -1):
                if self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_CODE'] == parmData['CURRENTFRAGMENT']:
                    currentFragmentID = i
            if currentFragmentID == -1:
                colorize_msg('Fragment %s does not exist!' % parmData['CURRENTFRAGMENT'], 'B')
                return

            maxID = 0
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_ERFRAG'])):
                if self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_CODE'] == parmData['NEWFRAGMENT']:
                    colorize_msg('Fragment %s already exists!' % parmData['NEWFRAGMENT'], 'B')
                    return
                if 'NEWID' in parmData and int(self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_ID']) == int(
                        parmData['NEWID']):
                    colorize_msg('Fragment ID %s already exists!' % parmData['NEWID'], 'B')
                    return
                if self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_ID'] > maxID:
                    maxID = self.cfgData['G2_CONFIG']['CFG_ERFRAG'][i]['ERFRAG_ID']

            if 'NEWID' not in parmData:
                parmData['NEWID'] = maxID + 1 if maxID >= 1000 else 1000

            fragmentCopy = self.cfgData['G2_CONFIG']['CFG_ERFRAG'][currentFragmentID].copy()
            fragmentCopy['ERFRAG_ID'] = int(parmData['NEWID'])
            fragmentCopy['ERFRAG_CODE'] = parmData['NEWFRAGMENT']
            self.cfgData['G2_CONFIG']['CFG_ERFRAG'].append(fragmentCopy)
            self.configUpdated = True
            colorize_msg('Successfully copied!', 'B')
            if self.doDebug:
                debug(fragmentCopy)

    # ===== rule commands =====

    def getRuleJson(self, record):

        return {"id": record["ERRULE_ID"],
                "rule": record["ERRULE_CODE"],
                "desc": record["ERRULE_DESC"],
                "resolve": record["RESOLVE"],
                "relate": record["RELATE"],
                "ref_score": record["REF_SCORE"],
                "fragment": record["QUAL_ERFRAG_CODE"],
                "disqualifier": showNullableJsonNumeric(record["DISQ_ERFRAG_CODE"]),
                "rtype_id": showNullableJsonNumeric(record["RTYPE_ID"]),
                "tier": showNullableJsonNumeric(record["ERRULE_TIER"])}

    def do_listRules(self, arg):
        """\nlistRules [search_filter]\n"""

        json_lines = []
        print()
        for ruleRecord in sorted(self.getRecordList('CFG_ERRULE'), key=lambda k: k['ERRULE_ID']):
            if arg and arg.lower() not in str(ruleRecord).lower():
                continue
            json_lines.append(self.getRuleJson(ruleRecord))
        self.print_json_lines(json_lines)

    def do_getRule(self, arg):
        """\ngetRule [id]\ngetRule [name]\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            if arg.startswith('{'):
                parmData = dictKeysUpper(json.loads(arg))
            elif arg.isdigit():
                parmData = {"ID": arg}
            else:
                parmData = {"RULE": arg}

            if 'RULE' in parmData and len(parmData['RULE'].strip()) != 0:
                searchField = 'ERRULE_CODE'
                searchValue = parmData['RULE'].upper()
            elif 'ID' in parmData and len(parmData['ID'].strip()) != 0:
                searchField = 'ERRULE_ID'
                searchValue = int(parmData['ID'])
            else:
                raise ValueError(arg)
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        foundRecords = self.getRecordList('CFG_ERRULE', searchField, searchValue)
        if not foundRecords:
            print('\nRecord not found!\n')
        else:
            print()
            for thisRecord in sorted(foundRecords, key=lambda k: k['ERRULE_ID']):
                self.print_json_record(self.getRuleJson(thisRecord))
            print()

    def do_deleteRule(self, arg):
        """\ndeleteRule {"id": "<rule_id>"}\n"""

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            if arg.startswith('{'):
                parmData = dictKeysUpper(json.loads(arg))
            elif arg.isdigit():
                parmData = {"ID": arg}
            else:
                parmData = {"RULE": arg}

            if 'RULE' in parmData and len(parmData['RULE'].strip()) != 0:
                searchField = 'ERRULE_CODE'
                searchValue = arg.upper()
            elif 'ID' in parmData and int(parmData['ID']) != 0:
                searchField = 'ERRULE_ID'
                searchValue = int(parmData['ID'])
            else:
                raise ValueError(arg)
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        deleteCnt = 0
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_ERRULE']) - 1, -1, -1):
            if self.cfgData['G2_CONFIG']['CFG_ERRULE'][i][searchField] == searchValue:
                del self.cfgData['G2_CONFIG']['CFG_ERRULE'][i]
                deleteCnt += 1
                self.configUpdated = True
        if deleteCnt == 0:
            colorize_msg('Record not found!', 'S')
        colorize_msg('Successfully deleted!', 'success')

    def do_setRule(self, arg):
        """
        Syntax:
            setRule <partial json configuration>

        Examples:
            setRule {"id": 111, "resolve": "No"}
            setRule {"id": 111, "relate": "Yes", "rtype_id": 2}

        Notes:
            You must at least specify the rule "id" you want to edit.  Then you can change the following settings:
                - resolve
                - relate
                - rtype    <-this is the relationship type 1=Resolve, 2=Possible match, 3=Possibly related, 4=Name only
        """
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['ID'] = int(parmData['ID'])

        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        print()

        # lookup rule and error if doesn't exist
        listID = -1
        for i in range(len(self.cfgData['G2_CONFIG']['CFG_ERRULE'])):
            if self.cfgData['G2_CONFIG']['CFG_ERRULE'][i]['ERRULE_ID'] == parmData['ID']:
                listID = i
        if listID == -1:
            colorize_msg('Rule %s does not exist!' % parmData['ID'])
            return

        if parmData.get('RESOLVE'):
            if parmData['RESOLVE'].upper() not in ('YES', 'NO'):
                colorize_msg('ERROR: Resolve should be Yes or No', 'B')
                return
            if parmData['RESOLVE'].upper() == 'YES':
                parmData['RELATE'] = 'No'
                parmData['RTYPE_ID'] = 1

        if parmData.get('RELATE'):
            if parmData['RELATE'].upper() not in ('YES', 'NO'):
                colorize_msg('ERROR: Relate should be Yes or No', 'B')
                return
            if parmData['RELATE'].upper() == 'YES':
                if parmData.get('RTYPE_ID'):
                    if parmData.get('RTYPE_ID') not in (2,3,4):
                        colorize_msg('ERROR: Relationship type (RTYPE_ID) must be 2 (possible match), 3 (possibly related) or 4 (name only)', 'B')
                        return
                elif self.cfgData['G2_CONFIG']['CFG_ERRULE'][listID]['RTYPE_ID'] == 1:
                    parmData['RTYPE_ID'] = 2

        if parmData.get('RULE'):
            self.cfgData['G2_CONFIG']['CFG_ERRULE'][listID]['ERRULE_CODE'] = parmData['RULE']
            colorize_msg('Rule code updated!')
            self.configUpdated = True

        if parmData.get('DESC'):
            self.cfgData['G2_CONFIG']['CFG_ERRULE'][listID]['ERRULE_DESC'] = parmData['DESC']
            colorize_msg('Rule description updated!')
            self.configUpdated = True

        if parmData.get('FRAGMENT'):
            self.cfgData['G2_CONFIG']['CFG_ERRULE'][listID]['QUAL_ERFRAG_CODE'] = parmData['FRAGMENT']
            colorize_msg('Rule fragment updated!')
            self.configUpdated = True

        if parmData.get('DISQUALIFIER'):
            self.cfgData['G2_CONFIG']['CFG_ERRULE'][listID]['DISQ_ERFRAG_CODE'] = parmData['DISQUALIFIER']
            colorize_msg('Rule disqualifier updated!')
            self.configUpdated = True

        if parmData.get('RESOLVE'):
            self.cfgData['G2_CONFIG']['CFG_ERRULE'][listID]['RESOLVE'] = parmData['RESOLVE'].capitalize()
            colorize_msg('Rule resolve updated!')
            self.configUpdated = True

        if parmData.get('RELATE'):
            self.cfgData['G2_CONFIG']['CFG_ERRULE'][listID]['RELATE'] = parmData['RELATE'].capitalize()
            colorize_msg('Rule relate updated!')
            self.configUpdated = True

        if parmData.get('RTYPE_ID'):
            self.cfgData['G2_CONFIG']['CFG_ERRULE'][listID]['RTYPE_ID'] = parmData['RTYPE_ID']
            colorize_msg('Relationship type (RTYPE_ID) updated!')
            self.configUpdated = True

        print()

    def do_addRule(self, arg):
        """
        \n\taddRule {"id": 130, "rule": "SF1_CNAME", "tier": 30, "resolve": "Yes", "relate": "No", "ref_score": 8, "fragment": "SF1_CNAME", "disqualifier": "DIFF_EXCL", "rtype_id": 1}
        \n\n\tFor additional example structures, use getRule or listRules\n
        """

        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return

        try:
            parmData = dictKeysUpper(json.loads(arg))
            parmData['ID'] = int(parmData['ID'])
        except (ValueError, KeyError) as e:
            print('\nError with argument(s) or parsing JSON - %s \n' % e)
        else:

            maxID = 0
            for i in range(len(self.cfgData['G2_CONFIG']['CFG_ERRULE'])):
                if self.cfgData['G2_CONFIG']['CFG_ERRULE'][i]['ERRULE_CODE'] == parmData['RULE']:
                    colorize_msg('Rule %s already exists!' % parmData['FRAGMENT'], 'B')
                    return
                if 'ID' in parmData and int(self.cfgData['G2_CONFIG']['CFG_ERRULE'][i]['ERRULE_ID']) == int(
                        parmData['ID']):
                    colorize_msg('Rule ID %s already exists!' % parmData['ID'], 'B')
                    return
                if self.cfgData['G2_CONFIG']['CFG_ERRULE'][i]['ERRULE_ID'] > maxID:
                    maxID = self.cfgData['G2_CONFIG']['CFG_ERRULE'][i]['ERRULE_ID']

            if 'ID' not in parmData:
                parmData['ID'] = maxID + 1 if maxID >= 1000 else 1000

            # must have a valid fragment field
            if 'FRAGMENT' not in parmData:
                colorize_msg('A fragment source field is required!', 'B')
                return
            else:
                # lookup the fragment code
                fragRecord = self.getRecord('CFG_ERFRAG', 'ERFRAG_CODE', parmData['FRAGMENT'])
                if not fragRecord:
                    colorize_msg('Invalid fragment reference: %s' % parmData['FRAGMENT'], 'B')
                    return

            # if no rule code, replace with fragment
            if 'CODE' not in parmData:
                parmData['CODE'] = parmData['FRAGMENT']

            # default or validate the disqualifier
            if 'DISQUALIFIER' not in parmData or not parmData['DISQUALIFIER']:
                parmData['DISQUALIFIER'] = None
            else:
                # lookup the disqualifier code
                fragRecord = self.getRecord('CFG_ERFRAG', 'ERFRAG_CODE', parmData['DISQUALIFIER'])
                if not fragRecord:
                    colorize_msg('Invalid disqualifer reference: %s' % parmData['DISQUALIFIER'], 'B')
                    return

            if 'TIER' not in parmData or not parmData['TIER']:
                parmData['TIER'] = None
            else:
                if not isinstance(parmData['TIER'], int) and parmData['TIER'].lower() != 'null':
                    try:
                        parmData['TIER'] = int(parmData['TIER'])
                    except ValueError:
                        colorize_msg(f'Invalid TIER value ({parmData["TIER"]}), should be an integer', 'B')
                        return

            newRecord = {}
            newRecord['ERRULE_ID'] = int(parmData['ID'])
            newRecord['ERRULE_CODE'] = parmData['RULE']
            newRecord['ERRULE_DESC'] = parmData['DESC'] if 'DESC' in parmData and parmData['DESC'] else parmData['RULE']
            newRecord['RESOLVE'] = parmData['RESOLVE']
            newRecord['RELATE'] = parmData['RELATE']
            newRecord['REF_SCORE'] = int(parmData['REF_SCORE'])
            newRecord['RTYPE_ID'] = int(parmData['RTYPE_ID'])
            newRecord['QUAL_ERFRAG_CODE'] = parmData['FRAGMENT']
            newRecord['DISQ_ERFRAG_CODE'] = storeNullableJsonString(parmData['DISQUALIFIER'])
            newRecord['ERRULE_TIER'] = parmData['TIER']

            self.cfgData['G2_CONFIG']['CFG_ERRULE'].append(newRecord)
            self.configUpdated = True
            colorize_msg('Successfully added!', 'success')
            if self.doDebug:
                debug(newRecord)

    # ===== system parameters  =====

    def do_listSystemParameters(self, arg):
        """\nlistSystemParameters\n"""

        for i in self.cfgData['G2_CONFIG']['CFG_RTYPE']:
            if i["RCLASS_ID"] == 2:
                print(f'\n{{"relationshipsBreakMatches": "{i["BREAK_RES"]}"}}\n')
                break

    def do_setSystemParameter(self, arg):
        """\nsetSystemParameter {"parameter": "<value>"}\n"""

        validParameters = ('relationshipsBreakMatches')
        if not arg:
            self.do_help(sys._getframe(0).f_code.co_name)
            return
        try:
            parmData = json.loads(arg)  # don't want these upper
        except (ValueError, KeyError) as err:
            colorize_msg(f'Invalid parameter: {err}', 'error')
            return

        # not really expecting a list here, getting the dictionary key they used
        for parameterCode in parmData:
            parameterValue = parmData[parameterCode]

            if parameterCode not in validParameters:
                colorize_msg('%s is an invalid system parameter' % parameterCode, 'B')

            # set all disclosed relationship types to break or not break matches
            elif parameterCode == 'relationshipsBreakMatches':
                if parameterValue.upper() in ('YES', 'Y'):
                    breakRes = 1
                elif parameterValue.upper() in ('NO', 'N'):
                    breakRes = 0
                else:
                    colorize_msg('%s is an invalid parameter for %s' % (parameterValue, parameterCode), 'B')
                    return

                for i in range(len(self.cfgData['G2_CONFIG']['CFG_RTYPE'])):
                    if self.cfgData['G2_CONFIG']['CFG_RTYPE'][i]['RCLASS_ID'] == 2:
                        self.cfgData['G2_CONFIG']['CFG_RTYPE'][i]['BREAK_RES'] = breakRes
                        self.configUpdated = True

    def do_touch(self, arg):
        """\nMarks configuration object as modified when no configuration changes have been applied yet.\n"""

        # This is a no-op. It marks the configuration as modified, without doing anything to it.
        self.configUpdated = True
        print()

    # ===== Class Utils =====

    def print_json_record(self, json_obj):
        if type(json_obj) not in [dict, list]:
            json_obj = json.loads(json_obj)

        if self.current_get_format == 'json':
            json_str = json.dumps(json_obj, indent=4)
        else:
            json_str = json.dumps(json_obj)

        if self.pygmentsInstalled:
            render_string = highlight(json_str, lexers.JsonLexer(), formatters.TerminalFormatter())
        else:
            render_string = colorize_json(json_str)

        if len(render_string.split('\n')) < 500:
            print(f'\n{render_string}\n')
        else:
            less = subprocess.Popen(["less", '-FMXSR'], stdin=subprocess.PIPE)
            try:
                less.stdin.write(render_string.encode('utf-8'))
            except IOError:
                pass
            less.stdin.close()
            less.wait()

    def print_json_lines(self, json_lines, display_header=''):
        if not json_lines:
            colorize_msg('Nothing to display', 'warning')
            return

        if self.current_list_format == 'table' and not prettytable:
            print('\nPlease install python pretty table (pip3 install prettytable)\n')
            return

        if display_header:
            print(f'\n{display_header}')

        if self.current_list_format == 'table':
            tblColumns = list(json_lines[0].keys())
            columnHeaderList = []
            for attr_name in tblColumns:
                columnHeaderList.append(colorize(attr_name,'attr_color'))
            table_object = prettytable.PrettyTable()
            table_object.field_names = columnHeaderList
            row_count = 0
            for json_data in json_lines:
                row_count += 1
                tblRow = []
                for attr_name in tblColumns:
                    attr_value = json.dumps(json_data[attr_name]) if type(json_data[attr_name]) in (list, dict) else str(json_data[attr_name])
                    if row_count % 2 == 0: # for future alternating colors
                        tblRow.append(colorize(attr_value, 'dim'))
                    else:
                        tblRow.append(colorize(attr_value, 'dim'))
                table_object.add_row(tblRow)

            table_object.align = 'l'
            if hasattr(prettytable, 'SINGLE_BORDER'):
                table_object.set_style(prettytable.SINGLE_BORDER)
            table_object.hrules = 1
            render_string = table_object.get_string()

        elif self.current_list_format == 'jsonl':
            render_string = ''
            for line in json_lines:
                if self.pygmentsInstalled:
                    render_string += highlight(json.dumps(line), lexers.JsonLexer(), formatters.TerminalFormatter()).replace('\n','') + '\n'
                else:
                    render_string += colorize_json(json.dumps(line)) + '\n'
        else:
            json_doc = '['
            for line in json_lines:
                json_doc += json.dumps(line) + ', '
            json_doc = json_doc[0:-2] + ']'
            render_string = colorize_json(json.dumps(json.loads(json_doc), indent=4))

        less = subprocess.Popen(["less", '-FMXSR'], stdin=subprocess.PIPE)
        try:
            less.stdin.write(render_string.encode('utf-8'))
        except IOError:
            pass
        less.stdin.close()
        less.wait()

        print()


# ===== Utility functions =====


def getFeatureBehavior(feature):
    featureBehavior = feature['FTYPE_FREQ']
    if str(feature['FTYPE_EXCL']).upper() in ('1', 'Y', 'YES'):
        featureBehavior += 'E'
    if str(feature['FTYPE_STAB']).upper() in ('1', 'Y', 'YES'):
        featureBehavior += 'S'
    return featureBehavior


def parseFeatureBehavior(behaviorCode):
    behaviorDict = {"EXCLUSIVITY": 'No', "STABILITY": 'No'}
    if behaviorCode not in ('NAME', 'NONE'):
        if 'E' in behaviorCode:
            behaviorDict['EXCLUSIVITY'] = 'Yes'
            behaviorCode = behaviorCode.replace('E', '')
        if 'S' in behaviorCode:
            behaviorDict['STABILITY'] = 'Yes'
            behaviorCode = behaviorCode.replace('S', '')
    if behaviorCode in ('A1', 'F1', 'FF', 'FM', 'FVM', 'NONE', 'NAME'):
        behaviorDict['FREQUENCY'] = behaviorCode
    else:
        behaviorDict = None
    return behaviorDict


def dictKeysUpper(dictionary):
    if isinstance(dictionary, list):
        return [v.upper() for v in dictionary]
    elif isinstance(dictionary, dict):
        return {k.upper(): v for k, v in dictionary.items()}
    else:
        return dictionary


def showNullableJsonString(val):
    if not val:
        return 'null'
    else:
        return '"%s"' % val


def showNullableJsonNumeric(val):
    if not val:
        return 'null'
    else:
        return '%s' % val


def storeNullableJsonString(val):
    if not val or val == 'null':
        return None
    else:
        return val


def storeNullableJsonNumeric(val):
    if not val or val == 'null':
        return None
    else:
        return val


def debug(data, loc=''):
    colorize_msg(textwrap.dedent(f'''\
    <--- DEBUG
    Func: {sys._getframe(1).f_code.co_name}
    Loc: {loc}
    Data: {data}
    --->
    '''), 'E')

if __name__ == '__main__':

    argParser = argparse.ArgumentParser()
    argParser.add_argument("fileToProcess", default=None, nargs='?')
    argParser.add_argument('-c', '--ini-file-name', dest='ini_file_name', default=None,
                           help='name of a G2Module.ini file to use')
    argParser.add_argument('-f', '--force', dest='forceMode', default=False, action='store_true',
                           help='when reading from a file, execute each command without prompts')
    argParser.add_argument('-H', '--histDisable', dest='histDisable', action='store_true', default=False,
                           help='disable history file usage')
    argParser.add_argument('-D', '--debug', action='store_true', default=False, help='turn on debug')
    args = argParser.parse_args()

    # Check if INI file or env var is specified, otherwise use default INI file
    iniFileName = None

    if args.ini_file_name:
        iniFileName = pathlib.Path(args.ini_file_name)
    elif os.getenv("SENZING_ENGINE_CONFIGURATION_JSON"):
        g2module_params = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
    else:
        iniFileName = pathlib.Path(G2Paths.get_G2Module_ini_path())

    if iniFileName:
        G2Paths.check_file_exists_and_readable(iniFileName)
        iniParamCreator = G2IniParams()
        g2module_params = iniParamCreator.getJsonINIParams(iniFileName)

    cmd_obj = G2CmdShell(g2module_params, args.histDisable, args.forceMode, args.fileToProcess, args.debug)

    if args.fileToProcess:
        cmd_obj.fileloop()
    else:
        cmd_obj.cmdloop()

    sys.exit()
