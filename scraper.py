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

    # write status and contents to output file so I can see what exactly the resp does and error codes
    # error codes split into pieces so I can read it easily
    with open('output.txt', 'w') as output:

        if (resp.status >= 200 and resp.status < 400):
            output.write(str(resp.status) + "\n")

        elif (resp.status >= 400 and resp.status <= 599):
            output.write(str(resp.status) + "\n")

        elif (resp.status >= 600 and resp.status <= 606):
            output.write(str(resp.status) + "\n")

        # just in case if instructions did not mention another code that could occur
        else:
            output.write(str(resp.status) + "\n")

    # add simhash to check similarity
    # needs data structure to hold the hash values

        soup = BeautifulSoup(resp.raw_response.content, "html.parser")
        tags = soup.find_all('a')
        links = []
        for link in tags:
            if link.has_attr('href'):
                links.append(link['href'])

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
        print('if http(s)')
        if parsed.scheme not in set(["http", "https"]):
            return False

        print('regex type of website')
        website = re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

        if website:
            return False

        print('regex uci domain')
        #possible regex
        return re.match(r'.*(\.ics\.uci\.edu\/|\.cs\.uci\.edu\/|\.informatics\.uci\.edu\/|\.stat\.uci\.edu\/).*', parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
