from enum import unique
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import hashlib

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
    
    global longestPage
    global freq
    global uniqueWebsites
    global crawledURL
    global crawledSites
    global subdomains
    
    with open('output.txt', 'a+') as output:

        if resp.status != 200:
            return list()

        hashURL = getTokenHash(resp.url)
        if '#' in resp.url:
            uniqueURL = url[0:resp.url.index('#')]
            uniqueURLHash = getTokenHash(uniqueURL)
            if uniqueURLHash not in crawledURL:
                uniqueWebsites += 1
        else:
            if hashURL not in crawledURL:
                uniqueWebsites += 1

        if (resp.raw_response == None):
            return list()

        soup = BeautifulSoup(resp.raw_response.content.decode('utf-8', 'ignore'), "html.parser")
        tokenList = tokenize(soup.text)
        
        #filter out low value urls
        if len(tokenList) < 100: 
            return list()

        # filter out large websites by character to avoid tokenizing a large website
        #if len(soup.text) > 4700:
        #    return list()

        if hashURL not in crawledURL:
            total = 0
            for hashedURL in crawledURL[-25:]:
                total += calculateSimilarity(hashURL, hashedURL)
                total /= 25
                if total >= 0.85:
                    return list()
            crawledURL.append(hashURL)
        else:
            return list()

        hashContent = simHash(tokenList)
        if hashContent not in crawledSites:
            total = 0
            for hashedContent in crawledSites[-25:]:
                total += calculateSimilarity(hashContent, hashedContent)
                total /= 25
                if total >= 0.80:
                    return list()
            crawledSites.append(hashContent)
        else:
            return list()


        tags = soup.find_all('a')
        links = []
        parsed = urlparse(resp.url)
        for link in tags:
            if link.has_attr('href'):
                absPath = link['href'].strip()
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

                if(len(tokenList) > longestPage):
                    longestPage = len(tokenList)
                    computeTokenFrequencies(tokenList)
                    freq = dict(sorted(freq.items(), key=lambda k: (-k[1], k[0])))
                
                links.append(absPath)
        
        if not ('www.ics.uci.edu' in url or 'www.informatics.uci.edu' in url or 'www.cs.uci.edu' in url or 'www.stat.uci.edu' in url):
            sub = parsed.scheme + '://' + parsed.netloc
            if sub in subdomains.keys():
                subdomains[sub] += 1
            else:
                subdomains[sub] = 1

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
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf|wp-content\/upload"
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
        '''
        inDomain = re.match(r'.*(\.ics\.uci\.edu\/|\.cs\.uci\.edu\/|\.informatics\.uci\.edu\/|\.stat\.uci\.edu\/).*', url.lower())
        global crawledURL
        if (inDomain):
            if url not in crawledURL:
                crawledURL.append(url)
                return True
        else:
            return False
        '''

    except TypeError:
        print ("TypeError for ", parsed)
        raise

# tokenizer method from Assignment 1
def tokenize(contents):

    words = re.findall(r'[a-z0-9]+', contents.lower())
    return words

# frequency method from Assignment 1
def computeTokenFrequencies(tokenList):
    #freq = {}
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
            if token in freq.keys():
                freq[token] += 1
            else:
                freq[token] = 1
    return freq

def getTokenHash(inputStr):
    hash = hashlib.sha256(inputStr.encode('utf-8')).digest() #hashes
    binaryHash = bin(int.from_bytes(hash, byteorder='big'))[2:].zfill(32) #converts into binary
    return binaryHash[:32] #returns the first 32 bits

def simHash(tokenList):
    vectorOutput = [0] * 32  # initialize output vector
    for token in tokenList:
        hashedToken = getTokenHash(token)  # hash every token
        for i in range(32):  # 32 is the number of bits that are returned from the hash
            if (hashedToken[i] == '0'):
                vectorOutput[i] = vectorOutput[i] - 1  # subtract if the bit is 0
            else:
                vectorOutput[i] = vectorOutput[i] + 1  # add if the bit is 1

    fingerprint = []
    for i in range(32):
        if vectorOutput[i] <= 0:
            fingerprint.append('0')
        else:
            fingerprint.append('1')

    return ''.join(fingerprint)

def calculateSimilarity(simOne, simTwo):
    counter = 0
    for i in range(32):
        if simOne[i] == simTwo[i]:
            counter += 1
    counter /= 32
    return counter

def writeReport():
    with open('report.txt', 'w+') as report:
        topFiftyDict = dict(list(freq.items())[0: 50]) #idk if it works https://www.geeksforgeeks.org/python-get-first-n-keyvalue-pairs-in-given-dictionary/
        for key, value in topFiftyDict.items():
            report.write('%s %s\n' % (key, value))
        for i in range(5):
            report.write("\n")
        report.write("Longest Page: " + str(longestPage))
        report.write("\nUnique Websites: " + str(uniqueWebsites))