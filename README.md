git-bigstore
============

git-bigstore is a Git extension that helps you track large files in Git.

Configuration
-------------

To get started with your local repository, just run the following commands to get set up.

    $ pip install git-bigstore
    $ git bigstore init

Now, just add an entry to your .gitattributes file for each filetype you want to store remotely. E.g.:

    $ echo "*.csv filter=bigstore" > .gitattributes

After you run this, every time you stage a csv file, it will transparently copy the file to ".git/storage/objects" and will replace the file contents (as stored in git) with an identifier string starting with "bigstore$" and ending with the file's md5 hash.

By default, git-bigstore won't sync to S3, so to do that, just run:

    $ git bigstore sync

This will download all remote files that aren't stored locally, and will upload all local files that aren't stored remotely.

License
-------

Licensed under Apache 2.0. See LICENSE for more details.

Copyright
---------

Copyright 2013, Dan Loewenherz <dan@aurora.io>.

Licensed under Apache 2.0. See LICENSE for details.

