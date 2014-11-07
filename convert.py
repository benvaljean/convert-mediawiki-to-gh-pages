#!/usr/bin/env python

class Mysql:

    def __init__ (self, database, username, password=None):
        """Initialize.

        database The database name.
        username The database username.
        password The password to use. This argument is optional.
        """

        self.database = database
        self.username = username
        self.password = password

        #query = "use %s;\n" % (self.database)
        #query += "select page.page_title, text.old_text from text "
        #query += "inner join revision on revision.rev_text_id = text.old_id "
        #query += "inner join page on page.page_id = revision.rev_page "
        #query += "where (revision.rev_id = page.page_latest && "
        #query += "page.page_namespace = 0)\n"

        self.mysql_command = [ "mysql", "-u", self.username ]
        if self.password:
            self.mysql_command += [ "--password=%s" % (self.password) ]

    def string_io_wrap (self, string):
        """Properly treat strings across python2/3 for IO operations
        (file.write()).

        This function returns a proper string.
        """

        import sys

        if sys.version_info.major == 3:
            string = bytes(string, "UTF-8")

        return string

    def query (self, query):
        """Query the database.

        query The query command to run.

        The function returns a list of strings with the output of the query.
        """

        import subprocess
        import sys

        mysql = subprocess.Popen(self.mysql_command, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        mysql.stdin.write(self.string_io_wrap("use %s;\n" % (self.database)))
        mysql.stdin.write(self.string_io_wrap(query))

        stdoutdata, stderrdata = mysql.communicate()

        if sys.version_info.major == 3:
            stdoutdata = stdoutdata.decode("UTF-8")

        stdoutdata = stdoutdata.splitlines()
        stdoutdata.pop(0)

        if mysql.returncode != 0:
            for i in stdoutdata:
                print(i.rstrip())
            raise Exception("failed to query database")

        return stdoutdata

    def get_page_ids (self):
        """Get all page ids from the database.

        This function returns a tuple of two list of integers, (main_pages,
        user_pages).
        """

        main_pages = [ int(i) for i in
                self.query("select page.page_id from page where page.page_namespace = 0") ]
        user_pages = [ int(i) for i in
                self.query("select page.page_id from page where page.page_namespace = 2") ]

        return (main_pages, user_pages)

    def get_page_name (self, page_id):
        """Get the page name given a page_id."""

        return self.query("select page.page_title from page where page_id = %d" % (page_id))

    def get_page_history (self, page_id):
        """Retrieve the editing history of a page identified by its page_id.

        This function returns a list of tuples, (timestamp, deleted, text).
        The deleted flag indicates whether the page was deleted or not.
        """

        import re

        result = self.query("select revision.rev_timestamp, "
                + "revision.rev_deleted, text.old_text from revision inner "
                + "join text on text.old_id = revision.rev_text_id where "
                + ("rev_page = %d " % (page_id))
                + "order by revision.rev_timestamp")

        parse = re.compile("^\s*([0-9]+)\s+([0-9]+)\s+(.*)$")
        history = []
        for i in result:
            p = parse.search(i)
            if p.group(2) == "0":
                deleted = False
            else:
                deleted = True
            history.append(( p.group(1), deleted, p.group(2) ))

        return history

def main ():
    """
    The main function.
    """

    import argparse
    import os
    import re
    import subprocess
    import sys

    parser = argparse.ArgumentParser()

    parser.add_argument("--database",
            help = "The mysql database",
            required = True)

    parser.add_argument("--user",
            help = "The mysql database user",
            required = True)

    parser.add_argument("--password",
            help = "The mysql database password")

    options = parser.parse_args()

    mysql = Mysql(options.database, options.user, options.password)

    for line in mysql.get_page_ids()[0]:
        print(line)
    history = mysql.get_page_history(1)
    for i in history:
        print(i[0])
    sys.exit(0)

    pandoc_cmd = [ "pandoc", "--from", "mediawiki", "--to", "markdown_github",
            "--base-header-level", "2" ]

    if os.path.exists("pages"):
        raise Exception("The output path '%s' already exists" % ("pages"))

    os.mkdir("pages")

    for line in mysql.stdoutdata.splitlines():
        page = line.split(None, 1)
        if len(page) < 2:
            continue
        page_title = page[0]
        page_text = page[1]
        page_title = re.sub(" ", "_", page_title)
        page_text = page_text.split("\\n")
        pandoc = subprocess.Popen( pandoc_cmd, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True)
        for i in page_text:
            pandoc.stdin.write(i + "\n")
        stdout_lines, stderr_lines = pandoc.communicate()

        new_page = open(os.path.join("./pages", page_title + ".md"), "w")
        new_page.write("---\n")
        new_page.write("layout: default\n")
        new_page.write("title: %s\n" % (re.sub("_", " ", page_title)))
        new_page.write("---\n")
        new_page.write("\n")

        for i in stdout_lines.splitlines():
            new_page.write(i + "\n")
        new_page.close()

if __name__ == "__main__":
    main()
