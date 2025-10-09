import json
from jsonpath_ng import jsonpath
from jsonpath_ng.ext import parse

defaults=['en','id']

def translate_list(lst,lang):
    res=[]
    langs=[lang.split('-')[0]]+defaults
    
    for l in langs:
        query=parse("$[*]."+l)
        words=query.find(lst)
        if len(words)>0:
            for w in words:
                res+=[w.value]
            return res
    raise TypeError('redsea.i18n.translate_list can not find translation %s in %s'%(langs,lst))

def translate(dictionnary,word,src_lang,dest_lang):
    src_langs =[src_lang.split('-')[0]]+defaults
    dest_langs=[dest_lang.split('-')[0]]+defaults
    for src_l in src_langs:
        for w in dictionnary:
            if w[src_l] == word:
                for dest_l in dest_langs:
                    if dest_l in w:
                        return w[dest_l]
    raise TypeError('redsea.i18n.translate can not find translation for %s from %s to %s in %s'%(word,src_langs,dest_langs,dictionnary))


# def translate(dictionnary,word,src_lang,dest_lang):
#     src_langs =[src_lang.split('-')[0]]+defaults
#     dest_langs=[dest_lang.split('-')[0]]+defaults
#     for src_l in src_langs:
#         for dest_l in dest_langs:
#             query=parse("$[?(@."+src_l+"=='"+word+"')]."+dest_l)
#             res_word=query.find(dictionnary)
#             if len(res_word)>0:
#                 return res_word[0].value
#     raise TypeError('redsea.i18n.translate can not find translation for %s from %s to %s in %s'%(word,src_langs,dest_langs,dictionnary))
