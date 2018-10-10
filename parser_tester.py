import re
import string
import os
import sys

nocase = False
multiline = False
dot = False
ungreedy = False
findall = False
distance0 = False
ignorelimit = False
normalizedheader = False
unnormalizedbody = False
error = False
output = ""
error_file = open('error_file.txt', 'w', encoding='UTF-8')
output_file = open('output_file.txt', 'w', encoding='UTF-8')

# enable flags
def flags(s):
    global nocase, multiline, dot, ungreedy, findall, starting, ending, distance0, ignorelimit, normalizedheader, unnormalizedbody, error
    if s[0] != '/':
        error = True
    l = s.rfind('/')
    if l < 1:
        error = True

    flags = s[l+1:].strip()
    if len(flags) > 0 and not all(f in 'smigUAEROHP' for f in flags):
        # print("the string s : {}    the flag : {}".format(s,flags))
        error = True

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
    if 'A' in flags:
        starting = True
    if 'E' in flags:
        if multiline == False:
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
    return s


# read expression
def regular(s, followsLiteral, start):
    # print(s)
    reg = ""
    isLiteral = False
    if len(s) == 0:
        return ""

    # if parenthesis
    if s.startswith("("):
        # find index of matching closing parenthesis
        found = 1
        idx = 0
        legit = True
        # print(s)
        while (found != 0):
            idx += 1
            if legit and (s[idx - 1] != '\\' or s[idx-2:idx] == '\\\\'): # still not getting (\\)) but there seemes no pcre as the mentioned one
            # if legit and s[idx - 1] != '\\':
            #     if s[idx] == '\\':
            #         idx+=1
                if s[idx] == ')':
                    found -= 1
                if s[idx] == '(':
                    found += 1
            if s[idx] == '[':
                legit = False
            if s[idx] == ']':
                legit = True
            # print("index:{}".format(idx))
            # print("found:{}".format(found))
            # print("s[idx]:{}".format(s[idx:]))
            # print(legit)
        # capture groups and mode modifier
        if s[1] == '?':
            # named group
            if s[2] == 'P':
                if s[3] == '<':
                    n = s.find('>')
                    reg = "( " + regular(s[n + 1:idx], isLiteral, True) + ") named <" + s[4:n] + "> "
                elif s[3] == '=':
                    reg = "<" + s[4:idx] + "> "
                else:
                	error = True
            # atomic group
            elif s[2] == '>':
                reg = "atomic group of ( " + regular(s[3:idx],isLiteral,True) + ") "
            # capturing group
            elif s[2] in ':<=!':
                i = 2
                if s[2] == ':':
                    capture = "non-capturing "
                if s[2] == '<':
                    i = 3
                if s[i] in '=!':
                    capture = ("positive" if s[i] == '=' else "negative")  + " look" + ("ahead of " if i == 2 else "behind of ")
                    reg = capture + "( " + regular(s[i + 1:idx], isLiteral, True) + ") "
                elif i == 3:
                    n = s.find('>')
                    reg = "( " + regular(s[n + 1:idx], isLiteral, True) + ") named <" + s[3:n] + "> "
                else:
                	error = True

            # mode modifier
            elif s[2] == 'i' or s[2] == '-':
                return "followed by " + modemodifier(s[2:idx]) + regular(s[idx + 1:], isLiteral, True)
            else: 
            	error = True
        # ordinary parenthesis
        else:
            reg = "( " + regular(s[1:idx], isLiteral, True) + ") "
        s = s[idx + 1:]

    # if choice brackets
    elif s.startswith("["):
        idx = s.find(']')
        while s[idx-1]=='\\':
            if s[idx-2]=='\\':
                break
            idx = s.find(']', idx+1)
        ex = s[1] == '^'
        if ex:
            reg = "token(s) excluding [" + choice(s[2:idx]) + "] "
        else:
            reg = "token(s) from [" + choice(s[1:idx]) + "] "
        s = s[idx + 1:]

    # if escape characters
    elif s.startswith("\\"):
        if s[1] == 'x' and len(s)>2:
            if s[2] == '{':
                idx = s.find('}')
                reg, isLiteral = hexadecimal(s[3:idx])
                s = s[idx+1:]
            else:
                if len(s)>3 and s[3] in string.hexdigits:
                    reg, isLiteral = hexadecimal(s[2:4])
                    s = s[4:]
                elif s[2] in string.hexdigits:
                    reg, isLiteral = hexadecimal(s[2:3])
                    s = s[3:]
                else:
                    #\x -> same as \x0 or \x00 and there are also escape characters like
                    #\xa but in there seems no cases like that in our file so i skipped them
                    reg, isLiteral = hexadecimal("0")
                    s=s[2:]
        else:
            reg, isLiteral = escape(s[1])
            s = s[2:]

    # else read single character
    else:
        if s[0] == '|':
            reg = "or "
        elif s[0] == '.':
            reg = "any character " + ("" if dot else "excluding NEWLINE ")
        elif s[0] == '^':
            reg = "start of " + ("line " if multiline else "string ")
        elif s[0] == '$':
            reg = "end of " + ("line " if multiline else "string ")
        else:
            isLiteral = True
            reg = "\"" + s[0] + "\" "
        s = s[1:]

    # check repetition
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
        if not p.match(s[0:idx + 1]):
            reg = reg + "followed by \"" + s[0: idx + 1] + "\""
        else:
            num = ""
            # {num}
            if com == -1 or com > idx:
                num = s[1:idx] + " "
            # {num, }
            elif idx - com == 1:
                num = s[1:com] + " or more "
            # {num, num}
            else:
                num = s[1:com] + " to " + s[com + 1:idx] + " "
            reg = num + reg
        s = s[idx + 1:]

    # return result
    if start:
        return reg + regular(s, isLiteral, False)
    if followsLiteral and isLiteral:
        return "BeTwEeN " + reg + regular(s, isLiteral, False)
    return "followed by " + reg + regular(s, isLiteral, False)


# handle choice brackets
def choice(s):
    if len(s) == 0:
        return ""
    to = False
    output = ""
    if s[0] == "\\":
        if s[1] == 'x' and len(s)>2:
            if s[2] == '{':
                idx = s.find('}')
                output, b = hexadecimal(s[3:idx])
                s = s[idx+1:]
            else:
                if len(s) > 3 and s[3] in string.hexdigits:
                    output, b = hexadecimal(s[2:4])
                    s = s[4:]
                elif s[2] in string.hexdigits:
                    output, b = hexadecimal(s[2:3])
                    s = s[3:]
                else:
                    #\x -> same as \x0 or \x00 and there are also escape characters like
                    #\xa but in there seems no cases like that in our file so i skipped them
                    output, b = hexadecimal("0")
                    s=s[2:]
        else:
            output, b = escape(s[1])
            s = s[2:]
        output = output[:-1]
    elif s[0] == '-' and len(s) != 1:
        to = True
        output = " to "
        s = s[1:]
    else:
        output = "\"" + s[0] + "\""
        s = s[1:]
    if len(s) > 0 and not to and (not s.startswith('-') or s == "-"):
        output += " and "
    else:
    	error = True # need to check
    return output + choice(s)


# handle hexadecimals
def hexadecimal(s):
    n = int(s, 16)
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
        return "\"" + chr(n) + "\" ", True
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


# handle escape characters
def escape(s):
    if s == 'n':
        s = 'NEWLINE '
    elif s == 'r':
        s = 'CARRIAGE RETURN '
    elif s == 'd':
        s = 'DIGIT '
    elif s == 'D':
        s = 'NON-DIGIT '
    elif s == 'w':
        s = 'WORD '
    elif s == 'W':
        s = 'NON-WORD '
    elif s == 's':
        s = 'WHITESPACE '
    elif s == 'S':
        s = 'NON-WHITESPACE '
    elif s == '\'':
        s = 'APOSTROPHE '
    elif s == '\"':
        s = 'QUOTATION '
    elif s == 't':
        s = 'TAB '
    elif s == '.':
        # s = "any character" + (" " if dot else "excluding NEWLINE ")
        s = 'DOT '
    elif s == 'x':
        s = 'NUL '
    else:
        return "\"" + s + "\" ", True
    return s, False


# mode modifiers
def modemodifier(s):
    global dot, error, multiline
    modifiers = {'i': 0, 's': 0, 'm': 0, 'x': 0, 'J': 0, 'U': 0}
    off = False
    output = ""
    for c in s:
        if c == '-':
            off = True
        else:
            modifiers[c] = 2 if off else 1
        if c not in '-ismxJU':
            error = True
            break
    if modifiers['i'] != 0:
        output += ("case insensitive, " if modifiers['i'] == 1 else "case sensitive, ")
    if modifiers['s'] != 0:
        dot = modifiers['s'] == 1
    if modifiers['m'] != 0:
        multiline = modifiers['m'] == 1
    if modifiers['x'] != 0:
        output += ("ignoring literal whitespace, " if modifiers['x'] == 1 else "not ignoring literal whitespace, ")
    if modifiers['J'] != 0:
        output += ("allowing duplicate names, " if modifiers['J'] == 1 else "no duplicate names, ")
    if modifiers['U'] != 0:
        output += ("lazy, " if modifiers['U'] == 1 else "greedy, ")
    if len(output)<2:
        return output
    return "(" + output[:-2] + " from here) "

noterror=0
errornum=0
allnum=0
input_file = sys.argv[1]
with open(input_file, "r+") as f:
    for line in f.readlines():
        #reset flags
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

        regex = flags(line)
        # print(regex)
        output = regular(regex, False, True)

        #remove excess
        output = output.replace('" BeTwEeN "', "")
        output = output.replace("followed by or followed by", "or")

        output = "search of: " + output
        if nocase or findall or ungreedy:
            if nocase:
                output = "case insensitive " + output
            if ungreedy:
                output = "lazy " + output
            if findall:
                output = "global " + output

        if not error:
            # print(output)
            output_file.write(output)
            noterror+=1
        else:
            # print("--------------------------------------------------------------")
            error_file.write("error line : {}".format(line))
            error_file.write("output : {}".format(output))
            error_file.write("\n\n")
            print("ERROR")
            # print("--------------------------------------------------------------\n\n")
            errornum+=1
        allnum+=1
        print("allnum: {} || noterrornum: {} || errornum: {}".format(allnum,noterror,errornum))