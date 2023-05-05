import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import hashlib

validURL = 0            # number of valid websites that we crawl
uniqueWebsites = 0      # number of unique websites
crawledURL = []         # list of url visited
crawledHashURL = []     # list of hashed url visited
crawledSites = []       # list of hashed websites visited
longestPage = 0         # length of the longest website by word
longestPageURL = ''     # url of the longest page
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
    global validURL
    global longestPage
    global longestPageURL
    global freq
    global crawledURL
    global crawledHashURL
    global crawledSites
    global subdomains
    global uniqueWebsites

    # codes in 300 means redirect, 200 means fine, everything outside that range means it is not a good website
    if resp.status < 200 or resp.status >= 400:
        return list()

    if (resp.raw_response == None):
        return list()

    # BeautifulSoup object to get the contents of the website
    soup = BeautifulSoup(resp.raw_response.text, "html.parser")

    # checks if current url has different url than what was passed in (redirect)
    # https://stackoverflow.com/questions/49419577/beautiful-soup-find-address-og-current-website
    realURL = resp.url
    canonical = soup.find('link', {'rel': 'canonical'})
    if canonical != None:
        canonical = canonical['href']
        if canonical.endswith('/'):
            canonical = realURL[:-1]
        if (canonical != realURL):
            realURL = canonical
            if not is_valid(realURL):
                return list()

    if realURL.endswith('/'):
        realURL = realURL[:-1]

    # url similarity checker using simhash
    # checks if the hash of the current url is in a list of hashed urls previously crawled.
    # loops through the previous 25 websites to add the similarity with the current url.
    # averages the similarity and checks if it is above the threshold to decide whether
    # to parse the url or not. appends hash of current url to list of crawled hashed urls.
    if realURL not in crawledURL:
        total = 0
        crawledURL.append(realURL)
        uniqueWebsites += 1

        urlCharTokens = []
        withoutScheme = realURL.rfind('://')  # parses out http(s)://
        if withoutScheme == -1:
            withoutScheme = 0

        for letter in realURL[withoutScheme:]:
            urlCharTokens.append(letter)

        urlLetterDict = computeCharacterFrequencies(urlCharTokens)
        hashURLDict = {}
        for key in urlLetterDict.keys():
            hashKey = getTokenHash(key)
            hashURLDict[hashKey] = urlLetterDict[key]

        hashURL = simHash(hashURLDict)

        for hashedURL in crawledHashURL[-100:]:
            total += calculateSimilarity(hashURL, hashedURL)
        total /= 100
        if total > 0.96:
            return list()
        crawledHashURL.append(hashURL)
    else:
        return list()

    # tokenize the contents of the website
    tokenList = tokenize(soup.text)

    # filter out low value urls, 150 words is about a paragraph
    if len(tokenList) < 150:
        return list()

    # filter out large websites by characters, 50k words is about 100 pages
    if len(tokenList) > 50000:
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
        for hashedContent in crawledSites[-100:]:
            total += calculateSimilarity(hashContent, hashedContent)
        total /= 100
        if total > 0.90:
            return list()
        crawledSites.append(hashContent)
    else:
        return list()

    # updates longest page length and url if longer page is found
    if (len(tokenList) > longestPage):
        longestPage = len(tokenList)
        longestPageURL = realURL

    # updates dictionary with token frequencies and valid urls crawled
    updateGlobalFrequency(tokenDict)
    validURL += 1

    # finds all the html tags with <a>, these can hold links
    tags = soup.find_all('a')
    # list to hold all the links on the current website
    links = []

    parsed = urlparse(realURL)

    # counts subdomains
    if not ('www.ics.uci.edu' in url or 'www.informatics.uci.edu' in url or 'www.cs.uci.edu' in url or 'www.stat.uci.edu' in url):
        sub = parsed.scheme + '://' + parsed.netloc
        if sub in subdomains.keys():
            subdomains[sub] += 1
        else:
            subdomains[sub] = 1

    # tuple holding the different parts of the url, used for relative paths
    # https://stackoverflow.com/questions/1080411/retrieve-links-from-web-page-using-python-and-beautifulsoup
    for link in tags:
        # if the <a> tag element has a link (href)
        if link.has_attr('href'):
            absPath = link['href'].strip()

            # detecting for relative path urls
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

            # defragments url
            if '#' in absPath:
                absPath = absPath[0:absPath.index('#')]
            if absPath.endswith('/'):
                absPath = absPath[:-1]

            links.append(absPath)

    # updates final report
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

        # regex to check if the url is within the ics/cs/inf/stats domains
        if (re.match(r'.*(\.ics\.uci\.edu\/|\.cs\.uci\.edu\/|\.informatics\.uci\.edu\/|\.stat\.uci\.edu\/).*', url.lower())):
            website = re.match(
                # might want to add php
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

            # parts of urls that caused 403/404 errors
            errors = re.match(r'.*(mailto|wp-content\/upload|action=login|precision=second|action=download|action=upload|(\.|\/)zip|(\.|\/)pdf|video).*', url)
            if errors:
                return False

        else:
            return False

        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise

# tokenizer method to extract words from the websites
def tokenize(text):

    words = re.findall(r'[a-z0-9\']+', text.lower())
    return words

# frequency method that counts the amount of tokens given a list, excluding stop words
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
        if token not in stopWords and len(token) > 1:
            if token in tokenFreq.keys():
                tokenFreq[token] += 1
            else:
                tokenFreq[token] = 1
    return tokenFreq

# similar to token frequency, this counts the frequency of characters for url similarity
def computeCharacterFrequencies(characterList):
    characterFreq = {}

    for token in characterList:
            if token in characterFreq.keys():
                characterFreq[token] += 1
            else:
                characterFreq[token] = 1
    return characterFreq

# uses sha256 hash to get the 32-bit binary hash value for a passed in string
def getTokenHash(inputStr):
    hash = hashlib.sha256(inputStr.encode('utf-8')).digest() #hashes https://stackoverflow.com/questions/48613002/sha-256-hashing-in-python
    binaryHash = bin(int.from_bytes(hash, byteorder='big'))[2:].zfill(32) #converts into binary https://crypto.stackexchange.com/questions/83224/how-to-get-an-output-of-sha-1-with-first-2-bit-are-zeros
    return binaryHash[:32] #returns the first 32 bits

# calculates the fingerprint values given the sim hash values
def calculateFingerprint(simHashList):
    fingerprint = []
    for i in range(32):
        if simHashList[i] <= 0:
            fingerprint.append('0')
        else:
            fingerprint.append('1')

    return ''.join(fingerprint)

# calculates simhash values according to frequencies of tokens
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

# calculates the similarities between two sim hash values
def calculateSimilarity(simOne, simTwo):
    counter = 0
    for i in range(32):
        if simOne[i] == simTwo[i]:
            counter += 1
    counter /= 32
    return counter

# updates the dictionary holding frequencies of tokens across all websites crawled
def updateGlobalFrequency(tokenFreqDict):
    for key, value in tokenFreqDict.items():
        if key in freq.keys():
            freq[key] = freq[key] + tokenFreqDict[key]
        else:
            freq[key] = tokenFreqDict[key]

# writes the final report with frequencies, subdomains, longest page, and unique websites
def writeReport():
    with open('report.txt', 'w+') as report:
        report.write("Report")
        report.write("1)")
        report.write("\nUnique Websites: " + str(uniqueWebsites))
        report.write("\nNumber of crawled valid websites are: " + str(validURL))
        report.write("\n2)")
        report.write("\nThe longest crawled page was " + longestPageURL + " with " + str(longestPage) + " words")

        for i in range(3):
            report.write("\n")

        report.write("3)")
        report.write('\nTop Fifty Most Common Words:\n')
        sortedFreq = dict(sorted(freq.items(), key=lambda k: (-k[1], k[0])))
        topFiftyDict = dict(list(sortedFreq.items())[0: 50]) #idk if it works https://www.geeksforgeeks.org/python-get-first-n-keyvalue-pairs-in-given-dictionary/
        for key, value in topFiftyDict.items():
            report.write('%s %s\n' % (key, value))

        for i in range(3):
            report.write("\n")

        report.write("4)")
        report.write('\nSubdomains:\n')
        for key, value in sorted(subdomains.items()):
            report.write('%s %s\n' % (key, value))