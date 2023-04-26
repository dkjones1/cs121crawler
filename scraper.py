import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    # had error while running: couldnt decode character so it was replaced with replacement character

    # write status and contents to output file so I can see what exactly the resp does and error codes
    # error codes split into pieces so I can read it easily
    with open('output.txt', 'a+') as output:
        
        
        if (resp.status >= 200 and resp.status < 400):
            output.write(str(resp.status) + "\n" + url + "\n")

        # probably doesnt work
        elif resp.status == 404:
            return list()

        elif (resp.status >= 400 and resp.status <= 599):
            output.write(str(resp.status) + "\n" + url + "\n")

        # if error occures between 600 and 606 (got error for 607), skip the current website
        elif resp.status >= 600:
            output.write(str(resp.status) + "\n" + url + "\n")
            return list()

        # just in case if instructions did not mention another code that could occur
        else:
            output.write(str(resp.status) + "\n" + url + "\n")
        '''
        if resp.status != 200:
            output.write(str(resp.status) + "\n" + url + "\n")
        '''

        # add simhash to check similarity
        # needs data structure to hold the hash values

        soup = BeautifulSoup(resp.raw_response.content, "html.parser")
        tags = soup.find_all('a')
        links = []
        for link in tags:
            if link.has_attr('href'):
                absPath = link['href']
                if not absPath.startswith('http'):
                    parsed = urlparse(url)

                    if absPath.startswith('www.'):
                        absPath = parsed.scheme + '://' + absPath

                    elif absPath.startswith('/www.'):
                        absPath = parsed.scheme + ':/' + absPath

                    elif absPath.startswith('//www.'):
                            absPath = parsed.scheme + absPath

                    else:
                            absPath = url + absPath
                if not url in absPath:
                    links.append(absPath)

        for link in links:
            output.write(link + '\n')
        output.write('-------------------------------------------------------------------\n')


    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        website = re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|ppsx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

        if website:
            return False

        mail = re.match(r'.*(mailto).*', url)

        if mail:
            return False

        # regex to check if the url is within the ics/cs/inf/stats domains
        return re.match(r'.*(\.ics\.uci\.edu\/|\.cs\.uci\.edu\/|\.informatics\.uci\.edu\/|\.stat\.uci\.edu\/).*', url.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

# tokenizer method from Assignment 1
def tokenize(website):
    
    try:
        # tokens is the list that will hold all the tokens from the file
        tokens = []
        
        # lastWord saves the last token in the list of tokens just in case
        # that the buffer splits a word into two parts
        lastToken = ''
        with open(filePath[1], 'rb') as file:
            while True:
                # reads in 1024 bytes of data from the file and makes sure the 
                # file is in utf-8 encoding and ignores any errors that can
                # cause the program to crash if it cannot be encoded
                bytesBuffer = file.read(1024).decode('utf-8', 'ignore').lower()
                # if file is read then break
                if not bytesBuffer:
                    break
                
                # saves last character in case it is invalid to add onto lastToken
                lastChar = bytesBuffer[-1]
                
                # appends the new slice of text to the last word saved from the
                # previous iteration to make sure that if a word was split, then
                # it will reconnect it
                entireStr = lastToken + bytesBuffer
                
                # sets the string to all lowercase and gets a list of tokens
                # that are alphanumeric
                parsedBytes = re.findall(r'[a-z0-9]+', entireStr)
                
                # gets the last token just in case the last token was split
                lastToken = parsedBytes.pop()
                if not ('0' <= lastChar <= '9') and not ('a' <= lastChar <= 'z'):
                    lastToken += lastChar
                
                # appends the tokens to the list
                for word in parsedBytes:
                    tokens.append(word)
                    
            # appends the final word of the file to the list
            tokens.append(lastToken)
            return tokens
            
    # handles FileNotFoundError exception if the file does not exist
    except FileNotFoundError:
        print("File not found")
        exit(0)

# frequency method from Assignment 1
def computeTokenFrequencies(tokenList):
    freq = {}
    for token in tokenList:
        if token in freq.keys():
            freq[token] += 1
        else:
            freq[token] = 1
    return freq