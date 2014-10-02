from gensim.models import word2vec
import subprocess
import os,sys,time
import nltk
import re,json,urllib,urllib2
from nltk import Tree
from Queue import *

testfile = str(sys.argv[1])
tokenized = str(sys.argv[2])
jarfile = 'ark-tweet-nlp-0.3.2.jar'
tokenizedFile = 'tokenized.txt'
tokenSeparator = '///'

service_url = 'https://www.googleapis.com/freebase/v1/search'
api_key = 'AIzaSyCU2pCtOmybSvuRGp3u2EjIo-d_NjmYxBA'
model1 = word2vec.Word2Vec.load_word2vec_format('freebase-vectors-skipgram1000-en.bin.gz', binary=True)



class TreeNode:
    children = []
    def __init__(self, label):
        self.label = label
        self.children = []

    def addChild(self, node):
        self.children.append(node)


def leaves(node):
    l = []
    if not node.children:
        l.append(node.label)
    for child in node.children:
        l += leaves(child)
    return l


def strToTree(strtree):
    if not strtree:
        return
    if not strtree.startswith('('):
        return TreeNode(strtree)

    strtree = strtree[1:-1]
    label = ''
    pos = 0
    for i in range(0, len(strtree)):
        if not strtree[i].isalpha():
            pos = i
            break
        label += strtree[i]
    node = TreeNode(label)
    
    while pos < len(strtree) and strtree[pos] == ' ':
        pos += 1
    
    if strtree[pos] == '(':
        stack = []
        for i in range(pos, len(strtree)):
            if strtree[i] == '(':
                stack.append(strtree[i])
            elif strtree[i] == ')':
                top = stack.pop()
                assert top == '('
            else:
                continue
            if not stack:
                node.addChild(strToTree(strtree[pos:i+1].strip()))
                pos = i + 1
    else:
        node.addChild(strToTree(strtree[pos:len(strtree)].strip()))

    return node

def printTree(tree, level):
    print ' ' * (2 * level) + tree.label

    for child in tree.children:
        printTree(child, level + 1)

#Execute the jar to tokenize the text in the text file
def tokenize():
    cmd = 'java -XX:ParallelGCThreads=2 -Xmx500m -jar '+jarfile +' --output-format conll --no-confidence --model model.ritter_ptb tmp.txt'
    process = subprocess.Popen(cmd,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,shell=True)
    return  iter(process.stdout.readline, b'')

def posTagger():
    sentence = ''
    for output_line in tokenize():
        if '\t' in output_line:
            part1, part2 = output_line.split()
            sentence = sentence + ' ' + part1 + tokenSeparator + part2
    sentence = sentence.strip()

    print sentence
    file = open(tokenizedFile,'w')
    file.write(sentence)
    file.close()

def treeBuilder():
    cmd = 'java -mx1g -cp "stanford-parser.jar:stanford-parser-models.jar" edu.stanford.nlp.parser.lexparser.LexicalizedParser -sentences newline -tokenized -tagSeparator ' + tokenSeparator + ' -tokenizerFactory edu.stanford.nlp.process.WhitespaceTokenizer -tokenizerMethod newCoreLabelTokenizerFactory edu/stanford/nlp/models/lexparser/englishPCFG.caseless.ser.gz tmp2.txt'
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,shell=True)
    treeIter = iter(process.stdout.readline, b'')

    ans = ''
    for i in treeIter:
        if i.strip().startswith('('):
            ans += i.strip()
    ans = ans.replace('\n', ' ')
    print ans

    tree = strToTree(ans)
    printTree(tree, 0)

    #tree = Tree.fromstring(ans)
    #print tree
    #tree.draw()

    return tree

def leavesToString(leaves):
    first = True
    ans = ''
    for l in leaves:
        if first:
            first = False
        else:
            ans += ' '
        ans += l
    return ans

def searchEntities(tree):
    Q = Queue()
    Q.put(tree)
    labels = ['NP', 'FW', 'NNP', 'NNPS', 'NN', 'NNS']

    candidates = []

    while not Q.empty():
        t = Q.get()
        # Check if this node is NP
        if t.label in labels:
            # Check if it is in FreeBase
            term = leavesToString(leaves(t))
            print 'Checking', term, '...'
            if check_mention(term):
                print 'Adding', term
                candidates.append(term)
                continue
        
        for child in t.children:
            Q.put(child)

    print candidates
    return candidates

def searchQueries(entity, tree):
    labels = ['NNP', 'NNPS', 'NN', 'NNS']
    queries = []

    Q = Queue()
    Q.put(tree)

    while not Q.empty():
        t = Q.get()
        term = leavesToString(leaves(t))
        print entity, term
        if term == entity:
            continue

        if t.label in labels:
            queries.append(entity + ' ' + term)

        for child in t.children:
            Q.put(child)
    for q in queries:
        print 'Results for', q, '=', checkAPI(q)
    #print queries


#Check if an ngram is a mention or not, by comparing against the entities in the vector model
def check_mention(element):
    e = '/en/'+'_'.join(element.split())
    if element.endswith('\'s'):
        element = element.replace('\'s','')
    try:
        if model1.most_similar(e.lower(),topn=1):
            return True
    except Exception:
        return False
    return False


#Extract possible candidates for a mention from Freebase API    
def checkAPI(term):
    term = term.lower()
    params = {
        'query': term,
        'limit' : 30,
        'key': api_key
        }
    url = service_url + '?' + urllib.urlencode(params)
    response = json.loads(urllib.urlopen(url).read())
    results = []
    for result in response['result']:
        try:
            name = result['name']
            if term not in name.lower():
                continue
            id_res = result['id'].encode('utf8')
            results.append(id_res)
        except Exception:
            pass
       
    return results



def main():
    open(tokenizedFile,'w').close()

    with open(testfile,'r') as file:
        for line in file:
            tempFile = open('tmp.txt','w')
            tempFile.write(line)
            tempFile.close()
            posTagger()

    with open(tokenizedFile,'r') as file2:
        for line in file2:
            tempFile2 = open('tmp2.txt','w')
            line = line.replace('(','{').replace(')', '}')
            tempFile2.write(line)
            tempFile2.close()
            tree = treeBuilder()
            #print leaves(tree)

    candidates = searchEntities(tree)
    searchQueries(candidates[0], tree)


if __name__ == "__main__":
    main()
