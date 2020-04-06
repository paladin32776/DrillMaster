import json


# def Settings2File(file,items):
#     f=open(file,'w')
#     for item in items:
#         f.write(type(item).__name__+'\n')
#         f.write(str(item)+'\n')
#     f.close()
#
# def File2Settings(file):
#     from pydoc import locate
#     f = open(file, 'r')
#     items=list()
#     try:
#         while True:
#             t=f.readline().strip('\n')
#             s=f.readline().strip('\n')
#             if not s: break  # EOF
#             items.append(eval(s))
#             #if t=='NoneType':
#             #    items.append(None)
#             #else:
#             #    items.append(locate(t)(s))
#     except:
#         pass
#     f.close()
#     return items

def SaveSettings(file, category='', items_dict={}):
    f = open(file, 'r')
    settings = json.loads(f.read())
    f.close()
    for key, value in items_dict.items():
        if category not in settings:
            settings[category]={}
        settings[category][key] = value
    f = open(file, 'w')
    f.write(json.dumps(settings))
    f.close()


def LoadSettings(file, category=None):
    f = open(file, 'r')
    settings = json.loads(f.read())
    f.close()
    if (category is not None) and (category in settings):
        return settings[category]
    else:
        return settings