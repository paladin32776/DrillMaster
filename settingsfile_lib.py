def Settings2File(file,items):
    f=open(file,'w')
    for item in items:
        f.write(type(item).__name__+'\n')
        f.write(str(item)+'\n')
    f.close()

def File2Settings(file):
    from pydoc import locate
    f = open(file, 'r')
    items=list()
    try:
        while True:
            t=f.readline().strip('\n')
            s=f.readline().strip('\n')
            if not s: break  # EOF
            items.append(eval(s))
            #if t=='NoneType':
            #    items.append(None)
            #else:
            #    items.append(locate(t)(s))
    except:
        pass
    f.close()
    return items

