git-bigstore
============

git-bigstore is an extension to Git that helps you track big files.

Configuration
-------------

To get started, set up an Amazon S3 bucket to store stuff. Once you have your access key id and secret access key on hand, run the following:

    $ pip install git-bigstore
    $ git bigstore init
    Please enter your S3 Credentials

    Access Key: XXX
    Secret Key: XXX
    Bucket Name: my-bucket-name

Well, that was easy! Your Git repository is now prepared to track big files. To specify filetypes to store remotely, add an entry to your .gitattributes. E.g., if you only want to store your big archive files in S3, run this command in your repository root:

    $ echo "*.zip filter=bigstore" > .gitattributes

After you run this, every time you stage a zip file, it will transparently copy the file to ".git/bigstore/objects" and will replace the file contents (as stored in git) with an identifier string starting with `bigstore$` and ending with the file's md5 hash.

git-bigstore won't automatically sync to S3 after a commit. To perform a sync, just run:

    $ git bigstore sync

This will download all remote files that aren't stored locally, and will upload all local files that aren't stored remotely.

But "INSERT X HERE" already exists...
---------------------------------

I've been using git-media for a few days now, and I've observed that it breaks down because it violates the following guideline in the [Git docs](https://www.kernel.org/pub/software/scm/git/docs/gitattributes.html):

> For best results, clean should not alter its output further if it is run twice ("clean→clean" should be equivalent to "clean"), and multiple smudge commands should not alter clean's output ("smudge→smudge→clean" should be equivalent to "clean").

This made it a bit tough to collaborate with multiple people, since Git would try to clean things that had already been cleaned, and smudge things that had already been smudged. No good!

Also, git-media hasn't been updated in a while. I promise to be a good maintainer!

git-annex is another alternative, but it's solving a different problem and its implementation is a bit less dependent on Git itself. As a result, you essentially have to learn a whole new set of commands to work with it. I wanted to create something with as minimal complexity as possible.

TODOs
-----

* Support for alternative storage backends (such as Rackspace Files, Google Cloud Storage, and Dropbox)
* Better internal code organization
* Less painless initialization when working on a team (maybe read credentials from a version-controlled configuration file?)
* ???

Copyright
---------

Copyright 2013, Dan Loewenherz <dan@aurora.io>.

Licensed under Apache 2.0. See LICENSE for more details.

