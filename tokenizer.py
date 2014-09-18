import subprocess
import os
import sys
import time


testfile = str(sys.argv[1])
tokenized = str(sys.argv[2])
jarfile = 'ark-tweet-nlp-0.3.2.jar'

#Execute the jar to tokenize the text in the text file
def tokenize():
    cmd = 'java -XX:ParallelGCThreads=2 -Xmx500m -jar '+jarfile+' \"'+testfile+'\"'
    process = subprocess.Popen(cmd,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,shell=True)
    return  iter(process.stdout.readline, b'')

    
def main():
    f= open(tokenized,'w')
    for output_line in tokenize():
        if '\t' in output_line:
            try:
                a,b,c,e = output_line.split('\t')
                f.write(a+'\t'+b+'\n')
            except Exception:
                print output_line
    f.close()

if __name__ == "__main__":
   main()
   

