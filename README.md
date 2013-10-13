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

Example Usage
--------------

Create Size File objects in memory:

    from sizefs import SizeFS
    sfs = SizeFS()
    sfs.read('/1B', 1, 0, None)
    sfs.read('/2B', 2, 0, None)
    sfs.read('/2K', 1024, 0, None)
    sfs.read('/128K', 1024*128, 0, None)
    sfs.read('/4G', 4*1024*1024, 0, None)

The folder structure is used to determine the content of the files:

    sfs.read('/zeros/5B', 5, 0, None).read(0, 5)
    out> 00000

    sfs.read('/ones/5B', 5, 0, None).read(0, 5)
    out> 11111

    sfs.read('/alpha_num/5B', 5, 0, None).read(0, 5)
    out> TMdEv

Folders can be created to manipulate the data:

    sfs.mkdir('/regex1', None)
    sfs.setxattr('/regex1', 'filler', '0', None)
    print sfs.read('/alpha_num/5B', 5, 0, None).read(0, 5)

    out> 00000

    sfs.mkdir('/regex2', None)
    sfs.setxattr('/regex2', 'filler', '1', None)
    print sfs.read('/regex2/5B', 5, 0, None).read(0, 5)

    out> 11111

    sfs.mkdir('/regex3', None)
    sfs.setxattr('/regex3', 'filler', '[a-zA-Z0-9]', None)
    print sfs.read('/regex3/5B', 5, 0, None).read(0, 5)

    out> 1JAbd

Files can be added to SizeFS using sfs.create:

    sfs.mkdir('/regex3', None)
    sfs.setxattr('/regex3', 'filler', '[a-zA-Z0-9]', None)
    sfs.create('/regex3/5B', None)
    print sfs.read('/regex3/5B', 5, 0, None)

    out> aS8yG

    sfs.create('/regex3/128K', None)
    print len(sfs.read('/regex3/128K', 128*1024, 0, None))

    out> 131072

    sfs.create('/regex3/128K-1B', None)
    print len(sfs.read('/regex3/128K-1B', 128*1024, 0, None))

    out> 131071

    sfs.create('/regex3/128K+1B', None)
    print len(sfs.read('/alphanum/128K+1B', 128*1024+1, 0, None))

    out> 131073

File content can be generated that matches a regex pattern by adding a directory

    sfs.mkdir('/regex1')
    sfs.setxattr('/regex1','filler','a(bcd)*e{4}[a-z03]*')
    sfs.create('/regex1','128K')
    print len(sfs.open('regex1/128KB').read(0, 128*1024))

    out> 131072

    sfs.create('/regex1','128K-1B')
    print len(sfs.open('regex1/128K-1B').read(0, 128*1024-1))

    out> 131071

    sfs.create('/regex1','128K+1B')
    print len(sfs.open('regex1/128KB+1B').read(0, 128*1024+1))

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

Testing
------------------------

Requires nose

From the command line:

    nosetests

Mounting as a filesystem
------------------------

Mac Mounting - http://osxfuse.github.com/

From the command line:

    python ./sizefs.py <mount_point>


