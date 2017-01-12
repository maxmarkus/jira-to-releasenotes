#!/usr/bin/env python3
import subprocess
import os
import sys
import re
import getpass
import getopt
from jira import JIRA, JIRAError

######################################################################################################
# This script is for outputting the release notes for copy-pasting.
#
#
# You need to install https://pypi.python.org/pypi/jira first. Tested for Python 3.4.3 (might not work for Python 2.1).
# If you do not have python3 yet, just type   
#   $ brew install python3
#   $ pip3 install jira
#   
# Long:
# ./releasenotes.py --tagsback 1 --output html   (or markdown)
# Short: 
# ./releasenotes.py -t 1 -o html   (or markdown)
#
# You can predefine your Jira credentials:
# export JIRA_USER=your.user@hybris.com
# export JIRA_PASS=yourpassword (optional)
#
# Put this file in your git repository root directory and add to global gitignore. Run it.
# Pay attention that it picks up the right tag, if not, play with the releases argument (--help displays usage info).
#
# Example output:
#
# [INFO] Looking for commits since 1 last tags
# [INFO] Extracting commits since tag: 4.5.0, since timestamp: 2015-11-05 13:14:46 +0100.
# [INFO] Filtering JIRAPREFIX-[0-9]+ issues
# [INFO] Connecting to JIRA to retrieve the issue titles.
# Enter your JIRA username (Enter to skip): monika.machunik@hybris.com
# Enter your JIRA password (will be transferred insecurely):
# Printing release notes:
#
# ### Sub-tasks
#  - YMKT-2222 - Throw inside finally (Spot check)
#
# ### User stories
#  - YMKT-2224 - Fortify findings for Servcie SDK - Compulsory
#
# ### Tasks
#  - YMKT-2225 - Update Dependencies for service sdk and services
#
# ### Bugs
# - YMKT-2228 - raml-rewriter: rewrite of baseUri / fails
#
# Forked from original Author:
# https://github.com/monami555/releasenotes
#
######################################################################################################

#### General Settings
defaultTagsBack = "1";
defaultOutputType = "html" # markdown or html
jiraServer = "https://jira.hybris.com" # full url to jira
issuePrefixRegex = "[Yy][Mm][Kk][Tt]-"; # jira group prefix as regex
gitMode = "ref" # ref or log. use log if you experience errors in tag selection

######################################################################################################

def log(str):
  print("[INFO] " + str)

# executes given Git command in the current directory (do not include "git" in the front)
def executeGit(command):
  pr = subprocess.Popen("git "+command, cwd = '.' , shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
  (out, error) = pr.communicate()
  if not error:
    return str(out)
  else:
    return str(error)


# returns the tag name of the tag tagsBack tags back
def getTagnameAndTimeStampTagsBack(tagsBack):

  if gitMode == "log":
    ## log approach
    tagInfo = executeGit("log --tags --simplify-by-decoration --pretty=\"format:%ai %d\" -n" + tagsBack)
    taginfologs = re.findall('(v.*)', tagInfo)
  else:
    ## for-each-ref approach
    tagInfo = executeGit("for-each-ref --sort='-*committerdate' --format=\"%(*committerdate:iso) (tag: %(refname:short))\" refs/tags --count=" + tagsBack);
    taginfologs = re.findall('\(tag\:(.+?)[,\)]', tagInfo)

  timestamps = re.findall('[0-9-:]+ [0-9-:]+ [0-9-:+]+', tagInfo)
  timestamp = timestamps[len(timestamps)-1]
  tagname = taginfologs[len(taginfologs)-1]
  return {
    'tagname': tagname.strip(),
    'timestamp': timestamp
  };

# returns all commit messages since given timestamp, as one string
def getCommitsSince(timestamp):
  return executeGit("log --pretty=\"%s\r%n\" --since=\""+timestamp+"\"")

# authenticates the user in JIRA and returns the Jira object
def authenticateInJira():
  newInput = ""
  try: 
    newInput = raw_input
  except NameError:
    newInput = input
    
  user = os.environ.get('JIRA_USER')
  if user == None:
    user = newInput('Enter your JIRA username (Enter to skip): ')
  if len(user)==0:
    print("No User provided.");
    sys.exit(1);

  password = os.environ.get('JIRA_PASS')
  if password == None:
    password = getpass.getpass('Enter your JIRA password (will be transferred insecurely): ')
  if len(password)==0:
    print("No Password provided.");
    sys.exit(1);

  return JIRA(basic_auth=(user, password), options={'server': jiraServer})

def usage():
  print("")
  print("Usage: releasenotes.py --tagsback [number_of_tags_back] --output [markdown|html]")
  print("")
  print("Options:")
  print("-t or --tagsback [number_of_tags_back]: How many tags back should be considered. This is determined by number of tags in the master branch. Default value is 1 (since last release).")
  print("-o or --output [type]  markdown or html output style")
  print("")
  print("  *)the script must be started in the directory of your git repository")
  print("")
  print("Did you know?")
  print("You can predefine your Jira credentials:")
  print("export JIRA_USER=markus.edenhauser@snk-interactive.de")
  print("export JIRA_PASS=yourpassword (optional)")
  sys.exit(0)

def createReleaseNotes(tagsBack, outputType):
  log("Looking for commits since " + tagsBack + " last tags")
  targetTag = getTagnameAndTimeStampTagsBack(tagsBack);

  timestamp = targetTag['timestamp']
  tagname = targetTag['tagname']

  log("Extracting commits since tag: " + tagname + ", timestamp: " + timestamp +".")
  commitMessages = getCommitsSince(timestamp)

  log("Filtering "+issuePrefixRegex+"[0-9]+ issues")
  issues = set(re.findall(issuePrefixRegex + "[0-9]+",commitMessages))

  log("Connecting to JIRA to retrieve the issue titles.")
  jira = authenticateInJira()

  issueMap = {}

  for issue in issues:
    issue = issue[:9] # truncate to fixed string length (hacky!! only for YMKT-0000 length)
    if jira != None:
      try:
        type = jira.issue(issue).fields.issuetype.name
        print("fetching: "+issue)
      except JIRAError as e:
        type = "Unknown"
        print(issue, e.status_code, e.text)
        pass
    else:
      type = "Unknown"
    if not type in issueMap.keys():
      issueMap[type] = []
    issueMap[type].append(issue)

  print("Printing release notes:")

  if outputType == "markdown":
    for type in issueMap.keys():
      print("")
      if type=="User story":
        print("### User stories")
      else:
        print("### " + type + "s")
      for issue in issueMap[type]:
        if jira != None:
          try:
            print(" - " + issue.upper() + " - " + jira.issue(issue).fields.summary)
          except JIRAError as e:
            pass
        else:
          print(" - " + issue.upper() + " - " + jiraServer + "/browse/" + issue)

  else:
    for type in issueMap.keys():
      print("")
      if type=="User story":
        print("<h2>User stories</h2>")
      else:
        print("<h2>" + type + "s</h2>")

      print("<ul>")
      for issue in issueMap[type]:
        if jira != None:
          try:
            print("    <li>[<a href='" + jiraServer + "/browse/" + issue + "'>" + issue.upper() + "</a>] - " + jira.issue(issue).fields.summary + "</li>")
          except JIRAError as e:
            pass
        else:
          print("    <li>[<a href='" + jiraServer + "/browse/" + issue + "'>" + issue + "</a>]</li>")

      print("</ul>")
  sys.exit(0)


#### main program:
def main(argv):
  try:
      opts, args = getopt.getopt(argv, "h:t:o:r", ["help", "releases=", "tagsback=", "output="])
  except getopt.GetoptError:
      usage()
      sys.exit(2)
  for opt, arg in opts:
      if opt in ("-h", "--help"):
          usage()
          sys.exit()
      # elif opt == '-d':
      #     global _debug
      #     _debug = 1
      elif opt in ("-t", "--releases", "--tagsback"):
          tagsback = arg
      elif opt in ("-o", "--output"):
          output = arg

  try:
      output
  except NameError:
      log("No --output specified, using default output: " + defaultOutputType)
      output = defaultOutputType
  try:
      tagsback
  except NameError:
      log("No --tagsback specified, using default: " + defaultTagsBack + " tags")
      tagsback = defaultTagsBack
  # source = "".join(args)
  # print("source", source)
  # print("output", output)
  # print("tagsback", tagsback)
  print("")
  createReleaseNotes(tagsback, output)

if __name__ == "__main__":
    main(sys.argv[1:])
