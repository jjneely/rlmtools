#!/usr/bin/env ruby
# Puppet Labs is a ruby shop, so why not do the post-receive hook in ruby?
require 'fileutils'
 
# Set this to where the main repos live
SOURCE_BASEDIR = "/afs/bp/system/config/linux-kickstart/puppet"

# Set this to where you want to keep your environments
ENVIRONMENT_BASEDIR = "/srv/puppet"
 
# The git_dir environment variable will override the --git-dir, so we remove it
# to allow us to create new repositories cleanly.
ENV.delete('GIT_DIR')
 
# Ensure that we have the underlying directories, otherwise the later commands
# may fail in somewhat cryptic manners.
for i in [ENVIRONMENT_BASEDIR, SOURCE_BASEDIR]
  unless File.directory? i
    puts %Q{#{i} does not exist, cannot update puppet repositories.}
    exit 1
  end
end

# List of environments that we have populated -- collision detection
envs = []

# XXX: Detect and clean up deleted branches/environments

Dir.foreach(SOURCE_BASEDIR) do |dir|
  source = File.join(SOURCE_BASEDIR, dir)

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
  if dir =~ /global-modules/
    # Skip the global modules directory for now
    next
  end

  #puts "Working on #{source} ..."

  # Make sure we account for the "master" branch
  branches = Dir.entries("#{source}/.git/refs/heads")
  if not branches.include?("master")
    branches.push("master")
  end

  branches.each do |branchname|
    if branchname != "master" and not File.file?(File.join("#{source}/.git/refs/heads", branchname))
      next
    end

    #puts "  Working on branch #{branchname} ..."

    if branchname =~ /[\W-]/
      puts %Q{Branch "#{branchname}" contains non-word characters, ignoring it.}
      next
    end
 
    if branchname == "master"
      environment_path = "#{ENVIRONMENT_BASEDIR}/#{dir}"
    else
      environment_path = "#{ENVIRONMENT_BASEDIR}/#{dir}_#{branchname}"
    end

    # Puppet environments cannont contain "-" characters
    environment_path.gsub!(/-/, "_")

    # Check to see if we have a collision with any other environment
    if envs.include?(environment_path)
      puts "Branch #{branchname} in #{dir} conflicts with another environment, skiping"
      next
    else
      envs.push(environment_path)
    end
 
    # We have been given a branch that needs to be created or updated. If the
    # environment exists, update it. Else, create it.
 
    if File.directory?(environment_path)
      # Update an existing environment. We do a fetch and then reset in the
      # case that someone did a force push to a branch.
 
      #puts "Updating existing environment #{environment_path}"
      Dir.chdir(environment_path)
      %x{git fetch -q --all}
      if $? != 0
        puts "ERROR running \"git fetch --all\" for #{environment_path}"
      end
      %x{git reset -q --hard "origin/#{branchname}"}
      if $? != 0
        puts "ERROR running git reset --hard \"origin/#{branchname}\" for #{environment_path}"
      end
    else
      # Instantiate a new environment from the current repository.
 
      #puts "Creating new environment #{environment_path}"
      Dir.chdir(ENVIRONMENT_BASEDIR)
      %x{git clone -q #{source} #{environment_path} --branch #{branchname}}
      if $? != 0
        puts "ERROR running \"git clone #{source} #{environment_path} --branch #{branchname}\""
      end
    end
  end
end
