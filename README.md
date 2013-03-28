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

After you run this, every time you stage a csv file, it will transparently copy the file to ".git/bigstore/objects" and will replace the file contents (as stored in git) with an identifier string starting with `bigstore$` and ending with the file's md5 hash.

git-bigstore won't automatically sync to S3 after a commit. To perform a sync, just run:

    $ git bigstore sync

This will download all remote files that aren't stored locally, and will upload all local files that aren't stored remotely.

But `git-media` already exists...
---------------------------------

I've been using git-media for a few days now, and I've observed that it breaks down because it violates the following guideline in the [Git docs](https://www.kernel.org/pub/software/scm/git/docs/gitattributes.html):

> For best results, clean should not alter its output further if it is run twice ("clean→clean" should be equivalent to "clean"), and multiple smudge commands should not alter clean's output ("smudge→smudge→clean" should be equivalent to "clean").

This made it a bit tough to collaborate with multiple people, since Git would try to clean things that had already been cleaned, and smudge things that had already been smudged. No good!

Also, git-media hasn't been updated in a while. I promise to be a good maintainer!

TODOs
-----

* Support for alternative storage backends (such as Rackspace Files, Google Cloud Storage, and Dropbox)
* Better internal code organization
* ???

Copyright
---------

Copyright 2013, Dan Loewenherz <dan@aurora.io>.

Licensed under Apache 2.0. See LICENSE for more details.

