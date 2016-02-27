import string


def remove_punct(string_input):
    "Takes in string, removes punctuation, returns string sans punctuation"
    punct_list=list(string.punctuation)
    string_list=[]
    input_list=[]
    #turn it into string just ot be sure. Inputing from Excel can make it think it's a number.

    #if is float, turn to int. then, turn to str. This is so import form Excel sheets won't have automatic decimal formatting.
    if isinstance(string_input, float):
        input_list=list(str(int(string_input)))
    else:#i think this should work for int and float, but of course won't work for None or bools.
    #try to make a list of the string input, if it's unicode or a string
        input_list=list(str(string_input))

    for char in input_list:
        if char not in punct_list:
            string_list.append(char)
    new_string="".join(string_list)

    return new_string

def ascii_only(string_input):
    "Takes in string, removes non-ascii chars, returns string. Doesn't do anything about punctuation."
    #print "srarting ascii_only ",string_input
    try:#in case is Bool or something
        try:
            decoded_str = string_input.decode('ascii', errors='ignore')
            newstring_ascii = decoded_str.encode('ascii', errors='ignore')
            #newstring_ascii = str(string_input).encode('ascii', errors='ignore').decode('ascii',errors='ignore')
        except:
            encoded_str = string_input.encode('ascii', errors='ignore')
            newstring_ascii= encoded_str.decode('ascii', errors='ignore')

        if (len(newstring_ascii)>=1 and newstring_ascii != " "):
            #print "ending ascii_only success ",newstring_ascii
            return newstring_ascii
        else:
            return None
    except:
        return string_input

def ascii_only_no_punct(string_input):
    "takes string, removes both non-ascii chars and punctuation, retuns cleaned string"
    step1=ascii_only(string_input)
    step2=remove_punct(step1)
    return step2
