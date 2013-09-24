import pandoc
import os

pandoc.core.PANDOC_PATH = '/usr/local/bin/pandoc'

if not os.path.exists(pandoc.core.PANDOC_PATH):
    raise ValueError('No pandoc executable')

doc = pandoc.Document()
doc.markdown = open('README.md').read()
f = open('README.txt', 'w+')
f.write(doc.rst)
f.close()

