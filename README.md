git-bigstore
============

git-bigstore is an extension to Git that helps you track big files. For technical details, check out the [Wiki](https://github.com/aurorasoftware/git-bigstore/wiki/Bigstore).

Configuration
-------------

To get started, set up an Amazon S3, Google Cloud Storage, or Rackspace Cloud account to store stuff. Once you have your credentials available, you're ready to get started:

    $ pip install git-bigstore
    $ git bigstore init

At this point, you will be prompted for which backend you would like to use and your credentials. Once you've entered this information, your Git repository is now prepared to track big files. If a ".bigstore" configuration file already exists in your repository, you will not be prompted for backend credentials.

To specify filetypes to store remotely, add an entry to your .gitattributes. E.g., if you only want to store your big archive files in your backend, run this command in your repository root:

    $ echo "*.zip filter=bigstore" > .gitattributes

After you run this, every time you stage a zip file, it will transparently copy the file to ".git/bigstore/objects" and will replace the file contents (as stored in git) with relevant identifying information.

git-bigstore won't automatically sync to your selected backend after a commit. To push changed files, just run:

    $ git bigstore push

To pull down remote changes:

    $ git bigstore pull

If uploading and downloading everything isn't your cup of tea, you can also specify the paths you care about to these commands. For example, let's say you just want to download the Word and PDF files in your repo. This is what you'd do:

    $ git bigstore pull *.pdf *.doc

Makes sense.

You can also view the upload and download history of any file tracked by bigstore.

    $ git bigstore log tsd20130403.pdf
    Mon Apr 8 11:48:51 2013 +0000: gs → Dan Loewenherz <dloewenherz@gmail.com>
    Mon Apr 8 11:48:04 2013 +0000: gs ← Dan Loewenherz <dloewenherz@gmail.com


But "INSERT X HERE" already exists...
---------------------------------

I've been using git-media for a few days now, and I've observed that it breaks down because it violates the following guideline in the [Git docs](https://www.kernel.org/pub/software/scm/git/docs/gitattributes.html):

> For best results, clean should not alter its output further if it is run twice ("clean→clean" should be equivalent to "clean"), and multiple smudge commands should not alter clean's output ("smudge→smudge→clean" should be equivalent to "clean").

This made it a bit tough to collaborate with multiple people, since Git would try to clean things that had already been cleaned, and smudge things that had already been smudged. No good!

git-annex is another alternative, but it's solving a different problem and its implementation is a bit less dependent on Git itself. As a result, you essentially have to learn a whole new set of commands to work with it. I wanted to create something with as minimal complexity as possible.

Copyright
---------

Copyright 2013 Aurora Software LLC <hi@aurora.io>.

Licensed under Apache 2.0. See LICENSE for more details.

