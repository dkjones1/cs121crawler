# from enum import unique
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import hashlib

# import mmh3

uniqueWebsites = 0      # number of unique websites
crawledURL = []         # list of hashed url visited
crawledSites = []       # list of hashed websites visited
longestPage = 0         # length of webpage by word
subdomains = {}         # key: subdomain, value: number of pages under the subdomain
freq = {}               # dictionary holding common words between all websites

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

    # global variables for report
    global longestPage
    global freq
    global crawledURL
    global crawledSites
    global subdomains
    global uniqueWebsites

    with open('output.txt', 'a+') as output:

        # codes in 300 means redirect, 200 means fine, everything outside that range means it is not a good website
        if resp.status < 200 or resp.status >= 400:
            return list()

        # if the website is empty/None then do not parse
        if (resp.raw_response == None):
            return list()

        # BeautifulSoup object to get the contents of the website
        soup = BeautifulSoup(resp.raw_response.text, "html.parser")

        # filter out large websites by character to avoid tokenizing a large website
        #if len(soup.text) > 4700:
        #    return list()

        # checks if current url has different url than what was passed in (redirect)
        realURL = resp.url
        canonical = soup.find('link', {'rel': 'canonical'})     # https://stackoverflow.com/questions/49419577/beautiful-soup-find-address-og-current-website
        if canonical != None:
            canonical = canonical['href']
            if (canonical != realURL):
                realURL = canonical

        if not (is_valid(realURL)):
            return list()

        if '#' in realURL:
            realURL = realURL[0:realURL.index('#')]

        # url similarity checker using simhash
        # checks if the hash of the current url is in a list of hashed urls previously crawled.
        # loops through the previous 25 websites to add the similarity with the current url.
        # averages the similarity and checks if it is above the threshold to decide whether
        # to parse the url or not. appends hash of current url to lsit of crawled hashed urls.
        hashURL = getTokenHash(realURL)
        if hashURL not in crawledURL:
            total = 0
            for hashedURL in crawledURL[-25:]:
                total += calculateSimilarity(hashURL, hashedURL)
                total /= 25
                if total >= 0.95:
                    return list()
            crawledURL.append(hashURL)
        else:
            return list()

        # tokenize the contents of the website
        tokenList = tokenize(soup.text)

        # filter out low value urls
        if len(tokenList) < 200:
            return list()

        # finds frequencies of tokens and creates new dictionary with hash value and frequency
        tokenDict = computeTokenFrequencies(tokenList)
        hashTokenDict = {}
        for key in tokenDict.keys():
            hashKey = getTokenHash(key)
            hashTokenDict[hashKey] = tokenDict[key]

        # content similarity checker using simhash
        # similar to the url similarity checker. checks if contents are
        # the same by hashing the tokens and checking the hash in the list
        # of hashed website contents that were already crawled. check the
        # previous 25 hashed website contents and calculate the similarity
        # of the 25. take the average of the similarity and don't parse the
        # current website if the similarity is above the threshold. append
        # the hashed website content to the list of hashed contents.
        hashContent = simHash(hashTokenDict)
        if hashContent not in crawledSites:
            total = 0
            for hashedContent in crawledSites[-25:]:
                total += calculateSimilarity(hashContent, hashedContent)
                total /= 25
                if total >= 0.90:
                    return list()
            crawledSites.append(hashContent)
        else:
            return list()

        if (len(tokenList) > longestPage):
            longestPage = len(tokenList)
        updateGlobalFrequency(tokenDict)
        uniqueWebsites += 1

        # finds all the html tags with <a>, these can hold links
        tags = soup.find_all('a')
        # list to hold all the links on the current website
        links = []

        # tuple holding the different parts of the url, used for relative paths
        parsed = urlparse(realURL)
        for link in tags:
            # if the <a> tag element has a link (href)
            if link.has_attr('href'):
                absPath = link['href'].strip()


                # detecting for relative path urls
                # missing http
                if not absPath.startswith('http'):

                    if absPath.startswith('www.'):
                        absPath = parsed.scheme + '://' + absPath

                    elif absPath.startswith('/www.'):
                        absPath = parsed.scheme + ':/' + absPath

                    elif absPath.startswith('//www.'):
                            absPath = parsed.scheme + absPath

                    elif absPath.startswith('//'):
                        absPath = parsed.scheme + ':' + absPath

                    else:
                        absPath = parsed.scheme + '://' + parsed.netloc + absPath

                links.append(absPath)
        
        if not ('www.ics.uci.edu' in url or 'www.informatics.uci.edu' in url or 'www.cs.uci.edu' in url or 'www.stat.uci.edu' in url):
            sub = parsed.scheme + '://' + parsed.netloc
            if sub in subdomains.keys():
                subdomains[sub] += 1
            else:
                subdomains[sub] = 1


        #output.write(str(resp.status) + '\n')
        #output.write(url + '\n' + resp.url + '\n' + resp.raw_response.url)
        #output.write('\n-------------------------------------------------------------------\n')

        for l in links:
            output.write(l + '\n')
            output.write('\n-------------------------------------------------------------------\n')

    writeReport()
    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        # maybe add php, TA said to add php but I think some php sites worked
        website = re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|php|wp-content\/upload"
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
def tokenize(text):

    words = re.findall(r'[a-z0-9\']+', text.lower())
    return words

# frequency method from Assignment 1
def computeTokenFrequencies(tokenList):
    tokenFreq = {}
    stopWords = ['a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t',
                 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
                 'can\'t', 'cannot', 'could', 'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing', 'don\'t',
                 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t', 'have',
                 'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s', 'her', 'here', 'here\'s', 'hers', 'herself',
                 'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll', 'i\'m', 'i\'ve', 'if', 'in', 'into',
                 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s', 'me', 'more', 'most', 'mustn\'t', 'my',
                 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours',
                 'ourselves', 'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll', 'she\'s', 'should',
                 'shouldn\'t', 'so', 'some', 'such', 'than', 'that', 'that\'s', 'the', 'their', 'theirs', 'them',
                 'themselves', 'then', 'there', 'there\'s', 'these', 'they', 'they\'d', 'they\'ll', 'they\'re', 'they\'ve',
                 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d',
                 'we\'ll', 'we\'re', 'we\'ve', 'were', 'weren\'t', 'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s',
                 'which', 'while', 'who', 'who\'s', 'whom', 'why', 'why\'s', 'with', 'won\'t', 'would', 'wouldn\'t', 'you',
                 'you\'d', 'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours', 'yourself', 'yourselves']

    for token in tokenList:
        if token not in stopWords:
            if token in tokenFreq.keys():
                tokenFreq[token] += 1
            else:
                tokenFreq[token] = 1
    return tokenFreq

def getTokenHash(inputStr):
    hash = hashlib.sha256(inputStr.encode('utf-8')).digest() #hashes
    binaryHash = bin(int.from_bytes(hash, byteorder='big'))[2:].zfill(32) #converts into binary
    return binaryHash[:32] #returns the first 32 bits

    """
    hashToInt = mmh3.hash(inputStr, signed = False) #hashes the token to an unsigned int
    hashToBinary = "{0:b}".format(hashToInt).zfill(32) #converts the int to 32 bit binary representation https://appdividend.com/2021/06/14/how-to-convert-python-int-to-binary-string/
    return hashToBinary
    """

def calculateFingerprint(simHashList):
    fingerprint = []
    for i in range(32):
        if simHashList[i] <= 0:
            fingerprint.append('0')
        else:
            fingerprint.append('1')

    return ''.join(fingerprint)

def simHash(hashDict):
    vectorOutput = [0] * 32  # initialize output vector
    for i in range(32):
        sum = 0
        for key in hashDict.keys():
            if (key[i] == '0'):
                sum -= hashDict[key]
            else:
                sum += hashDict[key]
        vectorOutput[i] = sum

    return calculateFingerprint(vectorOutput)

def calculateSimilarity(simOne, simTwo):
    counter = 0
    for i in range(32):
        if simOne[i] == simTwo[i]:
            counter += 1
    counter /= 32
    return counter


def updateGlobalFrequency(tokenFreqDict):
    global freq
    for key, value in tokenFreqDict.items():
        if key in freq.keys():
            freq[key] = freq[key] + tokenFreqDict[key]
        else:
            freq[key] = tokenFreqDict[key]


def writeReport():
    global freq
    with open('report.txt', 'w+') as report:
        sortedFreq = dict(sorted(freq.items(), key=lambda k: (-k[1], k[0])))
        topFiftyDict = dict(list(sortedFreq.items())[0: 50]) #idk if it works https://www.geeksforgeeks.org/python-get-first-n-keyvalue-pairs-in-given-dictionary/
        for key, value in topFiftyDict.items():
            report.write('%s %s\n' % (key, value))
        for i in range(5):
            report.write("\n")
        report.write("Longest Page: " + str(longestPage))
        report.write("\nUnique Websites: " + str(uniqueWebsites))