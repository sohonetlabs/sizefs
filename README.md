SizeFS
======

A mock Filesystem that exists in memory only and allows for the creation of
files of a size specified by the filename. The files contents can be specified
by a set of regular expressions.

For example, reading a file named 128M+1B will return a file of 128 Megabytes
plus 1 byte, reading a file named 128M-1B will return a file of 128 Megabytes
minus 1 byte

Example Usage
--------------

Create Size File objects in memory:

    > from sizefs import SizeFS
    > sfs = SizeFS()
    > sfs.get_size_file('1B').read(0, 1)
    > sfs.get_size_file('2B').read(0, 2)
    > sfs.get_size_file('1K').read(0, 1024)
    > sfs.get_size_file('128KB').read(0, 100))

The folder structure is used to determine the content of the files:

    > sfs.get_size_file('/zeros/5B').read(0, 5)
    out> 00000

    > sfs.get_size_file('/ones/5B').read(0, 5)
    out> 11111

    > sfs.get_size_file('/alpha_num/5B').read(0, 5)
    out> TMdEv

Folders can be created to manipulate the data:

    > sfs.mkdir('/regex1', None)
    > sfs.setxattr('/regex1', 'filler', '0', None)
    > print sfs.get_size_file('/alpha_num/5B').read(0, 5)

    out> 00000

    > sfs.mkdir('/regex2', None)
    > sfs.setxattr('/regex2', 'filler', '1', None)
    > print sfs.get_size_file('/regex2/5B').read(0, 5)

    out> 11111

    > sfs.mkdir('/regex3', None)
    > sfs.setxattr('/regex3', 'filler', '[a-zA-Z0-9]', None)
    > print sfs.get_size_file('/regex3/5B').read(0, 5)

    out> 1JAbd

Files can be added to SizeFS using sfs.create ::

    > sfs.mkdir('/regex3', None)
    > sfs.setxattr('/regex3', 'filler', '[a-zA-Z0-9]', None)
    > sfs.create('/regex3/5B', None)
    > print sfs.read('/regex3/5B', 5, 0, None)

    out> aS8yG

    > sfs.create('/regex3/128K', None)
    > print len(sfs.read('/regex3/128K', 128*1024, 0, None))

    out> 131072

    > sfs.create('/regex3/128K-1B', None)
    > print len(sfs.read('/regex3/128K-1B', 128*1024, 0, None))

    out> 131071

    > sfs.create('/regex3/128K+1B', None)
    > print len(sfs.read('/alphanum/128K+1B', 128*1024+1, 0, None))

    out> 131073

File content can be generated that matches a regex pattern by adding a directory

    > sfs.mkdir('/regex1')
    > sfs.setxattr('/regex1','filler','a(bcd)*e{4}[a-z03]*')
    > sfs.create('/regex1','128K')
    > print len(sfs.open('regex1/128KB').read(0, 128*1024))

    out> 131072

    > sfs.create('/regex1','128K-1B')
    > print len(sfs.open('regex1/128K-1B').read(0, 128*1024-1))

    out> 131071

    > sfs.create('/regex1','128K+1B')
    > print len(sfs.open('regex1/128KB+1B').read(0, 128*1024+1))

    out> 131073


Extended Usage
--------------

We can set up to 5 properties:

    prefix     - defined pattern for the start of a file (default = "")
    suffix     - defined pattern for the end of a file (default = "")
    filler     - repeating pattern to fill file content (default = 0)
    padder     - single character to fill between content and footer (default = 0)
    max_random - the largest number a + or * will resolve to 

Where 'prefix', 'suffix', 'filler', and 'padder' conform to the following
grammar:

      <Regex> ::= <Pattern>

      <Pattern> ::= <Expression>
                | <Expression> <Pattern>

      <Expression> ::= <Char> [<Multiplier>]
                   | "(" <Pattern> ")" [<Multiplier>]
                   | "[" <Set> "]" [<Multiplier>]

      <Multiplier> ::= "*"
                   | "+"
                   | "?"
                   | '{' <Num> '}'

      <Set> ::= <Char>
              | <Char> "-" <Char>
              | <Set> <Set>

If the requested file sizes are too small for the combination of header, footer
and some padding, then a warning will be logged, but the file will still
return as much content as possible to fill the exact file size requested.

The file contents will always match the following pattern:

    ^prefix(filler)*(padder)*suffix$

The generator will always produce a string containing the prefix and suffix if a
file of sufficient size is requested. Following that, the generator will fill
the remaining space with 'filler' generated as many times as can be contained.
If a filler pattern is generated that does not fit within the remaining space
the remainder is filled using the (possibly incomplete) padder pattern. The
padder pattern will only be used if a complete filler pattern will not fit in
the space remaining.

'max_random' is used to define the largest random repeat factor of any + or *
operators.

Random seeks within a file may produce inconsistent results for general file
contents, however prefix and suffix will always be consistent with the requested
pattern.


Mounting as a filesystem
------------------------

Mac Mounting - http://osxfuse.github.com/

From the command line:

    > python ./sizefs.py <mount_point>


