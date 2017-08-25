SizeFS
======

A mock Filesystem that exists in memory only and allows for the creation of
files of a size specified by the filename.

For example, reading a file named 128M+1B will return a file of 128 Megabytes
plus 1 byte, reading a file named 128M-1B will return a file of 128 Megabytes
minus 1 byte

Within the filesystem one level of folders may be created. Each of these folders
can have its extended attributes set to determine the default contents of each
file within the folder. The attributes of individual files may be overridden,
and, when mounted as a filesystem using fuse, should be set using 'xattr' for
OS X, or 'attr' for Linux. The attributes are described below in the 'Extended Usage'
section.

Files may only be created within the folders and can only be named with a valid
size descriptor. The names of the files should be a number followed by one of the
letters B, K, M, G, T, P or E (to mean bytes, kilobytes, megabytes ...). Optionally
an addition or subtraction may be specified to modify the base size of the file.

Examples of valid filenames:

    100K     - A 100 kilobyte file.
    4M       - A 4 megabyte file.
    2G-1B    - A file 1 byte smaller than 2 gigabytes.
    100K+10K - A file 10 kilobytes larger than 100 kilobytes.
    10E      - A ten exabyte file (yes really!)

File contents are generated as they are read, so it is entirely possible to 'create'
files that are larger than any available RAM or HD storage. This can be very useful
for testing large external storage systems, and the +/- operations are useful for
exploring file size limitations without having to specify a file size as a huge
number of bytes. The contents of each file are specified by a set of regular
expressions that are initially inherited from the containing folder.

Example Usage - SizeFS
----------------------

Create Size File objects in memory:

    from sizefs import SizeFS
    sfs = SizeFS()
    sfs.open('/1B').read()
    sfs.open('/20B').read(20)
    sfs.open('/2K').read(1024)
    sfs.open('/128K').read(1024*128)
    sfs.open('/4G').read(4*1024*1024)

The folder structure can be used to determine the content of the files:

    sfs.open('/zeros/5B').read(5)
    out> 00000

    sfs.open('/ones/5B').read(5)
    out> 11111

    sfs.open('/alpha_num/5B').read(5)
    out> TMdEv


Extended Usage - SizefsFuse
---------------------------

The folders 'ones', 'zeros' and 'alpha\_num' are always present, but new
folders can also be created. When files are created in a folder, the
xattrs of the folder determine that file's content until the file's
xattrs are updated:


    from sizefs.sizefsFuse import SizefsFuse
    sfs = SizefsFuse()
    sfs.mkdir('/regex1', None)
    sfs.setxattr('/regex1', 'generator', 'regex', None)
    sfs.setxattr('/regex1', 'filler', 'regex', None)
    print sfs.read('/regex1/5B', 5, 0, None)

    out> regex

    sfs.setxattr('/regex1/5B', 'filler', 'string', None)
    print sfs.read('/regex1/5B', 5, 0, None)

    out> string

    sfs.setxattr('/regex1/5B', 'filler', 'a{2}b{2}c', None)
    print sfs.read('/regex1/5B', 5, 0, None)

    out> aabbc

Files can also be added to SizeFS without reading their contents using
sfs.create():


    sfs.mkdir('/folder', None)
    sfs.create('/folder/5B', None)
    print sfs.read('/folder/5B', 5, 0, None)

    out> 11111

And as discussed above, the name of the file determines its size:



    # Try to read more contents than the files contains
    print len(sfs.read('/regex3/128K', 256*1000, 0, None))

    out> 128000

    # Try to read more contents than the files contains
    print len(sfs.read('/regex3/128K-1B', 256*1000, 0, None))

    out> 127999

    # Try to read more contents than the files contains
    print len(sfs.read('/alphanum/128K+1B', 256*1000, 0, None))

    out> 128001


The 'generator' xattr property defines the file content and can be set to one
of:

    ones       - files are filled with ones
    zeros      - files are filled with zeros
    alpha_num  - files are filled with alpha numeric characters
    regex      - files are filled according to a collection of regular expression patterns

We can set up to 5 properties to control the regular expression patterns:

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

Testing
------------------------

Single test run requires pytest

From the command line:

    pytest

Full test run requires tox

From the command line:

    tox

Mounting as a filesystem
------------------------

Mac Mounting - http://osxfuse.github.com/

    Usage:
      sizefs.py [--debug] <mount_pount>
      sizefs.py --version

      Options:
        --debug           Debug
        -h --help         Show this screen.
        --version         Show version.
