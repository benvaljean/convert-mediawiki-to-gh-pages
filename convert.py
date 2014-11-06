#!/usr/bin/env python

class Mysql:

    def __init__ (self, database, username, password=None):
        """
        Initialize.
        """

        import subprocess
        import sys

        self.database = database
        self.username = username
        self.password = password

        query = "use %s;\n" % (self.database)
        query += "select page.page_title, text.old_text from text "
        query += "inner join revision on revision.rev_text_id = text.old_id "
        query += "inner join page on page.page_id = revision.rev_page "
        query += "where (revision.rev_id = page.page_latest && "
        query += "page.page_namespace = 0)\n"

        if sys.version_info.major == 3:
            query = bytes(query, "UTF-8")

        mysql_command = [ "mysql", "-u", self.username ]
        if self.password:
            mysql_command += [ "--password=%s" % (self.password) ]

        mysql = subprocess.Popen(mysql_command, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        mysql.stdin.write(query)

        self.stdoutdata, self.stderrdata = mysql.communicate()

        if sys.version_info.major == 3:
            self.stdoutdata = self.stdoutdata.decode("UTF-8")

        if mysql.returncode != 0:
            for i in self.stdoutdata.splitlines():
                print(i.rstrip())
            raise Exception("failed to query database")

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

    if os.path.exists("pages"):
        raise Exception("The output path '%s' already exists" % ("pages"))

    mysql = Mysql(options.database, options.user, options.password)

    pandoc_cmd = [ "pandoc", "--from", "mediawiki", "--to", "markdown_github",
            "--base-header-level", "2" ]

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
