#!/usr/bin/env ruby

require 'fileutils'
 
# Set this to where the main repos live
SOURCE_BASEDIR = "/afs/bp/system/config/linux-kickstart/puppet/global-modules"

# Where our global modules live on the Puppet Masters
LOCAL_BASEDIR = "/srv/puppet/global-modules"
 
# The git_dir environment variable will override the --git-dir, so we remove it
# to allow us to create new repositories cleanly.
ENV.delete('GIT_DIR')
 
# Ensure that we have the underlying directories, otherwise the later commands
# may fail in somewhat cryptic manners.
if not File.directory?(SOURCE_BASEDIR)
  puts "#{SOURCE_BASEDIR} is not found, cannot continue."
  exit 1
end
if not File.directory?(LOCAL_BASEDIR)
  # Make our local directory if its not there
  Dir.mkdir(LOCAL_BASEDIR)
end

# To sync a git repository to the Puppet Masters as one of the modules
# available in the global-modules directory a flag must exist in the .git
# directory of the source git repo in AFS.  That flag is
#
#     ncsu-global-module
#
# For example in the global module "mysql" this file exists:
#
#     File.join(SOURCE_BASEDIR, "mysql/.git/ncsu-global-module")
#
# That file may also contain one line that is a branch, tag, or reference
# into that git repository.  The Puppet Masters will use that reference
# as HEAD when the repository is cloned on disk.  This allows us to
# specify which reference points to the production version, while also
# being able to test and do further development or merges from upstream.

Dir.foreach(SOURCE_BASEDIR) do |dir|
  source = File.join(SOURCE_BASEDIR, dir)
  target = File.join(LOCAL_BASEDIR, dir)

  if not File.directory?(source)
    #puts "  #{source} is not a directory, skipping"
    next
  end
  if dir =~ /^\./
    #puts "  #{source} is starts with a '.', skipping"
    next
  end
  if not File.directory?("#{source}/.git/refs/heads")
    #puts "  #{source} does not contain a Git repository"
    next
  end
  if not File.exists?("#{source}/.git/ncsu-global-module")
    #puts "  #{source} is not blessed"
    next
  end

  # What git reference should we use as production?
  ref = File.read("#{source}/.git/ncsu-global-module").strip()
  if ref == ""
    ref = "master"
  end

  #puts "Working on #{source} ..."

  if File.directory?(target)
    # Update an existing module. We do a fetch and then reset in the
    # case that someone did a force push to a branch.

    #puts "Updating existing module #{target}"
    Dir.chdir(target)
    %x{git fetch -q --all}
    if $? != 0
      puts "ERROR running \"git fetch --all\" for #{target}"
    end
    %x{git reset -q --hard "#{ref}"}
    if $? != 0
      puts "ERROR running git reset --hard \"#{ref}\""
    end
  else
    # Instantiate a new module from the source repository.

    #puts "Creating new module #{target}"
    Dir.chdir(LOCAL_BASEDIR)
    # Don't do the checkout -- yet
    %x{git clone -q --no-checkout #{source} #{target}}
    if $? != 0
      puts "ERROR running \"git clone #{source} #{environment_path} --branch #{branchname}\""
    end
    Dir.chdir(target)
    # Update the working copy to the specified git reference
    %x{git reset -q --hard "#{ref}"}
    if $? != 0
      puts "ERROR running git reset --hard \"#{ref}\""
    end
  end
end

