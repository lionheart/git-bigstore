git-bigstore
============

git-bigstore is an extension to Git that helps you track big files. For technical details, check out the [Wiki](https://github.com/lionheartsw/git-bigstore/wiki).

Requirements
============

* Python 2.7+
* An Amazon S3, Google Cloud Storage, or Rackspace Cloud account

Configuration
-------------

First, install the requirements via pip.

    pip install gitpython==0.3.2.RC1 boto==2.8.0 python-dateutil==1.5 pytz==2012h python-cloudfiles==1.7.10

Then, install bigstore.

    pip install git-bigstore

Finally, go to the directory root of your Git repo and initialize bigstore.

    git bigstore init

At this point, you will be prompted for which backend you would like to use (either S3, Google Storage, or Rackspace Cloudfiles) and your credentials. Once you've entered this information, your Git repository is now prepared to track big files. If a ".bigstore" configuration file already exists in your repository, you will not be prompted for backend credentials.

To specify filetypes to store remotely, add an entry to your .gitattributes. E.g., if you only want to store your big archive files in your backend, run this command in your repository root:

    $ echo "*.zip filter=bigstore" > .gitattributes

After you run this, every time you stage a zip file, it will transparently copy the file to ".git/bigstore/objects" and will replace the file contents (as stored in git) with relevant identifying information.

If you're storing large text files (or something else that is easily compressable), specify the "bigstore-compress" filter instead of the normal "bigstore" one. E.g.,

    $ echo "*.txt filter=bigstore-compress" > .gitattributes

This will compress your file using bz2 before uploading to your backend, and will decompress after downloading.

git-bigstore won't automatically sync to your selected backend after a commit. To push changed files, just run:

    $ git bigstore push

To pull down remote changes:

    $ git bigstore pull

If uploading and downloading everything isn't your cup of tea, you can also specify the paths you care about to these commands. For example, let's say you just want to download the Word and PDF files in your repo. This is what you'd do:

    $ git bigstore pull *.pdf *.doc

You can also view the upload and download history of any file tracked by bigstore.

    $ git bigstore log tsd20130403.pdf
    (946cc6) Sat Apr 13 21:52:21 2013 PDT: gs ← Dan Loewenherz <dloewenherz@gmail.com>
    (ebffdc) Fri Apr 12 11:00:39 2013 PDT: gs ← Dan Loewenherz <dloewenherz@gmail.com>
    (f9ffb5) Wed Apr 10 18:29:56 2013 PDT: gs → Dan Loewenherz <dloewenherz@gmail.com>
    (95aeaf) Wed Apr 10 18:28:42 2013 PDT: gs → Dan Loewenherz <dloewenherz@gmail.com>
    (95aeaf) Wed Apr 10 18:27:38 2013 PDT: gs → Dan Loewenherz <dloewenherz@gmail.com>
    (95aeaf) Wed Apr 10 17:55:00 2013 PDT: gs → Dan Loewenherz <dloewenherz@gmail.com>
    (95aeaf) Wed Apr 10 17:53:40 2013 PDT: gs → Dan Loewenherz <dloewenherz@gmail.com>
    (95aeaf) Wed Apr 10 17:49:49 2013 PDT: gs → Dan Loewenherz <dloewenherz@gmail.com>
    (95aeaf) Wed Apr 10 17:49:13 2013 PDT: gs → Dan Loewenherz <dloewenherz@gmail.com>
    (f9ffb5) Wed Apr 10 10:29:30 2013 PDT: gs ← Dan Loewenherz <dloewenherz@gmail.com>
    (95aeaf) Wed Apr 10 09:46:46 2013 PDT: gs ← Dan Loewenherz <dloewenherz@gmail.com>


Backend-Specific Instructions
-----------------------------

### Amazon S3

You probably will want to set up an IAM user to manage the bucket you'll be using to upload your media. Here's an example user policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Stmt1401201989000",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectAcl",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:AbortMultipartUpload",
        "s3:ListBucketMultipartUploads",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "arn:aws:s3:::BUCKET",
        "arn:aws:s3:::BUCKET/*"
      ]
    }
  ]
}
```


But "INSERT X HERE" already exists...
---------------------------------

I've been using git-media for a few days now, and I've observed that it breaks down because it violates the following guideline in the [Git docs](https://www.kernel.org/pub/software/scm/git/docs/gitattributes.html):

> For best results, clean should not alter its output further if it is run twice ("clean→clean" should be equivalent to "clean"), and multiple smudge commands should not alter clean's output ("smudge→smudge→clean" should be equivalent to "clean").

This made it a bit tough to collaborate with multiple people, since Git would try to clean things that had already been cleaned, and smudge things that had already been smudged. No good!

git-annex is another alternative, but it's solving a different problem and its implementation is a bit less dependent on Git itself. As a result, you essentially have to learn a whole new set of commands to work with it. I wanted to create something with as minimal complexity as possible.

Copyright
---------

Copyright 2015, Lionheart Software LLC.

Licensed under Apache 2.0. See [LICENSE](LICENSE) for more details.

