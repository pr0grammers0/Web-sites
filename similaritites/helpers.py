from nltk.tokenize import sent_tokenize


def lines(a, b):
    """Return lines in both a and b"""

    a1 = set(a.split("\n"))
    b1 = set(b.split("\n"))
    return list(a1 & b1)


def sentences(a, b):
    """Return sentences in both a and b"""

    a1 = set(sent_tokenize(a))
    b1 = set(sent_tokenize(b))
    return list(a1 & b1)


def substrings(a, b, n):
    """Return substrings of length n in both a and b"""
    
    a1 = list()
    mov = n
    i = 0
    while mov <= len(a):
        a1.append(a[i:mov])
        mov += 1
        i += 1
        
    b1 = list()
    mov = n
    i = 0
    while mov <= len(b):
        b1.append(b[i:mov])
        mov += 1
        i += 1
    a1 = set(a1)
    b1 = set(b1)
    return list(a1 & b1)
