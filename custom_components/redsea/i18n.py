import logging

from jsonpath_ng.ext import parse

from .dictionnary import DICTIONNARY

_LOGGER = logging.getLogger(__name__)

defaults = ["en", "id"]


def translate_list(lst, lang):
    res = []
    langs = [lang.split("-")[0]] + defaults

    for lang in langs:
        query = parse("$[*]." + lang)
        words = query.find(lst)
        if len(words) > 0:
            for w in words:
                res += [w.value]
            return res
    raise TypeError(
        "redsea.i18n.translate_list can not find translation %s in %s" % (langs, lst)
    )


def translate(word, dest_lang, dictionnary=DICTIONNARY, src_lang="id"):
    src_langs = [src_lang.split("-")[0]] + defaults
    dest_langs = [dest_lang.split("-")[0]] + defaults
    for src_l in src_langs:
        for w in dictionnary:
            if src_l in w and w[src_l] == word:
                for dest_l in dest_langs:
                    if dest_l in w:
                        return w[dest_l]
    raise TypeError(
        "redsea.i18n.translate can not find translation for %s from %s to %s in %s"
        % (word, src_langs, dest_langs, dictionnary)
    )
