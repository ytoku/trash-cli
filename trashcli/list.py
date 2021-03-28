import argparse

from .fs import FileSystemReader
from .trash import version
from .trash import TopTrashDirRules
from .trash import TrashDirsScanner
from .trash import Harvester
from .trash import PrintHelp
from .trash import PrintVersion
from .trash import parse_deletion_date
from .trash import ParseError
from .trash import parse_path
from .trash import unknown_date

def main():
    import sys
    import os
    from trashcli.list_mount_points import os_mount_points
    ListCmd(
        out          = sys.stdout,
        err          = sys.stderr,
        environ      = os.environ,
        getuid       = os.getuid,
        list_volumes = os_mount_points,
    ).run(*sys.argv)

class ListCmd:
    def __init__(self, out,
                       err,
                       environ,
                       list_volumes,
                       getuid,
                       file_reader = FileSystemReader(),
                       version     = version):

        self.output       = ListCmdOutput(out, err)
        self.err          = self.output.err
        self.environ      = environ
        self.list_volumes = list_volumes
        self.getuid       = getuid
        self.file_reader  = file_reader
        self.contents_of  = file_reader.contents_of
        self.version      = version

    def run(self, *argv):
        parser = maker_parser(True)
        parsed = parser.parse_args(argv[1:])
        if parsed.help:
            help_printer = PrintHelp(self.description, self.output.println)
            help_printer(argv[0])
        elif parsed.version:
            version_printer = PrintVersion(self.output.println, self.version)
            version_printer(argv[0])
        else:
            self.list_trash(parsed.trash_dirs)

    def list_trash(self, user_specified_trash_dirs):
        harvester = Harvester(self.file_reader)
        harvester.on_volume = self.output.set_volume_path
        harvester.on_trashinfo_found = self._print_trashinfo

        trashdirs_scanner = TrashDirsScanner(self.environ,
                                             self.getuid,
                                             self.list_volumes,
                                             TopTrashDirRules(self.file_reader))
        trash_dirs = decide_trash_dirs(user_specified_trash_dirs,
                                       trashdirs_scanner.scan_trash_dirs())
        for event, args in trash_dirs:
            if event == TrashDirsScanner.Found:
                path, volume = args
                harvester.analize_trash_directory(path, volume)
            elif event == TrashDirsScanner.SkippedBecauseParentNotSticky:
                path, = args
                self.output.top_trashdir_skipped_because_parent_not_sticky(path)
            elif event == TrashDirsScanner.SkippedBecauseParentIsSymlink:
                path, = args
                self.output.top_trashdir_skipped_because_parent_is_symlink(path)

    def _print_trashinfo(self, path):
        try:
            contents = self.contents_of(path)
        except IOError as e :
            self.output.print_read_error(e)
        else:
            deletion_date = parse_deletion_date(contents) or unknown_date()
            try:
                path = parse_path(contents)
            except ParseError:
                self.output.print_parse_path_error(path)
            else:
                self.output.print_entry(deletion_date, path)
    def description(self, program_name, printer):
        printer.usage('Usage: %s [OPTIONS...]' % program_name)
        printer.summary('List trashed files')
        printer.options(
           "  --version   show program's version number and exit",
           "  -h, --help  show this help message and exit")
        printer.bug_reporting()


def decide_trash_dirs(user_specified_dirs,
                      system_dirs):
    return system_dirs

def maker_parser(experimental):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--version', action='store_true', default=False)
    parser.add_argument('--help', action='store_true', default=False)
    if experimental:
        parser.add_argument('--trash-dir', action='append', default=[],
                            dest='trash_dirs')
    return parser


class ListCmdOutput:
    def __init__(self, out, err):
        self.out = out
        self.err = err
    def println(self, line):
        self.out.write(line+'\n')
    def error(self, line):
        self.err.write(line+'\n')
    def print_read_error(self, error):
        self.error(str(error))
    def print_parse_path_error(self, offending_file):
        self.error("Parse Error: %s: Unable to parse Path." % (offending_file))
    def top_trashdir_skipped_because_parent_not_sticky(self, trashdir):
        self.error("TrashDir skipped because parent not sticky: %s"
                % trashdir)
    def top_trashdir_skipped_because_parent_is_symlink(self, trashdir):
        self.error("TrashDir skipped because parent is symlink: %s"
                % trashdir)
    def set_volume_path(self, volume_path):
        self.volume_path = volume_path
    def print_entry(self, maybe_deletion_date, relative_location):
        import os
        original_location = os.path.join(self.volume_path, relative_location)
        self.println("%s %s" %(maybe_deletion_date, original_location))
