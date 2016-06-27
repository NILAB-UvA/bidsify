# spynoza
python package for fMRI data processing


## prerequisites
Spynoza uses nipype to organize processing workflows. 

## Setup and git workflow
CD to a folder where you want the spynoza git to be setup. To clone the repo into that dir run:

`$ git clone git@github.com:spinoza-center/spynoza.git`

This cloned the master branch into the repo. We also need the develop branch. To create a new branch that syncs with the upstream develop branch run: (no need to run additional pull)

`$ git checkout --track origin/develop`

This ensures that when you run `git pull` from the develop branch, it syncs with the origin/develop branch (instead of origin/master). 

Now we'll want to create our own feature branch to start working on our contribution. We can branch off of develop by running:

`$ git checkout -b my_feature develop`

To get an overview of the branches we've created, run:

`$ git branch`

To switch to another branch run:

`$ git checkout branch_name`

When working on your feature, make sure you first switch to your feature branch. Then, do your work, and run:

`$ git commit -am "Your message"`

Make sure you have a seperate feature branch for every distinct feature you're implementing. 

When your feature is finished, and you'd like to share it with your collaborators, merge your changes in develop without a fast-forward. First switch to the develop branch:

`$ git checkout develop`

Then merge your feature changes into develop:

`$ git merge --no-ff my_feature`

Now push changes to the server

`$ git push origin develop`
`$ git push origin my_feature`

You are now free to delete your own feature branch if you wish using:

`$ git branch -d my_feature`






