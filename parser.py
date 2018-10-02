import re

nocase = False
multiline = False
dot = False
ungreedy = False
findall = False
starting = False
ending = False
distance0 = False
ignorelimit = False
normalizedheader = False
unnormalizedbody = False
error = False
output = ""

with open("input.txt") as f:
    pcre = f.readline()

# enable flags
def flags(s):
    global nocase, multiline, dot, ungreedy, findall, starting, ending, distance0, ignorelimit, normalizedheader, unnormalizedbody, error
    if s[0] != '/':
        error = True
    l = s.rfind('/')
    if l < 1:
        error = True

    flags = s[l:]
    if 's' in flags:
        dot = True
    if 'm' in flags:
        multiline = True
    if 'i' in flags:
        nocase = True
    if 'g' in flags:
        findall = True
    if 'U' in flags:
        ungreedy = True
    if 'E' in flags:
        if multiline  == False :
            ending = True
    if 'R' in flags:
        distance0 = True
    if 'O' in flags:
        ignorelimit = True
    if 'H' in flags:
        normalizedheader = True
    if 'P' in flags:
        unnormalizedbody = True
    
    s = s[1:l]

    if s.startswith("^"):
        starting = True
        s = s[1:]

    if s.endswith("$"):
        ending = True
        s = s[:-1]
    return s

#read expression
def regular(s, followsLiteral, start):
    print(s)
    reg = ""
    isLiteral = False
    if len(s) == 0:
        return ""

    #if parenthesis
    if s.startswith("("):
        # find index of matching closing parenthesis
        found = 1
        idx = 0
        legit = True
        while (found != 0):
            idx += 1
            if legit and s[idx-1] != '\\':
                if s[idx]==')':
                    found -= 1
                if s[idx]=='(':
                    found += 1
            if s[idx] == '[':
                legit = False
            if s[idx] == ']':
                legit = True

        #capture groups and mode modifier
        if s[1] == '?':
            #named group
            if s[2] == 'P':
                if s[3]=='<':
                    n = s.find('>')
                    reg = "( " + regular(s[n+1:idx], isLiteral, True) + ") named <"+s[4:n]+"> "
                elif s[3] == '=':
                    reg = "<"+s[4:idx]+"> "

            #capturing group
            elif s[2]==':' or s[2]=='=' or s[2]=='!':
                if s[2]==':':
                    capture = "non-capturing "
                if s[2]=='=':
                    capture = "positive lookahead of "
                if s[2]=='!':
                    capture = "negative lookahead of "
                reg = capture + "( " + regular(s[3:idx], isLiteral, True) + ") "

            #mode modifier
            else:
                return "followed by " + modemodifier(s[2:idx]) + regular(s[idx+1:], isLiteral, True)

        #ordinary parenthesis
        else:
            reg = "( " + regular(s[1:idx], isLiteral, True) + ") "
        s = s[idx + 1:]

    #if choice brackets
    elif s.startswith("["):
        idx = s.find(']')
        ex = s[1] == '^'
        if ex:
            reg = "token(s) excluding [" + choice(s[2:idx]) + "] "
        else:
            reg = "token(s) from [" + choice(s[1:idx]) + "] "
        s = s[idx + 1:]

    #if escape characters
    elif s.startswith("\\"):
        if s[1] == 'x':
            if s[2] == '{':
                reg, isLiteral = hexadecimal(s[3:5])
                s=s[6:]
            else:
                reg, isLiteral = hexadecimal(s[2:4])
                s=s[4:]
        else:
            reg, isLiteral = escape(s[1])
            s = s[2:]

    #else read single character
    else:
        if s[0]=='|':
            reg = "or "
        elif s[0] == '.':
            reg = "any character " + (""if dot else "excluding NEWLINE ")
        else:
            isLiteral = True
            reg = "\"" + s[0] + "\" "
        s = s[1:]

    #check repetition
    if s.startswith('?'):
        isLiteral = False
        reg = "zero or one " + reg
        s = s[1:]
    elif s.startswith('+'):
        isLiteral = False
        if len(s) > 1 and s[1] == '?':
            reg = ("greedy " if ungreedy else "lazy ") + "match of one or more " + reg
            s = s[2:]
        else:
            reg = "one or more " + reg
        s = s[1:]
    elif s.startswith('*'):
        isLiteral = False
        if len(s) > 1 and s[1] == '?':
            reg = ("greedy " if ungreedy else "lazy ") + "match of zero or more " + reg
            s = s[2:]
        else:
            reg = "zero or more " + reg
            s = s[1:]
    elif s.startswith('{'):
        isLiteral = False
        idx = s.find("}")
        com = s.find(",")
        p = re.compile('{\d+(,\d*)?}')
        if not p.match(s[0:idx+1]):
            reg = reg + "followed by \"" + s[0: idx+1] + "\""
        else:
            num = ""
            #{num}
            if com == -1 or com > idx:
                num = s[1:idx] + " "
            #{num, }
            elif idx - com == 1:
                num = s[1:com] + " or more "
            #{num, num}
            else:
                num = s[1:com] + " to " + s[com+1:idx] + " "
            reg = num + reg
        s = s[idx+1:]

    #return result
    if start:
        return reg + regular(s, isLiteral, False)
    if followsLiteral and isLiteral:
        return "BeTwEeN " + reg + regular(s, isLiteral, False)
    return "followed by " + reg + regular(s, isLiteral, False)

#handle choice brackets
def choice(s):
    if len(s)==0:
        return ""
    to = False
    output=""
    if s[0]=="\\":
        if s[1] == 'x':
            output, b = hexadecimal(s[2:4])
            s=s[4:]
        else:
            output, b = escape(s[1])
            s=s[2:]
    elif s[0] == '-' and len(s) != 1:
        to = True
        output = " to "
        s=s[1:]
    else:
        output = "\""+s[0]+"\""
        s=s[1:]
    if len(s) > 0 and not to and (not s.startswith('-') or s=="-"):
        output += " and "
    return output + choice(s)

#handle hexadecimals
def hexadecimal(s):
    n = int(s,16)
    if n == 0:
        return "NUL ", False
    elif n == 1:
        return "START OF HEADER ", False
    elif n == 2:
        return "START OF TEXT ", False
    elif n == 3:
        return "END OF TEXT ", False
    elif n == 4:
        return "END OF TRANSMISSION ", False
    elif n == 5:
        return "ENQUIRE ", False
    elif n == 6:
        return "ACKNOWLEDGE ", False
    elif n == 7:
        return "BELL ", False
    elif n == 8:
        return "BACKSPACE ", False
    elif n == 9:
        return "HORIZONTAL TAB ", False
    elif n == 10:
        return "LINE FEED ", False
    elif n == 11:
        return "VERTICAL TAB ", False
    elif n == 12:
        return "FORM FEED ", False
    elif n == 13:
        return "CARRIAGE RETURN ", False
    elif n == 14:
        return "SHIFT OUT ", False
    elif n == 15:
        return "SHIFT IN ", False
    elif n == 16:
        return "DATA LINK ESCAPE ", False
    elif n == 17:
        return "DEVICE CONTROL 1/Xon ", False
    elif n == 18:
        return "DEVICE CNTROL 2 ", False
    elif n == 19:
        return "DEVICE CONTROL 3/Xoff ", False
    elif n == 20:
        return "DEVICE CONTROL 4 ", False
    elif n == 21:
        return "NEGATIVE ACKNOWLEDGE ", False
    elif n == 22:
        return "SYNCHRONOUS IDLE ", False
    elif n == 23:
        return "END OF TRANSMISSION BLOCK ", False
    elif n == 24:
        return "CANCEL ", False
    elif n == 25:
        return "END OF MEDIUM ", False
    elif n == 26:
        return "END OF FILE/ SUBSTITUTE ", False
    elif n == 27:
        return "ESCAPE ", False
    elif n == 28:
        return "FILE SEPARATOR ", False
    elif n == 29:
        return "GROUP SEPARATOR ", False
    elif n == 30:
        return "RECORD SEPARATOR ", False
    elif n == 31:
        return "UNIT SEPERATOR ", False
    elif n == 34:
        return "QUOTATION ", False
    elif n == 39:
        return "APOSTROPHE ", False
    elif n == 127:
        return "DEL ", False
    else:
        return "\""+chr(n)+"\" ",True
    """    elif n == 40:
            return "(", False
        elif n == 41:
            return ")", False
        elif n == 91:
            return "[", False
        elif n == 92:
            return "\\", False
        elif n == 93:
            return "]", False"""

#handle escape characters
def escape(s):
    if s == 'n':
        s = 'NEWLINE'
    elif s== 'r':
        s = 'CARRIAGE RETURN'
    elif s== 'd':
        s = 'DIGIT'
    elif s== 'D':
        s = 'NOT DIGIT'
    elif s== 'w':
        s = 'WORD'
    elif s== 'W':
        s = 'NOT WORD'
    elif s== 's':
        s = 'WHITESPACE'
    elif s== 'S':
        s = 'NOT WHITESPACE'
    elif s== '\'':
        s = 'APOSTROPHE'
    elif s== '\"':
        s = 'QUOTATION'
    elif s== 't':
        s = 'TAB'
    return "\""+s+"\" ",True

#mode modifiers
def modemodifier(s):
    global dot
    modifiers = {'i':0,'s':0,'m':0,'x':0,'J':0,'U':0}
    off = False
    output = ""

    for c in s:
        if c=='-':
            off = True
        else:
            modifiers[c] = 2 if off else 1
    if modifiers['i']!=0:
        output += ("case insensitive, " if modifiers['i']==1 else "case sensitive, ")
    if modifiers['s']!=0:
        dot = modifiers['s']==1
    if modifiers['m']!=0:
        output += ("line scope, " if modifiers['m']==1 else "string scope, ")
    if modifiers['x']!=0:
        output += ("ignoring literal whitespace, " if modifiers['x']==1 else "not ignoring literal whitespace, ")
    if modifiers['J']!=0:
        output += ("allowing duplicate names, " if modifiers['J']==1 else "no duplicate names, ")
    if modifiers['U']!=0:
        output += ("lazy, " if modifiers['U']==1 else "greedy, ")
    return "(" + output[:-2] + " from here) "

regex = flags(pcre)

output = regular(regex, False, True)

excess = '" BeTwEeN "'
fb = output.find(excess)
while fb != -1:
    output = output[0:fb] + output[fb+len(excess):]
    fb = output.find(excess)

excess = "followed by or followed by"
fb = output.find(excess)
while fb != -1:
    output = output[0:fb] + "or" + output[fb+len(excess):]
    fb = output.find(excess)

begin = "starting with "
if starting and ending:
    begin += "and ending with "
elif ending:
    begin = "ending with "
if starting or ending:
    if multiline:
        begin = "line " + begin
    else:
        begin = "string " + begin
else:
    begin = "substring " + begin
output = begin + ": " + output

if nocase or findall or ungreedy:
    output = "search of " + output
    if nocase:
        output = "case insensitive " + output
    if ungreedy:
        output = "ungreedy " + output
    if findall:
        output = "global " + output

if not error:
    print(output)
else:
    print("ERROR")
